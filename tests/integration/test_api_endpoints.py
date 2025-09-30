"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.app import client, sample_csv_file


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client: TestClient):
        """Test health check returns successful response."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


@pytest.mark.integration
class TestAttributionEndpoint:
    """Test attribution analysis endpoint."""
    
    def test_analyze_attribution_success(self, client: TestClient, sample_csv_file):
        """Test successful attribution analysis."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "results" in data
        assert "metadata" in data
        assert "insights" in data
        
        # Check results structure
        results = data["results"]
        assert "total_conversions" in results
        assert "total_revenue" in results
        assert "channel_attributions" in results
        assert "overall_confidence" in results
        
        # Check metadata structure
        metadata = data["metadata"]
        assert "model_used" in metadata
        assert "data_points_analyzed" in metadata
        assert "processing_time_ms" in metadata
        assert "linking_method" in metadata
    
    def test_analyze_attribution_different_models(self, client: TestClient, sample_csv_file):
        """Test attribution analysis with different models."""
        models = ["linear", "first_touch", "last_touch", "time_decay", "position_based"]
        
        for model_type in models:
            response = client.post(
                "/attribution/analyze",
                files={"file": ("test.csv", sample_csv_file, "text/csv")},
                data={"model_type": model_type}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["model_used"] == model_type
    
    def test_analyze_attribution_with_parameters(self, client: TestClient, sample_csv_file):
        """Test attribution analysis with model parameters."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={
                "model_type": "time_decay",
                "half_life_days": "14.0"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["model_used"] == "time_decay"
    
    def test_analyze_attribution_invalid_model(self, client: TestClient, sample_csv_file):
        """Test attribution analysis with invalid model type."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={"model_type": "invalid_model"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "invalid_model_type"
    
    def test_analyze_attribution_missing_file(self, client: TestClient):
        """Test attribution analysis without file upload."""
        response = client.post(
            "/attribution/analyze",
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_attribution_missing_model_type(self, client: TestClient, sample_csv_file):
        """Test attribution analysis without model type."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_attribution_invalid_file_format(self, client: TestClient):
        """Test attribution analysis with invalid file format."""
        invalid_content = "This is not a valid CSV file"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.txt", invalid_content, "text/plain")},
            data={"model_type": "linear"}
        )
        
        # Should handle gracefully - might return 422 or process as CSV
        assert response.status_code in [200, 422]
    
    def test_analyze_attribution_empty_file(self, client: TestClient):
        """Test attribution analysis with empty file."""
        empty_content = ""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("empty.csv", empty_content, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code in [200, 422]  # Should handle empty file
    
    def test_analyze_attribution_large_file_simulation(self, client: TestClient):
        """Test attribution analysis with large file (simulated)."""
        # Create a larger CSV file for testing
        large_csv_content = "timestamp,channel,event_type,customer_id,conversion_value\n"
        for i in range(1000):  # 1000 rows
            large_csv_content += f"2024-01-01 10:00:00,email,click,cust_{i % 100},\n"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("large_test.csv", large_csv_content, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["data_points_analyzed"] == 1000


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""
    
    def test_health_check_endpoint_always_available(self, client: TestClient):
        """Test that health check is always available."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_invalid_endpoint_returns_404(self, client: TestClient):
        """Test that invalid endpoints return 404."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404
    
    def test_attribution_endpoint_method_not_allowed(self, client: TestClient):
        """Test that GET method on attribution endpoint returns 405."""
        response = client.get("/attribution/analyze")
        assert response.status_code == 405  # Method not allowed
    
    def test_attribution_endpoint_malformed_request(self, client: TestClient):
        """Test attribution endpoint with malformed request."""
        response = client.post(
            "/attribution/analyze",
            data={"invalid_field": "value"}
        )
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestResponseFormat:
    """Test API response format consistency."""
    
    def test_response_contains_required_fields(self, client: TestClient, sample_csv_file):
        """Test that response contains all required fields."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required top-level fields
        required_fields = ["results", "metadata"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Required results fields
        results_fields = ["total_conversions", "total_revenue", "channel_attributions", "overall_confidence"]
        for field in results_fields:
            assert field in data["results"], f"Missing required results field: {field}"
        
        # Required metadata fields
        metadata_fields = ["model_used", "data_points_analyzed", "processing_time_ms", "linking_method"]
        for field in metadata_fields:
            assert field in data["metadata"], f"Missing required metadata field: {field}"
    
    def test_channel_attribution_format(self, client: TestClient, sample_csv_file):
        """Test that channel attribution format is correct."""
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", sample_csv_file, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        channel_attributions = data["results"]["channel_attributions"]
        
        for channel, attribution in channel_attributions.items():
            assert "credit" in attribution
            assert "conversions" in attribution
            assert "revenue" in attribution
            assert "confidence" in attribution
            
            # Validate ranges
            assert 0.0 <= attribution["credit"] <= 1.0
            assert attribution["conversions"] >= 0
            assert attribution["revenue"] >= 0.0
            assert 0.0 <= attribution["confidence"] <= 1.0
