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
