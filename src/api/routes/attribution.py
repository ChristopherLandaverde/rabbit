"""Attribution analysis endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import pandas as pd
import io
from datetime import datetime

from ...core.attribution_service import AttributionService
from ...models.attribution import AttributionResponse
from ...models.enums import AttributionModelType
from ...config import get_settings

router = APIRouter()
settings = get_settings()


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
