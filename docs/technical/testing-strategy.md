## 🎯 **Testing Philosophy**

## Testing Philosophy

The attribution API must deliver mathematically correct results with high confidence. Testing focuses on data accuracy, algorithm correctness, and production reliability rather than just code coverage metrics.

## Test Classification Framework

### Level 1: Algorithm Correctness Tests (30%)

Verify mathematical accuracy of attribution models and identity resolution logic.

### Level 2: Data Processing Tests (25%)

Validate data ingestion, transformation, and quality assessment capabilities.

### Level 3: API Contract Tests (20%)

Ensure API behavior matches specification under normal and error conditions.

### Level 4: System Integration Tests (15%)

Test complete workflows from file upload through result generation.

### Level 5: Performance & Reliability Tests (10%)

Validate system behavior under load and edge conditions.

---

## Detailed Testing Requirements

### Algorithm Correctness Tests

#### Attribution Model Testing

**Linear Attribution Model:**

python

```python
class TestLinearAttributionModel:
    def test_credit_distribution_sums_to_one(self):
        """Verify attribution credits always sum to exactly 1.0"""
        journey = create_test_journey(['google_ads', 'email', 'direct'])
        model = LinearAttributionModel()
        credits = model.calculate_attribution(journey)
        assert abs(sum(credits.values()) - 1.0) < 1e-10

    def test_equal_credit_distribution(self):
        """Verify equal credit across all touchpoints"""
        journey = create_test_journey(['channel_a', 'channel_b', 'channel_c'])
        model = LinearAttributionModel()
        credits = model.calculate_attribution(journey)
        expected_credit = 1.0 / 3
        for credit in credits.values():
            assert abs(credit - expected_credit) < 1e-10

    def test_single_touchpoint_gets_full_credit(self):
        """Single touchpoint should receive 100% credit"""
        journey = create_test_journey(['direct'])
        model = LinearAttributionModel()
        credits = model.calculate_attribution(journey)
        assert credits['direct'] == 1.0
```

**Time Decay Attribution Model:**

python

```python
class TestTimeDecayAttributionModel:
    def test_decay_rate_calculation(self):
        """Verify exponential decay formula correctness"""
        # Journey: Day 1 (google_ads) -> Day 7 (email) -> Day 10 (direct)
        journey = create_timed_journey([
            ('google_ads', datetime(2025, 1, 1)),
            ('email', datetime(2025, 1, 7)), 
            ('direct', datetime(2025, 1, 10))
        ])
        model = TimeDecayAttributionModel(half_life_days=7)
        credits = model.calculate_attribution(journey)
        
        # Verify mathematical relationship
        # More recent touchpoints should have higher credit
        assert credits['direct'] > credits['email'] > credits['google_ads']
        
        # Verify exact decay calculation
        expected_google_credit = 0.125  # 2^(-9/7)
        assert abs(credits['google_ads'] - expected_google_credit) < 1e-3
```

**Position-Based Attribution Model:**

python

```python
class TestPositionBasedAttributionModel:
    def test_40_20_40_distribution(self):
        """Verify 40% first, 40% last, 20% middle distribution"""
        journey = create_test_journey(['first', 'middle1', 'middle2', 'last'])
        model = PositionBasedAttributionModel()
        credits = model.calculate_attribution(journey)
        
        assert credits['first'] == 0.4
        assert credits['last'] == 0.4
        assert credits['middle1'] == 0.1  # 20% split between 2 middle
        assert credits['middle2'] == 0.1

    def test_two_touchpoint_split(self):
        """Two touchpoints should split 50/50"""
        journey = create_test_journey(['first', 'last'])
        model = PositionBasedAttributionModel()
        credits = model.calculate_attribution(journey)
        
        assert credits['first'] == 0.5
        assert credits['last'] == 0.5
```

#### Identity Resolution Testing

**Customer ID Linking:**

python

