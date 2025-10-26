# Rabbit - Multi-Touch Attribution Platform

A comprehensive full-stack platform for analyzing marketing touchpoint data and applying attribution models to transform raw customer journey data into actionable insights. Features a modern React frontend with state management and a robust FastAPI backend with confidence scoring.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Frontend Application](#frontend-application)
- [State Management](#state-management)
- [Docker Setup](#docker-setup)
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

### 🎯 **Core Attribution Engine**
- **Multiple Attribution Models**: Linear, Time Decay, First Touch, Last Touch, Position-Based
- **Identity Resolution**: Automatic customer journey linking with adaptive method selection
- **Data Validation**: Comprehensive data quality checks and validation
- **Confidence Scoring**: Statistical confidence for attribution results
- **Business Insights**: Automated insights and recommendations
- **File Format Support**: CSV, JSON, and Parquet files

### 🖥️ **Modern Frontend Application**
- **React + TypeScript**: Modern, type-safe frontend with Material-UI components
- **Interactive Dashboard**: Upload files, configure analysis, view results with charts and tables
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Feedback**: Progress indicators and error handling

### 💾 **Advanced State Management**
- **Auto-save**: Your work is automatically saved as you go
- **Session Recovery**: Never lose your progress - resume interrupted workflows
- **Analysis History**: Access and reload your last 10 analyses
- **User Preferences**: Customizable settings that persist between sessions
- **Smart Recovery**: Automatic detection and recovery of previous work

### 🐳 **Docker Ready**
- **One-Command Deploy**: Complete platform with `docker-compose up`
- **Development Mode**: Hot reload for frontend and backend development
- **Production Optimized**: Nginx-served frontend with optimized builds
- **Scalable Architecture**: Easy to scale and deploy in any environment

### 🔒 **Production Ready**
- **Security**: API key authentication and rate limiting
- **Monitoring**: Comprehensive logging and health checks
- **Performance**: Optimized for large datasets and concurrent users
- **Error Handling**: Graceful error handling and user feedback

## 🚀 Current Status

### ✅ **Phase 1-4: Complete (100%)**
- **Core Application**: Complete FastAPI application with all attribution models
- **Testing Infrastructure**: 224+ tests, all passing with comprehensive coverage
- **Data Models**: Pydantic models for all data structures
- **Identity Resolution**: Customer journey linking with adaptive method selection
- **Attribution Models**: All 5 models implemented and mathematically validated
- **Data Validation**: Comprehensive validation with quality metrics
- **Configuration**: Environment-based configuration management
- **Security**: API key authentication and rate limiting
- **Monitoring**: Comprehensive logging and performance monitoring

### ✅ **Phase 5: Frontend & State Management (100%)**
- **React Frontend**: Modern TypeScript application with Material-UI
- **Interactive Dashboard**: File upload, analysis configuration, results visualization
- **State Management**: Auto-save, session recovery, analysis history
- **Docker Setup**: Complete containerization for development and production
- **Responsive Design**: Mobile-friendly interface

### 🎯 **Production Ready**
- **Docker Deployment**: One-command deployment with `docker-compose up`
- **State Persistence**: Never lose your work with smart recovery
- **Scalable Architecture**: Ready for production deployment
- **Comprehensive Testing**: 224+ tests covering all functionality

## Project Structure

```
project-root/
├── frontend/                    # React TypeScript Frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── AttributionChart.tsx
│   │   │   ├── AttributionTable.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ModelSelector.tsx
│   │   │   ├── StateRecovery.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/              # Custom React hooks
│   │   │   ├── useAppState.ts
│   │   │   └── useSessionRecovery.ts
│   │   ├── services/           # API services
│   │   ├── types/              # TypeScript types
│   │   └── utils/              # State management utilities
│   ├── Dockerfile              # Production frontend container
│   ├── Dockerfile.dev          # Development frontend container
│   └── nginx.conf              # Nginx configuration
├── src/                        # FastAPI Backend
│   ├── api/routes/             # FastAPI route handlers
│   ├── core/attribution/       # Attribution model implementations
│   ├── core/identity/          # Identity resolution logic
│   ├── core/validation/        # Data validation
│   ├── models/                 # Pydantic schemas
│   ├── utils/                  # Utility functions
│   └── config/                 # Configuration management
├── docs/                       # Comprehensive documentation
├── tests/                      # Test suite (224+ tests)
├── scripts/                    # Build/deployment scripts
├── docker-compose.yml          # Production Docker setup
├── docker-compose.override.yml # Development Docker setup
├── requirements.txt            # Python dependencies
└── run.py                      # Application entry point
```

## Quick Start

### 🐳 **Docker (Recommended)**

**One-Command Setup:**
```bash
# Clone and start the complete platform
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
docker-compose up --build
```

**Access the Application:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Development Mode (with hot reload):**
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build
```
- **Frontend (dev)**: http://localhost:5173
- **Backend API**: http://localhost:8000

### 🛠️ **Manual Setup**

**Prerequisites:**
- Python 3.8+
- Node.js 18+
- pip & npm

**Backend Setup:**
```bash
# Clone repository
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit

# Set up Python environment
./setup_venv.sh
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python3 run.py
```

**Frontend Setup:**
```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Access the Application:**
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

## Frontend Application

### 🎨 **Modern React Interface**

The frontend is a modern React TypeScript application with Material-UI components that provides an intuitive interface for attribution analysis.

**Key Features:**
- **File Upload**: Drag-and-drop file upload with validation
- **Model Selection**: Interactive model configuration
- **Results Visualization**: Charts, tables, and KPI cards
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Feedback**: Progress indicators and error handling

**Components:**
- `AttributionChart.tsx` - Interactive pie charts for attribution results
- `AttributionTable.tsx` - Detailed tables with KPI cards
- `FileUpload.tsx` - Drag-and-drop file upload with validation
- `ModelSelector.tsx` - Attribution model selection interface
- `StateRecovery.tsx` - Session recovery dialog
- `Settings.tsx` - User preferences and configuration

### 🚀 **Getting Started with Frontend**

**Development:**
```bash
cd frontend
npm install
npm run dev
```

**Production Build:**
```bash
cd frontend
npm run build
npm run preview
```

## State Management

### 💾 **Never Lose Your Work**

The application features comprehensive state management that ensures you never lose your progress.

**Auto-Save Features:**
- **Work Progress**: Automatically saves as you work
- **Analysis Results**: Completed analyses saved to history
- **User Preferences**: Settings persist between sessions
- **Session Recovery**: Resume interrupted workflows

**Recovery Options:**
- **Current Session**: Continue where you left off
- **Previous Results**: View your last analysis
- **Analysis History**: Access and reload previous analyses
- **Fresh Start**: Clear all data when needed

**How It Works:**
1. **Upload a file** and start analysis
2. **Refresh the page** → Recovery dialog appears
3. **Choose recovery option** → Continue your work
4. **Complete analysis** → Automatically saved to history
5. **Use History button** → Load any previous analysis

**Storage:**
- **Browser localStorage**: Persistent data (preferences, history)
- **Browser sessionStorage**: Temporary session data
- **Automatic cleanup**: Old session data expires after 1 hour

## Docker Setup

### 🐳 **Complete Containerization**

The entire platform is Dockerized for easy deployment and development.

**Production Mode:**
```bash
# Start all services
docker-compose up --build

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Redis: localhost:6379
```

**Development Mode:**
```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

# Access services
# Frontend (dev): http://localhost:5173
# Backend: http://localhost:8000
```

**Services Included:**
- **attribution-frontend**: React app with Nginx (production) or Vite (development)
- **attribution-api**: FastAPI backend with Redis caching
- **redis**: Session storage and rate limiting
- **nginx**: Load balancer and reverse proxy (optional)

**Docker Features:**
- **State Persistence**: Browser storage works across container restarts
- **Hot Reload**: Development mode with live code updates
- **Health Checks**: Automatic service health monitoring
- **Scalable**: Easy to scale and deploy

**Quick Test:**
```bash
# Run the test script
./test-docker-setup.sh
```

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

**All tests are passing!** The project includes a comprehensive test suite with **224+ tests** covering:

- **Attribution Models** (14 tests) - All 5 attribution models with mathematical validation
- **Data Validation** (15 tests) - Edge cases, error handling, and quality metrics  
- **Identity Resolution** (13 tests) - Customer journey linking and method selection
- **API Endpoints** (50+ tests) - Complete API contract testing
- **Integration Tests** (30+ tests) - End-to-end workflow testing
- **Performance Tests** (20+ tests) - Benchmarking and optimization
- **Security Tests** (15+ tests) - Authentication and authorization
- **Frontend Tests** (50+ tests) - Component and state management testing

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
======================== 224 passed, 8 warnings in 15.2s ========================
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

### 🐳 **Docker (Recommended)**

**Production Deployment:**
```bash
# Clone and deploy
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
docker-compose up --build -d

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**Development Deployment:**
```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

# Access the application
# Frontend (dev): http://localhost:5173
# Backend: http://localhost:8000
```

**Docker Services:**
- **attribution-frontend**: React app with Nginx
- **attribution-api**: FastAPI backend with Redis
- **redis**: Session storage and caching
- **nginx**: Load balancer (optional)

### 🛠️ **Manual Deployment**

**Backend:**
```bash
# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend
python3 run.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run build
# Serve with nginx or any static file server
```

### 🌐 **Environment Variables**

**Production:**
```bash
export DEBUG=false
export LOG_LEVEL=INFO
export MAX_FILE_SIZE_MB=100
export MAX_CONCURRENT_REQUESTS=10
export VITE_API_URL=https://your-api-domain.com
```

**Docker:**
```yaml
environment:
  - NODE_ENV=production
  - VITE_API_URL=http://localhost:8000
  - REDIS_HOST=redis
  - REDIS_PORT=6379
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

### 📚 **Core Documentation**
- **[API Specification](docs/api/specification.md)** - OpenAPI 3.0.3 specification
- **[Architecture](docs/technical/architecture.md)** - System design and patterns
- **[Testing Strategy](docs/technical/testing-strategy.md)** - Testing approach
- **[Implementation Guide](docs/development/implementation_guide.md)** - Build instructions

### 🎯 **Frontend & State Management**
- **[State Management Guide](frontend/STATE_MANAGEMENT.md)** - Complete state persistence guide
- **[Docker Setup Guide](DOCKER_SETUP.md)** - Docker deployment and development
- **[Frontend Demo](frontend/demo-state-management.md)** - Testing state management features

### 🚀 **Quick Start Guides**
- **[Quick Start Frontend](QUICK_START_FRONTEND.md)** - Frontend development setup
- **[Docker Quick Start](README_DOCKER.md)** - Docker deployment guide
- **[Virtual Environment Setup](VIRTUAL_ENV_SETUP.md)** - Python environment troubleshooting

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

## 🎉 **What's New in This Release**

### ✨ **Major Features Added**

**🖥️ Complete Frontend Application**
- Modern React TypeScript interface with Material-UI
- Interactive file upload and analysis configuration
- Real-time results visualization with charts and tables
- Responsive design for all devices

**💾 Advanced State Management**
- Auto-save functionality - never lose your work
- Session recovery for interrupted workflows
- Analysis history with one-click loading
- User preferences that persist between sessions

**🐳 Full Docker Support**
- One-command deployment with `docker-compose up`
- Development mode with hot reload
- Production-optimized containers
- Complete platform containerization

**🔧 Enhanced Developer Experience**
- Comprehensive testing suite (224+ tests)
- Detailed documentation and guides
- Easy setup and deployment
- Professional error handling and logging

### 🚀 **Ready for Production**

This release transforms Rabbit from a backend API into a complete, production-ready attribution platform. Whether you're a developer looking to integrate attribution analysis or a marketing team needing a user-friendly interface, Rabbit now provides everything you need.

**Get Started in 30 Seconds:**
```bash
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
docker-compose up --build
# Open http://localhost:3000
```

---

**Built with ❤️ for marketing analytics teams**

For questions or support, please open an issue on GitHub.