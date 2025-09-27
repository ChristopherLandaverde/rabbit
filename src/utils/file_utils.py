"""File utility functions."""

from typing import Union
import pandas as pd
import io


def read_data_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Read data file content into a pandas DataFrame.
    
    Args:
        file_content: File content as bytes
        filename: Original filename to determine format
        
    Returns:
        pandas DataFrame
        
    Raises:
        ValueError: If file format is not supported
    """
    file_extension = filename.lower().split('.')[-1] if filename else 'csv'
    
    if file_extension == 'csv':
        return pd.read_csv(io.BytesIO(file_content))
    elif file_extension == 'json':
        return pd.read_json(io.BytesIO(file_content))
    elif file_extension == 'parquet':
        return pd.read_parquet(io.BytesIO(file_content))
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")


def validate_file_format(filename: str) -> bool:
    """
    Validate that the file format is supported.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if format is supported, False otherwise
    """
    supported_formats = {'csv', 'json', 'parquet'}
    file_extension = filename.lower().split('.')[-1] if filename else ''
    return file_extension in supported_formats