```python
class TestCustomerIdLinking:
    def test_perfect_customer_id_linking(self):
        """Test linking with complete customer IDs"""
        data = create_test_data([
            {'customer_id': 'cust_001', 'channel': 'google_ads', 'timestamp': '2025-01-01 10:00'},
            {'customer_id': 'cust_001', 'channel': 'email', 'timestamp': '2025-01-01 11:00'},
            {'customer_id': 'cust_001', 'channel': 'direct', 'timestamp': '2025-01-01 12:00', 'event_type': 'conversion'}
        ])
        
        resolver = IdentityResolver()
        journeys = resolver.resolve(data, LinkingMethod.CUSTOMER_ID)
        
        assert len(journeys) == 1
        assert journeys[0].customer_id == 'cust_001'
        assert len(journeys[0].touchpoints) == 3
        assert journeys[0].touchpoints[-1].event_type == 'conversion'

    def test_confidence_scoring_with_missing_ids(self):
        """Test confidence degradation with incomplete customer IDs"""
        data = create_test_data([
            {'customer_id': 'cust_001', 'channel': 'google_ads'},
            {'customer_id': None, 'channel': 'email'},  # Missing ID
            {'customer_id': 'cust_001', 'channel': 'direct', 'event_type': 'conversion'}
        ])
        
        resolver = IdentityResolver()
        result = resolver.resolve(data, LinkingMethod.CUSTOMER_ID)
        
        assert result.confidence_score < 0.9  # Should be lower due to missing data
```

**Email-Based Linking:**

python

```python
class TestEmailLinking:
    def test_email_normalization(self):
        """Test email address normalization and matching"""
        data = create_test_data([
            {'email': 'user@example.com', 'channel': 'google_ads'},
            {'email': 'User@Example.com', 'channel': 'email'},  # Case difference
            {'email': 'user@example.com', 'channel': 'direct', 'event_type': 'conversion'}
        ])
        
        resolver = IdentityResolver()
        journeys = resolver.resolve(data, LinkingMethod.EMAIL_ONLY)
        
        assert len(journeys) == 1
        assert len(journeys[0].touchpoints) == 3

    def test_email_fuzzy_matching(self):
        """Test fuzzy matching for similar email addresses"""
        # This tests the edge case handling for typos in email addresses
        data = create_test_data([
            {'email': 'user@gmail.com', 'channel': 'google_ads'},
            {'email': 'user@gmial.com', 'channel': 'email'},  # Typo
            {'email': 'user@gmail.com', 'channel': 'direct', 'event_type': 'conversion'}
        ])
        
        resolver = IdentityResolver()
        result = resolver.resolve(data, LinkingMethod.EMAIL_ONLY)
        
        # Should link with reduced confidence
        assert result.confidence_score > 0.5
        assert result.confidence_score < 0.9
```

### Data Processing Tests

#### File Format Testing

**CSV Processing:**

python

```python
class TestCSVProcessing:
    def test_various_csv_delimiters(self):
        """Test CSV files with different delimiters"""
        csv_comma = "timestamp,channel,event_type\n2025-01-01,google_ads,click"
        csv_semicolon = "timestamp;channel;event_type\n2025-01-01;google_ads;click"
        csv_tab = "timestamp\tchannel\tevent_type\n2025-01-01\tgoogle_ads\tclick"
        
        processor = DataProcessor()
        
        for csv_content in [csv_comma, csv_semicolon, csv_tab]:
            df = processor.parse_csv(StringIO(csv_content))
            assert len(df) == 1
            assert df.iloc[0]['channel'] == 'google_ads'

    def test_csv_encoding_detection(self):
        """Test automatic encoding detection"""
        # Test UTF-8, Latin-1, and other common encodings
        processor = DataProcessor()
        
        utf8_content = "channel,customer\nemaíl,José"  # UTF-8 accents
        latin1_content = utf8_content.encode('latin-1')
        
        df_utf8 = processor.parse_csv(StringIO(utf8_content))
        df_latin1 = processor.parse_csv(BytesIO(latin1_content))
        
        assert df_utf8.iloc[0]['customer'] == 'José'
        assert df_latin1.iloc[0]['customer'] == 'José'

    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV data"""
        malformed_csv = """timestamp,channel,event_type
        2025-01-01,google_ads,click
        2025-01-02,"unclosed quote,email,click
        2025-01-03,facebook,impression"""
        
        processor = DataProcessor()
        result = processor.parse_csv(StringIO(malformed_csv))
        
        # Should handle gracefully and report issues
        assert result.errors is not None
        assert len(result.valid_rows) >= 2  # At least 2 valid rows
```

