#!/bin/bash

# Docker run script for Multi-Touch Attribution API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 Running Multi-Touch Attribution API with Docker${NC}"

# Configuration
IMAGE_NAME="attribution-api"
TAG=${1:-"latest"}
PORT=${2:-"8000"}
REDIS_PORT=${3:-"6379"}

echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "   Image: ${IMAGE_NAME}:${TAG}"
echo -e "   API Port: ${PORT}"
echo -e "   Redis Port: ${REDIS_PORT}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Check if image exists
if ! docker image inspect "${IMAGE_NAME}:${TAG}" &> /dev/null; then
    echo -e "${YELLOW}📦 Image not found, building...${NC}"
    ./scripts/docker-build.sh "${TAG}"
fi

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

# Start Redis
echo -e "${YELLOW}🗄️  Starting Redis...${NC}"
docker run -d \
    --name attribution-redis \
    -p "${REDIS_PORT}:6379" \
    redis:7-alpine \
    redis-server --appendonly yes

# Wait for Redis to be ready
echo -e "${YELLOW}⏳ Waiting for Redis to be ready...${NC}"
sleep 5

# Start the API
echo -e "${YELLOW}🚀 Starting Attribution API...${NC}"
docker run -d \
    --name attribution-api \
    -p "${PORT}:8000" \
    --link attribution-redis:redis \
    -e REDIS_HOST=redis \
    -e REDIS_PORT=6379 \
    -e ENABLE_API_KEY_AUTH=true \
    -e LOG_LEVEL=INFO \
    -v "$(pwd)/logs:/app/logs" \
    "${IMAGE_NAME}:${TAG}"

# Wait for API to be ready
echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"
sleep 10

# Health check
echo -e "${YELLOW}🏥 Running health check...${NC}"
if curl -f "http://localhost:${PORT}/health/live" &> /dev/null; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo -e "${YELLOW}📝 API logs:${NC}"
    docker logs attribution-api --tail=20
    exit 1
fi

# Show status
echo -e "${GREEN}✅ API is running!${NC}"
echo -e "${BLUE}📊 Container status:${NC}"
docker ps --filter "name=attribution"

echo -e "${GREEN}🌐 API is available at:${NC}"
echo -e "   http://localhost:${PORT}"
echo -e "   Health: http://localhost:${PORT}/health"
echo -e "   Docs: http://localhost:${PORT}/docs"

echo -e "${YELLOW}💡 Useful commands:${NC}"
echo -e "   View logs: docker logs attribution-api -f"
echo -e "   Stop API: docker stop attribution-api"
echo -e "   Stop Redis: docker stop attribution-redis"
echo -e "   Clean up: docker rm attribution-api attribution-redis"

echo -e "${GREEN}🎉 Multi-Touch Attribution API is running!${NC}"
