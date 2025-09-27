"""Application settings and configuration."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    app_name: str = Field(default="Multi-Touch Attribution API", description="Application name")
    version: str = Field(default="1.0.0", description="API version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # File Processing Limits
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")
    max_concurrent_requests: int = Field(default=10, description="Maximum concurrent requests")
    max_memory_usage_gb: float = Field(default=2.0, description="Maximum memory usage in GB")
    
    # Processing Timeouts
    processing_timeout_seconds: int = Field(default=300, description="Processing timeout in seconds")
    small_file_timeout_seconds: int = Field(default=5, description="Small file processing timeout")
    
    # Attribution Model Defaults
    default_time_decay_half_life_days: float = Field(default=7.0, description="Default time decay half-life")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold")
    
    # Data Quality Thresholds
    minimum_data_completeness: float = Field(default=0.8, description="Minimum data completeness threshold")
    minimum_data_consistency: float = Field(default=0.7, description="Minimum data consistency threshold")
    
    # Security
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
