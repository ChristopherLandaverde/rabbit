"""Enums for the Multi-Touch Attribution API."""

from enum import Enum


class AttributionModelType(str, Enum):
    """Available attribution model types."""
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"


class LinkingMethod(str, Enum):
    """Methods for linking customer touchpoints."""
    CUSTOMER_ID = "customer_id"
    SESSION_EMAIL = "session_email"
    EMAIL_ONLY = "email_only"
    AGGREGATE = "aggregate"


class EventType(str, Enum):
    """Types of marketing events."""
    VIEW = "view"
    CLICK = "click"
    CONVERSION = "conversion"
    PURCHASE = "purchase"
    SIGNUP = "signup"
