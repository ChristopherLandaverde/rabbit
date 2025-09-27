## Overview

This guide provides comprehensive instructions for implementing the Multi-Touch Attribution API in your applications. The API delivers flexible multi-touch attribution insights from marketing data using adaptive identity resolution and multiple attribution models.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Data Requirements](#data-requirements)
4. [API Endpoints](#api-endpoints)
5. [Implementation Examples](#implementation-examples)
6. [Attribution Models](#attribution-models)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

- Valid API key for the Attribution API
- Marketing data in supported format (CSV, JSON, or Parquet)
- Understanding of your customer journey touchpoints

### Base URLs

```
Production:  https://api.attribution.example.com/v1
Staging:     https://staging-api.attribution.example.com/v1
```

### Quick Start

Test API connectivity:

bash

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://api.attribution.example.com/v1/health
```

Expected response:

json

```json
{
  "status": "healthy",
  "timestamp": "2025-09-24T10:30:00Z",
  "version": "1.0.0"
}
```

## Authentication

All requests require an API key in the header:

bash

```bash
X-API-Key: your-api-key-here
```

Example with curl:

bash

```bash
curl -H "X-API-Key: abc123xyz789" \
  -X GET https://api.attribution.example.com/v1/attribution/methods
```

## Data Requirements

### Minimum Required Fields

Your data file must contain these fields:

|Field|Type|Description|Example|
|---|---|---|---|
|`timestamp`|datetime|When the touchpoint occurred|`2025-09-20 14:30:00`|
|`channel`|string|Marketing channel name|`google_ads`, `facebook`, `email`|
|`event_type`|string|Type of interaction|`impression`, `click`, `conversion`|

### Optional Fields (Recommended)

|Field|Type|Description|Benefit|
|---|---|---|---|
|`customer_id`|string|Unique customer identifier|Best linking accuracy|
|`session_id`|string|Session identifier|Good for session-based tracking|
|`email`|string|Customer email|Useful for cross-device tracking|
|`revenue`|decimal|Revenue amount|Required for revenue attribution|
|`campaign`|string|Campaign name|Granular attribution insights|

### Sample Data Format

**CSV Example:**

csv

```csv
timestamp,customer_id,channel,event_type,revenue,campaign
2025-09-20 10:00:00,cust_001,google_ads,impression,0,brand_campaign
2025-09-20 10:15:00,cust_001,google_ads,click,0,brand_campaign
2025-09-20 10:30:00,cust_001,email,click,0,welcome_series
2025-09-20 11:00:00,cust_001,direct,conversion,99.99,
```

**JSON Example:**

json

```json
[
  {
    "timestamp": "2025-09-20T10:00:00Z",
    "customer_id": "cust_001",
    "channel": "google_ads",
    "event_type": "impression",
    "revenue": 0,
    "campaign": "brand_campaign"
  },
  {
    "timestamp": "2025-09-20T10:15:00Z",
    "customer_id": "cust_001",
    "channel": "google_ads",
    "event_type": "click",
    "revenue": 0,
    "campaign": "brand_campaign"
  }
]
```

## API Endpoints

### 1. Validate Data Schema

Before running attribution analysis, validate your data structure:

bash

```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@marketing_data.csv" \
  https://api.attribution.example.com/v1/attribution/validate
```

Response:

json

```json
{
  "valid": true,
  "schema_detection": {
    "detected_columns": {
      "timestamp": "datetime",
      "channel": "string",
      "customer_id": "string"
    },
    "confidence": 0.95,
    "required_columns_present": true
  },
  "recommendations": [
    "Consider adding revenue column for revenue attribution"
  ]
}
```

### 2. Run Attribution Analysis

Main endpoint for attribution analysis:

bash

```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@marketing_data.csv" \
  -F "model=linear" \
  -F "attribution_window=30" \
  -F "linking_method=auto" \
  https://api.attribution.example.com/v1/attribution/analyze
```

### 3. Get Available Methods

Retrieve supported attribution models and linking methods:

bash

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://api.attribution.example.com/v1/attribution/methods
```

## Implementation Examples

### Python Implementation

python

```python
import requests
import json

class AttributionAPI:
    def __init__(self, api_key, base_url="https://api.attribution.example.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def validate_data(self, file_path):
        """Validate data schema before analysis"""
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(
                f"{self.base_url}/attribution/validate",
                headers=self.headers,
                files=files
            )
        return response.json()
    
    def analyze_attribution(self, file_path, model="linear", 
                          attribution_window=30, linking_method="auto"):
        """Run attribution analysis"""
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {
                'model': model,
                'attribution_window': attribution_window,
                'linking_method': linking_method
            }
            response = requests.post(
                f"{self.base_url}/attribution/analyze",
                headers=self.headers,
                files=files,
                data=data
            )
        return response.json()

# Usage example
api = AttributionAPI("your-api-key")

# Validate data first
validation = api.validate_data("marketing_data.csv")
print(f"Data valid: {validation['valid']}")

# Run analysis if data is valid
if validation['valid']:
    results = api.analyze_attribution(
        "marketing_data.csv",
        model="time_decay",
        attribution_window=45
    )
    
    # Extract channel attribution
    for channel, attribution in results['results']['channel_attribution'].items():
        print(f"{channel}: {attribution['credit']:.2%} credit, "
              f"{attribution['conversions']} conversions")
```

### JavaScript/Node.js Implementation

javascript

```javascript
const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

class AttributionAPI {
    constructor(apiKey, baseUrl = 'https://api.attribution.example.com/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = { 'X-API-Key': apiKey };
    }

    async validateData(filePath) {
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));

        const response = await axios.post(
            `${this.baseUrl}/attribution/validate`,
            form,
            { 
                headers: { 
                    ...this.headers, 
                    ...form.getHeaders() 
                }
            }
        );
        return response.data;
    }

    async analyzeAttribution(filePath, options = {}) {
        const {
            model = 'linear',
            attributionWindow = 30,
            linkingMethod = 'auto'
        } = options;

        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        form.append('model', model);
        form.append('attribution_window', attributionWindow.toString());
        form.append('linking_method', linkingMethod);

        const response = await axios.post(
            `${this.baseUrl}/attribution/analyze`,
            form,
            { 
                headers: { 
                    ...this.headers, 
                    ...form.getHeaders() 
                }
            }
        );
        return response.data;
    }
}

// Usage example
async function runAttribution() {
    const api = new AttributionAPI('your-api-key');
    
    try {
        // Validate data
        const validation = await api.validateData('marketing_data.csv');
        console.log('Data validation:', validation.valid);
        
        if (validation.valid) {
            // Run analysis
            const results = await api.analyzeAttribution('marketing_data.csv', {
                model: 'position_based',
                attributionWindow: 60
            });
            
            // Display results
            const channelAttribution = results.results.channel_attribution;
            Object.entries(channelAttribution).forEach(([channel, data]) => {
                console.log(`${channel}: ${(data.credit * 100).toFixed(1)}% credit`);
            });
        }
    } catch (error) {
        console.error('API Error:', error.response?.data || error.message);
    }
}

runAttribution();
```

## Attribution Models

The API supports five attribution models:

### 1. First-Touch Attribution

bash

```bash
-F "model=first_touch"
```

- **Use Case**: Brand awareness campaigns
- **Credit**: 100% to first touchpoint
- **Best For**: Understanding top-of-funnel performance

### 2. Last-Touch Attribution

bash

```bash
-F "model=last_touch"
```

- **Use Case**: Performance marketing optimization
- **Credit**: 100% to last touchpoint before conversion
- **Best For**: Direct response campaigns

### 3. Linear Attribution

bash

```bash
-F "model=linear"
```

- **Use Case**: Balanced view of customer journey
- **Credit**: Equal distribution across all touchpoints
- **Best For**: General attribution analysis

### 4. Time-Decay Attribution

bash

```bash
-F "model=time_decay"
```

- **Use Case**: Recent touchpoints are more important
- **Credit**: Exponential decay, more recent = more credit
- **Best For**: Short sales cycles

### 5. Position-Based Attribution (40/20/40)

bash

```bash
-F "model=position_based"
```

- **Use Case**: Balanced first and last touch importance
- **Credit**: 40% first, 40% last, 20% middle touchpoints
- **Best For**: Complex B2B sales cycles

## Linking Methods

The API uses different methods to connect touchpoints into customer journeys:

### Auto (Recommended)

bash

```bash
-F "linking_method=auto"
```

Automatically selects the best linking method based on available data.

### Customer ID

bash

```bash
-F "linking_method=customer_id"
```

Links touchpoints using customer_id field. Highest accuracy when available.

### Session + Email

bash

```bash
-F "linking_method=session_email"
```

Combines session_id and email for cross-session tracking.

### Email Only

bash

```bash
-F "linking_method=email_only"
```

Links touchpoints using email addresses only.

### Aggregate

bash

```bash
-F "linking_method=aggregate"
```

Statistical modeling when individual identifiers aren't available.

## Error Handling

### Common Error Responses

**400 Bad Request:**

json

```json
{
  "error": "bad_request",
  "message": "Invalid attribution model specified",
  "timestamp": "2025-09-24T10:30:00Z"
}
```

**413 File Too Large:**

json

```json
{
  "error": "file_too_large",
  "message": "File size exceeds 100MB limit",
  "timestamp": "2025-09-24T10:30:00Z"
}
```

**422 Validation Error:**

json

```json
{
  "error": "validation_error",
  "message": "Missing required columns",
  "details": {
    "missing_columns": ["timestamp", "channel"]
  },
  "timestamp": "2025-09-24T10:30:00Z"
}
```

### Error Handling Example

python

```python
def safe_attribution_analysis(api, file_path):
    try:
        # Validate first
        validation = api.validate_data(file_path)
        if not validation['valid']:
            print("Validation errors:")
            for error in validation.get('errors', []):
                print(f"- {error['message']}")
            return None
        
        # Run analysis
        results = api.analyze_attribution(file_path)
        return results
        
    except requests.exceptions.RequestException as e:
        if e.response:
            error_data = e.response.json()
            print(f"API Error: {error_data['message']}")
        else:
            print(f"Network Error: {str(e)}")
        return None
```

## Best Practices

### Data Quality

1. **Clean Your Data**: Remove duplicates and invalid entries before upload
2. **Consistent Timestamps**: Use consistent timezone and format
3. **Standardize Channel Names**: Use consistent naming (e.g., "google_ads" not "Google Ads")
4. **Include Customer IDs**: When possible, include unique customer identifiers

### File Optimization

1. **File Size**: Keep files under 100MB for optimal performance
2. **Format Choice**:
    - CSV: Best for simple tabular data
    - Parquet: Best for large datasets with good compression
    - JSON: Best for nested data structures

### Attribution Window Selection

- **E-commerce**: 30-45 days typical
- **B2B**: 60-90 days for longer sales cycles
- **Mobile Apps**: 7-30 days for shorter cycles
- **High-consideration purchases**: 90+ days

### Model Selection Guidelines

python

```python
def recommend_attribution_model(business_type, sales_cycle_days):
    if business_type == "brand_awareness":
        return "first_touch"
    elif business_type == "performance_marketing":
        return "last_touch"
    elif sales_cycle_days < 30:
        return "time_decay"
    elif sales_cycle_days > 60:
        return "position_based"
    else:
        return "linear"
```

### Rate Limits and Performance

- **Concurrent Requests**: Maximum 5 concurrent requests per API key
- **File Processing**: Large files (>10MB) may take several minutes
- **Caching**: Results are cached for 1 hour for identical requests

### Monitoring and Alerts

python

```python
def monitor_attribution_quality(results):
    metadata = results['metadata']
    
    # Check confidence score
    if metadata['confidence_score'] < 0.7:
        print("WARNING: Low confidence score, consider improving data quality")
    
    # Check data quality metrics
    data_quality = metadata['data_quality']
    if data_quality['completeness'] < 0.8:
        print("WARNING: Low data completeness")
    
    # Check for warnings
    if metadata.get('warnings'):
        print("API Warnings:")
        for warning in metadata['warnings']:
            print(f"- {warning}")
```

## Advanced Usage

### Batch Processing

python

```python
import os
import time

def process_attribution_batch(api, file_directory):
    results = {}
    
    for filename in os.listdir(file_directory):
        if filename.endswith('.csv'):
            print(f"Processing {filename}...")
            
            file_path = os.path.join(file_directory, filename)
            result = api.analyze_attribution(file_path)
            results[filename] = result
            
            # Rate limiting
            time.sleep(1)
    
    return results
```

### Custom Confidence Thresholds

bash

```bash
curl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@marketing_data.csv" \
  -F "model=linear" \
  -F "confidence_threshold=0.8" \
  https://api.attribution.example.com/v1/attribution/analyze
```

### Interpreting Results

python

```python
def interpret_results(results):
    attribution = results['results']['channel_attribution']
    summary = results['results']['summary']
    metadata = results['metadata']
    
    print(f"Analysis Summary:")
    print(f"- Total Conversions: {summary['total_conversions']:,}")
    print(f"- Total Revenue: ${summary['total_revenue']:,.2f}")
    print(f"- Average Journey Length: {summary['average_journey_length']:.1f}")
    print(f"- Confidence Score: {metadata['confidence_score']:.1%}")
    
    print(f"\nChannel Attribution:")
    sorted_channels = sorted(attribution.items(), 
                           key=lambda x: x[1]['credit'], reverse=True)
    
    for channel, data in sorted_channels:
        print(f"  {channel}: {data['credit']:.1%} credit "
              f"({data['conversions']} conversions, "
              f"${data['revenue']:,.2f} revenue)")
```