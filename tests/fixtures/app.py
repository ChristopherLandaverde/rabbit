"""Application fixtures for testing."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from unittest.mock import Mock

from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from unittest.mock import Mock
    settings = Mock()
    settings.max_file_size_mb = 100
    settings.max_concurrent_requests = 10
    settings.max_memory_usage_gb = 2.0
    settings.debug = True
    settings.log_level = "DEBUG"
    return settings


@pytest.fixture
def sample_journey():
    """Sample customer journey for testing."""
    from src.models.touchpoint import CustomerJourney, Touchpoint
    from src.models.enums import EventType
    from datetime import datetime
    
    touchpoints = [
        Touchpoint(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            channel="email",
            event_type=EventType.CLICK,
            customer_id="cust_001",
            session_id="sess_001",
            email="user1@example.com"
        ),
        Touchpoint(
            timestamp=datetime(2024, 1, 2, 11, 0, 0),  # 1 day later
            channel="social",
            event_type=EventType.VIEW,
            customer_id="cust_001",
            session_id="sess_002",
            email="user1@example.com"
        ),
        Touchpoint(
            timestamp=datetime(2024, 1, 3, 12, 0, 0),  # 2 days later
            channel="paid_search",
            event_type=EventType.CONVERSION,
            customer_id="cust_001",
            session_id="sess_003",
            email="user1@example.com",
            conversion_value=100.0
        )
    ]
    
    return CustomerJourney(
        touchpoints=touchpoints,
        total_conversions=1,
        total_revenue=100.0,
        journey_id="cust_001"
    )


@pytest.fixture
def mock_data_quality():
    """Mock data quality metrics for testing."""
    from src.core.validation.validators import DataQuality
    
    return DataQuality(
        completeness=0.95,
        consistency=0.90,
        freshness=0.85
    )
