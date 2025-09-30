"""Unit tests for attribution models."""

import pytest
from src.core.attribution.linear import LinearAttributionModel
from src.core.attribution.first_touch import FirstTouchAttributionModel
from src.core.attribution.last_touch import LastTouchAttributionModel
from src.core.attribution.time_decay import TimeDecayAttributionModel
from src.core.attribution.position_based import PositionBasedAttributionModel
from tests.fixtures.app import sample_journey


@pytest.mark.unit
@pytest.mark.algorithm
class TestLinearAttributionModel:
    """Test linear attribution model."""
    
    def test_linear_attribution_equal_distribution(self, sample_journey):
        """Test that linear attribution distributes credit equally."""
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(sample_journey)
        
        # Should have 3 touchpoints, each gets 1/3 credit
        expected_credit = 1.0 / 3.0
        assert attribution['email'] == pytest.approx(expected_credit, abs=1e-10)
        assert attribution['social'] == pytest.approx(expected_credit, abs=1e-10)
        assert attribution['paid_search'] == pytest.approx(expected_credit, abs=1e-10)
        
        # Total credit should equal 1.0
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_linear_attribution_empty_journey(self):
        """Test linear attribution with empty journey."""
        from src.models.touchpoint import CustomerJourney
        
        model = LinearAttributionModel()
        empty_journey = CustomerJourney(
            touchpoints=[],
            total_conversions=0,
            total_revenue=0.0,
            journey_id="empty"
        )
        
        attribution = model.calculate_attribution(empty_journey)
        assert attribution == {}
    
    def test_linear_attribution_single_touchpoint(self):
        """Test linear attribution with single touchpoint."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        single_touchpoint = Touchpoint(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            channel="email",
            event_type=EventType.CONVERSION,
            customer_id="cust_001"
        )
        
        journey = CustomerJourney(
            touchpoints=[single_touchpoint],
            total_conversions=1,
            total_revenue=100.0,
            journey_id="single"
        )
        
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        assert attribution['email'] == 1.0
        assert len(attribution) == 1


@pytest.mark.unit
@pytest.mark.algorithm
class TestFirstTouchAttributionModel:
    """Test first touch attribution model."""
    
    def test_first_touch_attribution(self, sample_journey):
        """Test that first touch gets all credit."""
        model = FirstTouchAttributionModel()
        attribution = model.calculate_attribution(sample_journey)
        
        # First touchpoint is email
        assert attribution['email'] == 1.0
        assert len(attribution) == 1
    
    def test_first_touch_empty_journey(self):
        """Test first touch attribution with empty journey."""
        from src.models.touchpoint import CustomerJourney
        
        model = FirstTouchAttributionModel()
        empty_journey = CustomerJourney(
            touchpoints=[],
            total_conversions=0,
            total_revenue=0.0,
            journey_id="empty"
        )
        
        attribution = model.calculate_attribution(empty_journey)
        assert attribution == {}


@pytest.mark.unit
@pytest.mark.algorithm
class TestLastTouchAttributionModel:
    """Test last touch attribution model."""
    
    def test_last_touch_attribution(self, sample_journey):
        """Test that last touch gets all credit."""
        model = LastTouchAttributionModel()
        attribution = model.calculate_attribution(sample_journey)
        
        # Last touchpoint is paid_search
        assert attribution['paid_search'] == 1.0
        assert len(attribution) == 1
    
    def test_last_touch_empty_journey(self):
        """Test last touch attribution with empty journey."""
        from src.models.touchpoint import CustomerJourney
        
        model = LastTouchAttributionModel()
        empty_journey = CustomerJourney(
            touchpoints=[],
            total_conversions=0,
            total_revenue=0.0,
            journey_id="empty"
        )
        
        attribution = model.calculate_attribution(empty_journey)
        assert attribution == {}


@pytest.mark.unit
@pytest.mark.algorithm
class TestTimeDecayAttributionModel:
    """Test time decay attribution model."""
    
    def test_time_decay_attribution(self, sample_journey):
        """Test that recent touchpoints get more credit."""
        model = TimeDecayAttributionModel(half_life_days=7.0)
        attribution = model.calculate_attribution(sample_journey)
        
        # Total credit should equal 1.0
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
        
        # Last touchpoint (paid_search) should have highest credit
        assert attribution['paid_search'] > attribution['social']
        assert attribution['paid_search'] > attribution['email']
    
    def test_time_decay_empty_journey(self):
        """Test time decay attribution with empty journey."""
        from src.models.touchpoint import CustomerJourney
        
        model = TimeDecayAttributionModel()
        empty_journey = CustomerJourney(
            touchpoints=[],
            total_conversions=0,
            total_revenue=0.0,
            journey_id="empty"
        )
        
        attribution = model.calculate_attribution(empty_journey)
        assert attribution == {}
    
    def test_time_decay_custom_half_life(self):
        """Test time decay with custom half-life parameter."""
        model = TimeDecayAttributionModel(half_life_days=1.0)  # Very short half-life
        attribution = model.calculate_attribution(sample_journey)
        
        # With very short half-life, last touchpoint should get almost all credit
        assert attribution['paid_search'] > 0.9


@pytest.mark.unit
@pytest.mark.algorithm
class TestPositionBasedAttributionModel:
    """Test position-based attribution model."""
    
    def test_position_based_attribution(self, sample_journey):
        """Test position-based attribution with default weights."""
        model = PositionBasedAttributionModel()
        attribution = model.calculate_attribution(sample_journey)
        
        # Total credit should equal 1.0
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
        
        # First and last should have 40% each (0.4), middle should have 20% (0.2)
        assert attribution['email'] == pytest.approx(0.4, abs=1e-10)  # First
        assert attribution['paid_search'] == pytest.approx(0.4, abs=1e-10)  # Last
        assert attribution['social'] == pytest.approx(0.2, abs=1e-10)  # Middle
    
    def test_position_based_custom_weights(self, sample_journey):
        """Test position-based attribution with custom weights."""
        model = PositionBasedAttributionModel(
            first_touch_weight=0.5,
            last_touch_weight=0.5
        )
        attribution = model.calculate_attribution(sample_journey)
        
        # With custom weights, middle should get 0% credit
        assert attribution['email'] == pytest.approx(0.5, abs=1e-10)  # First
        assert attribution['paid_search'] == pytest.approx(0.5, abs=1e-10)  # Last
        assert 'social' not in attribution or attribution['social'] == 0.0
    
    def test_position_based_single_touchpoint(self):
        """Test position-based attribution with single touchpoint."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        single_touchpoint = Touchpoint(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            channel="email",
            event_type=EventType.CONVERSION,
            customer_id="cust_001"
        )
        
        journey = CustomerJourney(
            touchpoints=[single_touchpoint],
            total_conversions=1,
            total_revenue=100.0,
            journey_id="single"
        )
        
        model = PositionBasedAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        assert attribution['email'] == 1.0
        assert len(attribution) == 1
    
    def test_position_based_empty_journey(self):
        """Test position-based attribution with empty journey."""
        from src.models.touchpoint import CustomerJourney
        
        model = PositionBasedAttributionModel()
        empty_journey = CustomerJourney(
            touchpoints=[],
            total_conversions=0,
            total_revenue=0.0,
            journey_id="empty"
        )
        
        attribution = model.calculate_attribution(empty_journey)
        assert attribution == {}
