"""Data validation functions."""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from ...models.validation import ValidationError


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
    
    # Check channel consistency (non-empty strings and consistent casing)
    if 'channel' in df.columns:
        valid_channels = df['channel'].astype(str).str.len().gt(0).sum()
        # Check for casing inconsistency (compare original values to lowercased)
        original_channels = df['channel'].astype(str)
        lower_channels = original_channels.str.lower()
        # If original has more unique values than lowercased, casing is inconsistent
        original_unique = len(original_channels.unique())
        lower_unique = len(lower_channels.unique())
        casing_consistent = original_unique == lower_unique or original_unique == 1
        
        if not casing_consistent:
            consistency_scores.append(0.7)  # Penalize casing inconsistency
        else:
            consistency_scores.append(valid_channels / total_rows)
    else:
        consistency_scores.append(0.0)
    
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
            # Calculate average freshness score (0-1 scale, 0 = very old, 1 = very recent)
            # Data within 7 days gets score 1, 7-30 days gets 0.5-1, >30 days gets lower score
            freshness_scores = []
            for days in days_old:
                if days <= 7:
                    score = 1.0
                elif days <= 30:
                    score = 1.0 - ((days - 7) / 46)  # Linear decay from 7 to 30 days
                else:
                    score = max(0.0, 0.5 - ((days - 30) / 60))  # Further decay after 30 days
                freshness_scores.append(score)
            freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0.0
        except:
            freshness = 0.0
    else:
        freshness = 0.0
    
    return DataQuality(
        completeness=completeness,
        consistency=consistency,
        freshness=freshness
    )
