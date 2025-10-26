# 🐳 Docker Setup Guide

Your Rabbit MVP application is now fully Dockerized with state management support!

## 🚀 Quick Start

### Production Mode
```bash
# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Redis: localhost:6379
```

### Development Mode
```bash
# Start with development overrides (hot reload)
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

# Access the application
# Frontend (dev server): http://localhost:5173
# Backend API: http://localhost:8000
```

## 📦 Services Included

### 1. **attribution-frontend** (Port 3000/5173)
- **Production**: Nginx-served React app with state management
- **Development**: Vite dev server with hot reload
- **Features**: Full state persistence, recovery dialogs, analysis history
- **Storage**: Browser localStorage/sessionStorage (client-side)

### 2. **attribution-api** (Port 8000)
- **Backend**: FastAPI application with Redis caching
- **Features**: Attribution analysis, file processing, security
- **Storage**: Redis for caching, file system for logs

### 3. **redis** (Port 6379)
- **Cache**: Session storage and rate limiting
- **Persistence**: Redis data volume for cache persistence

### 4. **nginx** (Port 80/443) - Optional
- **Load Balancer**: Production-ready reverse proxy
- **SSL**: HTTPS termination (when SSL certificates provided)

## 🔧 State Management in Docker

### ✅ **What Works in Docker:**
- **Browser Storage**: localStorage and sessionStorage work normally
- **State Persistence**: User preferences and analysis history persist
- **Session Recovery**: Interrupted workflows recover on page refresh
- **Cross-Container Communication**: Frontend communicates with backend API
- **File Uploads**: Large file processing with proper timeouts

### 🎯 **Key Features:**
- **Auto-save**: Work is automatically saved as you go
- **Recovery Dialogs**: App detects and offers to restore previous work
- **Analysis History**: Last 10 analyses are saved and accessible
- **User Preferences**: Settings persist between Docker restarts
- **Session Management**: Temporary session data for workflow recovery

## 🛠️ Configuration

### Environment Variables

#### Frontend (.env or docker-compose.yml):
```yaml
environment:
  - VITE_API_URL=http://localhost:8000  # Backend API URL
  - NODE_ENV=production                 # Environment mode
```

#### Backend (already configured):
```yaml
environment:
  - REDIS_HOST=redis                    # Redis container name
  - REDIS_PORT=6379                     # Redis port
  - MAX_FILE_SIZE_MB=100               # File upload limit
  - PROCESSING_TIMEOUT_SECONDS=300     # Analysis timeout
```

### Port Configuration:
- **Frontend (Production)**: `3000:80` → http://localhost:3000
- **Frontend (Development)**: `5173:5173` → http://localhost:5173
- **Backend API**: `8000:8000` → http://localhost:8000
- **Redis**: `6379:6379` → localhost:6379
- **Nginx**: `80:80` → http://localhost:80

## 🔄 Development Workflow

### 1. **Start Development Environment:**
```bash
# Clone and navigate to project
cd /path/to/rabbit

# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

# Or use the shorthand
docker-compose up --build
```

### 2. **Make Changes:**
- **Frontend**: Changes auto-reload via Vite dev server
- **Backend**: Changes auto-reload via uvicorn --reload
- **State Management**: All persistence features work normally

### 3. **Test State Management:**
1. Upload a file and start analysis
2. Refresh the page → Recovery dialog appears
3. Complete analysis → Results saved to history
4. Restart Docker containers → Preferences persist
5. Use History button → Previous analyses load

### 4. **Production Build:**
```bash
# Build production images
docker-compose -f docker-compose.yml build

# Start production services
docker-compose -f docker-compose.yml up
```

## 🐛 Troubleshooting

### Common Issues:

#### **Frontend Can't Connect to Backend:**
```bash
# Check if backend is running
docker-compose ps

# Check backend logs
docker-compose logs attribution-api

# Verify API URL in browser dev tools
```

#### **State Not Persisting:**
- Check browser localStorage is enabled
- Verify you're not in incognito/private mode
- Clear browser cache and try again

#### **File Upload Fails:**
```bash
# Check file size limits
docker-compose logs attribution-api | grep "file size"

# Increase limits in docker-compose.yml
- MAX_FILE_SIZE_MB=200
```

#### **Port Conflicts:**
```bash
# Check what's using ports
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# Change ports in docker-compose.yml
ports:
  - "3001:80"  # Frontend
  - "8001:8000"  # Backend
```

### Debug Commands:

```bash
# View all container logs
docker-compose logs

# View specific service logs
docker-compose logs attribution-frontend
docker-compose logs attribution-api

# Execute commands in running container
docker-compose exec attribution-frontend sh
docker-compose exec attribution-api bash

# Rebuild specific service
docker-compose build attribution-frontend
docker-compose up attribution-frontend
```

## 📊 Monitoring

### Health Checks:
- **Frontend**: `http://localhost:3000/health`
- **Backend**: `http://localhost:8000/health/live`
- **Redis**: `docker-compose exec redis redis-cli ping`

### Logs Location:
- **Application Logs**: `./logs/` directory
- **Container Logs**: `docker-compose logs`
- **Nginx Logs**: `docker-compose logs nginx`

## 🚀 Production Deployment

### 1. **Environment Setup:**
```bash
# Set production environment variables
export NODE_ENV=production
export VITE_API_URL=https://your-api-domain.com

# Build production images
docker-compose -f docker-compose.yml build
```

### 2. **SSL Configuration:**
```bash
# Add SSL certificates
mkdir ssl
# Copy your SSL certificates to ./ssl/

# Update nginx configuration for HTTPS
```

### 3. **Scaling:**
```bash
# Scale backend services
docker-compose up --scale attribution-api=3

# Use external Redis for production
# Update REDIS_HOST in environment variables
```

## 🎯 State Management Features in Docker

### ✅ **Fully Supported:**
- **Auto-save**: Works across container restarts
- **Session Recovery**: Detects interrupted workflows
- **Analysis History**: Persistent across Docker restarts
- **User Preferences**: Settings saved in browser
- **File Persistence**: Uploaded files processed correctly

### 🔧 **Docker-Specific Considerations:**
- **Browser Storage**: Client-side only (not affected by container restarts)
- **API Communication**: Handled via Docker networking
- **File Processing**: Backend processes files in container
- **Caching**: Redis provides session and rate limiting

Your state management system is fully compatible with Docker and provides a seamless experience whether running locally or in production containers!
