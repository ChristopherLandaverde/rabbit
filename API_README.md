# Multi-Touch Attribution API

A FastAPI-based service for analyzing marketing touchpoint data and applying attribution models.

## Features

- **Multiple Attribution Models**: Linear, Time Decay, First Touch, Last Touch, Position-Based
- **Identity Resolution**: Automatic customer journey linking
- **Data Validation**: Comprehensive data quality checks
- **Confidence Scoring**: Statistical confidence for attribution results
- **Business Insights**: Automated insights and recommendations
- **File Format Support**: CSV, JSON, and Parquet files

## Quick Start

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

## API Endpoints

### Health Check
- `GET /health` - Check API health status

### Attribution Analysis
- `POST /attribution/analyze` - Analyze attribution from uploaded data

## Example Usage

Upload a CSV file with touchpoint data:

```bash
curl -X POST "http://localhost:8000/attribution/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_data.csv" \
  -F "model_type=linear"
```

## Data Format

Your CSV file should include these columns:

- `timestamp`: When the touchpoint occurred (ISO format)
- `channel`: Marketing channel (e.g., email, social, paid_search)
- `event_type`: Type of event (view, click, conversion, purchase, signup)
- `customer_id`: Customer identifier (optional)
- `session_id`: Session identifier (optional)
- `email`: Customer email (optional)
- `conversion_value`: Value of conversion (optional)

## Attribution Models

- **linear**: Equal credit to all touchpoints
- **time_decay**: More credit to recent touchpoints
- **first_touch**: All credit to first touchpoint
- **last_touch**: All credit to last touchpoint
- **position_based**: Weighted credit by position (40% first, 40% last, 20% middle)

## Configuration

Create a `.env` file to customize settings:

```env
DEBUG=true
MAX_FILE_SIZE_MB=100
DEFAULT_TIME_DECAY_HALF_LIFE_DAYS=7.0
```
