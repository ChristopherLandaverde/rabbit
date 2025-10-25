"""Unit tests for attribution models."""

import pytest
from src.core.attribution.linear import LinearAttributionModel
from src.core.attribution.first_touch import FirstTouchAttributionModel
from src.core.attribution.last_touch import LastTouchAttributionModel
from src.core.attribution.time_decay import TimeDecayAttributionModel
from src.core.attribution.position_based import PositionBasedAttributionModel
from src.core.attribution.factory import AttributionModelFactory
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
    
    def test_time_decay_custom_half_life(self, sample_journey):
        """Test time decay with custom half-life parameter."""
        model = TimeDecayAttributionModel(half_life_days=1.0)  # Very short half-life
        attribution = model.calculate_attribution(sample_journey)
        
        # With very short half-life, last touchpoint should get more credit
        assert attribution['paid_search'] > attribution['email']
        assert attribution['paid_search'] > attribution['social']


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


@pytest.mark.unit
@pytest.mark.algorithm
class TestAttributionModelFactory:
    """Test attribution model factory."""
    
    def test_create_linear_model(self):
        """Test creating linear attribution model."""
        model = AttributionModelFactory.create_model("linear")
        assert isinstance(model, LinearAttributionModel)
    
    def test_create_first_touch_model(self):
        """Test creating first touch attribution model."""
        model = AttributionModelFactory.create_model("first_touch")
        assert isinstance(model, FirstTouchAttributionModel)
    
    def test_create_last_touch_model(self):
        """Test creating last touch attribution model."""
        model = AttributionModelFactory.create_model("last_touch")
        assert isinstance(model, LastTouchAttributionModel)
    
    def test_create_time_decay_model(self):
        """Test creating time decay attribution model."""
        model = AttributionModelFactory.create_model("time_decay")
        assert isinstance(model, TimeDecayAttributionModel)
    
    def test_create_position_based_model(self):
        """Test creating position-based attribution model."""
        model = AttributionModelFactory.create_model("position_based")
        assert isinstance(model, PositionBasedAttributionModel)
    
    def test_create_model_with_parameters(self):
        """Test creating model with custom parameters."""
        model = AttributionModelFactory.create_model(
            "time_decay", 
            half_life_days=14.0
        )
        assert isinstance(model, TimeDecayAttributionModel)
        assert model.half_life_days == 14.0
    
    def test_create_invalid_model_raises_error(self):
        """Test that creating invalid model raises error."""
        with pytest.raises(ValueError, match="Unsupported attribution model type"):
            AttributionModelFactory.create_model("invalid_model")


