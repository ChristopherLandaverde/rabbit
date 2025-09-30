# Test Suite Documentation

This directory contains the comprehensive test suite for the Multi-Touch Attribution API.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_attribution_models.py
│   ├── test_data_validation.py
│   └── test_identity_resolution.py
├── integration/             # Integration tests for API endpoints
│   └── test_api_endpoints.py
├── performance/             # Performance and benchmark tests
│   └── test_benchmarks.py
├── fixtures/                # Test data and fixtures
│   ├── data.py
│   └── app.py
└── README.md               # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m performance   # Performance tests only

# Run specific test file
pytest tests/unit/test_attribution_models.py

# Run with verbose output
pytest -v
```

### Using the Test Runner Script

```bash
# Run all tests with coverage and linting
python scripts/run_tests.py --coverage

# Run only unit tests
python scripts/run_tests.py --unit

# Run performance tests only
python scripts/run_tests.py --performance

# Run tests in parallel (faster)
python scripts/run_tests.py --parallel 4

# Skip slow tests
python scripts/run_tests.py --fast
```

## Test Categories

### Unit Tests (`pytest -m unit`)

Test individual components in isolation:

- **Attribution Models**: Test each attribution algorithm for correctness
- **Data Validation**: Test data validation and quality assessment
- **Identity Resolution**: Test customer journey linking logic

### Integration Tests (`pytest -m integration`)

Test API endpoints and component interactions:

- **Health Endpoint**: Test API health check
- **Attribution Endpoint**: Test full attribution analysis workflow
- **Error Handling**: Test API error responses
- **Response Format**: Test API response structure

### Performance Tests (`pytest -m performance`)

Benchmark performance and scalability:

- **Processing Speed**: Test attribution processing time
- **Memory Usage**: Test memory efficiency
- **Concurrent Requests**: Test API under load
- **Scalability**: Test performance with different dataset sizes

## Test Data

### Sample Datasets

- **`sample_touchpoint_data`**: Small dataset for basic testing
- **`large_dataset`**: 10,000 row dataset for performance testing
- **`ground_truth_*`**: Expected results for algorithm validation

### Invalid Data Scenarios

Test error handling with:
- Missing required columns
- Invalid data types
- Malformed timestamps
- Empty datasets

## Test Coverage

Target coverage: **80%+**

Current coverage areas:
- ✅ Attribution model algorithms
- ✅ Data validation logic
- ✅ Identity resolution
- ✅ API endpoints
- ✅ Error handling
- ✅ Performance benchmarks

## Test Configuration

### pytest.ini

Main pytest configuration with:
- Test discovery patterns
- Marker definitions
- Output formatting
- Coverage settings

### conftest.py

Global fixtures and configuration:
- Test environment setup
- Shared fixtures
- Path configuration

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```bash
# CI test command
pytest --cov=src --cov-fail-under=80 --junitxml=test-results.xml
```

## Writing New Tests

### Test Structure

```python
@pytest.mark.unit
class TestMyComponent:
    """Test my component functionality."""
    
    def test_success_case(self, fixture_name):
        """Test successful operation."""
        # Arrange
        # Act
        # Assert
    
    def test_error_case(self):
        """Test error handling."""
        # Test error scenarios
```

### Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow tests (skipped with `--fast`)

### Fixtures

Use existing fixtures or create new ones in `tests/fixtures/`:

```python
@pytest.fixture
def my_test_data():
    """Provide test data for my tests."""
    return {"key": "value"}
```

## Debugging Tests

### Verbose Output

```bash
pytest -vv  # Very verbose
pytest -s   # Show print statements
```

### Debug Specific Test

```bash
pytest tests/unit/test_attribution_models.py::TestLinearAttributionModel::test_linear_attribution_equal_distribution -vv
```

### Coverage Report

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Performance Testing

### Benchmark Results

Performance targets:
- **10MB file**: < 5 seconds
- **100MB file**: < 5 minutes
- **Memory usage**: < 2GB per request
- **Concurrent requests**: 10 simultaneous

### Running Benchmarks

```bash
pytest tests/performance/ --benchmark-only --benchmark-sort=mean
```

## Test Maintenance

### Adding New Tests

1. Choose appropriate test category (unit/integration/performance)
2. Create test file following naming convention
3. Add appropriate markers
4. Use existing fixtures when possible
5. Update this documentation

### Updating Fixtures

When updating test data:
1. Ensure backward compatibility
2. Update related tests if needed
3. Document changes in fixtures

### Performance Regression

Monitor test execution time:
- Unit tests should complete in < 30 seconds
- Integration tests should complete in < 2 minutes
- Performance tests should complete in < 5 minutes
