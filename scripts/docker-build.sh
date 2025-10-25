#!/bin/bash

# Docker build script for Multi-Touch Attribution API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 Building Multi-Touch Attribution API Docker Image${NC}"

# Build arguments
IMAGE_NAME="attribution-api"
TAG=${1:-"latest"}
REGISTRY=${2:-""}

# Full image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
fi

echo -e "${YELLOW}📦 Building image: ${FULL_IMAGE_NAME}${NC}"

# Build the Docker image
docker build -t "${FULL_IMAGE_NAME}" .

echo -e "${GREEN}✅ Docker image built successfully: ${FULL_IMAGE_NAME}${NC}"

# Show image size
echo -e "${YELLOW}📏 Image size:${NC}"
docker images "${FULL_IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Optional: Run security scan
if command -v trivy &> /dev/null; then
    echo -e "${YELLOW}🔍 Running security scan...${NC}"
    trivy image "${FULL_IMAGE_NAME}"
fi

# Optional: Push to registry
if [ -n "$REGISTRY" ] && [ "$3" = "--push" ]; then
    echo -e "${YELLOW}📤 Pushing to registry...${NC}"
    docker push "${FULL_IMAGE_NAME}"
    echo -e "${GREEN}✅ Image pushed to registry${NC}"
fi

echo -e "${GREEN}🎉 Build complete!${NC}"
echo -e "${YELLOW}💡 To run the container:${NC}"
echo -e "   docker run -p 8000:8000 ${FULL_IMAGE_NAME}"
echo -e "${YELLOW}💡 To run with docker-compose:${NC}"
echo -e "   docker-compose up -d"
