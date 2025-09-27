#!/usr/bin/env python3
"""Run the Multi-Touch Attribution API."""

import uvicorn
from src.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