**JSON Processing:**

python

```python
class TestJSONProcessing:
    def test_nested_json_flattening(self):
        """Test flattening of nested JSON structures"""
        nested_json = [
            {
                "timestamp": "2025-01-01T10:00:00Z",
                "channel": "google_ads",
                "customer": {
                    "id": "cust_001",
                    "email": "user@example.com"
                },
                "campaign": {
                    "name": "brand_campaign",
                    "type": "search"
                }
            }
        ]
        
        processor = DataProcessor()
        df = processor.parse_json(nested_json)
        
        assert 'customer_id' in df.columns
        assert 'customer_email' in df.columns
        assert 'campaign_name' in df.columns
        assert df.iloc[0]['customer_id'] == 'cust_001'
```

#### Schema Detection Testing

python

```python
class TestSchemaDetection:
    def test_column_type_inference(self):
        """Test automatic column type detection"""
        data = pd.DataFrame({
            'timestamp_col': ['2025-01-01 10:00:00', '2025-01-02 11:00:00'],
            'revenue_col': [99.99, 149.99],
            'channel_col': ['google_ads', 'facebook'],
            'customer_id_col': ['cust_001', 'cust_002']
        })
        
        detector = SchemaDetector()
        schema = detector.detect_schema(data)
        
        assert schema.column_types['timestamp_col'] == 'datetime'
        assert schema.column_types['revenue_col'] == 'numeric'
        assert schema.column_types['channel_col'] == 'categorical'
        assert schema.column_types['customer_id_col'] == 'identifier'

    def test_required_column_detection(self):
        """Test detection of required columns from various naming patterns"""
        test_cases = [
            (['timestamp', 'channel', 'event_type'], True),
            (['date_time', 'source', 'action'], True),  # Alternative names
            (['ts', 'ch', 'event'], True),  # Abbreviated names
            (['timestamp', 'channel'], False),  # Missing event_type
            (['random_col1', 'random_col2'], False)  # No required columns
        ]
        
        detector = SchemaDetector()
        
        for columns, expected_valid in test_cases:
            df = pd.DataFrame({col: [f'test_{i}'] for i, col in enumerate(columns)})
            result = detector.detect_required_columns(df)
            assert result.has_required_columns == expected_valid

    def test_confidence_scoring(self):
        """Test schema detection confidence scoring"""
        # Perfect data should have high confidence
        perfect_data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=100, freq='H'),
            'channel': ['google_ads'] * 100,
            'event_type': ['click'] * 100,
            'customer_id': [f'cust_{i:03d}' for i in range(100)]
        })
        
        # Messy data should have lower confidence
        messy_data = pd.DataFrame({
            'ts': ['2025-01-01', '2025/01/02', 'invalid_date'],
            'ch': ['google_ads', '', 'fb'],
            'evt': ['click', 'impression', None]
        })
        
        detector = SchemaDetector()
        
        perfect_result = detector.detect_schema(perfect_data)
        messy_result = detector.detect_schema(messy_data)
        
        assert perfect_result.confidence > 0.9
        assert messy_result.confidence < 0.7
```

### API Contract Tests

#### Endpoint Testing

python

