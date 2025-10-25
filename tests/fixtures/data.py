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


@pytest.fixture
def complex_multi_customer_dataset():
    """Complex dataset with multiple customers and various journey patterns."""
    data = []
    
    # Customer 1: Long journey with multiple touchpoints
    customer_1_touchpoints = [
        {'timestamp': '2024-01-01 09:00:00', 'channel': 'organic', 'event_type': 'view', 'customer_id': 'cust_001', 'session_id': 'sess_001', 'email': 'user1@example.com'},
        {'timestamp': '2024-01-01 10:30:00', 'channel': 'email', 'event_type': 'click', 'customer_id': 'cust_001', 'session_id': 'sess_002', 'email': 'user1@example.com'},
        {'timestamp': '2024-01-01 14:00:00', 'channel': 'social', 'event_type': 'view', 'customer_id': 'cust_001', 'session_id': 'sess_003', 'email': 'user1@example.com'},
        {'timestamp': '2024-01-02 11:00:00', 'channel': 'paid_search', 'event_type': 'click', 'customer_id': 'cust_001', 'session_id': 'sess_004', 'email': 'user1@example.com'},
        {'timestamp': '2024-01-02 15:30:00', 'channel': 'display', 'event_type': 'view', 'customer_id': 'cust_001', 'session_id': 'sess_005', 'email': 'user1@example.com'},
        {'timestamp': '2024-01-03 09:15:00', 'channel': 'email', 'event_type': 'conversion', 'customer_id': 'cust_001', 'session_id': 'sess_006', 'email': 'user1@example.com', 'conversion_value': 150.0}
    ]
    data.extend(customer_1_touchpoints)
    
    # Customer 2: Short journey, first touch conversion
    customer_2_touchpoints = [
        {'timestamp': '2024-01-01 16:00:00', 'channel': 'affiliate', 'event_type': 'conversion', 'customer_id': 'cust_002', 'session_id': 'sess_007', 'email': 'user2@example.com', 'conversion_value': 75.0}
    ]
    data.extend(customer_2_touchpoints)
    
    # Customer 3: Medium journey, last touch conversion
    customer_3_touchpoints = [
        {'timestamp': '2024-01-02 08:00:00', 'channel': 'social', 'event_type': 'view', 'customer_id': 'cust_003', 'session_id': 'sess_008', 'email': 'user3@example.com'},
        {'timestamp': '2024-01-02 12:00:00', 'channel': 'organic', 'event_type': 'click', 'customer_id': 'cust_003', 'session_id': 'sess_009', 'email': 'user3@example.com'},
        {'timestamp': '2024-01-02 18:00:00', 'channel': 'paid_search', 'event_type': 'conversion', 'customer_id': 'cust_003', 'session_id': 'sess_010', 'email': 'user3@example.com', 'conversion_value': 200.0}
    ]
    data.extend(customer_3_touchpoints)
    
    # Customer 4: No conversion journey
    customer_4_touchpoints = [
        {'timestamp': '2024-01-03 10:00:00', 'channel': 'email', 'event_type': 'view', 'customer_id': 'cust_004', 'session_id': 'sess_011', 'email': 'user4@example.com'},
        {'timestamp': '2024-01-03 14:00:00', 'channel': 'social', 'event_type': 'click', 'customer_id': 'cust_004', 'session_id': 'sess_012', 'email': 'user4@example.com'}
    ]
    data.extend(customer_4_touchpoints)
    
    # Customer 5: Multiple conversions
    customer_5_touchpoints = [
        {'timestamp': '2024-01-04 09:00:00', 'channel': 'organic', 'event_type': 'click', 'customer_id': 'cust_005', 'session_id': 'sess_013', 'email': 'user5@example.com'},
        {'timestamp': '2024-01-04 11:00:00', 'channel': 'email', 'event_type': 'conversion', 'customer_id': 'cust_005', 'session_id': 'sess_014', 'email': 'user5@example.com', 'conversion_value': 100.0},
        {'timestamp': '2024-01-05 10:00:00', 'channel': 'paid_search', 'event_type': 'click', 'customer_id': 'cust_005', 'session_id': 'sess_015', 'email': 'user5@example.com'},
        {'timestamp': '2024-01-05 15:00:00', 'channel': 'display', 'event_type': 'conversion', 'customer_id': 'cust_005', 'session_id': 'sess_016', 'email': 'user5@example.com', 'conversion_value': 250.0}
    ]
    data.extend(customer_5_touchpoints)
    
    return pd.DataFrame(data)


