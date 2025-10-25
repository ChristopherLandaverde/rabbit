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


@pytest.mark.integration
class TestAPISecurity:
    """Test API security and input validation."""
    
    def test_sql_injection_attempts(self, client: TestClient):
        """Test API protection against SQL injection attempts."""
        malicious_csv = "timestamp,channel,event_type,customer_id\n2024-01-01,email'; DROP TABLE users; --,click,cust_001"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("malicious.csv", malicious_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle malicious input gracefully
        assert response.status_code in [200, 422]  # Either process or reject
    
    def test_xss_attempts(self, client: TestClient):
        """Test API protection against XSS attempts."""
        xss_csv = "timestamp,channel,event_type,customer_id\n2024-01-01,<script>alert('xss')</script>,click,cust_001"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("xss.csv", xss_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle XSS attempts safely
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            # Ensure no script tags in response
            response_text = str(data)
            assert "<script>" not in response_text
    
    def test_path_traversal_attempts(self, client: TestClient):
        """Test API protection against path traversal attempts."""
        malicious_filename = "../../../etc/passwd"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": (malicious_filename, "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001", "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle path traversal attempts safely
        assert response.status_code in [200, 422]
    
    def test_large_file_upload_limits(self, client: TestClient):
        """Test API handling of large file uploads."""
        # Create a very large CSV content
        large_content = "timestamp,channel,event_type,customer_id\n"
        for i in range(100000):  # 100k rows
            large_content += f"2024-01-01 10:00:00,email,click,cust_{i}\n"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("large.csv", large_content, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should either process or reject based on size limits
        assert response.status_code in [200, 413, 422]  # 413 = Payload Too Large
    
    def test_concurrent_request_limits(self, client: TestClient):
        """Test API handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.post(
                "/attribution/analyze",
                files={"file": ("test.csv", "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001", "text/csv")},
                data={"model_type": "linear"}
            )
            results.append(response.status_code)
        
        # Make 20 concurrent requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should handle concurrent requests gracefully
        assert len(results) == 20
        # Most should succeed, some might be rate limited
        success_count = sum(1 for status in results if status == 200)
        assert success_count >= 10  # At least half should succeed


@pytest.mark.integration
class TestAPIEdgeCases:
    """Test API edge cases and boundary conditions."""
    
    def test_analyze_attribution_with_minimal_data(self, client: TestClient):
        """Test attribution analysis with minimal valid data."""
        minimal_csv = "timestamp,channel,event_type,customer_id\n2024-01-01 10:00:00,email,conversion,cust_001"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("minimal.csv", minimal_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["total_conversions"] == 1
        assert data["results"]["total_revenue"] == 0.0  # No conversion value
    
    def test_analyze_attribution_with_no_conversions(self, client: TestClient):
        """Test attribution analysis with no conversion events."""
        no_conversion_csv = "timestamp,channel,event_type,customer_id\n2024-01-01 10:00:00,email,click,cust_001\n2024-01-02 11:00:00,social,view,cust_001"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("no_conversion.csv", no_conversion_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["total_conversions"] == 0
        assert data["results"]["total_revenue"] == 0.0
    
    def test_analyze_attribution_with_single_customer_multiple_journeys(self, client: TestClient):
        """Test attribution analysis with single customer having multiple journeys."""
        multi_journey_csv = """timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 11:00:00,social,conversion,cust_001,100.0
2024-01-02 10:00:00,paid_search,click,cust_001,
2024-01-02 11:00:00,organic,conversion,cust_001,200.0"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("multi_journey.csv", multi_journey_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["total_conversions"] == 2
        assert data["results"]["total_revenue"] == 300.0
    
    def test_analyze_attribution_with_duplicate_timestamps(self, client: TestClient):
        """Test attribution analysis with duplicate timestamps."""
        duplicate_timestamp_csv = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,cust_001
2024-01-01 10:00:00,social,view,cust_001
2024-01-01 10:00:00,paid_search,conversion,cust_001"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("duplicate_timestamp.csv", duplicate_timestamp_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["total_conversions"] == 1
    
    def test_analyze_attribution_with_negative_conversion_values(self, client: TestClient):
        """Test attribution analysis with negative conversion values."""
        negative_value_csv = """timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 11:00:00,social,conversion,cust_001,-50.0"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("negative_value.csv", negative_value_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle negative values gracefully
        assert response.status_code in [200, 422]
    
    def test_analyze_attribution_with_very_long_customer_ids(self, client: TestClient):
        """Test attribution analysis with very long customer IDs."""
        long_id_csv = f"""timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,{'cust_' + 'x' * 1000}
2024-01-01 11:00:00,social,conversion,{'cust_' + 'x' * 1000}"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("long_id.csv", long_id_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle long IDs gracefully
        assert response.status_code in [200, 422]
    
    def test_analyze_attribution_with_special_characters(self, client: TestClient):
        """Test attribution analysis with special characters in data."""
        special_char_csv = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email@domain,click,cust_001
2024-01-01 11:00:00,social media 📱,conversion,cust_001
2024-01-01 12:00:00,paid-search,view,cust_001"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("special_char.csv", special_char_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["total_conversions"] == 1
    
    def test_analyze_attribution_with_unicode_data(self, client: TestClient):
        """Test attribution analysis with unicode data."""
        unicode_csv = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,cust_001
2024-01-01 11:00:00,social,conversion,cust_001"""
        
        # Encode with UTF-8
        unicode_bytes = unicode_csv.encode('utf-8')
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("unicode.csv", unicode_bytes, "text/csv")},
            data={"model_type": "linear"}
        )
        
        assert response.status_code == 200


@pytest.mark.integration
class TestAPIPerformance:
    """Test API performance characteristics."""
    
    def test_response_time_under_load(self, client: TestClient):
        """Test API response time under normal load."""
        import time
        
        start_time = time.time()
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001", "text/csv")},
            data={"model_type": "linear"}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds
    
    def test_memory_usage_with_large_dataset(self, client: TestClient):
        """Test memory usage with large dataset."""
        # Create a moderately large dataset
        large_csv = "timestamp,channel,event_type,customer_id\n"
        for i in range(10000):  # 10k rows
            large_csv += f"2024-01-01 10:00:00,email,click,cust_{i % 100}\n"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("large.csv", large_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle large dataset without memory issues
        assert response.status_code in [200, 413]  # Either process or reject due to size
    
    def test_concurrent_request_performance(self, client: TestClient):
        """Test performance under concurrent requests."""
        import threading
        import time
        
        results = []
        start_time = time.time()
        
        def make_request():
            response = client.post(
                "/attribution/analyze",
                files={"file": ("test.csv", "timestamp,channel,event_type,customer_id\n2024-01-01,email,click,cust_001", "text/csv")},
                data={"model_type": "linear"}
            )
            results.append((response.status_code, time.time() - start_time))
        
        # Make 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all requests within reasonable time
        assert total_time < 30.0  # All requests within 30 seconds
        assert len(results) == 10
        
        # Most requests should succeed
        success_count = sum(1 for status, _ in results if status == 200)
        assert success_count >= 8  # At least 80% should succeed


@pytest.mark.integration
class TestAPIErrorRecovery:
    """Test API error recovery and resilience."""
    
    def test_graceful_degradation_on_error(self, client: TestClient):
        """Test API graceful degradation on internal errors."""
        # This test would require mocking internal components to simulate errors
        # For now, we'll test with malformed data that might cause processing errors
        
        malformed_csv = "timestamp,channel,event_type,customer_id\ninvalid_data"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("malformed.csv", malformed_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should handle malformed data gracefully
        assert response.status_code in [200, 422]
    
    def test_partial_data_processing(self, client: TestClient):
        """Test API handling of partial data processing."""
        partial_csv = """timestamp,channel,event_type,customer_id
2024-01-01 10:00:00,email,click,cust_001
2024-01-01 11:00:00,social,conversion,cust_001
invalid_row_data
2024-01-01 12:00:00,paid_search,view,cust_002"""
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("partial.csv", partial_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should process valid rows and handle invalid ones gracefully
        assert response.status_code in [200, 422]
    
    def test_timeout_handling(self, client: TestClient):
        """Test API timeout handling."""
        # Create a dataset that might take longer to process
        timeout_csv = "timestamp,channel,event_type,customer_id\n"
        for i in range(1000):  # 1k rows
            timeout_csv += f"2024-01-01 10:00:00,email,click,cust_{i}\n"
        
        response = client.post(
            "/attribution/analyze",
            files={"file": ("timeout.csv", timeout_csv, "text/csv")},
            data={"model_type": "linear"}
        )
        
        # Should either complete or timeout gracefully
        assert response.status_code in [200, 408, 422]  # 408 = Request Timeout
