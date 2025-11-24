# Railway Setup with Docker Image

## Quick Setup

### 1. Build Images Locally

```bash
# Build backend
cd backend
docker build -t your-username/orca-backend:latest .

# Build executor (needed for user containers)
cd ../docker/executor
docker build -t your-username/orca-executor:latest .
```

### 2. Push to Docker Hub

```bash
docker login
docker push your-username/orca-backend:latest
docker push your-username/orca-executor:latest
```

### 3. Connect to Railway

In Railway Dashboard → Service Settings:

**Source:**
- Click **"Connect Image"**
- Enter: `your-username/orca-backend:latest`
- Railway will pull and deploy

**Deploy:**
- Start Command: Leave empty (uses Dockerfile CMD)
- Healthcheck Path: `/health`

### 4. Environment Variables

Add in Railway → Variables:

```
WORKSPACE_ROOT=/app/workspace
DOCKER_IMAGE_NAME=your-username/orca-executor:latest
CONTAINER_MEMORY_LIMIT=2g
CONTAINER_CPU_LIMIT=2
PORT=8000
```

### 5. Docker Access

Set up Docker service or socket (see main Railway setup docs).

## Updating

When you make changes:

```bash
# Rebuild
docker build -t your-username/orca-backend:latest ./backend

# Push
docker push your-username/orca-backend:latest

# Railway will auto-redeploy (if watching the tag)
# Or manually trigger redeploy in Railway dashboard
```

## Benefits

- ✅ Faster - No build time on Railway
- ✅ Test locally first
- ✅ Version control with tags
- ✅ Works with any registry (Docker Hub, GHCR, Railway registry)

