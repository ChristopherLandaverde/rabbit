"""Tests for Phase 3 API endpoints (/validate, /methods)."""

import pytest
import pandas as pd
import io
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import os

from src.main import app
from src.models.attribution import ValidationResponse, SchemaDetection, DataQualityMetrics


class TestValidateEndpoint:
    """Test cases for /attribution/validate endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data for testing."""
        df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(5)],
            'channel': ['email', 'social', 'paid', 'organic', 'direct'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion'],
            'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2'],
            'revenue': [0, 0, 100, 0, 50]
        })
        return df.to_csv(index=False)
    
    @pytest.fixture
    def sample_json_data(self):
        """Create sample JSON data for testing."""
        data = [
            {
                'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
                'channel': ['email', 'social', 'paid', 'organic', 'direct'][i],
                'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion'][i],
                'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2'][i],
                'revenue': [0, 0, 100, 0, 50][i]
            }
            for i in range(5)
        ]
        return json.dumps(data)
    
    @pytest.fixture
    def invalid_csv_data(self):
        """Create invalid CSV data for testing."""
        return "invalid,csv,data\n1,2,3\n"
    
    def test_validate_csv_file_success(self, client, sample_csv_data):
        """Test successful validation of CSV file."""
        files = {"file": ("test.csv", sample_csv_data, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "schema_detection" in data
        assert "data_quality" in data
        assert "errors" in data
        assert "recommendations" in data
        assert "warnings" in data
        
        # Check schema detection
        schema = data["schema_detection"]
        assert "detected_columns" in schema
        assert "confidence" in schema
        assert "required_columns_present" in schema
        assert schema["required_columns_present"] is True
        
        # Check data quality
        quality = data["data_quality"]
        assert "completeness" in quality
        assert "consistency" in quality
        assert "freshness" in quality
        assert "overall_quality" in quality
        
        assert 0.0 <= quality["completeness"] <= 1.0
        assert 0.0 <= quality["consistency"] <= 1.0
        assert 0.0 <= quality["freshness"] <= 1.0
        assert 0.0 <= quality["overall_quality"] <= 1.0
    
    def test_validate_json_file_success(self, client, sample_json_data):
        """Test successful validation of JSON file."""
        files = {"file": ("test.json", sample_json_data, "application/json")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["schema_detection"]["required_columns_present"] is True
    
    def test_validate_file_missing_required_columns(self, client):
        """Test validation with missing required columns."""
        # Create CSV without required columns
        invalid_data = "channel,event_type\nemail,touchpoint\nsocial,conversion"
        files = {"file": ("test.csv", invalid_data, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert data["schema_detection"]["required_columns_present"] is False
        assert len(data["errors"]) > 0
        assert "timestamp" in data["recommendations"][0]
    
    def test_validate_file_large_size(self, client):
        """Test validation with file exceeding size limit."""
        # Create large file content
        large_data = "timestamp,channel,event_type\n" + "\n".join([
            f"{datetime.now().isoformat()},email,touchpoint" for _ in range(100000)
        ])
        
        files = {"file": ("large.csv", large_data, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        # Should return 413 status code for file too large
        assert response.status_code == 413
        data = response.json()
        assert "file_too_large" in data["detail"]["error"]
    
    def test_validate_file_parsing_error(self, client):
        """Test validation with file parsing error."""
        files = {"file": ("test.txt", "invalid file content", "text/plain")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 422
        data = response.json()
        assert "file_parsing_error" in data["detail"]["error"]
    
    def test_validate_file_with_poor_quality_data(self, client):
        """Test validation with poor quality data."""
        # Create data with missing values and inconsistencies
        poor_quality_data = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=100)] + [None] * 4,  # Old and missing timestamps
            'channel': ['email', '', 'invalid_channel', 'social', None],  # Missing and invalid channels
            'event_type': ['touchpoint', 'touchpoint', 'invalid_event', None, 'conversion'],  # Invalid and missing events
            'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2']
        }).to_csv(index=False)
        
        files = {"file": ("poor_quality.csv", poor_quality_data, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have low quality scores
        quality = data["data_quality"]
        assert quality["completeness"] < 0.8
        assert quality["consistency"] < 0.8
        assert quality["freshness"] < 0.5
        
        # Should have recommendations for improvement
        assert len(data["recommendations"]) > 0
        assert any("completeness" in rec.lower() for rec in data["recommendations"])
    
    def test_validate_file_with_small_dataset(self, client):
        """Test validation with small dataset."""
        small_data = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(5)],
            'channel': ['email', 'social', 'paid', 'organic', 'direct'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion']
        }).to_csv(index=False)
        
        files = {"file": ("small.csv", small_data, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have warning about small dataset
        assert len(data["warnings"]) > 0
        assert any("small dataset" in warning.lower() for warning in data["warnings"])
    
    def test_validate_file_with_optional_columns(self, client):
        """Test validation with optional columns present."""
        data_with_optional = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(5)],
            'channel': ['email', 'social', 'paid', 'organic', 'direct'],
            'event_type': ['touchpoint', 'touchpoint', 'conversion', 'touchpoint', 'conversion'],
            'customer_id': ['C1', 'C1', 'C1', 'C2', 'C2'],
            'session_id': ['S1', 'S1', 'S1', 'S2', 'S2'],
            'email': ['user1@test.com', 'user1@test.com', 'user1@test.com', 'user2@test.com', 'user2@test.com'],
            'revenue': [0, 0, 100, 0, 50],
            'campaign': ['campaign1', 'campaign1', 'campaign1', 'campaign2', 'campaign2']
        }).to_csv(index=False)
        
        files = {"file": ("complete.csv", data_with_optional, "text/csv")}
        
        response = client.post("/attribution/validate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have high schema confidence due to optional columns
        assert data["schema_detection"]["confidence"] > 0.8
        assert data["valid"] is True


class TestMethodsEndpoint:
    """Test cases for /attribution/methods endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_methods_success(self, client):
        """Test successful retrieval of available methods."""
        response = client.get("/attribution/methods")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "attribution_models" in data
        assert "linking_methods" in data
        assert "recommendations" in data
        
        # Check attribution models
        models = data["attribution_models"]
        assert len(models) == 5  # Should have 5 models
        
        model_names = [model["name"] for model in models]
        expected_models = ["linear", "first_touch", "last_touch", "time_decay", "position_based"]
        assert all(model in model_names for model in expected_models)
        
        # Check model structure
        for model in models:
            assert "name" in model
            assert "display_name" in model
            assert "description" in model
            assert "use_case" in model
            assert "best_for" in model
            assert "parameters" in model
            
            assert isinstance(model["parameters"], list)
        
        # Check linking methods
        linking_methods = data["linking_methods"]
        assert len(linking_methods) == 5  # Should have 5 linking methods
        
        method_names = [method["name"] for method in linking_methods]
        expected_methods = ["auto", "customer_id", "session_email", "email_only", "aggregate"]
        assert all(method in method_names for method in expected_methods)
        
        # Check linking method structure
        for method in linking_methods:
            assert "name" in method
            assert "display_name" in method
            assert "description" in method
            assert "requirements" in method
            assert "accuracy" in method
            assert "coverage" in method
        
        # Check recommendations
        recommendations = data["recommendations"]
        assert "best_for_ecommerce" in recommendations
        assert "best_for_b2b" in recommendations
        assert "best_for_awareness" in recommendations
        assert "best_for_conversion" in recommendations
        assert "best_linking_method" in recommendations
    
    def test_get_methods_attribution_model_details(self, client):
        """Test detailed attribution model information."""
        response = client.get("/attribution/methods")
        data = response.json()
        
        models = data["attribution_models"]
        
        # Test linear model
        linear_model = next(model for model in models if model["name"] == "linear")
        assert linear_model["display_name"] == "Linear Attribution"
        assert "Equal distribution" in linear_model["description"]
        assert len(linear_model["parameters"]) == 0  # No parameters
        
        # Test time decay model
        time_decay_model = next(model for model in models if model["name"] == "time_decay")
        assert time_decay_model["display_name"] == "Time Decay Attribution"
        assert "Exponential decay" in time_decay_model["description"]
        assert len(time_decay_model["parameters"]) == 1  # Has half_life_days parameter
        
        half_life_param = time_decay_model["parameters"][0]
        assert half_life_param["name"] == "half_life_days"
        assert half_life_param["type"] == "float"
        assert half_life_param["default"] == 7.0
        assert half_life_param["range"] == [1.0, 365.0]
        
        # Test position-based model
        position_model = next(model for model in models if model["name"] == "position_based")
        assert position_model["display_name"] == "Position-Based Attribution"
        assert "40% first touchpoint" in position_model["description"]
        assert len(position_model["parameters"]) == 2  # Has two parameters
        
        first_touch_param = next(param for param in position_model["parameters"] if param["name"] == "first_touch_weight")
        assert first_touch_param["default"] == 0.4
        assert first_touch_param["range"] == [0.0, 1.0]
    
    def test_get_methods_linking_method_details(self, client):
        """Test detailed linking method information."""
        response = client.get("/attribution/methods")
        data = response.json()
        
        methods = data["linking_methods"]
        
        # Test auto method
        auto_method = next(method for method in methods if method["name"] == "auto")
        assert auto_method["display_name"] == "Automatic Selection"
        assert "Automatically selects" in auto_method["description"]
        assert auto_method["accuracy"] == "High"
        assert auto_method["coverage"] == "High"
        
        # Test customer_id method
        customer_id_method = next(method for method in methods if method["name"] == "customer_id")
        assert customer_id_method["display_name"] == "Customer ID Linking"
        assert "customer_id field" in customer_id_method["requirements"]
        assert customer_id_method["accuracy"] == "Highest"
        assert customer_id_method["coverage"] == "Medium"
        
        # Test aggregate method
        aggregate_method = next(method for method in methods if method["name"] == "aggregate")
        assert aggregate_method["display_name"] == "Aggregate Linking"
        assert "Statistical modeling" in aggregate_method["description"]
        assert aggregate_method["accuracy"] == "Low"
        assert aggregate_method["coverage"] == "Highest"
    
    def test_get_methods_recommendations(self, client):
        """Test method recommendations."""
        response = client.get("/attribution/methods")
        data = response.json()
        
        recommendations = data["recommendations"]
        
        # Test e-commerce recommendations
        ecommerce_models = recommendations["best_for_ecommerce"]
        assert "linear" in ecommerce_models
        assert "time_decay" in ecommerce_models
        
        # Test B2B recommendations
        b2b_models = recommendations["best_for_b2b"]
        assert "position_based" in b2b_models
        assert "linear" in b2b_models
        
        # Test awareness recommendations
        awareness_models = recommendations["best_for_awareness"]
        assert "first_touch" in awareness_models
        
        # Test conversion recommendations
        conversion_models = recommendations["best_for_conversion"]
        assert "last_touch" in conversion_models
        
        # Test best linking method
        assert recommendations["best_linking_method"] == "auto"
    
    def test_get_methods_error_handling(self, client):
        """Test error handling in methods endpoint."""
        # Mock an error in the endpoint
        with patch('src.api.routes.attribution.datetime') as mock_datetime:
            mock_datetime.utcnow.side_effect = Exception("Test error")
            
            response = client.get("/attribution/methods")
            
            assert response.status_code == 500
            data = response.json()
            assert "methods_retrieval_error" in data["detail"]["error"]
            assert "Test error" in data["detail"]["message"]


class TestAnalyzeEndpointPhase3:
    """Test cases for enhanced /attribution/analyze endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_analysis_data(self):
        """Create sample data for analysis testing."""
        return pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(10)],
            'channel': ['email', 'social', 'paid', 'organic', 'direct'] * 2,
            'event_type': ['touchpoint'] * 8 + ['conversion'] * 2,
            'customer_id': ['C1'] * 5 + ['C2'] * 5,
            'revenue': [0] * 8 + [100, 50]
        }).to_csv(index=False)
    
    def test_analyze_with_confidence_scoring(self, client, sample_analysis_data):
        """Test analysis endpoint with confidence scoring."""
        files = {"file": ("test.csv", sample_analysis_data, "text/csv")}
        data = {"model_type": "linear"}
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Should have confidence metrics
        assert "confidence" in result
        assert "journey_analysis" in result
        assert "business_insights" in result
        
        # Check confidence structure
        confidence = result["confidence"]
        assert "overall_confidence" in confidence
        assert "data_quality" in confidence
        assert "sample_size" in confidence
        assert "model_fit" in confidence
        assert "identity_resolution" in confidence
        
        assert 0.0 <= confidence["overall_confidence"] <= 1.0
    
    def test_analyze_with_journey_analysis(self, client, sample_analysis_data):
        """Test analysis endpoint with journey analysis."""
        files = {"file": ("test.csv", sample_analysis_data, "text/csv")}
        data = {"model_type": "linear"}
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check journey analysis structure
        journey_analysis = result["journey_analysis"]
        assert "journey_lengths" in journey_analysis
        assert "conversion_paths" in journey_analysis
        assert "time_to_conversion" in journey_analysis
        assert "insights" in journey_analysis
    
    def test_analyze_with_business_insights(self, client, sample_analysis_data):
        """Test analysis endpoint with business insights."""
        files = {"file": ("test.csv", sample_analysis_data, "text/csv")}
        data = {"model_type": "linear"}
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check business insights structure
        insights = result["business_insights"]
        assert isinstance(insights, list)
        
        if len(insights) > 0:
            for insight in insights:
                assert "type" in insight
                assert "category" in insight
                assert "title" in insight
                assert "description" in insight
                assert "impact_score" in insight
                assert "recommendation" in insight
                assert "priority" in insight
    
    def test_analyze_invalid_model_type(self, client, sample_analysis_data):
        """Test analysis endpoint with invalid model type."""
        files = {"file": ("test.csv", sample_analysis_data, "text/csv")}
        data = {"model_type": "invalid_model"}
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 422
        error_data = response.json()
        assert "invalid_model_type" in error_data["detail"]["error"]
        assert "invalid_model" in error_data["detail"]["message"]
    
    def test_analyze_with_model_parameters(self, client, sample_analysis_data):
        """Test analysis endpoint with model parameters."""
        files = {"file": ("test.csv", sample_analysis_data, "text/csv")}
        data = {
            "model_type": "time_decay",
            "half_life_days": 14.0
        }
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Should successfully process with time decay model
        assert "attribution_results" in result
        assert "confidence" in result
    
    def test_analyze_file_too_large(self, client):
        """Test analysis endpoint with file exceeding size limit."""
        # Create large file content
        large_data = "timestamp,channel,event_type\n" + "\n".join([
            f"{datetime.now().isoformat()},email,touchpoint" for _ in range(100000)
        ])
        
        files = {"file": ("large.csv", large_data, "text/csv")}
        data = {"model_type": "linear"}
        
        response = client.post("/attribution/analyze", files=files, data=data)
        
        assert response.status_code == 413
        error_data = response.json()
        assert "file_too_large" in error_data["detail"]["error"]


