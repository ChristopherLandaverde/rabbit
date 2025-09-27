```markdown
# Multi-Touch Attribution API - Architecture Documentation

## Project Overview
A flexible API that delivers multi-touch attribution insights from marketing data with adaptive identity resolution, multiple attribution models, and confidence scoring.

## System Architecture

### Core Components
```

┌─────────────────────────────────────────────────────────┐ │ API Gateway Layer │ │ ┌─────────────────┐ ┌─────────────────┐ ┌───────────┐ │ │ │ Health Check │ │ Data Validation│ │ Methods │ │ │ └─────────────────┘ └─────────────────┘ └───────────┘ │ └─────────────────────────────────────────────────────────┘ │ ┌─────────────────────────────────────────────────────────┐ │ Processing Pipeline │ │ │ │ 1. Data Ingestion & Validation │ │ ├── Schema Detection │ │ ├── File Format Support (CSV, JSON, Parquet) │ │ └── Data Quality Assessment │ │ │ │ 2. Identity Resolution │ │ ├── Customer ID Matching │ │ ├── Session-Email Linking │ │ ├── Email-Only Matching │ │ ├── Statistical Modeling │ │ └── Aggregate Analysis │ │ │ │ 3. Journey Reconstruction │ │ ├── Touchpoint Sequencing │ │ ├── Attribution Window Application │ │ └── Customer Journey Mapping │ │ │ │ 4. Attribution Modeling │ │ ├── First-Touch Attribution │ │ ├── Last-Touch Attribution │ │ ├── Linear Attribution │ │ ├── Time-Decay Attribution │ │ └── Position-Based Attribution │ │ │ │ 5. Results & Insights │ │ ├── Confidence Scoring │ │ ├── Business Insights Generation │ │ └── Journey Analysis │ └─────────────────────────────────────────────────────────┘

````

## Technology Stack

### API Framework
- **Framework**: FastAPI (Python 3.8+)
- **API Spec**: OpenAPI 3.0.3
- **Authentication**: API Key (X-API-Key header)
- **File Handling**: Multipart form data for file uploads

### Data Processing
- **Data Formats**: CSV, JSON, Parquet
- **Processing Libraries**: 
  - pandas for data manipulation
  - numpy for numerical operations  
  - scikit-learn for statistical modeling
- **File Size Limits**: Configurable (default: 100MB)

### Attribution Engine
- **Models**: Pluggable attribution model architecture
- **Confidence Scoring**: Bayesian confidence intervals
- **Identity Resolution**: Multi-stage linking algorithm

## Data Models

### Core Entities

#### AttributionRequest
```python
class AttributionRequest:
    file: UploadFile
    model: AttributionModel = "linear"
    attribution_window: int = 30  # days
    linking_method: LinkingMethod = "auto"
    confidence_threshold: float = 0.7
````

#### AttributionResults

python

```python
class AttributionResults:
    channel_attribution: Dict[str, ChannelAttribution]
    summary: AttributionSummary
    journey_analysis: JourneyAnalysis
```

#### ChannelAttribution

python

```python
class ChannelAttribution:
    credit: float  # 0.0 to 1.0
    conversions: int
    revenue: float
    confidence: float  # quality score
```

## Processing Pipeline Details

### 1. Data Validation & Schema Detection

- **Input Validation**: File format, size, basic structure
- **Schema Detection**: Automatic column mapping using heuristics
- **Quality Assessment**: Completeness, consistency, freshness scores
- **Error Handling**: Detailed validation errors with suggestions

### 2. Identity Resolution Strategy

```
auto -> Analyze data quality -> Select optimal method:
├── customer_id: High-confidence customer IDs present
├── session_email: Session tracking + email data available
├── email_only: Only email matching possible
└── aggregate: Statistical modeling when individual tracking impossible
```

### 3. Attribution Model Implementation

- **Modular Design**: Each model as separate class implementing `AttributionModel` interface
- **Credit Distribution**: Configurable logic per model type
- **Time-based Weighting**: Exponential decay for time-decay model
- **Position-based Logic**: Configurable first/last touch weighting

### 4. Confidence Scoring

- **Data Quality Factors**:
    - Record completeness (missing fields)
    - Data consistency (format adherence)
    - Temporal freshness (recency of data)
- **Model Certainty**:
    - Identity resolution confidence
    - Attribution model fit quality
    - Statistical significance

## API Endpoints

### Core Operations

- `POST /attribution/analyze` - Main attribution analysis
- `POST /attribution/validate` - Data validation without processing
- `GET /attribution/methods` - Available models and methods
- `GET /health` - System health check

### Request/Response Flow

```
Client Upload -> Validation -> Processing -> Results
     │              │              │           │
     └── File ──────┼──────────────┼───────────┘
                    │              │
                    └── Errors ────┼── Validation Response
                                   │
                                   └── Attribution Response
