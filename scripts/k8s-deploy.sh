#!/bin/bash

# Kubernetes deployment script for Multi-Touch Attribution API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Multi-Touch Attribution API to Kubernetes${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if we can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Cluster info:${NC}"
kubectl cluster-info

# Create namespace if it doesn't exist
NAMESPACE="attribution-api"
echo -e "${YELLOW}📦 Creating namespace: ${NAMESPACE}${NC}"
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Deploy Redis first
echo -e "${YELLOW}🗄️  Deploying Redis...${NC}"
kubectl apply -f k8s/deployment.yaml -n "${NAMESPACE}"

# Wait for Redis to be ready
echo -e "${YELLOW}⏳ Waiting for Redis to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=redis -n "${NAMESPACE}" --timeout=300s

# Deploy the API
echo -e "${YELLOW}🚀 Deploying Attribution API...${NC}"
kubectl apply -f k8s/deployment.yaml -n "${NAMESPACE}"

# Wait for API to be ready
echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=attribution-api -n "${NAMESPACE}" --timeout=300s

# Deploy monitoring (optional)
if [ "$1" = "--with-monitoring" ]; then
    echo -e "${YELLOW}📊 Deploying monitoring stack...${NC}"
    kubectl apply -f k8s/monitoring.yaml -n "${NAMESPACE}"
fi

# Deploy ingress (optional)
if [ "$2" = "--with-ingress" ]; then
    echo -e "${YELLOW}🌐 Deploying ingress...${NC}"
    kubectl apply -f k8s/ingress.yaml -n "${NAMESPACE}"
fi

# Show deployment status
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${BLUE}📊 Deployment status:${NC}"
kubectl get pods -n "${NAMESPACE}"
kubectl get services -n "${NAMESPACE}"

# Show logs
echo -e "${BLUE}📝 Recent logs:${NC}"
kubectl logs -l app=attribution-api -n "${NAMESPACE}" --tail=10

# Show service URLs
echo -e "${GREEN}🌐 Service URLs:${NC}"
kubectl get services -n "${NAMESPACE}" -o wide

# Health check
echo -e "${YELLOW}🏥 Running health check...${NC}"
API_POD=$(kubectl get pods -l app=attribution-api -n "${NAMESPACE}" -o jsonpath='{.items[0].metadata.name}')
if kubectl exec "${API_POD}" -n "${NAMESPACE}" -- curl -f http://localhost:8000/health/live &> /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo -e "${YELLOW}💡 To access the API:${NC}"
echo -e "   kubectl port-forward service/attribution-api-service 8000:8000 -n ${NAMESPACE}"
echo -e "   Then visit: http://localhost:8000"
