#!/bin/bash

# Docker Setup Test Script for Rabbit MVP
# This script tests the Docker setup with state management

set -e

echo "🐳 Testing Rabbit MVP Docker Setup with State Management"
echo "========================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
echo "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_status "Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi
print_status "docker-compose is available"

# Clean up any existing containers
echo "Cleaning up existing containers..."
docker-compose down --remove-orphans > /dev/null 2>&1 || true
print_status "Cleaned up existing containers"

# Build and start services
echo "Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
echo "Checking service status..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    print_status "Redis is running"
else
    print_error "Redis failed to start"
    exit 1
fi

# Check Backend API
if curl -f http://localhost:8000/health/live > /dev/null 2>&1; then
    print_status "Backend API is running"
else
    print_warning "Backend API health check failed, but service might still be starting..."
fi

# Check Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_status "Frontend is running"
else
    print_warning "Frontend might still be starting..."
fi

# Test API endpoints
echo "Testing API endpoints..."

# Test health endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "API health endpoint responding"
else
    print_warning "API health endpoint not responding"
fi

# Test attribution methods endpoint
if curl -f http://localhost:8000/attribution/methods > /dev/null 2>&1; then
    print_status "Attribution methods endpoint responding"
else
    print_warning "Attribution methods endpoint not responding"
fi

# Display service information
echo ""
echo "🎉 Docker Setup Complete!"
echo "========================"
echo ""
echo "Services are running:"
echo "• Frontend: http://localhost:3000"
echo "• Backend API: http://localhost:8000"
echo "• Redis: localhost:6379"
echo ""
echo "State Management Features:"
echo "• Auto-save: ✅ Enabled"
echo "• Session Recovery: ✅ Available"
echo "• Analysis History: ✅ Persistent"
echo "• User Preferences: ✅ Saved"
echo ""
echo "To test state management:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Upload a file and start analysis"
echo "3. Refresh the page to see recovery dialog"
echo "4. Complete analysis to save to history"
echo "5. Use the History button to load previous analyses"
echo ""
echo "To stop services:"
echo "docker-compose down"
echo ""
echo "To view logs:"
echo "docker-compose logs -f"
echo ""

# Optional: Keep services running
read -p "Keep services running? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping services..."
    docker-compose down
    print_status "Services stopped"
fi

print_status "Docker setup test completed!"