@pytest.mark.unit
@pytest.mark.algorithm
class TestAttributionModelEdgeCases:
    """Test attribution models with edge cases."""
    
    def test_attribution_with_duplicate_channels(self):
        """Test attribution with multiple touchpoints in same channel."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        # Journey with multiple email touchpoints
        touchpoints = [
            Touchpoint(
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                channel="email",
                event_type=EventType.CLICK,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=datetime(2024, 1, 2, 11, 0, 0),
                channel="email",
                event_type=EventType.VIEW,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=datetime(2024, 1, 3, 12, 0, 0),
                channel="social",
                event_type=EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=100.0
            )
        ]
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=100.0,
            journey_id="duplicate_channels"
        )
        
        # Test linear attribution
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        # Should have 3 touchpoints total, email gets 2/3, social gets 1/3
        assert attribution['email'] == pytest.approx(2.0/3.0, abs=1e-10)
        assert attribution['social'] == pytest.approx(1.0/3.0, abs=1e-10)
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_attribution_with_same_timestamp_touchpoints(self):
        """Test attribution with touchpoints at same timestamp."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        same_time = datetime(2024, 1, 1, 10, 0, 0)
        touchpoints = [
            Touchpoint(
                timestamp=same_time,
                channel="email",
                event_type=EventType.CLICK,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=same_time,
                channel="social",
                event_type=EventType.VIEW,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=same_time,
                channel="paid_search",
                event_type=EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=100.0
            )
        ]
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=100.0,
            journey_id="same_timestamp"
        )
        
        # Test linear attribution
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        # All should get equal credit
        expected_credit = 1.0 / 3.0
        assert attribution['email'] == pytest.approx(expected_credit, abs=1e-10)
        assert attribution['social'] == pytest.approx(expected_credit, abs=1e-10)
        assert attribution['paid_search'] == pytest.approx(expected_credit, abs=1e-10)
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_attribution_with_zero_conversion_value(self):
        """Test attribution with zero conversion value."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        touchpoints = [
            Touchpoint(
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                channel="email",
                event_type=EventType.CLICK,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=datetime(2024, 1, 2, 11, 0, 0),
                channel="social",
                event_type=EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=0.0  # Zero conversion value
            )
        ]
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=0.0,  # Zero revenue
            journey_id="zero_conversion"
        )
        
        # Test that attribution still works with zero conversion value
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        assert attribution['email'] == pytest.approx(0.5, abs=1e-10)
        assert attribution['social'] == pytest.approx(0.5, abs=1e-10)
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_attribution_with_very_long_journey(self):
        """Test attribution with very long customer journey."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime, timedelta
        
        # Create journey with 20 touchpoints
        touchpoints = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        channels = ['email', 'social', 'paid_search', 'organic', 'display']
        
        for i in range(20):
            touchpoints.append(Touchpoint(
                timestamp=base_time + timedelta(hours=i),
                channel=channels[i % len(channels)],
                event_type=EventType.CLICK if i < 19 else EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=100.0 if i == 19 else None
            ))
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=100.0,
            journey_id="long_journey"
        )
        
        # Test linear attribution with long journey
        model = LinearAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        # Each channel should get credit proportional to number of touchpoints
        # email: 4 touchpoints, social: 4, paid_search: 4, organic: 4, display: 4
        expected_credit = 4.0 / 20.0  # 0.2 each
        for channel in channels:
            assert attribution[channel] == pytest.approx(expected_credit, abs=1e-10)
        
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_time_decay_with_very_short_half_life(self):
        """Test time decay with very short half-life."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime, timedelta
        
        # Journey spanning 30 days
        touchpoints = [
            Touchpoint(
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                channel="email",
                event_type=EventType.CLICK,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=datetime(2024, 1, 31, 10, 0, 0),  # 30 days later
                channel="social",
                event_type=EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=100.0
            )
        ]
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=100.0,
            journey_id="long_time_span"
        )
        
        # Very short half-life (1 hour)
        model = TimeDecayAttributionModel(half_life_days=1.0/24.0)  # 1 hour
        attribution = model.calculate_attribution(journey)
        
        # Social (last touchpoint) should get almost all credit
        assert attribution['social'] > 0.99
        assert attribution['email'] < 0.01
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
    
    def test_position_based_with_two_touchpoints(self):
        """Test position-based attribution with exactly two touchpoints."""
        from src.models.touchpoint import CustomerJourney, Touchpoint
        from src.models.enums import EventType
        from datetime import datetime
        
        touchpoints = [
            Touchpoint(
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                channel="email",
                event_type=EventType.CLICK,
                customer_id="cust_001"
            ),
            Touchpoint(
                timestamp=datetime(2024, 1, 2, 11, 0, 0),
                channel="social",
                event_type=EventType.CONVERSION,
                customer_id="cust_001",
                conversion_value=100.0
            )
        ]
        
        journey = CustomerJourney(
            touchpoints=touchpoints,
            total_conversions=1,
            total_revenue=100.0,
            journey_id="two_touchpoints"
        )
        
        model = PositionBasedAttributionModel()
        attribution = model.calculate_attribution(journey)
        
        # With 2 touchpoints, first and last should get 40% each, middle gets 20%
        # But since there's no middle, first and last should split the middle's 20%
        # So: first gets 40% + 10% = 50%, last gets 40% + 10% = 50%
        assert attribution['email'] == pytest.approx(0.5, abs=1e-10)
        assert attribution['social'] == pytest.approx(0.5, abs=1e-10)
        assert sum(attribution.values()) == pytest.approx(1.0, abs=1e-10)
