"""Factory for creating attribution models."""

from typing import Optional
from .base import AttributionModel
from .linear import LinearAttributionModel
from .time_decay import TimeDecayAttributionModel
from .first_touch import FirstTouchAttributionModel
from .last_touch import LastTouchAttributionModel
from .position_based import PositionBasedAttributionModel
from ...models.enums import AttributionModelType


class AttributionModelFactory:
    """Factory for creating attribution model instances."""
    
    @staticmethod
    def create_model(
        model_type: AttributionModelType, 
        **kwargs
    ) -> AttributionModel:
        """
        Create an attribution model instance.
        
        Args:
            model_type: Type of attribution model to create
            **kwargs: Additional parameters for model initialization
            
        Returns:
            AttributionModel instance
            
        Raises:
            ValueError: If model_type is not supported
        """
        if model_type == AttributionModelType.LINEAR:
            return LinearAttributionModel()
        elif model_type == AttributionModelType.TIME_DECAY:
            half_life_days = kwargs.get('half_life_days', 7.0)
            return TimeDecayAttributionModel(half_life_days=half_life_days)
        elif model_type == AttributionModelType.FIRST_TOUCH:
            return FirstTouchAttributionModel()
        elif model_type == AttributionModelType.LAST_TOUCH:
            return LastTouchAttributionModel()
        elif model_type == AttributionModelType.POSITION_BASED:
            first_touch_weight = kwargs.get('first_touch_weight', 0.4)
            last_touch_weight = kwargs.get('last_touch_weight', 0.4)
            return PositionBasedAttributionModel(
                first_touch_weight=first_touch_weight,
                last_touch_weight=last_touch_weight
            )
        else:
            raise ValueError(f"Unsupported attribution model type: {model_type}")
