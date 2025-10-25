# Multi-Touch Attribution API - Phase 4 Documentation

## Overview

The Multi-Touch Attribution API is now production-ready with comprehensive security, monitoring, caching, and performance optimizations. This document covers the enhanced features introduced in Phase 4.

## Table of Contents

1. [Security Features](#security-features)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Caching](#caching)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Performance Optimizations](#performance-optimizations)
7. [API Endpoints](#api-endpoints)
8. [Error Handling](#error-handling)
9. [Deployment](#deployment)

## Security Features

### Authentication
- **API Key Authentication**: All endpoints require valid API keys
- **Rate Limiting**: Per-API-key and global rate limiting
- **Input Validation**: Comprehensive input sanitization and validation
- **Security Headers**: Automatic security headers on all responses

### Data Protection
- **File Size Limits**: Configurable file size restrictions
- **File Type Validation**: Only allowed file types (CSV, JSON, Parquet)
- **Input Sanitization**: Automatic sanitization of all inputs
- **Audit Logging**: Complete security event logging

## Authentication

### API Key Management

All requests require an API key in the header:

```bash
X-API-Key: your-api-key-here
```

### Development Mode

For development, you can use the default API key:

```bash
X-API-Key: dev-api-key
```

### Production API Keys

Production API keys are generated through the API key management system:

```python
from src.core.security import APIKeyManager

# Generate a new API key
api_key_manager = APIKeyManager()
api_key = api_key_manager.generate_api_key(
    user_id="user123",
    permissions=["read", "write"]
)
```

## Rate Limiting

### Default Limits
- **Per API Key**: 1000 requests per hour
- **Global**: System-wide rate limiting
- **File Processing**: Concurrent request limits

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded

When rate limits are exceeded:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded for this API key",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Caching

### Response Caching
- **Attribution Results**: Cached for 1 hour
- **Validation Results**: Cached for 30 minutes
- **File Metadata**: Cached for 2 hours
- **API Methods**: Cached for 24 hours

### Cache Headers

Responses include cache information:

```http
Cache-Control: public, max-age=3600
X-Cache-Status: HIT
```

### Cache Invalidation

Caches are automatically invalidated when:
- File content changes
- Model parameters change
- Cache TTL expires

## Monitoring & Health Checks

### Health Check Endpoints

#### Basic Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Detailed Health Check
```bash
GET /health/detailed
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "type": "redis",
      "response_time": 0.001
    },
    "system": {
      "status": "healthy",
      "cpu_percent": 45.2,
      "memory_percent": 67.8
    },
    "application": {
      "status": "healthy",
      "uptime_seconds": 3600,
      "request_count": 150,
      "error_rate": 0.02
    }
  }
}
```

#### Metrics Endpoint
```bash
GET /health/metrics
```

Response:
```json
{
  "uptime_seconds": 3600,
  "request_count": 150,
  "error_count": 3,
  "error_rate": 0.02,
  "requests_per_minute": 2.5,
  "cache_stats": {
    "hits": 45,
    "misses": 105,
    "hit_rate": 0.3
  }
}
```

### Kubernetes Probes

#### Readiness Probe
```bash
GET /health/ready
```

#### Liveness Probe
```bash
GET /health/live
```

## Performance Optimizations

### Caching System
- **Redis Integration**: High-performance caching
- **Memory Fallback**: In-memory cache when Redis unavailable
- **Cache Statistics**: Comprehensive cache metrics

### Async Processing
- **File Processing**: Asynchronous file handling
- **Database Operations**: Non-blocking database calls
- **Concurrent Requests**: Multiple simultaneous processing

### Memory Management
- **Efficient Data Processing**: Optimized memory usage
- **Resource Cleanup**: Automatic resource cleanup
- **Memory Monitoring**: Real-time memory usage tracking

## API Endpoints

### Authentication Required

All endpoints now require authentication:

```python
import requests

headers = {
    "X-API-Key": "your-api-key-here"
}

# Validate data
response = requests.post(
    "https://api.attribution.example.com/v1/attribution/validate",
    headers=headers,
    files={"file": open("data.csv", "rb")}
)
```

### Enhanced Error Responses

All errors now include comprehensive information:

```json
{
  "error": "validation_error",
  "message": "Detailed error message",
  "details": {
    "error_type": "ValueError",
    "field": "timestamp",
    "suggestion": "Use ISO format: YYYY-MM-DDTHH:MM:SS"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Handling

### Error Categories

#### Authentication Errors (401)
```json
{
  "error": "missing_api_key",
  "message": "API key is required",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Authorization Errors (403)
```json
{
  "error": "insufficient_permissions",
  "message": "Write permission required for file uploads",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Rate Limit Errors (429)
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded for this API key",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Validation Errors (422)
```json
{
  "error": "invalid_parameter",
  "message": "half_life_days must be a positive number",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Server Errors (500)
```json
{
  "error": "processing_error",
  "message": "Error processing attribution analysis",
  "details": {
    "error_type": "ValueError"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Deployment

### Environment Variables

Required environment variables:

```bash
# Security
ENABLE_API_KEY_AUTH=true
DEFAULT_RATE_LIMIT=1000
API_KEY_TTL_SECONDS=2592000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=INFO
ENABLE_SECURITY_LOGGING=true

# File Processing
MAX_FILE_SIZE_MB=100
MAX_CONCURRENT_REQUESTS=10
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY logs/ ./logs/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: attribution-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: attribution-api
  template:
    metadata:
      labels:
        app: attribution-api
    spec:
      containers:
      - name: attribution-api
        image: attribution-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: ENABLE_API_KEY_AUTH
          value: "true"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Load Balancer Configuration

```yaml
apiVersion: v1
kind: Service
metadata:
  name: attribution-api-service
spec:
  selector:
    app: attribution-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring & Alerting

### Log Files

- **Application Logs**: `logs/application.log`
- **Security Logs**: `logs/security.log`
- **Performance Logs**: `logs/performance.log`
- **Business Logs**: `logs/business.log`

### Metrics Collection

The API automatically collects:
- Request metrics
- Performance metrics
- Business metrics
- Cache statistics
- Error rates

### Alerting

Automatic alerts for:
- High error rates (>5%)
- High CPU usage (>80%)
- High memory usage (>80%)
- Database connectivity issues
- Rate limit violations

## Best Practices

### Security
1. **Use Strong API Keys**: Generate secure, random API keys
2. **Monitor Usage**: Regularly review API usage logs
3. **Rotate Keys**: Regularly rotate API keys
4. **Limit Permissions**: Use minimal required permissions

### Performance
1. **Use Caching**: Leverage response caching for repeated requests
2. **Optimize Files**: Use appropriate file formats and sizes
3. **Monitor Resources**: Keep an eye on system resources
4. **Batch Processing**: Process multiple files efficiently

### Monitoring
1. **Health Checks**: Regularly check health endpoints
2. **Log Analysis**: Monitor log files for issues
3. **Metrics Tracking**: Track key performance metrics
4. **Alert Response**: Respond quickly to alerts

## Conclusion

Phase 4 has transformed the Multi-Touch Attribution API into a production-ready system with enterprise-grade security, monitoring, and performance features. The API is now ready for customer launch with comprehensive observability and reliability.

**Key Achievements:**
- ✅ Security hardening with authentication and authorization
- ✅ Performance optimization with caching and async processing
- ✅ Comprehensive monitoring and health checks
- ✅ Production deployment configuration
- ✅ Complete API documentation

The API is now ready for production deployment with 99.9% availability target and comprehensive security measures.
