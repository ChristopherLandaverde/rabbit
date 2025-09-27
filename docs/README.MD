The Multi-Touch Attribution API helps marketing teams understand the true impact of their campaigns by analyzing customer touchpoints across channels and applying sophisticated attribution models. The API automatically handles data validation, identity resolution, and provides confidence-scored results for reliable decision-making.


## Visual Progress

### Testing Progress
Phase 1: Foundation    ████████████████████ 100%
Phase 2: Testing       ░░░░░░░░░░░░░░░░░░░░   0%
Phase 3: Integration   ░░░░░░░░░░░░░░░░░░░░   0%
Phase 4: Production    ░░░░░░░░░░░░░░░░░░░░   0%

### Test Categories
Algorithm Tests     ░░░░░░░░░░░░░░░░░░░░  0/15
Data Processing     ░░░░░░░░░░░░░░░░░░░░  0/12
API Contract        ░░░░░░░░░░░░░░░░░░░░  0/8
Performance         ░░░░░░░░░░░░░░░░░░░░  0/5

Key Features

Universal Data Ingestion: Support for CSV, JSON, and Parquet files up to 100MB
Adaptive Identity Resolution: Automatic selection of optimal customer linking methods
Multiple Attribution Models: 5 different approaches (first-touch, last-touch, linear, time-decay, position-based)
Confidence Scoring: Reliability metrics for all attribution results
Business Insights: Actionable recommendations based on analysis
Developer-First Design: Complete OpenAPI 3.0.3 specification

Quick Start
1. Health Check
Test API connectivity:
bashcurl -H "X-API-Key: YOUR_API_KEY" \
  https://api.attribution.example.com/v1/health
2. Validate Your Data
Before analysis, validate your data structure:
bashcurl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@marketing_data.csv" \
  https://api.attribution.example.com/v1/attribution/validate
3. Run Attribution Analysis
Analyze your marketing data:
bashcurl -X POST \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@marketing_data.csv" \
  -F "model=linear" \
  -F "attribution_window=30" \
  https://api.attribution.example.com/v1/attribution/analyze
Data Requirements
Required Fields
FieldTypeDescriptionExampletimestampdatetimeWhen the touchpoint occurred2025-09-20 14:30:00channelstringMarketing channel namegoogle_ads, facebook, emailevent_typestringType of interactionimpression, click, conversion
Optional Fields (Recommended)
FieldTypeDescriptionBenefitcustomer_idstringUnique customer identifierBest linking accuracyemailstringCustomer email addressCross-device attributionrevenuedecimalRevenue amountRevenue attribution analysiscampaignstringCampaign identifierGranular insights
Sample Data Format
csvtimestamp,customer_id,channel,event_type,revenue,campaign
2025-09-20 10:00:00,cust_001,google_ads,impression,0,brand_campaign
2025-09-20 10:15:00,cust_001,google_ads,click,0,brand_campaign
2025-09-20 11:00:00,cust_001,email,click,0,welcome_series
2025-09-20 12:00:00,cust_001,direct,conversion,99.99,
Attribution Models
Linear Attribution (Default)
Equal credit distribution across all touchpoints. Best for balanced journey analysis.
First-Touch Attribution
100% credit to first touchpoint. Ideal for brand awareness campaigns.
Last-Touch Attribution
100% credit to last touchpoint. Perfect for performance marketing optimization.
Time-Decay Attribution
Exponential decay with recent touchpoints receiving more credit. Great for short sales cycles.
Position-Based Attribution
40% first touchpoint, 40% last touchpoint, 20% middle touchpoints. Excellent for complex B2B cycles.
API Endpoints
Core Operations

GET /health - System health check
POST /attribution/validate - Data validation without processing
POST /attribution/analyze - Main attribution analysis
GET /attribution/methods - Available models and linking methods

Example Response
json{
  "results": {
    "channel_attribution": {
      "google_ads": {
        "credit": 0.35,
        "conversions": 145,
        "revenue": 72500.00,
        "confidence": 0.89
      },
      "email": {
        "credit": 0.28,
        "conversions": 116,
        "revenue": 58000.00,
        "confidence": 0.95
      }
    },
    "summary": {
      "total_conversions": 414,
      "total_revenue": 207000.00,
      "average_journey_length": 3.2,
      "unique_customers": 298
    }
  },
  "metadata": {
    "linking_method": "customer_id",
    "confidence_score": 0.87,
    "processing_time": 2.34
  }
}
Implementation Examples
Python
pythonimport requests

class AttributionAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.attribution.example.com/v1"
        self.headers = {"X-API-Key": api_key}
    
    def analyze_attribution(self, file_path, model="linear"):
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {'model': model}
            response = requests.post(
                f"{self.base_url}/attribution/analyze",
                headers=self.headers,
                files=files,
                data=data
            )
        return response.json()

# Usage
api = AttributionAPI("your-api-key")
results = api.analyze_attribution("marketing_data.csv", model="time_decay")
JavaScript/Node.js
javascriptconst fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

async function analyzeAttribution(filePath, apiKey) {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    form.append('model', 'linear');

    const response = await axios.post(
        'https://api.attribution.example.com/v1/attribution/analyze',
        form,
        { 
            headers: { 
                'X-API-Key': apiKey,
                ...form.getHeaders() 
            }
        }
    );
    return response.data;
}
Error Handling
The API provides detailed error responses with specific guidance:
json{
  "error": "validation_error",
  "message": "Missing required columns",
  "details": {
    "missing_columns": ["timestamp", "channel"]
  },
  "timestamp": "2025-09-24T10:30:00Z"
}
Common HTTP status codes:

200 OK - Request successful
400 Bad Request - Invalid parameters
413 Payload Too Large - File exceeds 100MB limit
422 Unprocessable Entity - Data validation errors
429 Too Many Requests - Rate limit exceeded

Best Practices
Data Quality

Clean your data and remove duplicates before upload
Use consistent channel naming conventions
Include customer identifiers when possible
Maintain consistent timestamp formats

Attribution Window Selection

E-commerce: 30-45 days
B2B: 60-90 days for longer sales cycles
Mobile Apps: 7-30 days
High-consideration purchases: 90+ days

Model Selection

Brand awareness: First-touch attribution
Performance marketing: Last-touch attribution
Balanced analysis: Linear attribution
Short cycles: Time-decay attribution
Complex B2B: Position-based attribution

Rate Limits and Performance

File Size Limit: 100MB maximum
Processing Time: Up to 5 minutes for large files
Rate Limits: 1000 requests per hour per API key
Concurrent Requests: Maximum 5 simultaneous uploads

Documentation
Comprehensive documentation is available in the repository:

Product Requirements - Business logic and use cases
API Specification - Complete OpenAPI 3.0.3 spec
Implementation Guide - Detailed integration instructions
Architecture - System design and technical details
Testing Strategy - Testing approach and requirements

Support

API Documentation: Complete OpenAPI specification available
Rate Limits: 1000 requests/hour, contact support for increases
File Size: 100MB limit, contact for enterprise solutions
Support Email: support@attribution-api.com

Technology Stack

API Framework: FastAPI (Python 3.8+)
Data Processing: pandas, numpy, scikit-learn
File Formats: CSV, JSON, Parquet support
Authentication: API key-based
Documentation: OpenAPI 3.0.3 specification

License
MIT License - see LICENSE file for details.