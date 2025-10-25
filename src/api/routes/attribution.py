"""Attribution analysis endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
import pandas as pd
import io
import hashlib
import time
from datetime import datetime

from ...core.attribution_service import AttributionService
from ...models.attribution import AttributionResponse, ValidationResponse, SchemaDetection, DataQualityMetrics
from ...models.enums import AttributionModelType
from ...core.validation.validators import validate_required_columns, validate_data_types, validate_data_quality
from ...core.auth import get_current_user, validate_file_upload, validate_analysis_request
from ...core.caching import attribution_cache, api_cache
from ...core.logging import security_logger, performance_logger, business_logger
from ...core.security import input_validator
from ...config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/validate", response_model=ValidationResponse)
async def validate_data(
    file: UploadFile = File(...),
    current_user: dict = Depends(validate_file_upload)
):
    """
    Validate data schema and structure before analysis.
    
    Args:
        file: CSV, JSON, or Parquet file containing touchpoint data
        
    Returns:
        Data validation results with schema detection and quality metrics
    """
    try:
        # Validate file size
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "file_too_large",
                    "message": f"File size {file_size_mb:.1f}MB exceeds maximum allowed size of {settings.max_file_size_mb}MB",
                    "details": {"max_size_mb": settings.max_file_size_mb, "actual_size_mb": file_size_mb},
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Parse file based on content type
        df = await _parse_uploaded_file(file_content, file.filename)
        
        # Perform schema detection
        detected_columns = {col: str(dtype) for col, dtype in df.dtypes.items()}
        required_columns = ['timestamp', 'channel', 'event_type']
        required_columns_present = all(col in df.columns for col in required_columns)
        
        # Calculate schema detection confidence
        schema_confidence = 0.0
        if required_columns_present:
            schema_confidence = 0.8  # Base confidence for required columns
            # Add confidence for optional columns
            optional_columns = ['customer_id', 'session_id', 'email', 'revenue', 'campaign']
            optional_present = sum(1 for col in optional_columns if col in df.columns)
            schema_confidence += min(0.2, optional_present * 0.05)  # Up to 0.2 additional confidence
        
        schema_detection = SchemaDetection(
            detected_columns=detected_columns,
            confidence=schema_confidence,
            required_columns_present=required_columns_present
        )
        
        # Perform data validation
        validation_errors = []
        validation_errors.extend(validate_required_columns(df))
        validation_errors.extend(validate_data_types(df))
        
        # Calculate data quality metrics
        data_quality = validate_data_quality(df)
        overall_quality = (data_quality.completeness + data_quality.consistency + data_quality.freshness) / 3
        
        data_quality_metrics = DataQualityMetrics(
            completeness=data_quality.completeness,
            consistency=data_quality.consistency,
            freshness=data_quality.freshness,
            overall_quality=overall_quality
        )
        
        # Generate recommendations
        recommendations = []
        warnings = []
        
        if not required_columns_present:
            recommendations.append("Add required columns: timestamp, channel, event_type")
        
        if data_quality.completeness < 0.9:
            recommendations.append("Improve data completeness by filling missing values")
        
        if data_quality.consistency < 0.8:
            recommendations.append("Standardize data formats and values for better consistency")
        
        if data_quality.freshness < 0.5:
            warnings.append("Data appears to be older than 30 days - consider using more recent data")
        
        if len(df) < 100:
            warnings.append("Small dataset detected - results may not be statistically significant")
        
        # Convert validation errors to dictionaries
        error_dicts = []
        for error in validation_errors:
            error_dicts.append({
                "field": error.field,
                "error_code": error.error_code,
                "message": error.message,
                "suggestion": error.suggestion
            })
        
        # Determine if data is valid
        is_valid = len(error_dicts) == 0 and required_columns_present and overall_quality > 0.5
        
        return ValidationResponse(
            valid=is_valid,
            schema_detection=schema_detection,
            data_quality=data_quality_metrics,
            errors=error_dicts,
            recommendations=recommendations,
            warnings=warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "validation_error",
                "message": f"Error validating data: {str(e)}",
                "details": {"error_type": type(e).__name__},
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/methods")
async def get_available_methods():
    """
    Get available attribution models and linking methods.
    
    Returns:
        List of available attribution models and linking methods with descriptions
    """
    try:
        attribution_models = [
            {
                "name": "linear",
                "display_name": "Linear Attribution",
                "description": "Equal distribution across all touchpoints in the customer journey",
                "use_case": "Balanced view of entire customer journey",
                "best_for": "General attribution analysis and budget allocation",
                "parameters": []
            },
            {
                "name": "first_touch",
                "display_name": "First Touch Attribution",
                "description": "100% credit to the first touchpoint in the customer journey",
                "use_case": "Brand awareness and top-of-funnel analysis",
                "best_for": "Understanding customer acquisition channels",
                "parameters": []
            },
            {
                "name": "last_touch",
                "display_name": "Last Touch Attribution",
                "description": "100% credit to the last touchpoint before conversion",
                "use_case": "Performance marketing optimization",
                "best_for": "Direct response and conversion optimization",
                "parameters": []
            },
            {
                "name": "time_decay",
                "display_name": "Time Decay Attribution",
                "description": "Exponential decay with recent touchpoints receiving more credit",
                "use_case": "Short sales cycles where recent interactions matter more",
                "best_for": "E-commerce and quick purchase decisions",
                "parameters": [
                    {
                        "name": "half_life_days",
                        "type": "float",
                        "description": "Half-life in days for the decay function",
                        "default": 7.0,
                        "range": [1.0, 365.0]
                    }
                ]
            },
            {
                "name": "position_based",
                "display_name": "Position-Based Attribution",
                "description": "40% first touchpoint, 40% last touchpoint, 20% middle touchpoints",
                "use_case": "Complex B2B sales cycles valuing both awareness and conversion",
                "best_for": "Long consideration periods with multiple touchpoints",
                "parameters": [
                    {
                        "name": "first_touch_weight",
                        "type": "float",
                        "description": "Weight for first touchpoint (default: 0.4)",
                        "default": 0.4,
                        "range": [0.0, 1.0]
                    },
                    {
                        "name": "last_touch_weight",
                        "type": "float",
                        "description": "Weight for last touchpoint (default: 0.4)",
                        "default": 0.4,
                        "range": [0.0, 1.0]
                    }
                ]
            }
        ]
        
        linking_methods = [
            {
                "name": "auto",
                "display_name": "Automatic Selection",
                "description": "Automatically selects optimal linking method based on available data",
                "requirements": "Any combination of customer_id, session_id, email fields",
                "accuracy": "High",
                "coverage": "High"
            },
            {
                "name": "customer_id",
                "display_name": "Customer ID Linking",
                "description": "Links touchpoints using customer_id field",
                "requirements": "customer_id field must be present",
                "accuracy": "Highest",
                "coverage": "Medium"
            },
            {
                "name": "session_email",
                "display_name": "Session + Email Linking",
                "description": "Combines session_id and email for cross-session attribution",
                "requirements": "session_id and email fields must be present",
                "accuracy": "High",
                "coverage": "High"
            },
            {
                "name": "email_only",
                "display_name": "Email Only Linking",
                "description": "Links touchpoints using email addresses only",
                "requirements": "email field must be present",
                "accuracy": "Medium",
                "coverage": "Medium"
            },
            {
                "name": "aggregate",
                "display_name": "Aggregate Linking",
                "description": "Statistical modeling approach for anonymous attribution",
                "requirements": "No specific fields required",
                "accuracy": "Low",
                "coverage": "Highest"
            }
        ]
        
        return {
            "attribution_models": attribution_models,
            "linking_methods": linking_methods,
            "recommendations": {
                "best_for_ecommerce": ["linear", "time_decay"],
                "best_for_b2b": ["position_based", "linear"],
                "best_for_awareness": ["first_touch"],
                "best_for_conversion": ["last_touch"],
                "best_linking_method": "auto"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "methods_retrieval_error",
                "message": f"Error retrieving available methods: {str(e)}",
                "details": {"error_type": type(e).__name__},
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/analyze", response_model=AttributionResponse)
async def analyze_attribution(
    file: UploadFile = File(...),
    model_type: str = Form(...),
    half_life_days: Optional[float] = Form(None),
    first_touch_weight: Optional[float] = Form(None),
    last_touch_weight: Optional[float] = Form(None)
):
    """
    Analyze attribution from uploaded data file.
    
    Args:
        file: CSV, JSON, or Parquet file containing touchpoint data
        model_type: Attribution model to use (linear, time_decay, first_touch, last_touch, position_based)
        half_life_days: Half-life for time decay model (optional)
        first_touch_weight: First touch weight for position-based model (optional)
        last_touch_weight: Last touch weight for position-based model (optional)
        
    Returns:
        Attribution analysis results
    """
    try:
        # Validate file size
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "file_too_large",
                    "message": f"File size {file_size_mb:.1f}MB exceeds maximum allowed size of {settings.max_file_size_mb}MB",
                    "details": {"max_size_mb": settings.max_file_size_mb, "actual_size_mb": file_size_mb},
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Parse file based on content type
        df = await _parse_uploaded_file(file_content, file.filename)
        
        # Validate model type
        try:
            attribution_model_type = AttributionModelType(model_type)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_model_type",
                    "message": f"Invalid model type '{model_type}'. Must be one of: {[e.value for e in AttributionModelType]}",
                    "details": {"provided_model": model_type, "valid_models": [e.value for e in AttributionModelType]},
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Prepare model parameters
        model_kwargs = {}
        if half_life_days is not None:
            model_kwargs['half_life_days'] = half_life_days
        if first_touch_weight is not None:
            model_kwargs['first_touch_weight'] = first_touch_weight
        if last_touch_weight is not None:
            model_kwargs['last_touch_weight'] = last_touch_weight
        
        # Perform attribution analysis
        attribution_service = AttributionService()
        result = await attribution_service.analyze_attribution(
            df, attribution_model_type, **model_kwargs
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "processing_error",
                "message": f"Error processing attribution analysis: {str(e)}",
                "details": {"error_type": type(e).__name__},
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def _parse_uploaded_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded file content into a DataFrame."""
    file_extension = filename.lower().split('.')[-1] if filename else 'csv'
    
    try:
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(file_content))
        elif file_extension == 'json':
            df = pd.read_json(io.BytesIO(file_content))
        elif file_extension == 'parquet':
            df = pd.read_parquet(io.BytesIO(file_content))
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        # Normalize column names to lowercase
        df.columns = df.columns.str.lower()
        
        # Ensure timestamp column is properly parsed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
        
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "file_parsing_error",
                "message": f"Error parsing uploaded file: {str(e)}",
                "details": {"file_extension": file_extension, "error_type": type(e).__name__},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
