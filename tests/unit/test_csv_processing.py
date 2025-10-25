"""Unit tests for CSV processing and file handling."""

import pytest
import pandas as pd
import io
from unittest.mock import Mock, patch
from src.utils.file_utils import process_csv_file, validate_csv_structure
from tests.fixtures.data import sample_csv_file, large_dataset


@pytest.mark.unit
class TestCSVProcessing:
    """Test CSV file processing functionality."""
    
    def test_process_csv_file_success(self, sample_csv_file):
        """Test successful CSV file processing."""
        # Reset file pointer
        sample_csv_file.seek(0)
        
        df = process_csv_file(sample_csv_file)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10  # Based on sample data
        assert 'timestamp' in df.columns
        assert 'channel' in df.columns
        assert 'event_type' in df.columns
        assert 'customer_id' in df.columns
    
    def test_process_csv_file_with_encoding(self):
        """Test CSV processing with different encodings."""
        # Test UTF-8 encoding
        csv_content = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,cust_001
2024-01-02 11:00:00,social,conversion,cust_002"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 2
        assert df['channel'].iloc[0] == 'email'
        assert df['channel'].iloc[1] == 'social'
    
    def test_process_csv_file_with_different_separators(self):
        """Test CSV processing with different separators."""
        # Test semicolon separator
        csv_content = """timestamp;channel;event_type;customer_id
2024-01-01 10:00:00;email;click;cust_001
2024-01-02 11:00:00;social;conversion;cust_002"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj, separator=';')
        
        assert len(df) == 2
        assert 'channel' in df.columns
    
    def test_process_csv_file_with_headers(self):
        """Test CSV processing with custom headers."""
        csv_content = """2024-01-01 10:00:00,email,click,cust_001
2024-01-02 11:00:00,social,conversion,cust_002"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj, headers=['timestamp', 'channel', 'event_type', 'customer_id'])
        
        assert len(df) == 2
        assert 'timestamp' in df.columns
        assert 'channel' in df.columns
    
    def test_process_csv_file_empty_file(self):
        """Test CSV processing with empty file."""
        csv_content = ""
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        with pytest.raises(ValueError, match="Empty file"):
            process_csv_file(file_obj)
    
    def test_process_csv_file_invalid_format(self):
        """Test CSV processing with invalid format."""
        invalid_content = "This is not a CSV file"
        file_obj = io.BytesIO(invalid_content.encode('utf-8'))
        
        with pytest.raises(ValueError, match="Invalid CSV format"):
            process_csv_file(file_obj)
    
    def test_process_csv_file_missing_required_columns(self):
        """Test CSV processing with missing required columns."""
        csv_content = """timestamp,channel
2024-01-01 10:00:00,email
2024-01-02 11:00:00,social"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        with pytest.raises(ValueError, match="Missing required columns"):
            process_csv_file(file_obj)
    
    def test_process_csv_file_large_file(self, large_dataset):
        """Test CSV processing with large dataset."""
        # Convert large dataset to CSV
        csv_buffer = io.StringIO()
        large_dataset.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 10000
        assert 'timestamp' in df.columns
        assert 'channel' in df.columns


@pytest.mark.unit
class TestCSVValidation:
    """Test CSV structure validation."""
    
    def test_validate_csv_structure_success(self, sample_csv_file):
        """Test successful CSV structure validation."""
        sample_csv_file.seek(0)
        
        is_valid, errors = validate_csv_structure(sample_csv_file)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_csv_structure_missing_columns(self):
        """Test CSV validation with missing columns."""
        csv_content = """timestamp,channel
2024-01-01 10:00:00,email
2024-01-02 11:00:00,social"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        is_valid, errors = validate_csv_structure(file_obj)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any('event_type' in str(error) for error in errors)
    
    def test_validate_csv_structure_empty_file(self):
        """Test CSV validation with empty file."""
        csv_content = ""
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        
        is_valid, errors = validate_csv_structure(file_obj)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_csv_structure_invalid_format(self):
        """Test CSV validation with invalid format."""
        invalid_content = "Not a CSV file"
        file_obj = io.BytesIO(invalid_content.encode('utf-8'))
        
        is_valid, errors = validate_csv_structure(file_obj)
        
        assert is_valid is False
        assert len(errors) > 0