@pytest.fixture
def edge_case_dataset():
    """Dataset with various edge cases for testing."""
    data = []
    
    # Edge case 1: Same timestamp for multiple touchpoints
    same_timestamp = '2024-01-01 12:00:00'
    data.extend([
        {'timestamp': same_timestamp, 'channel': 'email', 'event_type': 'click', 'customer_id': 'cust_edge_001', 'session_id': 'sess_edge_001', 'email': 'edge1@example.com'},
        {'timestamp': same_timestamp, 'channel': 'social', 'event_type': 'view', 'customer_id': 'cust_edge_001', 'session_id': 'sess_edge_002', 'email': 'edge1@example.com'},
        {'timestamp': same_timestamp, 'channel': 'paid_search', 'event_type': 'conversion', 'customer_id': 'cust_edge_001', 'session_id': 'sess_edge_003', 'email': 'edge1@example.com', 'conversion_value': 50.0}
    ])
    
    # Edge case 2: Very long customer journey
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    for i in range(20):  # 20 touchpoints
        data.append({
            'timestamp': base_time + timedelta(hours=i),
            'channel': f'channel_{i % 5}',
            'event_type': 'click' if i < 19 else 'conversion',
            'customer_id': 'cust_edge_002',
            'session_id': f'sess_edge_{i+4}',
            'email': 'edge2@example.com',
            'conversion_value': 100.0 if i == 19 else None
        })
    
    # Edge case 3: Zero conversion value
    data.append({
        'timestamp': '2024-01-02 10:00:00',
        'channel': 'email',
        'event_type': 'conversion',
        'customer_id': 'cust_edge_003',
        'session_id': 'sess_edge_024',
        'email': 'edge3@example.com',
        'conversion_value': 0.0
    })
    
    # Edge case 4: Negative conversion value
    data.append({
        'timestamp': '2024-01-02 11:00:00',
        'channel': 'social',
        'event_type': 'conversion',
        'customer_id': 'cust_edge_004',
        'session_id': 'sess_edge_025',
        'email': 'edge4@example.com',
        'conversion_value': -25.0
    })
    
    # Edge case 5: Very high conversion value
    data.append({
        'timestamp': '2024-01-02 12:00:00',
        'channel': 'paid_search',
        'event_type': 'conversion',
        'customer_id': 'cust_edge_005',
        'session_id': 'sess_edge_026',
        'email': 'edge5@example.com',
        'conversion_value': 999999.99
    })
    
    return pd.DataFrame(data)


