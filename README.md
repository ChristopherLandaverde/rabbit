# Multi-Touch Attribution API

A comprehensive FastAPI-based service for analyzing marketing touchpoint data and applying attribution models to transform raw customer journey data into actionable insights with confidence scoring.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Data Format](#data-format)
- [Attribution Models](#attribution-models)
- [Configuration](#configuration)
- [Testing](#testing)
- [Development](#development)
- [Deployment](#deployment)
- [Performance](#performance)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Multiple Attribution Models**: Linear, Time Decay, First Touch, Last Touch, Position-Based
- **Identity Resolution**: Automatic customer journey linking with adaptive method selection
- **Data Validation**: Comprehensive data quality checks and validation
- **Confidence Scoring**: Statistical confidence for attribution results
- **Business Insights**: Automated insights and recommendations
- **File Format Support**: CSV, JSON, and Parquet files
- **Production Ready**: Proper error handling, logging, and configuration management

## 🚀 Current Status

### ✅ Completed
- **Core Application**: Complete FastAPI application with all attribution models
- **Testing Infrastructure**: 42 unit tests, all passing with comprehensive coverage
- **Data Models**: Pydantic models for all data structures
- **Identity Resolution**: Customer journey linking with adaptive method selection
- **Attribution Models**: All 5 models implemented and mathematically validated
- **Data Validation**: Comprehensive validation with quality metrics
- **Configuration**: Environment-based configuration management
- **Documentation**: API documentation and project README

### 🔄 In Progress
- **Integration Testing**: API endpoint testing
- **Performance Testing**: Benchmarking and optimization

### 📋 Next Steps
- **Docker Setup**: Containerization for easy deployment
- **CI/CD Pipeline**: GitHub Actions for automated testing
- **Authentication**: API key authentication and rate limiting
- **Monitoring**: Logging, metrics, and performance monitoring
- **Deployment**: Cloud platform setup and deployment

## Project Structure

```
project-root/
├── src/
│   ├── api/routes/          # FastAPI route handlers
│   ├── core/attribution/    # Attribution model implementations
│   ├── core/identity/       # Identity resolution logic
│   ├── core/validation/     # Data validation
│   ├── models/             # Pydantic schemas
│   ├── utils/              # Utility functions
│   └── config/             # Configuration management
├── docs/                   # Comprehensive documentation
├── tests/                  # Test suite
├── scripts/               # Build/deployment scripts
├── requirements.txt       # Python dependencies
└── run.py                 # Application entry point
```

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ChristopherLandaverde/rabbit.git
   cd rabbit
   ```

2. **Quick Installation (One Command)**
   ```bash
   ./quick_start.sh
   ```
   This will set up the virtual environment, install all dependencies, and verify the installation.

3. **Manual Installation (Step by Step)**
   
   **Set up virtual environment**
   
   **Option A: Quick Setup (Recommended)**
   ```bash
   ./setup_venv.sh
   source venv/bin/activate
   ```
   
   **Option B: Manual Setup**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
   
   > **Having permission/sudo issues?** See [VIRTUAL_ENV_SETUP.md](VIRTUAL_ENV_SETUP.md) for detailed troubleshooting.
   
   **Install dependencies**
   ```bash
   # For basic functionality
   pip install -r requirements-minimal.txt
   
   # For full features (includes pandas, numpy, etc.)
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python3 test_setup.py
   ```

5. **Run the application**
   ```bash
   python3 run.py
   ```

6. **Access the API**
   - API: `http://localhost:8000`
   - Interactive Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check endpoint |
| `POST` | `/attribution/analyze` | Analyze attribution from uploaded data |

### Example Usage

**Upload and analyze attribution data:**

```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_data.csv" \
  -F "model_type=linear"
```

**Response format:**
```json
{
  "results": {
    "total_conversions": 3,
    "total_revenue": 225.0,
    "channel_attributions": {
      "email": {
        "credit": 0.4,
        "conversions": 1,
        "revenue": 90.0,
        "confidence": 0.85
      }
    },
    "overall_confidence": 0.82
  },
  "metadata": {
    "model_used": "linear",
    "data_points_analyzed": 10,
    "processing_time_ms": 150
  },
  "insights": [
    {
      "insight_type": "performance",
      "title": "Top Performing Channel",
      "description": "email is your top performing channel with 40.0% attribution credit.",
      "recommendation": "Consider increasing investment in email to maximize ROI."
    }
  ]
}
```

## Data Format

Your data file should include these columns:

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| `timestamp` | ✅ | DateTime | When the touchpoint occurred (ISO format) |
| `channel` | ✅ | String | Marketing channel (e.g., email, social, paid_search) |
| `event_type` | ✅ | String | Type of event (view, click, conversion, purchase, signup) |
| `customer_id` | ❌ | String | Customer identifier |
| `session_id` | ❌ | String | Session identifier |
| `email` | ❌ | String | Customer email |
| `conversion_value` | ❌ | Float | Value of conversion |

### Sample Data

```csv
timestamp,channel,event_type,customer_id,session_id,email,conversion_value
2024-01-01 10:00:00,email,click,cust_001,sess_001,user1@example.com,
2024-01-01 11:30:00,paid_search,click,cust_001,sess_002,user1@example.com,
2024-01-01 13:00:00,email,conversion,cust_001,sess_004,user1@example.com,100.00
```

## Attribution Models

### Available Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `linear` | Equal credit to all touchpoints | Balanced attribution across all channels |
| `time_decay` | More credit to recent touchpoints | Recent touchpoints are more influential |
| `first_touch` | All credit to first touchpoint | Focus on acquisition channels |
| `last_touch` | All credit to last touchpoint | Focus on conversion channels |
| `position_based` | Weighted by position (40% first, 40% last, 20% middle) | Balanced with emphasis on key touchpoints |

### Model Parameters

**Time Decay Model:**
```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -F "file=@data.csv" \
  -F "model_type=time_decay" \
  -F "half_life_days=7.0"
```

**Position-Based Model:**
```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -F "file=@data.csv" \
  -F "model_type=position_based" \
  -F "first_touch_weight=0.4" \
  -F "last_touch_weight=0.4"
```

## Configuration

Create a `.env` file to customize settings:

```env
# Application Settings
DEBUG=false
APP_NAME=Multi-Touch Attribution API
VERSION=1.0.0

# Server Configuration
HOST=0.0.0.0
PORT=8000

# File Processing Limits
MAX_FILE_SIZE_MB=100
MAX_CONCURRENT_REQUESTS=10
MAX_MEMORY_USAGE_GB=2.0

# Attribution Model Defaults
DEFAULT_TIME_DECAY_HALF_LIFE_DAYS=7.0
CONFIDENCE_THRESHOLD=0.7

# Data Quality Thresholds
MINIMUM_DATA_COMPLETENESS=0.8
MINIMUM_DATA_CONSISTENCY=0.7

# Logging
LOG_LEVEL=INFO
```

## Testing

### Current Test Status ✅

**All tests are passing!** The project includes a comprehensive test suite with **42 unit tests** covering:

- **Attribution Models** (14 tests) - All 5 attribution models with mathematical validation
- **Data Validation** (15 tests) - Edge cases, error handling, and quality metrics  
- **Identity Resolution** (13 tests) - Customer journey linking and method selection

### Run Tests

```bash
# Using the test runner script (recommended)
python3 scripts/run_tests.py

# Run specific test types
python3 scripts/run_tests.py --unit          # Unit tests only
python3 scripts/run_tests.py --integration   # Integration tests only
python3 scripts/run_tests.py --performance   # Performance benchmarks

# Direct pytest usage
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/performance/             # Performance tests
pytest --cov=src tests/               # With coverage report
```

### Test Results
```
======================== 42 passed, 4 warnings in 3.89s ========================
✅ Test Suite completed successfully
```

### Test Data

Use the included `test_data.csv` file for testing:

```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -F "file=@test_data.csv" \
  -F "model_type=linear"
```

## Development

### Code Standards

- **Style**: Follow PEP 8 with 88-character line length (Black formatter)
- **Type Hints**: Use type hints for all functions
- **Error Handling**: Implement structured error responses
- **Async Patterns**: Use async/await for I/O operations

### Attribution Model Implementation

All attribution models implement the strategy pattern:

```python
from abc import ABC, abstractmethod
from typing import Dict
from src.models.touchpoint import CustomerJourney

class AttributionModel(ABC):
    @abstractmethod
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        """Calculate attribution credit for each channel."""
        pass
```

### Identity Resolution

Automatic method selection based on data quality:

```python
def select_linking_method(df: pd.DataFrame) -> LinkingMethod:
    """Select the best linking method based on data quality."""
    if 'customer_id' in df.columns and df['customer_id'].notna().mean() > 0.8:
        return LinkingMethod.CUSTOMER_ID
    elif 'session_id' in df.columns and 'email' in df.columns:
        return LinkingMethod.SESSION_EMAIL
    elif 'email' in df.columns:
        return LinkingMethod.EMAIL_ONLY
    else:
        return LinkingMethod.AGGREGATE
```

### Adding New Attribution Models

1. Create a new model class in `src/core/attribution/`
2. Implement the `AttributionModel` interface
3. Add the model type to `AttributionModelType` enum
4. Register the model in `AttributionModelFactory`

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY run.py .

EXPOSE 8000
CMD ["python", "run.py"]
```

### Environment Variables

Set these environment variables in production:

```bash
export DEBUG=false
export LOG_LEVEL=INFO
export MAX_FILE_SIZE_MB=100
export MAX_CONCURRENT_REQUESTS=10
```

## Performance

### Benchmarks

| File Size | Processing Time | Memory Usage |
|-----------|----------------|--------------|
| 10MB | <5 seconds | <500MB |
| 100MB | <5 minutes | <2GB |

### Optimization Tips

- Use Parquet format for large datasets
- Ensure proper indexing on timestamp columns
- Monitor memory usage with large concurrent requests

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[API Specification](docs/api/specification.md)** - OpenAPI 3.0.3 specification
- **[Architecture](docs/technical/architecture.md)** - System design and patterns
- **[Testing Strategy](docs/technical/testing-strategy.md)** - Testing approach
- **[Implementation Guide](docs/development/implementation_guide.md)** - Build instructions

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Make your changes** following the coding standards
4. **Add tests** for new functionality
5. **Submit a pull request**

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install

# Run code formatting
black src/ tests/
isort src/ tests/

# Run linting
flake8 src/ tests/
mypy src/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for marketing analytics teams**

For questions or support, please open an issue on GitHub.