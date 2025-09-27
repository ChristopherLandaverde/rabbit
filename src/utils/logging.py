"""Logging configuration."""

import logging
import sys
from ..config import get_settings


def setup_logging():
    """Set up application logging configuration."""
    settings = get_settings()
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Set up basic logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Create logger for the application
    logger = logging.getLogger("attribution_api")
    
    return logger
