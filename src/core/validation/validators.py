"""Data validation functions."""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from ..models.validation import ValidationError


class DataQuality:
    """Data quality metrics."""
    
    def __init__(self, completeness: float, consistency: float, freshness: float):
        self.completeness = completeness
        self.consistency = consistency
        self.freshness = freshness


def validate_required_columns(df: pd.DataFrame) -> List[ValidationError]:
    """Validate that required columns are present in the DataFrame."""
    errors = []
    required_columns = ['timestamp', 'channel', 'event_type']
    
    for column in required_columns:
        if column not in df.columns:
            errors.append(ValidationError(
                field=column,
                error_code="missing_required_column",
                message=f"Required column '{column}' is missing",
                suggestion=f"Add a '{column}' column to your data"
            ))
    
    return errors


def validate_data_types(df: pd.DataFrame) -> List[ValidationError]:
    """Validate data types for critical columns."""
    errors = []
    
    # Validate timestamp column
    if 'timestamp' in df.columns:
        try:
            pd.to_datetime(df['timestamp'], errors='raise')
        except (ValueError, TypeError) as e:
            errors.append(ValidationError(
                field='timestamp',
                error_code="invalid_timestamp_format",
                message=f"Timestamp column contains invalid dates: {str(e)}",
                suggestion="Ensure timestamps are in ISO format or parseable by pandas"
            ))
    
    # Validate numeric columns
    numeric_columns = ['conversion_value', 'cost']
    for col in numeric_columns:
        if col in df.columns:
            try:
                pd.to_numeric(df[col], errors='raise')
            except (ValueError, TypeError) as e:
                errors.append(ValidationError(
                    field=col,
                    error_code="invalid_numeric_format",
                    message=f"Column '{col}' contains non-numeric values: {str(e)}",
                    suggestion="Ensure all values in this column are numeric"
                ))
    
    return errors


def validate_data_quality(df: pd.DataFrame) -> DataQuality:
    """Calculate data quality metrics."""
    total_rows = len(df)
    
    if total_rows == 0:
        return DataQuality(completeness=0.0, consistency=0.0, freshness=0.0)
    
    # Calculate completeness (non-null values)
    required_fields = ['timestamp', 'channel', 'event_type']
    completeness_scores = []
    
    for field in required_fields:
        if field in df.columns:
            non_null_count = df[field].notna().sum()
            completeness_scores.append(non_null_count / total_rows)
        else:
            completeness_scores.append(0.0)
    
    completeness = sum(completeness_scores) / len(completeness_scores)
    
    # Calculate consistency (valid values in expected ranges)
    consistency_scores = []
    
    # Check timestamp consistency (no future dates)
    if 'timestamp' in df.columns:
        try:
            timestamps = pd.to_datetime(df['timestamp'])
            now = pd.Timestamp.now()
            valid_timestamps = (timestamps <= now).sum()
            consistency_scores.append(valid_timestamps / total_rows)
        except:
            consistency_scores.append(0.0)
    
    # Check channel consistency (non-empty strings)
    if 'channel' in df.columns:
        valid_channels = df['channel'].astype(str).str.len().gt(0).sum()
        consistency_scores.append(valid_channels / total_rows)
    
    # Check event_type consistency (valid enum values)
    if 'event_type' in df.columns:
        valid_events = df['event_type'].isin(['view', 'click', 'conversion', 'purchase', 'signup']).sum()
        consistency_scores.append(valid_events / total_rows)
    
    consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    # Calculate freshness (recent data)
    if 'timestamp' in df.columns:
        try:
            timestamps = pd.to_datetime(df['timestamp'])
            now = pd.Timestamp.now()
            days_old = (now - timestamps).dt.days
            # Consider data fresh if it's within 30 days
            fresh_data = (days_old <= 30).sum()
            freshness = fresh_data / total_rows
        except:
            freshness = 0.0
    else:
        freshness = 0.0
    
    return DataQuality(
        completeness=completeness,
        consistency=consistency,
        freshness=freshness
    )