```

## Data Quality Framework

### Quality Metrics

- **Completeness**: % of non-null values in required fields
- **Consistency**: Adherence to expected data types and formats
- **Freshness**: Recency relative to current date
- **Uniqueness**: Duplicate detection and handling

### Quality Thresholds

- **High Quality**: >90% completeness, >95% consistency
- **Medium Quality**: 70-90% completeness, 80-95% consistency
- **Low Quality**: <70% completeness, <80% consistency

## Security & Compliance

### Authentication

- API Key authentication via `X-API-Key` header
- Rate limiting per API key
- Request logging for audit trails

### Data Handling

- **File Upload Security**: Type validation, size limits, virus scanning
- **Data Retention**: Configurable retention policies
- **Privacy**: No persistent storage of customer data
- **Encryption**: TLS 1.3 for data in transit

## Performance Considerations

### Scalability

- **Async Processing**: FastAPI async/await for I/O operations
- **Streaming**: Large file processing with chunked reading
- **Caching**: Results caching for duplicate analyses
- **Queue System**: Background processing for large datasets

### Optimization

- **Memory Management**: Efficient pandas operations
- **CPU Utilization**: Parallel processing for independent calculations
- **Storage**: Temporary file cleanup after processing

## Error Handling

### Error Categories

- **400 Bad Request**: Invalid parameters or malformed data
- **413 Payload Too Large**: File size exceeds limits
- **422 Unprocessable Entity**: Data validation failures
- **500 Internal Server Error**: Processing failures

### Error Response Format

json

```json
{
  "error": "validation_error",
  "message": "Data validation failed",
  "details": {
    "field": "customer_id",
    "issue": "missing_required_column"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Development Guidelines

### Code Organization

```
src/
├── api/                    # FastAPI routes and middleware
│   ├── routes/
│   ├── dependencies/
│   └── middleware/
├── core/                   # Business logic
│   ├── attribution/        # Attribution models
│   ├── identity/          # Identity resolution
│   ├── validation/        # Data validation
│   └── insights/          # Business insights
├── models/                # Data models and schemas
├── utils/                 # Utility functions
└── config/                # Configuration management
```

### Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end API testing
- **Performance Tests**: Load testing with various file sizes
- **Data Quality Tests**: Validation logic testing

### Deployment

- **Containerization**: Docker with multi-stage builds
- **Environment Management**: Configuration via environment variables
- **Health Checks**: Comprehensive system health monitoring
- **Logging**: Structured logging with correlation IDs

## Future Enhancements

### Planned Features

- **Real-time Processing**: Streaming data ingestion
- **Advanced Models**: Machine learning attribution models
- **Visualization**: Attribution insights dashboards
- **Integration APIs**: Direct integration with marketing platforms

### Scalability Roadmap

- **Microservices**: Service decomposition for horizontal scaling
- **Message Queues**: Async processing with Redis/RabbitMQ
- **Database Integration**: Persistent storage for historical analysis
- **Multi-tenant**: Support for multiple customer environments

---

_This architecture is designed to be modular, scalable, and maintainable while providing accurate attribution insights with confidence scoring._

```

This architecture document provides Cursor with comprehensive context about your Multi-Touch Attribution API project. It covers the system design, data flow, implementation details, and development guidelines that will help Cursor provide more accurate and contextually relevant code suggestions and assistance.

The document includes visual representations of the system architecture, detailed explanations of the processing pipeline, and clear guidelines for code organization - all formatted to work well with Cursor's context awareness features.
```