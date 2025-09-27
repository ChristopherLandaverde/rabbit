# Multi-Touch Attribution API

A comprehensive FastAPI-based service for analyzing marketing touchpoint data and applying attribution models to transform raw customer journey data into actionable insights with confidence scoring.

## 🚀 Features

- **Multiple Attribution Models**: Linear, Time Decay, First Touch, Last Touch, Position-Based
- **Identity Resolution**: Automatic customer journey linking with adaptive method selection
- **Data Validation**: Comprehensive data quality checks and validation
- **Confidence Scoring**: Statistical confidence for attribution results
- **Business Insights**: Automated insights and recommendations
- **File Format Support**: CSV, JSON, and Parquet files
- **Production Ready**: Proper error handling, logging, and configuration management

## 📁 Project Structure

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

## 🏃‍♂️ Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python run.py
```

The API will be available at `http://localhost:8000`

### 3. Test the API

Visit `http://localhost:8000/docs` for the interactive API documentation.

## 📡 API Endpoints

### Health Check
- `GET /health` - Check API health status

### Attribution Analysis
- `POST /attribution/analyze` - Analyze attribution from uploaded data

## 💡 Example Usage

Upload a CSV file with touchpoint data:

```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_data.csv" \
  -F "model_type=linear"
```

## 📊 Data Format

Your CSV file should include these columns:

- `timestamp`: When the touchpoint occurred (ISO format)
- `channel`: Marketing channel (e.g., email, social, paid_search)
- `event_type`: Type of event (view, click, conversion, purchase, signup)
- `customer_id`: Customer identifier (optional)
- `session_id`: Session identifier (optional)
- `email`: Customer email (optional)
- `conversion_value`: Value of conversion (optional)

## 🎯 Attribution Models

- **linear**: Equal credit to all touchpoints
- **time_decay**: More credit to recent touchpoints (configurable half-life)
- **first_touch**: All credit to first touchpoint
- **last_touch**: All credit to last touchpoint
- **position_based**: Weighted credit by position (40% first, 40% last, 20% middle)

## ⚙️ Configuration

Create a `.env` file to customize settings:

```env
DEBUG=true
MAX_FILE_SIZE_MB=100
DEFAULT_TIME_DECAY_HALF_LIFE_DAYS=7.0
LOG_LEVEL=INFO
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[API Specification](docs/api/specification.md)** - OpenAPI 3.0.3 specification
- **[Architecture](docs/technical/architecture.md)** - System design and patterns
- **[Testing Strategy](docs/technical/testing-strategy.md)** - Testing approach
- **[Implementation Guide](docs/development/implementation_guide.md)** - Build instructions

## 🔧 Development

### Code Standards
- Follow PEP 8 with 88-character line length (Black formatter)
- Use type hints for all functions
- Implement proper error handling with structured responses
- Follow async/await patterns for I/O operations

### Attribution Model Implementation
All attribution models implement the strategy pattern:

```python
class AttributionModel(ABC):
    @abstractmethod
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        pass
```

### Identity Resolution
Automatic method selection based on data quality:

```python
def select_linking_method(df: pd.DataFrame) -> LinkingMethod:
    if 'customer_id' in df.columns and df['customer_id'].notna().mean() > 0.8:
        return LinkingMethod.CUSTOMER_ID
    elif 'session_id' in df.columns and 'email' in df.columns:
        return LinkingMethod.SESSION_EMAIL
    elif 'email' in df.columns:
        return LinkingMethod.EMAIL_ONLY
    else:
        return LinkingMethod.AGGREGATE
```

## 🚀 Deployment

The application is production-ready with:

- Proper error handling and logging
- Configuration management
- File size and memory limits
- CORS support
- Health check endpoints

## 📈 Performance Requirements

- Process files up to 10MB in <5 seconds
- Process files up to 100MB in <5 minutes
- Memory usage <2GB per request
- Support 10 concurrent requests per API key

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes following the coding standards
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

This project provides a complete foundation for building a production-ready attribution API that delivers reliable, confidence-scored marketing insights.
