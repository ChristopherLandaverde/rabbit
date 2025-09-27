"""Identity resolution logic for linking customer touchpoints."""

from .resolver import IdentityResolver, select_linking_method
from .journey_builder import JourneyBuilder

__all__ = [
    "IdentityResolver",
    "select_linking_method", 
    "JourneyBuilder",
]
