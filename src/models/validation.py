"""Validation error models."""

from typing import Optional
from pydantic import BaseModel


class ValidationError(BaseModel):
    """Validation error details."""
    field: str = Field(..., description="Field that failed validation")
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the error")
    value: Optional[str] = Field(None, description="The invalid value that caused the error")