```python
class TestAttributionEndpoints:
    @pytest.mark.asyncio
    async def test_analyze_endpoint_success(self, client: AsyncClient):
        """Test successful attribution analysis"""
        test_file = create_test_csv_file([
            'timestamp,customer_id,channel,event_type,revenue',
            '2025-01-01 10:00,cust_001,google_ads,click,0',
            '2025-01-01 11:00,cust_001,email,click,0',
            '2025-01-01 12:00,cust_001,direct,conversion,99.99'
        ])
        
        response = await client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", test_file, "text/csv")},
            data={
                "model": "linear",
                "attribution_window": 30,
                "linking_method": "customer_id"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Validate response structure
        assert "results" in result
        assert "metadata" in result
        assert "channel_attribution" in result["results"]
        
        # Validate attribution results
        attribution = result["results"]["channel_attribution"]
        assert len(attribution) == 3  # google_ads, email, direct
        
        # Validate credits sum to 1.0
        total_credit = sum(channel["credit"] for channel in attribution.values())
        assert abs(total_credit - 1.0) < 1e-10

    @pytest.mark.asyncio
    async def test_validation_endpoint(self, client: AsyncClient):
        """Test data validation endpoint"""
        # Valid file
        valid_file = create_test_csv_file([
            'timestamp,customer_id,channel,event_type',
            '2025-01-01 10:00,cust_001,google_ads,click'
        ])
        
        response = await client.post(
            "/attribution/validate",
            files={"file": ("valid.csv", valid_file, "text/csv")},
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] == True
        assert result["schema_detection"]["required_columns_present"] == True

    @pytest.mark.asyncio
    async def test_error_handling(self, client: AsyncClient):
        """Test various error conditions"""
        
        # Test missing API key
        response = await client.post("/attribution/analyze")
        assert response.status_code == 401
        
        # Test invalid file format
        invalid_file = BytesIO(b"invalid binary data")
        response = await client.post(
            "/attribution/analyze",
            files={"file": ("invalid.bin", invalid_file, "application/octet-stream")},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 422
        
        # Test file too large (mock large file)
        with patch('api.dependencies.FILE_SIZE_LIMIT', 1024):  # 1KB limit
            large_file = BytesIO(b"x" * 2048)  # 2KB file
            response = await client.post(
                "/attribution/analyze",
                files={"file": ("large.csv", large_file, "text/csv")},
                headers={"X-API-Key": "test-api-key"}
            )
            assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client: AsyncClient):
        """Test API rate limiting"""
        test_file = create_minimal_test_file()
        
        # Make requests up to the limit
        responses = []
        for _ in range(10):  # Assuming 10 requests per minute limit
            response = await client.post(
                "/attribution/analyze",
                files={"file": ("test.csv", test_file, "text/csv")},
                headers={"X-API-Key": "test-api-key"}
            )
            responses.append(response.status_code)
        
        # Next request should be rate limited
        response = await client.post(
            "/attribution/analyze",
            files={"file": ("test.csv", test_file, "text/csv")},
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 429
```

### Performance & Reliability Tests

#### Load Testing

python

```python
class TestPerformance:
    def test_processing_time_benchmarks(self, benchmark):
        """Benchmark processing times for different file sizes"""
        
        # Small file (1K rows)
        small_data = create_test_dataset(rows=1000)
        result = benchmark(process_attribution_data, small_data, 'linear')
        assert result.processing_time < 2.0  # 2 seconds max
        
        # Medium file (100K rows)
        medium_data = create_test_dataset(rows=100000)
        result = benchmark(process_attribution_data, medium_data, 'linear')
        assert result.processing_time < 30.0  # 30 seconds max
        
    def test_memory_usage_limits(self):
        """Test memory usage stays within bounds"""
        large_data = create_test_dataset(rows=1000000)  # 1M rows
        
        memory_before = get_memory_usage()
        result = process_attribution_data(large_data, 'linear')
        memory_after = get_memory_usage()
        
        memory_increase = memory_after - memory_before
        assert memory_increase < 2048  # 2GB max increase

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent request handling"""
        test_data = create_test_dataset(rows=10000)
        
        # Process 5 requests concurrently
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                process_attribution_data_async(test_data, 'linear')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        assert all(result.success for result in results)
        
        # Processing times should be reasonable even under load
        max_time = max(result.processing_time for result in results)
        assert max_time < 60.0  # 1 minute max under load
```

