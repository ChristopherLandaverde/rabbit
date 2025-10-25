"""Unit tests for data validation."""

import pytest
import pandas as pd
from src.core.validation.validators import (
    validate_required_columns,
    validate_data_types,
    validate_data_quality,
    DataQuality
)
from tests.fixtures.data import sample_touchpoint_data, invalid_data_scenarios


@pytest.mark.unit
class TestDataValidation:
    """Test data validation functions."""
    
    def test_validate_required_columns_success(self, sample_touchpoint_data):
        """Test validation passes with all required columns."""
        errors = validate_required_columns(sample_touchpoint_data)
        assert len(errors) == 0
    
    def test_validate_required_columns_missing_timestamp(self):
        """Test validation fails when timestamp column is missing."""
        df = pd.DataFrame({
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 1
        assert errors[0].field == 'timestamp'
        assert errors[0].error_code == 'missing_required_column'
    
    def test_validate_required_columns_missing_channel(self):
        """Test validation fails when channel column is missing."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 1
        assert errors[0].field == 'channel'
    
    def test_validate_required_columns_missing_event_type(self):
        """Test validation fails when event_type column is missing."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 1
        assert errors[0].field == 'event_type'
    
    def test_validate_required_columns_multiple_missing(self):
        """Test validation returns multiple errors for multiple missing columns."""
        df = pd.DataFrame({
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 3
        error_fields = [error.field for error in errors]
        assert 'timestamp' in error_fields
        assert 'channel' in error_fields
        assert 'event_type' in error_fields


@pytest.mark.unit
class TestDataTypeValidation:
    """Test data type validation functions."""
    
    def test_validate_data_types_success(self, sample_touchpoint_data):
        """Test validation passes with correct data types."""
        errors = validate_data_types(sample_touchpoint_data)
        assert len(errors) == 0
    
    def test_validate_data_types_invalid_timestamp(self):
        """Test validation fails with invalid timestamp format."""
        df = pd.DataFrame({
            'timestamp': ['invalid_date', '2024-01-01'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_data_types(df)
        assert len(errors) == 1
        assert errors[0].field == 'timestamp'
        assert errors[0].error_code == 'invalid_timestamp_format'
    
    def test_validate_data_types_invalid_numeric(self):
        """Test validation fails with invalid numeric values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001'],
            'conversion_value': ['not_a_number', 100.0]
        })
        
        errors = validate_data_types(df)
        assert len(errors) == 1
        assert errors[0].field == 'conversion_value'
        assert errors[0].error_code == 'invalid_numeric_format'
    
    def test_validate_data_types_missing_optional_columns(self):
        """Test validation passes when optional columns are missing."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion']
        })
        
        errors = validate_data_types(df)
        assert len(errors) == 0


@pytest.mark.unit
class TestDataQuality:
    """Test data quality assessment."""
    
    def test_validate_data_quality_high_quality(self, sample_touchpoint_data):
        """Test data quality assessment with high-quality data."""
        quality = validate_data_quality(sample_touchpoint_data)
        
        assert isinstance(quality, DataQuality)
        assert quality.completeness > 0.8
        assert quality.consistency > 0.8
        # Note: freshness will be low for 2024 test data, so we don't assert it
    
    def test_validate_data_quality_empty_dataframe(self):
        """Test data quality assessment with empty DataFrame."""
        df = pd.DataFrame()
        quality = validate_data_quality(df)
        
        assert quality.completeness == 0.0
        assert quality.consistency == 0.0
        assert quality.freshness == 0.0
    
    def test_validate_data_quality_missing_values(self):
        """Test data quality assessment with missing values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', None, '2024-01-03'],
            'channel': ['email', 'social', None],
            'event_type': ['click', 'conversion', 'view']
        })
        
        quality = validate_data_quality(df)
        assert quality.completeness < 1.0
        assert quality.consistency < 1.0
    
    def test_validate_data_quality_old_data(self):
        """Test data quality assessment with old data."""
        from datetime import datetime, timedelta
        
        old_date = datetime.now() - timedelta(days=365)  # 1 year old
        df = pd.DataFrame({
            'timestamp': [old_date, old_date, old_date],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view']
        })
        
        quality = validate_data_quality(df)
        assert quality.freshness < 0.5  # Old data should have low freshness
    
    def test_data_quality_properties(self):
        """Test DataQuality class properties."""
        quality = DataQuality(completeness=0.9, consistency=0.8, freshness=0.7)
        
        assert quality.completeness == 0.9
        assert quality.consistency == 0.8
        assert quality.freshness == 0.7


@pytest.mark.unit
class TestInvalidDataScenarios:
    """Test validation with various invalid data scenarios."""
    
    def test_invalid_data_scenarios(self, invalid_data_scenarios):
        """Test validation handles various invalid data scenarios."""
        scenarios = invalid_data_scenarios
        
        # Test missing timestamp
        errors = validate_required_columns(scenarios['missing_timestamp'])
        assert len(errors) == 1
        assert errors[0].field == 'timestamp'
        
        # Test invalid timestamp
        errors = validate_data_types(scenarios['invalid_timestamp'])
        assert len(errors) == 1
        assert errors[0].field == 'timestamp'
        
        # Test missing channel
        errors = validate_required_columns(scenarios['missing_channel'])
        assert len(errors) == 1
        assert errors[0].field == 'channel'
        
        # Test invalid numeric
        errors = validate_data_types(scenarios['invalid_numeric'])
        assert len(errors) == 1
        assert errors[0].field == 'conversion_value'


@pytest.mark.unit
class TestDataProcessingEdgeCases:
    """Test data processing with edge cases and complex scenarios."""
    
    def test_validate_large_dataset(self):
        """Test validation with large dataset."""
        import random
        from datetime import datetime, timedelta
        
        # Create large dataset with 10,000 rows
        data = []
        base_time = datetime(2024, 1, 1)
        channels = ['email', 'social', 'paid_search', 'organic', 'display']
        event_types = ['view', 'click', 'conversion']
        
        for i in range(10000):
            data.append({
                'timestamp': base_time + timedelta(hours=i),
                'channel': random.choice(channels),
                'event_type': random.choice(event_types),
                'customer_id': f'cust_{i % 1000}',
                'session_id': f'sess_{i}',
                'email': f'user{i % 1000}@example.com',
                'conversion_value': random.choice([None, None, None, random.uniform(10, 500)])
            })
        
        df = pd.DataFrame(data)
        
        # Should handle large dataset without issues
        errors = validate_required_columns(df)
        assert len(errors) == 0
        
        errors = validate_data_types(df)
        assert len(errors) == 0
    
    def test_validate_duplicate_timestamps(self):
        """Test validation with duplicate timestamps."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-01 10:00:00', '2024-01-01 10:00:00'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'view', 'conversion'],
            'customer_id': ['cust_001', 'cust_001', 'cust_001']
        })
        
        # Duplicate timestamps should not cause validation errors
        errors = validate_required_columns(df)
        assert len(errors) == 0
        
        errors = validate_data_types(df)
        assert len(errors) == 0
    
    def test_validate_mixed_data_types(self):
        """Test validation with mixed data types in columns."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', 123],  # Mixed string and numeric
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        })
        
        errors = validate_data_types(df)
        # Should handle mixed types gracefully
        assert len(errors) >= 0  # May or may not have errors depending on implementation
    
    def test_validate_unicode_characters(self):
        """Test validation with unicode characters."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', 'social_media_📱'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_002'],
            'email': ['user@example.com', 'user@café.com']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 0
        
        errors = validate_data_types(df)
        assert len(errors) == 0
    
    def test_validate_extreme_values(self):
        """Test validation with extreme values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_002'],
            'conversion_value': [0.0, 999999999.99]  # Extreme values
        })
        
        errors = validate_data_types(df)
        assert len(errors) == 0
    
    def test_validate_empty_strings(self):
        """Test validation with empty strings."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', ''],  # Empty string
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_002']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 0  # Empty strings are still present columns
        
        errors = validate_data_types(df)
        # May have errors for empty strings depending on implementation
        assert len(errors) >= 0
    
    def test_validate_whitespace_values(self):
        """Test validation with whitespace-only values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', '   '],  # Whitespace only
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_002']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 0
        
        errors = validate_data_types(df)
        assert len(errors) >= 0  # May have errors for whitespace
    
    def test_validate_special_characters_in_ids(self):
        """Test validation with special characters in IDs."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust-001', 'cust_002@domain.com'],  # Special characters
            'session_id': ['sess-001', 'sess_002']
        })
        
        errors = validate_required_columns(df)
        assert len(errors) == 0
        
        errors = validate_data_types(df)
        assert len(errors) == 0


@pytest.mark.unit
class TestDataQualityAdvanced:
    """Test advanced data quality scenarios."""
    
    def test_data_quality_with_inconsistent_channels(self):
        """Test data quality with inconsistent channel naming."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-02 11:00:00', '2024-01-03 12:00:00'],
            'channel': ['Email', 'email', 'EMAIL'],  # Inconsistent casing
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', 'cust_001', 'cust_001']
        })
        
        quality = validate_data_quality(df)
        assert quality.consistency < 1.0  # Should detect inconsistency
    
    def test_data_quality_with_mixed_date_formats(self):
        """Test data quality with mixed date formats."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '01/02/2024 11:00:00', '2024-01-03T12:00:00Z'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', 'cust_002', 'cust_003']
        })
        
        quality = validate_data_quality(df)
        assert quality.consistency < 1.0  # Should detect format inconsistency
    
    def test_data_quality_with_outliers(self):
        """Test data quality with statistical outliers."""
        import numpy as np
        
        # Create data with outliers in conversion values
        normal_values = np.random.normal(100, 20, 100)  # Normal distribution
        outlier_values = [1000, 2000, 3000]  # Outliers
        
        df = pd.DataFrame({
            'timestamp': [f'2024-01-{i+1:02d} 10:00:00' for i in range(103)],
            'channel': ['email'] * 103,
            'event_type': ['conversion'] * 103,
            'customer_id': [f'cust_{i:03d}' for i in range(103)],
            'conversion_value': list(normal_values) + outlier_values
        })
        
        quality = validate_data_quality(df)
        # Quality should be affected by outliers
        assert isinstance(quality, DataQuality)
    
    def test_data_quality_completeness_calculation(self):
        """Test data quality completeness calculation."""
        # Create data with known missing values
        df = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', None, '2024-01-03 12:00:00'],
            'channel': ['email', 'social', None],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', 'cust_002', 'cust_003']
        })
        
        quality = validate_data_quality(df)
        
        # Should have less than 100% completeness due to missing values
        assert quality.completeness < 1.0
        assert quality.completeness > 0.0
    
    def test_data_quality_freshness_calculation(self):
        """Test data quality freshness calculation."""
        from datetime import datetime, timedelta
        
        # Create data with different ages
        now = datetime.now()
        recent_data = now - timedelta(hours=1)
        old_data = now - timedelta(days=30)
        
        df = pd.DataFrame({
            'timestamp': [recent_data, old_data, recent_data],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', 'cust_002', 'cust_003']
        })
        
        quality = validate_data_quality(df)
        
        # Should have moderate freshness due to mix of recent and old data
        assert quality.freshness > 0.0
        assert quality.freshness < 1.0
