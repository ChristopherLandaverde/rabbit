"""Unit tests for identity resolution."""

import pytest
import pandas as pd
from src.core.identity.resolver import IdentityResolver, select_linking_method
from src.models.enums import LinkingMethod
from tests.fixtures.data import sample_touchpoint_data


@pytest.mark.unit
class TestLinkingMethodSelection:
    """Test automatic linking method selection."""
    
    def test_select_customer_id_method(self):
        """Test selection of customer_id method when data is high quality."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'customer_id': ['cust_001', 'cust_002']  # 100% complete
        })
        
        method = select_linking_method(df)
        assert method == LinkingMethod.CUSTOMER_ID
    
    def test_select_customer_id_method_partial(self):
        """Test selection when customer_id has some missing values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', 'cust_002', None]  # 66% complete
        })
        
        method = select_linking_method(df)
        # With 66% completion, should fall back to aggregate
        assert method == LinkingMethod.AGGREGATE
    
    def test_select_session_email_method(self):
        """Test selection of session_email method when both columns exist."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'session_id': ['sess_001', 'sess_002'],
            'email': ['user1@example.com', 'user2@example.com']
        })
        
        method = select_linking_method(df)
        assert method == LinkingMethod.SESSION_EMAIL
    
    def test_select_email_only_method(self):
        """Test selection of email_only method when only email exists."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion'],
            'email': ['user1@example.com', 'user2@example.com']
        })
        
        method = select_linking_method(df)
        assert method == LinkingMethod.EMAIL_ONLY
    
    def test_select_aggregate_method(self):
        """Test selection of aggregate method when no identity columns exist."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'channel': ['email', 'social'],
            'event_type': ['click', 'conversion']
        })
        
        method = select_linking_method(df)
        assert method == LinkingMethod.AGGREGATE
    
    def test_select_method_customer_id_low_quality(self):
        """Test that customer_id method is not selected when quality is low."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'channel': ['email', 'social', 'paid_search', 'organic'],
            'event_type': ['click', 'conversion', 'view', 'click'],
            'customer_id': ['cust_001', None, None, None],  # 25% complete (below 80% threshold)
            'session_id': ['sess_001', 'sess_002', 'sess_003', 'sess_004'],
            'email': ['user1@example.com', 'user2@example.com', 'user3@example.com', 'user4@example.com']
        })
        
        method = select_linking_method(df)
        assert method == LinkingMethod.SESSION_EMAIL


@pytest.mark.unit
class TestIdentityResolver:
    """Test identity resolution logic."""
    
    def test_resolve_by_customer_id(self, sample_touchpoint_data):
        """Test identity resolution using customer_id."""
        resolver = IdentityResolver(LinkingMethod.CUSTOMER_ID)
        identity_map = resolver.resolve_identities(sample_touchpoint_data)
        
        # Should have 3 unique customers
        assert len(identity_map) == 3
        assert 'cust_001' in identity_map
        assert 'cust_002' in identity_map
        assert 'cust_003' in identity_map
        
        # Check that each customer has correct number of touchpoints
        assert len(identity_map['cust_001']) == 4  # 4 touchpoints
        assert len(identity_map['cust_002']) == 3  # 3 touchpoints
        assert len(identity_map['cust_003']) == 3  # 3 touchpoints
    
    def test_resolve_by_customer_id_with_missing_values(self):
        """Test identity resolution with missing customer_id values."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', None, 'cust_002']
        })
        
        resolver = IdentityResolver(LinkingMethod.CUSTOMER_ID)
        identity_map = resolver.resolve_identities(df)
        
        # Should only have 2 customers (excluding None values)
        assert len(identity_map) == 2
        assert 'cust_001' in identity_map
        assert 'cust_002' in identity_map
        assert len(identity_map['cust_001']) == 1
        assert len(identity_map['cust_002']) == 1
    
    def test_resolve_by_session_email(self):
        """Test identity resolution using session_id and email combination."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'session_id': ['sess_001', 'sess_002', 'sess_003'],
            'email': ['user1@example.com', 'user1@example.com', 'user2@example.com']
        })
        
        resolver = IdentityResolver(LinkingMethod.SESSION_EMAIL)
        identity_map = resolver.resolve_identities(df)
        
        # Should have 3 unique combinations
        assert len(identity_map) == 3
        assert 'sess_001:user1@example.com' in identity_map
        assert 'sess_002:user1@example.com' in identity_map
        assert 'sess_003:user2@example.com' in identity_map
    
    def test_resolve_by_email_only(self):
        """Test identity resolution using email only."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'email': ['user1@example.com', 'user1@example.com', 'user2@example.com']
        })
        
        resolver = IdentityResolver(LinkingMethod.EMAIL_ONLY)
        identity_map = resolver.resolve_identities(df)
        
        # Should have 2 unique emails
        assert len(identity_map) == 2
        assert 'user1@example.com' in identity_map
        assert 'user2@example.com' in identity_map
        assert len(identity_map['user1@example.com']) == 2
        assert len(identity_map['user2@example.com']) == 1
    
    def test_resolve_aggregate(self, sample_touchpoint_data):
        """Test aggregate identity resolution (no linking)."""
        resolver = IdentityResolver(LinkingMethod.AGGREGATE)
        identity_map = resolver.resolve_identities(sample_touchpoint_data)
        
        # Should have single aggregate identity with all rows
        assert len(identity_map) == 1
        assert 'aggregate' in identity_map
        assert len(identity_map['aggregate']) == len(sample_touchpoint_data)
    
    def test_resolve_with_nan_values(self):
        """Test identity resolution handles NaN values correctly."""
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'channel': ['email', 'social', 'paid_search'],
            'event_type': ['click', 'conversion', 'view'],
            'customer_id': ['cust_001', pd.NaT, 'cust_002']
        })
        
        resolver = IdentityResolver(LinkingMethod.CUSTOMER_ID)
        identity_map = resolver.resolve_identities(df)
        
        # Should only include non-NaN values
        assert len(identity_map) == 2
        assert 'cust_001' in identity_map
        assert 'cust_002' in identity_map
    
    def test_resolve_empty_dataframe(self):
        """Test identity resolution with empty DataFrame."""
        df = pd.DataFrame()
        
        resolver = IdentityResolver(LinkingMethod.CUSTOMER_ID)
        identity_map = resolver.resolve_identities(df)
        
        assert len(identity_map) == 0
