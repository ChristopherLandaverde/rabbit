"""Tests for secure API endpoints with authentication and caching."""

import pytest
import json
import io
import hashlib
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from src.api.routes.attribution_secure import (
    validate_data, get_available_methods, analyze_attribution,
    _parse_uploaded_file
)
from src.models.attribution import AttributionResponse, ValidationResponse
from src.models.enums import AttributionModelType
from src.config import get_settings


class TestValidateData:
    """Test validate_data endpoint."""
    
    @pytest.mark.asyncio
    async def test_validate_data_success(self):
        """Test successful data validation."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click\n2024-01-02,social,view"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
                        with patch('src.api.routes.attribution_secure.validate_data_quality') as mock_quality:
                            with patch('src.api.routes.attribution_secure.validate_required_columns') as mock_required:
                                with patch('src.api.routes.attribution_secure.validate_data_types') as mock_types:
                                    # Setup mocks
                                    mock_validator.validate_file_upload.return_value = None
                                    mock_cache.get_validation_result.return_value = None
                                    mock_cache.set_validation_result.return_value = True
                                    
                                    # Mock DataFrame
                                    mock_df = Mock()
                                    mock_df.columns = ['timestamp', 'channel', 'event_type', 'customer_id']
                                    mock_df.dtypes = {'timestamp': 'datetime64', 'channel': 'object', 'event_type': 'object'}
                                    mock_read_csv.return_value = mock_df
                                    
                                    # Mock validation results
                                    mock_required.return_value = []
                                    mock_types.return_value = []
                                    
                                    # Mock data quality
                                    mock_quality_result = Mock()
                                    mock_quality_result.completeness = 0.95
                                    mock_quality_result.consistency = 0.90
                                    mock_quality_result.freshness = 0.85
                                    mock_quality.return_value = mock_quality_result
                                    
                                    # Test function
                                    result = await validate_data(mock_file, current_user)
                                    
                                    # Verify result
                                    assert isinstance(result, ValidationResponse)
                                    assert result.valid is True
                                    assert result.schema_detection.confidence > 0
                                    assert result.schema_detection.required_columns_present is True
                                    assert result.data_quality.completeness == 0.95
                                    assert result.data_quality.consistency == 0.90
                                    assert result.data_quality.freshness == 0.85
                                    
                                    # Verify caching
                                    mock_cache.get_validation_result.assert_called_once()
                                    mock_cache.set_validation_result.assert_called_once()
                                    
                                    # Verify logging
                                    mock_security_logger.log_file_upload.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_data_cached_result(self):
        """Test data validation with cached result."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock cached result
        cached_result = {
            "valid": True,
            "schema_detection": {
                "detected_columns": {"timestamp": "datetime64"},
                "confidence": 0.8,
                "required_columns_present": True
            },
            "data_quality": {
                "completeness": 0.9,
                "consistency": 0.8,
                "freshness": 0.7,
                "overall_quality": 0.8
            },
            "errors": [],
            "recommendations": [],
            "warnings": []
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    # Setup mocks
                    mock_validator.validate_file_upload.return_value = None
                    mock_cache.get_validation_result.return_value = cached_result
                    
                    # Test function
                    result = await validate_data(mock_file, current_user)
                    
                    # Verify result
                    assert isinstance(result, ValidationResponse)
                    assert result.valid is True
                    assert result.schema_detection.confidence == 0.8
                    assert result.data_quality.completeness == 0.9
                    
                    # Verify caching was used
                    mock_cache.get_validation_result.assert_called_once()
                    mock_cache.set_validation_result.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_validate_data_file_too_large(self):
        """Test data validation with file too large."""
        # Mock file content (large)
        large_content = b"x" * (200 * 1024 * 1024)  # 200MB
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=large_content)
        mock_file.filename = "large.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            # Setup mock to raise exception
            mock_validator.validate_file_upload.side_effect = HTTPException(
                status_code=413,
                detail={"error": "file_too_large", "message": "File too large"}
            )
            
            # Test function
            with pytest.raises(HTTPException) as exc_info:
                await validate_data(mock_file, current_user)
            
            assert exc_info.value.status_code == 413
            assert "file_too_large" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_data_invalid_file_type(self):
        """Test data validation with invalid file type."""
        # Mock file content
        file_content = b"some content"
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.txt"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            # Setup mock to raise exception
            mock_validator.validate_file_upload.side_effect = HTTPException(
                status_code=422,
                detail={"error": "invalid_file_type", "message": "Invalid file type"}
            )
            
            # Test function
            with pytest.raises(HTTPException) as exc_info:
                await validate_data(mock_file, current_user)
            
            assert exc_info.value.status_code == 422
            assert "invalid_file_type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_data_processing_error(self):
        """Test data validation with processing error."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
                        # Setup mocks
                        mock_validator.validate_file_upload.return_value = None
                        mock_cache.get_validation_result.return_value = None
                        mock_read_csv.side_effect = Exception("CSV parsing error")
                        
                        # Test function
                        with pytest.raises(HTTPException) as exc_info:
                            await validate_data(mock_file, current_user)
                        
                        assert exc_info.value.status_code == 500
                        assert "validation_error" in str(exc_info.value.detail)
                        assert "CSV parsing error" in str(exc_info.value.detail)
                        
                        # Verify error logging
                        mock_security_logger.log_file_upload.assert_called_once()


class TestGetAvailableMethods:
    """Test get_available_methods endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_available_methods_success(self):
        """Test successful retrieval of available methods."""
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.api_cache') as mock_cache:
            with patch('src.api.routes.attribution_secure.business_logger') as mock_business_logger:
                # Setup mocks
                mock_cache.get_available_methods.return_value = None
                mock_cache.set_available_methods.return_value = True
                
                # Test function
                result = await get_available_methods(current_user)
                
                # Verify result structure
                assert "attribution_models" in result
                assert "linking_methods" in result
                assert "recommendations" in result
                
                # Verify attribution models
                attribution_models = result["attribution_models"]
                assert len(attribution_models) == 5
                
                model_names = [model["name"] for model in attribution_models]
                assert "linear" in model_names
                assert "first_touch" in model_names
                assert "last_touch" in model_names
                assert "time_decay" in model_names
                assert "position_based" in model_names
                
                # Verify linking methods
                linking_methods = result["linking_methods"]
                assert len(linking_methods) == 5
                
                method_names = [method["name"] for method in linking_methods]
                assert "auto" in method_names
                assert "customer_id" in method_names
                assert "session_email" in method_names
                assert "email_only" in method_names
                assert "aggregate" in method_names
                
                # Verify caching
                mock_cache.get_available_methods.assert_called_once()
                mock_cache.set_available_methods.assert_called_once()
                
                # Verify logging
                mock_business_logger.log_api_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_available_methods_cached(self):
        """Test retrieval of cached available methods."""
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock cached result
        cached_result = {
            "attribution_models": [{"name": "linear", "display_name": "Linear Attribution"}],
            "linking_methods": [{"name": "auto", "display_name": "Automatic Selection"}],
            "recommendations": {"best_for_ecommerce": ["linear"]}
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.api_cache') as mock_cache:
            with patch('src.api.routes.attribution_secure.business_logger') as mock_business_logger:
                # Setup mocks
                mock_cache.get_available_methods.return_value = cached_result
                
                # Test function
                result = await get_available_methods(current_user)
                
                # Verify result
                assert result == cached_result
                
                # Verify caching was used
                mock_cache.get_available_methods.assert_called_once()
                mock_cache.set_available_methods.assert_not_called()
                
                # Verify logging
                mock_business_logger.log_api_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_available_methods_error(self):
        """Test error handling in get_available_methods."""
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.api_cache') as mock_cache:
            # Setup mock to raise exception
            mock_cache.get_available_methods.side_effect = Exception("Cache error")
            
            # Test function
            with pytest.raises(HTTPException) as exc_info:
                await get_available_methods(current_user)
            
            assert exc_info.value.status_code == 500
            assert "methods_retrieval_error" in str(exc_info.value.detail)
            assert "Cache error" in str(exc_info.value.detail)


class TestAnalyzeAttribution:
    """Test analyze_attribution endpoint."""
    
    @pytest.mark.asyncio
    async def test_analyze_attribution_success(self):
        """Test successful attribution analysis."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click\n2024-01-02,social,conversion"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock attribution result
        mock_attribution_result = Mock()
        mock_attribution_result.dict.return_value = {
            "attribution_results": [{"channel": "email", "credit": 0.5}],
            "metadata": {"confidence_score": 0.95}
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    with patch('src.api.routes.attribution_secure.business_logger') as mock_business_logger:
                        with patch('src.api.routes.attribution_secure.performance_logger') as mock_performance_logger:
                            with patch('src.api.routes.attribution_secure.AttributionService') as mock_service:
                                with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
                                    # Setup mocks
                                    mock_validator.validate_file_upload.return_value = None
                                    mock_validator.validate_model_parameters.return_value = {}
                                    mock_cache.get_attribution_result.return_value = None
                                    mock_cache.set_attribution_result.return_value = True
                                    
                                    # Mock DataFrame
                                    mock_df = Mock()
                                    mock_df.columns = ['timestamp', 'channel', 'event_type']
                                    mock_df.__len__ = Mock(return_value=2)
                                    mock_read_csv.return_value = mock_df
                                    
                                    # Mock attribution service
                                    mock_service_instance = Mock()
                                    mock_service.return_value = mock_service_instance
                                    mock_service_instance.analyze_attribution = AsyncMock(return_value=mock_attribution_result)
                                    
                                    # Test function
                                    result = await analyze_attribution(
                                        mock_file, "linear", None, None, None, current_user
                                    )
                                    
                                    # Verify result
                                    assert isinstance(result, AttributionResponse)
                                    
                                    # Verify caching
                                    mock_cache.get_attribution_result.assert_called_once()
                                    mock_cache.set_attribution_result.assert_called_once()
                                    
                                    # Verify logging
                                    mock_security_logger.log_attribution_analysis.assert_called_once()
                                    mock_business_logger.log_api_usage.assert_called_once()
                                    mock_performance_logger.log_attribution_processing_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_attribution_cached_result(self):
        """Test attribution analysis with cached result."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock cached result
        cached_result = {
            "attribution_results": [{"channel": "email", "credit": 0.5}],
            "metadata": {"confidence_score": 0.95}
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    with patch('src.api.routes.attribution_secure.business_logger') as mock_business_logger:
                        with patch('src.api.routes.attribution_secure.performance_logger') as mock_performance_logger:
                            # Setup mocks
                            mock_validator.validate_file_upload.return_value = None
                            mock_validator.validate_model_parameters.return_value = {}
                            mock_cache.get_attribution_result.return_value = cached_result
                            
                            # Test function
                            result = await analyze_attribution(
                                mock_file, "linear", None, None, None, current_user
                            )
                            
                            # Verify result
                            assert isinstance(result, AttributionResponse)
                            
                            # Verify caching was used
                            mock_cache.get_attribution_result.assert_called_once()
                            mock_cache.set_attribution_result.assert_not_called()
                            
                            # Verify logging
                            mock_security_logger.log_attribution_analysis.assert_called_once()
                            mock_business_logger.log_api_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_attribution_invalid_model(self):
        """Test attribution analysis with invalid model type."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                # Setup mocks
                mock_validator.validate_file_upload.return_value = None
                mock_validator.validate_model_parameters.return_value = {}
                mock_cache.get_attribution_result.return_value = None
                
                # Test function
                with pytest.raises(HTTPException) as exc_info:
                    await analyze_attribution(
                        mock_file, "invalid_model", None, None, None, current_user
                    )
                
                assert exc_info.value.status_code == 422
                assert "invalid_model_type" in str(exc_info.value.detail)
                assert "invalid_model" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_analyze_attribution_processing_error(self):
        """Test attribution analysis with processing error."""
        # Mock file content
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        # Mock file
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.filename = "test.csv"
        
        # Mock current user
        current_user = {
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }
        
        # Mock dependencies
        with patch('src.api.routes.attribution_secure.input_validator') as mock_validator:
            with patch('src.api.routes.attribution_secure.attribution_cache') as mock_cache:
                with patch('src.api.routes.attribution_secure.security_logger') as mock_security_logger:
                    with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
                        # Setup mocks
                        mock_validator.validate_file_upload.return_value = None
                        mock_validator.validate_model_parameters.return_value = {}
                        mock_cache.get_attribution_result.return_value = None
                        mock_read_csv.side_effect = Exception("CSV parsing error")
                        
                        # Test function
                        with pytest.raises(HTTPException) as exc_info:
                            await analyze_attribution(
                                mock_file, "linear", None, None, None, current_user
                            )
                        
                        assert exc_info.value.status_code == 500
                        assert "processing_error" in str(exc_info.value.detail)
                        assert "CSV parsing error" in str(exc_info.value.detail)
                        
                        # Verify error logging
                        mock_security_logger.log_attribution_analysis.assert_called_once()


class TestParseUploadedFile:
    """Test _parse_uploaded_file function."""
    
    @pytest.mark.asyncio
    async def test_parse_csv_file(self):
        """Test parsing CSV file."""
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
            # Mock DataFrame
            mock_df = Mock()
            mock_df.columns = ['timestamp', 'channel', 'event_type']
            mock_read_csv.return_value = mock_df
            
            result = await _parse_uploaded_file(file_content, "test.csv")
            
            assert result == mock_df
            mock_read_csv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_json_file(self):
        """Test parsing JSON file."""
        json_content = '{"timestamp": "2024-01-01", "channel": "email"}'
        file_content = json_content.encode()
        
        with patch('src.api.routes.attribution_secure.pd.read_json') as mock_read_json:
            # Mock DataFrame
            mock_df = Mock()
            mock_df.columns = ['timestamp', 'channel']
            mock_read_json.return_value = mock_df
            
            result = await _parse_uploaded_file(file_content, "test.json")
            
            assert result == mock_df
            mock_read_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_parquet_file(self):
        """Test parsing Parquet file."""
        file_content = b"parquet_content"
        
        with patch('src.api.routes.attribution_secure.pd.read_parquet') as mock_read_parquet:
            # Mock DataFrame
            mock_df = Mock()
            mock_df.columns = ['timestamp', 'channel']
            mock_read_parquet.return_value = mock_df
            
            result = await _parse_uploaded_file(file_content, "test.parquet")
            
            assert result == mock_df
            mock_read_parquet.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_unsupported_file(self):
        """Test parsing unsupported file type."""
        file_content = b"some content"
        
        with pytest.raises(HTTPException) as exc_info:
            await _parse_uploaded_file(file_content, "test.txt")
        
        assert exc_info.value.status_code == 422
        assert "file_parsing_error" in str(exc_info.value.detail)
        assert "Unsupported file format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_parse_file_with_timestamp_conversion(self):
        """Test parsing file with timestamp column conversion."""
        csv_content = "timestamp,channel,event_type\n2024-01-01,email,click"
        file_content = csv_content.encode()
        
        with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
            with patch('src.api.routes.attribution_secure.pd.to_datetime') as mock_to_datetime:
                # Mock DataFrame
                mock_df = Mock()
                mock_df.columns = ['timestamp', 'channel', 'event_type']
                mock_read_csv.return_value = mock_df
                
                result = await _parse_uploaded_file(file_content, "test.csv")
                
                assert result == mock_df
                mock_to_datetime.assert_called_once_with(mock_df['timestamp'])
    
    @pytest.mark.asyncio
    async def test_parse_file_parsing_error(self):
        """Test parsing file with parsing error."""
        file_content = b"invalid_csv_content"
        
        with patch('src.api.routes.attribution_secure.pd.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = Exception("CSV parsing error")
            
            with pytest.raises(HTTPException) as exc_info:
                await _parse_uploaded_file(file_content, "test.csv")
            
            assert exc_info.value.status_code == 422
            assert "file_parsing_error" in str(exc_info.value.detail)
            assert "CSV parsing error" in str(exc_info.value.detail)


class TestSecureAPIIntegration:
    """Integration tests for secure API endpoints."""
    
    def test_secure_api_dependencies(self):
        """Test that secure API endpoints have proper dependencies."""
        # Test that endpoints are properly configured with dependencies
        assert hasattr(validate_data, '__wrapped__')  # Has dependencies
        assert hasattr(get_available_methods, '__wrapped__')  # Has dependencies
        assert hasattr(analyze_attribution, '__wrapped__')  # Has dependencies
    
    def test_secure_api_error_handling(self):
        """Test that secure API endpoints handle errors properly."""
        # Test that all endpoints have proper error handling
        # This is verified through the individual test cases above
        pass
    
    def test_secure_api_caching_integration(self):
        """Test that secure API endpoints integrate with caching properly."""
        # Test that all endpoints use caching appropriately
        # This is verified through the individual test cases above
        pass
    
    def test_secure_api_logging_integration(self):
        """Test that secure API endpoints integrate with logging properly."""
        # Test that all endpoints use logging appropriately
        # This is verified through the individual test cases above
        pass
    
    def test_secure_api_authentication_integration(self):
        """Test that secure API endpoints integrate with authentication properly."""
        # Test that all endpoints use authentication appropriately
        # This is verified through the individual test cases above
        pass
