"""Test data fixtures for attribution testing."""

import io
import pandas as pd
from datetime import datetime, timedelta
import pytest


@pytest.fixture
def sample_touchpoint_data():
    """Sample touchpoint data for testing."""
    data = {
        'timestamp': [
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 30, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 13, 0, 0),
            datetime(2024, 1, 2, 9, 0, 0),
            datetime(2024, 1, 2, 10, 30, 0),
            datetime(2024, 1, 2, 11, 0, 0),
            datetime(2024, 1, 3, 14, 0, 0),
            datetime(2024, 1, 3, 15, 0, 0),
            datetime(2024, 1, 3, 16, 0, 0),
        ],
        'channel': [
            'email', 'paid_search', 'social', 'email',
            'organic', 'paid_search', 'email',
            'social', 'email', 'organic'
        ],
        'event_type': [
            'click', 'click', 'view', 'conversion',
            'view', 'click', 'conversion',
            'view', 'click', 'conversion'
        ],
        'customer_id': [
            'cust_001', 'cust_001', 'cust_001', 'cust_001',
            'cust_002', 'cust_002', 'cust_002',
            'cust_003', 'cust_003', 'cust_003'
        ],
        'session_id': [
            'sess_001', 'sess_002', 'sess_003', 'sess_004',
            'sess_005', 'sess_006', 'sess_007',
            'sess_008', 'sess_009', 'sess_010'
        ],
        'email': [
            'user1@example.com', 'user1@example.com', 'user1@example.com', 'user1@example.com',
            'user2@example.com', 'user2@example.com', 'user2@example.com',
            'user3@example.com', 'user3@example.com', 'user3@example.com'
        ],
        'conversion_value': [
            None, None, None, 100.0,
            None, None, 75.0,
            None, None, 50.0
        ]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_csv_file():
    """Sample CSV file content for API testing."""
    csv_content = """timestamp,channel,event_type,customer_id,session_id,email,conversion_value
2024-01-01 10:00:00,email,click,cust_001,sess_001,user1@example.com,
2024-01-01 11:30:00,paid_search,click,cust_001,sess_002,user1@example.com,
2024-01-01 12:00:00,social,view,cust_001,sess_003,user1@example.com,
2024-01-01 13:00:00,email,conversion,cust_001,sess_004,user1@example.com,100.00
2024-01-02 09:00:00,organic,view,cust_002,sess_005,user2@example.com,
2024-01-02 10:30:00,paid_search,click,cust_002,sess_006,user2@example.com,
2024-01-02 11:00:00,email,conversion,cust_002,sess_007,user2@example.com,75.00
2024-01-03 14:00:00,social,view,cust_003,sess_008,user3@example.com,
2024-01-03 15:00:00,email,click,cust_003,sess_009,user3@example.com,
2024-01-03 16:00:00,organic,conversion,cust_003,sess_010,user3@example.com,50.00"""
    
    return io.BytesIO(csv_content.encode('utf-8'))


@pytest.fixture
def ground_truth_linear_attribution():
    """Expected linear attribution results for validation."""
    return {
        'cust_001': {
            'email': 0.5,  # 2 touchpoints out of 4
            'paid_search': 0.25,  # 1 touchpoint out of 4
            'social': 0.25  # 1 touchpoint out of 4
        },
        'cust_002': {
            'organic': 0.333,  # 1 touchpoint out of 3
            'paid_search': 0.333,  # 1 touchpoint out of 3
            'email': 0.333  # 1 touchpoint out of 3
        },
        'cust_003': {
            'social': 0.333,  # 1 touchpoint out of 3
            'email': 0.333,  # 1 touchpoint out of 3
            'organic': 0.333  # 1 touchpoint out of 3
        }
    }


@pytest.fixture
def ground_truth_first_touch_attribution():
    """Expected first touch attribution results for validation."""
    return {
        'cust_001': {'email': 1.0},  # First touchpoint
        'cust_002': {'organic': 1.0},  # First touchpoint
        'cust_003': {'social': 1.0}  # First touchpoint
    }


@pytest.fixture
def ground_truth_last_touch_attribution():
    """Expected last touch attribution results for validation."""
    return {
        'cust_001': {'email': 1.0},  # Last touchpoint
        'cust_002': {'email': 1.0},  # Last touchpoint
        'cust_003': {'organic': 1.0}  # Last touchpoint
    }


@pytest.fixture
def invalid_data_scenarios():
    """Various invalid data scenarios for testing error handling."""
    return {
        'missing_timestamp': pd.DataFrame({
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        }),
        
        'invalid_timestamp': pd.DataFrame({
            'timestamp': ['invalid_date', '2024-01-01'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        }),
        
        'missing_channel': pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-01 11:00:00'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001']
        }),
        
        'invalid_numeric': pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-01 11:00:00'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_001'],
            'conversion_value': ['not_a_number', 100.0]
        })
    }


@pytest.fixture
def large_dataset():
    """Large dataset for performance testing."""
    # Generate 10,000 rows of test data
    import random
    from datetime import datetime, timedelta
    
    channels = ['email', 'social', 'paid_search', 'organic', 'display']
    event_types = ['view', 'click', 'conversion']
    
    data = []
    base_time = datetime(2024, 1, 1)
    
    for i in range(10000):
        customer_id = f"cust_{i % 1000}"  # 1000 unique customers
        data.append({
            'timestamp': base_time + timedelta(hours=i),
            'channel': random.choice(channels),
            'event_type': random.choice(event_types),
            'customer_id': customer_id,
            'session_id': f"sess_{i}",
            'email': f"user{i % 1000}@example.com",
            'conversion_value': random.choice([None, None, None, random.uniform(10, 500)])  # 25% conversions
        })
    
    return pd.DataFrame(data)
