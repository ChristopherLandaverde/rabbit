

```markdown
# Multi-Touch Attribution API - Project Rules

## Project Context
You are working on a Multi-Touch Attribution API that analyzes marketing data to provide attribution insights. This is a FastAPI-based Python project that processes marketing touchpoint data and applies various attribution models.

## Core Functionality
- Data ingestion (CSV, JSON, Parquet files)
- Identity resolution using multiple methods
- Attribution modeling (first-touch, last-touch, linear, time-decay, position-based)
- Confidence scoring based on data quality
- Business insights generation

## Key Technical Requirements
- Follow OpenAPI 3.0.3 specification exactly as defined in SPECIFICATION.md
- All responses must include confidence scoring
- Support multiple file formats with proper validation
- Implement proper error handling with detailed error messages
- Use async/await patterns for I/O operations
```

### `.cursor/rules/python-standards.mdc`

markdown

````markdown
# Python Development Standards

## Code Style
- Follow PEP 8 with 88-character line length (Black formatter)
- Use type hints for all function parameters and return values
- Use descriptive variable names, avoid abbreviations
- Prefer explicit over implicit (Zen of Python)

## FastAPI Patterns
- Use dependency injection for shared logic
- Implement proper request/response models with Pydantic
- Use HTTPException for API errors with proper status codes
- Structure routes in separate modules by feature

## Error Handling
- Always include error_code, message, and timestamp in error responses
- Provide helpful suggestions in validation errors
- Use appropriate HTTP status codes (400, 413, 422, 500)
- Log errors with correlation IDs for traceability

## Example Code Patterns

### FastAPI Route Structure:
```python
@router.post("/attribution/analyze", response_model=AttributionResponse)
async def analyze_attribution(
    request: AnalyzeRequest = Depends(),
    background_tasks: BackgroundTasks,
) -> AttributionResponse:
    try:
        # Implementation
        pass
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
````

### Data Model Pattern:

python

```python
class ChannelAttribution(BaseModel):
    credit: float = Field(..., ge=0.0, le=1.0, description="Attribution credit")
    conversions: int = Field(..., ge=0, description="Number of conversions")
    revenue: float = Field(..., ge=0.0, description="Attributed revenue")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
```

````

### `.cursor/rules/data-processing.mdc`
```markdown
# Data Processing Guidelines

## File Handling
- Always validate file formats before processing
- Use streaming for large files to manage memory
- Implement proper cleanup for temporary files
- Support CSV, JSON, and Parquet formats

## Data Validation Patterns
```python
def validate_schema(df: pd.DataFrame) -> ValidationResult:
    """Validate data schema and return detailed results."""
    errors = []
    required_columns = ['timestamp', 'channel', 'customer_identifier']
    
    # Check required columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        errors.append(ValidationError(
            field="columns",
            error_code="missing_required_columns",
            message=f"Missing required columns: {missing_cols}",
            suggestion="Ensure your data includes timestamp, channel, and customer identifier columns"
        ))
    
    return ValidationResult(valid=len(errors) == 0, errors=errors)
````

## Attribution Logic

- Always include confidence scoring in attribution results
- Use adaptive identity resolution based on data quality
- Implement attribution windows as configurable parameters
- Support multiple attribution models through strategy pattern

## Identity Resolution Strategy

python

```python
def select_optimal_linking_method(df: pd.DataFrame) -> LinkingMethod:
    """Auto-select the best linking method based on data quality."""
    if 'customer_id' in df.columns and df['customer_id'].notna().mean() > 0.8:
        return LinkingMethod.CUSTOMER_ID
    elif 'session_id' in df.columns and 'email' in df.columns:
        return LinkingMethod.SESSION_EMAIL
    elif 'email' in df.columns and df['email'].notna().mean() > 0.6:
        return LinkingMethod.EMAIL_ONLY
    else:
        return LinkingMethod.AGGREGATE
```

````

### `.cursor/rules/testing-standards.mdc`
```markdown
# Testing Standards

## Test Structure
- Use pytest for all testing
- Organize tests to mirror src/ directory structure
- Use fixtures for common test data
- Mock external dependencies

## Test Categories
- Unit tests: Individual function testing
- Integration tests: API endpoint testing
- Performance tests: File processing benchmarks
- Data quality tests: Validation logic testing

## Example Test Patterns