@pytest.fixture
def international_dataset():
    """Dataset with international characters and various formats."""
    data = []
    
    # International customer data
    international_customers = [
        {'email': 'josé@café.com', 'name': 'José García'},
        {'email': 'maria@españa.es', 'name': 'María López'},
        {'email': 'françois@français.fr', 'name': 'François Dubois'},
        {'email': 'hans@deutschland.de', 'name': 'Hans Müller'},
        {'email': 'yuki@日本.jp', 'name': 'Yuki Tanaka'},
        {'email': 'ahmed@العربية.ae', 'name': 'أحمد محمد'}
    ]
    
    for i, customer in enumerate(international_customers):
        data.append({
            'timestamp': f'2024-01-01 10:{i:02d}:00',
            'channel': f'channel_{i % 3}',
            'event_type': 'conversion',
            'customer_id': f'cust_int_{i:03d}',
            'session_id': f'sess_int_{i:03d}',
            'email': customer['email'],
            'conversion_value': 100.0 + i * 10
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def time_series_dataset():
    """Dataset with time series patterns for testing time decay models."""
    data = []
    
    # Create data over 30 days
    base_date = datetime(2024, 1, 1)
    channels = ['email', 'social', 'paid_search', 'organic', 'display']
    
    for day in range(30):
        for hour in range(0, 24, 6):  # Every 6 hours
            for channel in channels:
                # Create touchpoints with decreasing frequency over time
                if (day + hour) % (7 - day // 5) == 0:  # Decreasing frequency
                    data.append({
                        'timestamp': base_date + timedelta(days=day, hours=hour),
                        'channel': channel,
                        'event_type': 'click' if (day + hour) % 10 != 0 else 'conversion',
                        'customer_id': f'cust_ts_{day % 10}',
                        'session_id': f'sess_ts_{day}_{hour}',
                        'email': f'user{day % 10}@example.com',
                        'conversion_value': 50.0 + day * 2 if (day + hour) % 10 == 0 else None
                    })
    
    return pd.DataFrame(data)


@pytest.fixture
def attribution_ground_truth():
    """Ground truth data for attribution model validation."""
    return {
        'linear_expected': {
            'cust_001': {
                'organic': 1/6, 'email': 2/6, 'social': 1/6, 'paid_search': 1/6, 'display': 1/6
            },
            'cust_002': {
                'affiliate': 1.0
            },
            'cust_003': {
                'social': 1/3, 'organic': 1/3, 'paid_search': 1/3
            },
            'cust_005': {
                'organic': 1/4, 'email': 1/4, 'paid_search': 1/4, 'display': 1/4
            }
        },
        'first_touch_expected': {
            'cust_001': {'organic': 1.0},
            'cust_002': {'affiliate': 1.0},
            'cust_003': {'social': 1.0},
            'cust_005': {'organic': 1.0}
        },
        'last_touch_expected': {
            'cust_001': {'email': 1.0},
            'cust_002': {'affiliate': 1.0},
            'cust_003': {'paid_search': 1.0},
            'cust_005': {'display': 1.0}
        },
        'position_based_expected': {
            'cust_001': {
                'organic': 0.4, 'email': 0.4, 'social': 0.2, 'paid_search': 0.0, 'display': 0.0
            },
            'cust_002': {'affiliate': 1.0},
            'cust_003': {
                'social': 0.4, 'organic': 0.2, 'paid_search': 0.4
            },
            'cust_005': {
                'organic': 0.4, 'email': 0.2, 'paid_search': 0.2, 'display': 0.4
            }
        }
    }


@pytest.fixture
def performance_test_scenarios():
    """Different scenarios for performance testing."""
    scenarios = {}
    
    # Small dataset (1k rows)
    small_data = []
    for i in range(1000):
        small_data.append({
            'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
            'channel': f'channel_{i % 5}',
            'event_type': 'click' if i % 10 != 0 else 'conversion',
            'customer_id': f'cust_{i % 100}',
            'conversion_value': 100.0 if i % 10 == 0 else None
        })
    scenarios['small'] = pd.DataFrame(small_data)
    
    # Medium dataset (10k rows)
    medium_data = []
    for i in range(10000):
        medium_data.append({
            'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
            'channel': f'channel_{i % 10}',
            'event_type': 'click' if i % 10 != 0 else 'conversion',
            'customer_id': f'cust_{i % 1000}',
            'conversion_value': 100.0 if i % 10 == 0 else None
        })
    scenarios['medium'] = pd.DataFrame(medium_data)
    
    # Large dataset (50k rows)
    large_data = []
    for i in range(50000):
        large_data.append({
            'timestamp': f'2024-01-01 10:{i % 60:02d}:00',
            'channel': f'channel_{i % 20}',
            'event_type': 'click' if i % 10 != 0 else 'conversion',
            'customer_id': f'cust_{i % 5000}',
            'conversion_value': 100.0 if i % 10 == 0 else None
        })
    scenarios['large'] = pd.DataFrame(large_data)
    
    return scenarios
