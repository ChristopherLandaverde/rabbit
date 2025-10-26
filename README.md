# Rabbit - Multi-Touch Attribution Platform

A full-stack platform for analyzing marketing touchpoint data using attribution models. Features a React frontend and FastAPI backend with confidence scoring and business insights.

## Quick Start

### Docker (Recommended)
```bash
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
docker-compose up --build
```
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### Manual Setup
```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 run.py

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

## Features

- **5 Attribution Models**: Linear, Time Decay, First Touch, Last Touch, Position-Based
- **Interactive Frontend**: React dashboard with file upload, model selection, and results visualization
- **State Persistence**: Auto-save, session recovery, and analysis history
- **Docker Support**: One-command deployment for development and production
- **File Support**: CSV, JSON, and Parquet files
- **Confidence Scoring**: Statistical confidence for attribution results

## Data Format

Your CSV file should include these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `timestamp` | ✅ | When the touchpoint occurred |
| `channel` | ✅ | Marketing channel (email, social, etc.) |
| `event_type` | ✅ | Type of event (click, conversion, etc.) |
| `customer_id` | ❌ | Customer identifier |
| `conversion_value` | ❌ | Value of conversion |

**Example:**
```csv
timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 13:00:00,email,conversion,cust_001,100.00
```

## API Usage

**Upload and analyze data:**
```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -F "file=@data.csv" \
  -F "model_type=linear"
```

**Response:**
```json
{
  "results": {
    "total_conversions": 3,
    "channel_attributions": {
      "email": {
        "credit": 0.4,
        "conversions": 1,
        "revenue": 90.0,
        "confidence": 0.85
      }
    }
  }
}
```

## Attribution Models

| Model | Description |
|-------|-------------|
| `linear` | Equal credit to all touchpoints |
| `time_decay` | More credit to recent touchpoints |
| `first_touch` | All credit to first touchpoint |
| `last_touch` | All credit to last touchpoint |
| `position_based` | Weighted by position (40% first, 40% last, 20% middle) |

## Testing

```bash
# Run all tests
python3 scripts/run_tests.py

# Run specific test types
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/performance/   # Performance tests
```

## Development

```bash
# Backend development
python3 run.py

# Frontend development
cd frontend && npm run dev

# Docker development
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

## Documentation

- [State Management Guide](frontend/STATE_MANAGEMENT.md)
- [Docker Setup Guide](DOCKER_SETUP.md)
- [API Documentation](http://localhost:8000/docs)

## License

MIT License - see [LICENSE](LICENSE) file for details.