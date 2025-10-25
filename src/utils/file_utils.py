"""File utility functions."""

from typing import Union, List, Optional
import pandas as pd
import io


def process_csv_file(file_obj, separator=',', headers=None, validate_required=True):
    """
    Process CSV file from file-like object.
    
    Args:
        file_obj: File-like object containing CSV data
        separator: CSV separator (default: ',')
        headers: Optional list of headers
        validate_required: Whether to validate required columns (default: True)
        
    Returns:
        pandas DataFrame
        
    Raises:
        ValueError: If file is empty or invalid
    """
    # Handle file path string
    if isinstance(file_obj, str):
        try:
            with open(file_obj, 'rb') as f:
                content = f.read()
            file_obj = io.BytesIO(content)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_obj}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {file_obj}")
    
    if not hasattr(file_obj, 'seek'):
        # Handle other string input
        content = file_obj if isinstance(file_obj, str) else file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        file_obj = io.StringIO(content)
    
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
        content = file_obj.read()
        
        if isinstance(content, bytes):
            # Try UTF-8 with BOM first, then fallback to regular UTF-8
            try:
                content = content.decode('utf-8-sig')
            except:
                content = content.decode('utf-8')
    
    if not content or not content.strip():
        raise ValueError("Empty file")
    
    # Try to determine if it's valid CSV
    try:
        # First pass: read with flexible handling to detect issues
        if headers:
            df = pd.read_csv(io.StringIO(content), sep=separator, names=headers, skiprows=0, on_bad_lines='warn')
        else:
            df = pd.read_csv(io.StringIO(content), sep=separator, on_bad_lines='warn')
            
        # Check for column count mismatch by comparing expected vs actual
        # Only check if there are no quoted fields (which can contain commas/newlines)
        if '"' not in content:
            lines = content.strip().split('\n')
            if len(lines) >= 2:
                expected_fields = len(lines[0].split(separator))
                # Check each data row
                for line in lines[1:]:
                    actual_fields = len(line.split(separator))
                    if actual_fields != expected_fields:
                        if actual_fields < expected_fields:
                            raise ValueError(f"Incomplete data")
                        else:
                            raise ValueError(f"Column count mismatch")
    except ValueError:
        raise  # Re-raise our custom errors
    except pd.errors.ParserError as e:
        error_msg = str(e).lower()
        if 'expected' in error_msg and ('fields' in error_msg or 'field' in error_msg):
            raise ValueError(f"Incomplete data")
        elif 'expected' in error_msg and ('columns' in error_msg or 'column' in error_msg):
            raise ValueError(f"Column count mismatch")
        else:
            raise ValueError(f"Invalid CSV format") from e
    except MemoryError as e:
        raise MemoryError(f"Not enough memory to process file") from e
    except Exception as e:
        raise ValueError(f"Invalid CSV format") from e
    
    # Validate it has data
    if df.empty:
        raise ValueError("Invalid CSV format - no data rows")
    
    # Check for incomplete rows (rows with NaN in required columns)
    required_cols = ['timestamp', 'channel', 'event_type', 'customer_id']
    available_required = [col for col in required_cols if col in df.columns]
    if available_required:
        # Check if any row has all required columns as NaN
        incomplete_rows = df[available_required].isna().all(axis=1).sum()
        if incomplete_rows > 0:
            raise ValueError(f"Incomplete data")
        # Check for column count mismatch (if we have customer_id but it contains comma values)
        if 'customer_id' in df.columns:
            # Look for values that contain commas (likely extra fields concatenated)
            has_extra_fields = df['customer_id'].astype(str).str.contains(',', na=False).any()
            if has_extra_fields:
                raise ValueError(f"Column count mismatch")
    
    # Clean string columns - trim whitespace
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
    
    # Validate required columns if requested
    if validate_required:
        is_valid, errors = validate_csv_structure(df)
        if not is_valid:
            raise ValueError(errors[0] if errors else "Validation failed")
    
    return df


def validate_csv_structure(file_or_df, required_columns: Optional[List[str]] = None):
    """
    Validate that file or DataFrame has required columns.
    
    Args:
        file_or_df: File-like object or DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        
    Raises:
        ValueError: If required columns are missing (when called programmatically)
    """
    if required_columns is None:
        required_columns = ['timestamp', 'channel', 'event_type']
    
    errors = []
    
    try:
        # If it's a file-like object, try to read it
        if hasattr(file_or_df, 'read'):
            # Process CSV and get DataFrame
            df = process_csv_file(file_or_df, validate_required=False)
        elif isinstance(file_or_df, pd.DataFrame):
            df = file_or_df
        else:
            return False, ["Invalid input: expected file-like object or DataFrame"]
        
        # Check required columns
        missing = set(required_columns) - set(df.columns)
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
        
        if errors:
            return False, errors
        return True, []
        
    except Exception as e:
        return False, [str(e)]


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