### API Test Pattern:
```python
@pytest.mark.asyncio
async def test_analyze_attribution_success(client: AsyncClient, sample_csv_file):
    """Test successful attribution analysis."""
    response = await client.post(
        "/attribution/analyze",
        files={"file": ("test.csv", sample_csv_file, "text/csv")},
        data={"model": "linear", "attribution_window": 30}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "results" in result
    assert "metadata" in result
    assert result["metadata"]["confidence_score"] >= 0.0
````

### Data Processing Test:

python

```python
def test_identity_resolution_customer_id(sample_data_with_customer_id):
    """Test customer ID-based identity resolution."""
    resolver = IdentityResolver()
    journeys = resolver.resolve(sample_data_with_customer_id, LinkingMethod.CUSTOMER_ID)
    
    assert len(journeys) > 0
    assert all(journey.customer_id is not None for journey in journeys)
    assert all(len(journey.touchpoints) > 0 for journey in journeys)
```

````

## Legacy Approach: `.cursorrules` File
```markdown
# Multi-Touch Attribution API - Cursor Rules

You are an expert Python developer working on a Multi-Touch Attribution API built with FastAPI. This system processes marketing data to provide attribution insights with confidence scoring.

## Project Overview
- **Purpose**: Analyze marketing touchpoint data and apply attribution models
- **Tech Stack**: Python 3.8+, FastAPI, pandas, numpy, scikit-learn
- **Data Formats**: CSV, JSON, Parquet file support
- **Attribution Models**: First-touch, last-touch, linear, time-decay, position-based
- **Key Features**: Adaptive identity resolution, confidence scoring, business insights

## Code Standards

### Python Style
- Follow PEP 8 with 88-character line length (Black formatter)
- Use type hints for all functions: `def process_data(df: pd.DataFrame) -> AttributionResult:`
- Prefer explicit imports: `from typing import Dict, List, Optional`
- Use descriptive variable names: `attribution_results` not `attr_res`

### FastAPI Patterns
- Use Pydantic models for all request/response schemas
- Implement proper dependency injection
- Use HTTPException with structured error responses
- Follow async/await patterns for I/O operations

### Error Handling
Always structure errors like this:
```python
raise HTTPException(
    status_code=422,
    detail={
        "error": "validation_error",
        "message": "Detailed error description",
        "details": {"field": "customer_id", "issue": "missing_column"},
        "timestamp": datetime.utcnow().isoformat()
    }
)
````

### Data Processing

- Validate file formats before processing
- Use streaming for large files to manage memory
- Always include confidence scoring in results
- Implement proper cleanup for temporary files

## API Response Structure

All responses must follow the OpenAPI spec in SPECIFICATION.md:

python

```python
class AttributionResponse(BaseModel):
    results: AttributionResults
    metadata: AnalysisMetadata
    insights: Optional[List[BusinessInsight]] = None

class ChannelAttribution(BaseModel):
    credit: float = Field(..., ge=0.0, le=1.0)
    conversions: int = Field(..., ge=0)
    revenue: float = Field(..., ge=0.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
```

## File Structure

```
src/
├── api/routes/          # FastAPI route handlers
├── core/attribution/    # Attribution model implementations
├── core/identity/       # Identity resolution logic
├── core/validation/     # Data validation
├── models/             # Pydantic schemas
├── utils/              # Utility functions
└── config/             # Configuration management
```

## Identity Resolution Logic

Always use this pattern for auto-selection:

python

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

## Attribution Models

Implement all models using strategy pattern:

python

```python
class AttributionModel(ABC):
    @abstractmethod
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        pass

class LinearAttributionModel(AttributionModel):
    def calculate_attribution(self, journey: CustomerJourney) -> Dict[str, float]:
        # Equal credit distribution
        credit_per_touchpoint = 1.0 / len(journey.touchpoints)
        return {tp.channel: credit_per_touchpoint for tp in journey.touchpoints}
```

## Testing Requirements

- Use pytest with async support
- Mock file uploads in tests
- Test all attribution models separately
- Include performance benchmarks
- Test error conditions thoroughly

## Key Principles

1. **Always validate data before processing**
2. **Include confidence scores in all results**
3. **Use proper HTTP status codes (400, 413, 422, 500)**
4. **Follow the OpenAPI specification exactly**
5. **Implement proper logging with correlation IDs**
6. **Handle file cleanup and memory management**
7. **Use dependency injection for testability**

When generating code, always consider:

- Data quality and edge cases
- Memory efficiency for large files
- Proper error handling and user feedback
- Confidence scoring methodology
- API specification compliance