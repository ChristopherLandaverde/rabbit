# Docker Deployment Guide

This guide covers deploying the Multi-Touch Attribution API using Docker and Docker Compose.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services (API + Redis + Nginx)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Scripts

```bash
# Build the image
./scripts/docker-build.sh

# Run with Docker
./scripts/docker-run.sh

# Deploy to Kubernetes
./scripts/k8s-deploy.sh
```

## Docker Configuration

### Dockerfile

The `Dockerfile` creates a production-ready container with:

- **Base Image**: Python 3.10 slim
- **Security**: Non-root user
- **Health Checks**: Built-in health monitoring
- **Optimization**: Multi-stage build for smaller image size

### Docker Compose

The `docker-compose.yml` includes:

- **Attribution API**: Main application container
- **Redis**: Caching and rate limiting
- **Nginx**: Load balancer and reverse proxy
- **Networking**: Isolated network for services
- **Volumes**: Persistent data storage

## Services

### Attribution API

```yaml
attribution-api:
  build: .
  ports:
    - "8000:8000"
  environment:
    - REDIS_HOST=redis
    - ENABLE_API_KEY_AUTH=true
  depends_on:
    redis:
      condition: service_healthy
```

### Redis

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

### Nginx

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

## Environment Variables

### Security
- `ENABLE_API_KEY_AUTH=true` - Enable API key authentication
- `DEFAULT_RATE_LIMIT=1000` - Rate limit per hour
- `API_KEY_TTL_SECONDS=2592000` - API key TTL (30 days)

### Redis Configuration
- `REDIS_HOST=redis` - Redis hostname
- `REDIS_PORT=6379` - Redis port
- `REDIS_DB=0` - Redis database number

### File Processing
- `MAX_FILE_SIZE_MB=100` - Maximum file size
- `MAX_CONCURRENT_REQUESTS=10` - Concurrent request limit
- `MAX_MEMORY_USAGE_GB=2.0` - Memory usage limit

### Logging
- `LOG_LEVEL=INFO` - Logging level
- `ENABLE_SECURITY_LOGGING=true` - Security event logging

## Usage Examples

### Basic Deployment

```bash
# Clone the repository
git clone <repository-url>
cd rabbit

# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f attribution-api
```

### Development Mode

```bash
# Run with development settings
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production Deployment

```bash
# Build production image
./scripts/docker-build.sh latest

# Tag for registry
docker tag attribution-api:latest your-registry/attribution-api:latest

# Push to registry
docker push your-registry/attribution-api:latest

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

## Health Checks

### API Health Endpoints

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health status
- `GET /health/metrics` - Performance metrics
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

### Docker Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1
```

## Monitoring

### Log Files

- **Application**: `logs/application.log`
- **Security**: `logs/security.log`
- **Performance**: `logs/performance.log`
- **Business**: `logs/business.log`

### Metrics

Access metrics at `/health/metrics`:

```json
{
  "uptime_seconds": 3600,
  "request_count": 150,
  "error_count": 3,
  "error_rate": 0.02,
  "cache_stats": {
    "hits": 45,
    "misses": 105,
    "hit_rate": 0.3
  }
}
```

## Troubleshooting

### Common Issues

#### API Not Starting

```bash
# Check logs
docker logs attribution-api

# Check Redis connection
docker exec attribution-api curl http://localhost:8000/health/detailed
```

#### Redis Connection Issues

```bash
# Check Redis status
docker exec attribution-redis redis-cli ping

# Check Redis logs
docker logs attribution-redis
```

#### Port Conflicts

```bash
# Check port usage
netstat -tulpn | grep :8000

# Use different ports
docker-compose up -d --scale attribution-api=1 -p 8001
```

### Debug Mode

```bash
# Run with debug logging
docker run -e LOG_LEVEL=DEBUG attribution-api:latest

# Interactive shell
docker run -it attribution-api:latest /bin/bash
```

## Security

### API Key Authentication

```bash
# Test with API key
curl -H "X-API-Key: dev-api-key" http://localhost:8000/health

# Test without API key (should fail)
curl http://localhost:8000/health
```

### Rate Limiting

```bash
# Test rate limiting
for i in {1..10}; do
  curl -H "X-API-Key: dev-api-key" http://localhost:8000/attribution/methods
done
```

## Scaling

### Horizontal Scaling

```bash
# Scale API instances
docker-compose up -d --scale attribution-api=3

# Check load distribution
docker-compose ps
```

### Load Balancing

The Nginx configuration includes:

- **Rate Limiting**: Per-IP and per-endpoint limits
- **File Upload Limits**: Special handling for large files
- **Health Checks**: Automatic health monitoring
- **SSL/TLS**: HTTPS support (configure certificates)

## Production Considerations

### Resource Limits

```yaml
services:
  attribution-api:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

### Persistent Storage

```yaml
volumes:
  redis_data:
    driver: local
  logs:
    driver: local
```

### Security

- **Non-root User**: Container runs as non-root user
- **Security Headers**: Automatic security headers
- **Input Validation**: Comprehensive input sanitization
- **Audit Logging**: Complete security event logging

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker rmi attribution-api:latest

# Clean up everything
docker system prune -a
```

## Support

For issues and questions:

1. Check the logs: `docker-compose logs -f`
2. Verify health: `curl http://localhost:8000/health`
3. Check documentation: `http://localhost:8000/docs`
4. Review configuration files
5. Check system resources

The Multi-Touch Attribution API is now ready for production deployment! 🚀