class TestAPIEndpointIntegration:
    """Integration tests for Phase 3 API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_full_workflow_validation_to_analysis(self, client):
        """Test complete workflow from validation to analysis."""
        # Create comprehensive test data
        test_data = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(20)],
            'channel': ['email', 'social', 'paid', 'organic', 'direct'] * 4,
            'event_type': ['touchpoint'] * 16 + ['conversion'] * 4,
            'customer_id': ['C1'] * 10 + ['C2'] * 10,
            'session_id': ['S1'] * 10 + ['S2'] * 10,
            'email': ['user1@test.com'] * 10 + ['user2@test.com'] * 10,
            'revenue': [0] * 16 + [100, 50, 75, 25]
        }).to_csv(index=False)
        
        # Step 1: Validate data
        files = {"file": ("workflow_test.csv", test_data, "text/csv")}
        validation_response = client.post("/attribution/validate", files=files)
        
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        assert validation_data["valid"] is True
        
        # Step 2: Get available methods
        methods_response = client.get("/attribution/methods")
        assert methods_response.status_code == 200
        methods_data = methods_response.json()
        assert len(methods_data["attribution_models"]) == 5
        
        # Step 3: Perform analysis
        analysis_data = {"model_type": "linear"}
        analysis_response = client.post("/attribution/analyze", files=files, data=analysis_data)
        
        assert analysis_response.status_code == 200
        analysis_result = analysis_response.json()
        
        # Verify comprehensive response structure
        assert "attribution_results" in analysis_result
        assert "confidence" in analysis_result
        assert "journey_analysis" in analysis_result
        assert "business_insights" in analysis_result
        assert "metadata" in analysis_result
        
        # Verify confidence scoring
        confidence = analysis_result["confidence"]
        assert 0.0 <= confidence["overall_confidence"] <= 1.0
        
        # Verify journey analysis
        journey = analysis_result["journey_analysis"]
        assert "journey_lengths" in journey
        assert "conversion_paths" in journey
        assert "time_to_conversion" in journey
        
        # Verify business insights
        insights = analysis_result["business_insights"]
        assert isinstance(insights, list)
    
    def test_error_handling_consistency(self, client):
        """Test that error handling is consistent across endpoints."""
        # Test with invalid file format
        files = {"file": ("test.txt", "invalid content", "text/plain")}
        
        # Validation endpoint should handle gracefully
        validation_response = client.post("/attribution/validate", files=files)
        assert validation_response.status_code == 422
        
        # Analysis endpoint should handle gracefully
        analysis_data = {"model_type": "linear"}
        analysis_response = client.post("/attribution/analyze", files=files, data=analysis_data)
        assert analysis_response.status_code == 422
        
        # Both should return consistent error structure
        validation_error = validation_response.json()
        analysis_error = analysis_response.json()
        
        assert "error" in validation_error["detail"]
        assert "error" in analysis_error["detail"]
        assert "timestamp" in validation_error["detail"]
        assert "timestamp" in analysis_error["detail"]