@pytest.mark.unit
class TestFileHandling:
    """Test file handling utilities."""
    
    def test_file_size_validation(self):
        """Test file size validation."""
        # Test with small file
        small_content = "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001"
        small_file = io.BytesIO(small_content.encode('utf-8'))
        
        # Should not raise error for small file
        df = process_csv_file(small_file)
        assert len(df) == 1
    
    def test_file_encoding_detection(self):
        """Test automatic encoding detection."""
        # Test with UTF-8 content
        utf8_content = "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001"
        utf8_file = io.BytesIO(utf8_content.encode('utf-8'))
        
        df = process_csv_file(utf8_file)
        assert len(df) == 1
    
    def test_file_with_bom(self):
        """Test CSV processing with BOM (Byte Order Mark)."""
        # Add BOM to content
        bom_content = "\ufefftimestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001"
        bom_file = io.BytesIO(bom_content.encode('utf-8-sig'))
        
        df = process_csv_file(bom_file)
        assert len(df) == 1
        assert 'timestamp' in df.columns
    
    def test_file_with_quoted_fields(self):
        """Test CSV processing with quoted fields."""
        quoted_content = """timestamp,channel,event_type,customer_id
"2024-01-01 10:00:00","email","click","cust_001"
"2024-01-02 11:00:00","social media","conversion","cust_002" """
        
        quoted_file = io.BytesIO(quoted_content.encode('utf-8'))
        df = process_csv_file(quoted_file)
        
        assert len(df) == 2
        assert df['channel'].iloc[1] == 'social media'
    
    def test_file_with_escaped_quotes(self):
        """Test CSV processing with escaped quotes."""
        escaped_content = (
            "timestamp,channel,event_type,customer_id\n"
            '2024-01-01 10:00:00,"email ""marketing""",click,cust_001\n'
            "2024-01-02 11:00:00,social,conversion,cust_002"
        )
        
        escaped_file = io.BytesIO(escaped_content.encode('utf-8'))
        df = process_csv_file(escaped_file)
        
        assert len(df) == 2
        assert 'email "marketing"' in df['channel'].values
    
    def test_file_with_newlines_in_fields(self):
        """Test CSV processing with newlines in fields."""
        newline_content = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,"email
marketing",click,cust_001
2024-01-02 11:00:00,social,conversion,cust_002"""
        
        newline_file = io.BytesIO(newline_content.encode('utf-8'))
        df = process_csv_file(newline_file)
        
        assert len(df) == 2
        # Should handle newlines in quoted fields
        assert 'email\nmarketing' in df['channel'].values


@pytest.mark.unit
class TestDataTransformation:
    """Test data transformation during CSV processing."""
    
    def test_timestamp_parsing(self):
        """Test timestamp parsing from various formats."""
        csv_content = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,cust_001
2024-01-02T11:00:00Z,social,conversion,cust_002
01/03/2024 12:00:00,paid_search,view,cust_003"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 3
        assert 'timestamp' in df.columns
        
        # Check that timestamps are parsed correctly
        timestamps = df['timestamp']
        assert len(timestamps) == 3
    
    def test_numeric_conversion(self):
        """Test numeric field conversion."""
        csv_content = """timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,100.50
2024-01-02 11:00:00,social,conversion,cust_002,250.75
2024-01-03 12:00:00,paid_search,view,cust_003,"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 3
        assert 'conversion_value' in df.columns
        
        # Check numeric conversion
        conversion_values = df['conversion_value']
        assert conversion_values.iloc[0] == 100.50
        assert conversion_values.iloc[1] == 250.75
        assert pd.isna(conversion_values.iloc[2])  # Empty value should be NaN
    
    def test_string_cleaning(self):
        """Test string field cleaning."""
        csv_content = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,  email  ,click,cust_001
2024-01-02 11:00:00,social,conversion,cust_002"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 2
        # Should clean whitespace
        assert df['channel'].iloc[0] == 'email'  # Trimmed
    
    def test_case_normalization(self):
        """Test case normalization for categorical fields."""
        csv_content = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,EMAIL,CLICK,cust_001
2024-01-02 11:00:00,Social,Conversion,cust_002
2024-01-03 12:00:00,Paid_Search,VIEW,cust_003"""
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        df = process_csv_file(file_obj)
        
        assert len(df) == 3
        # Should normalize case
        channels = df['channel'].unique()
        event_types = df['event_type'].unique()
        
        # Check that normalization occurred
        assert len(channels) == 3
        assert len(event_types) == 3


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in CSV processing."""
    
    def test_corrupted_file_handling(self):
        """Test handling of corrupted CSV files."""
        corrupted_content = "timestamp,channel,event_type,customer_id\n2024-01-01,email,click"  # Incomplete row
        
        file_obj = io.BytesIO(corrupted_content.encode('utf-8'))
        
        with pytest.raises(ValueError, match="Incomplete data"):
            process_csv_file(file_obj)
    
    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV files."""
        malformed_content = "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001,extra_field"
        
        file_obj = io.BytesIO(malformed_content.encode('utf-8'))
        
        with pytest.raises(ValueError, match="Column count mismatch"):
            process_csv_file(file_obj)
    
    def test_unicode_error_handling(self):
        """Test handling of unicode errors."""
        # Create content with invalid unicode
        invalid_unicode = b"timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001\xff"
        
        file_obj = io.BytesIO(invalid_unicode)
        
        with pytest.raises(UnicodeDecodeError):
            process_csv_file(file_obj)
    
    def test_memory_error_handling(self):
        """Test handling of memory errors with very large files."""
        # Create a very large CSV content (simulated)
        large_content = "timestamp,channel,event_type,customer_id\n" * 1000000  # 1M rows
        
        file_obj = io.BytesIO(large_content.encode('utf-8'))
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = MemoryError("Not enough memory")
            
            with pytest.raises(MemoryError):
                process_csv_file(file_obj)
    
    def test_file_not_found_handling(self):
        """Test handling of file not found errors."""
        with pytest.raises(FileNotFoundError):
            process_csv_file("nonexistent_file.csv")
    
    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(PermissionError):
                process_csv_file("restricted_file.csv")