## Test Data Management

### Ground Truth Datasets

Create validation datasets with known attribution results:

python

```python
def create_ground_truth_dataset():
    """Create dataset with known attribution outcomes"""
    return {
        'linear_test': {
            'data': [
                # Customer journey: Google Ads -> Email -> Direct conversion
                {'customer_id': 'test_001', 'channel': 'google_ads', 'event_type': 'click', 'timestamp': '2025-01-01 10:00'},
                {'customer_id': 'test_001', 'channel': 'email', 'event_type': 'click', 'timestamp': '2025-01-01 11:00'},
                {'customer_id': 'test_001', 'channel': 'direct', 'event_type': 'conversion', 'timestamp': '2025-01-01 12:00', 'revenue': 100.0}
            ],
            'expected_attribution': {
                'google_ads': {'credit': 0.333, 'conversions': 1, 'revenue': 33.33},
                'email': {'credit': 0.333, 'conversions': 1, 'revenue': 33.33},
                'direct': {'credit': 0.333, 'conversions': 1, 'revenue': 33.33}
            }
        }
    }
```

### Synthetic Data Generation

python

```python
class SyntheticDataGenerator:
    def generate_customer_journey(self, 
                                 customer_id: str,
                                 channels: List[str],
                                 start_date: datetime,
                                 conversion_probability: float = 0.3) -> List[Dict]:
        """Generate realistic customer journey data"""
        
        journey = []
        current_time = start_date
        
        for i, channel in enumerate(channels):
            # Add realistic time gaps between touchpoints
            if i > 0:
                gap_hours = random.uniform(1, 48)  # 1-48 hours
                current_time += timedelta(hours=gap_hours)
            
            touchpoint = {
                'customer_id': customer_id,
                'channel': channel,
                'event_type': 'impression' if i == 0 else 'click',
                'timestamp': current_time.isoformat(),
                'revenue': 0.0
            }
            journey.append(touchpoint)
        
        # Add conversion with probability
        if random.random() < conversion_probability:
            conversion_time = current_time + timedelta(hours=random.uniform(1, 24))
            conversion = {
                'customer_id': customer_id,
                'channel': channels[-1],  # Last channel gets conversion
                'event_type': 'conversion',
                'timestamp': conversion_time.isoformat(),
                'revenue': random.uniform(50, 500)
            }
            journey.append(conversion)
        
        return journey
```

## Success Criteria

### Mathematical Accuracy

- Attribution model calculations must be correct within 0.001 precision
- Credit distributions must sum to exactly 1.0 (within floating point precision)
- Time-based calculations must handle timezone and daylight saving transitions

### Data Processing Reliability

- Schema detection accuracy > 90% on real-world marketing data
- File processing success rate > 99% for properly formatted files
- Error messages must be actionable and specific

### Performance Requirements

- Files up to 10MB: Process in < 5 seconds
- Files up to 50MB: Process in < 30 seconds
- Files up to 100MB: Process in < 5 minutes
- Memory usage: < 2GB per request
- Concurrent requests: Support 10 simultaneous uploads

### API Contract Compliance

- All responses must match OpenAPI specification exactly
- Error responses must include proper HTTP status codes and structured error messages
- Authentication and rate limiting must function as documented

## Continuous Testing Pipeline

### Pre-commit Hooks

- Code formatting (Black, isort)
- Type checking (mypy)
- Basic unit tests
- Security scanning (bandit)

### Pull Request Testing

- Full test suite execution
- Performance regression testing
- API contract validation
- Test coverage reporting (minimum 85%)

### Production Deployment Testing

- Canary deployment testing
- Load testing with production-like data
- Rollback procedure validation
- Monitoring and alerting verification

This testing strategy prioritizes accuracy and reliability over simple code coverage metrics, ensuring the attribution API delivers mathematically correct and trustworthy results for business decision-making.