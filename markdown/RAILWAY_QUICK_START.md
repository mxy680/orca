# Railway Quick Start Guide

## Step-by-Step Setup

### 1. Configure Service Settings

In Railway Dashboard → Service Settings:

**Source:**
- Connect your GitHub repository
- Root Directory: `/`

**Build:**
- Builder: `Dockerfile` (auto-detected)
- **Dockerfile Path**: `backend/Dockerfile` ⚠️ **IMPORTANT: Change this!**
- Metal Build Environment: Leave unchecked for now

**Deploy:**
- Start Command: Leave empty (uses Dockerfile CMD)
- Healthcheck Path: `/health`

**Resource Limits:**
- CPU: 2 vCPU (minimum)
- Memory: 2 GB (minimum)

### 2. Add Environment Variables

Go to Railway Dashboard → Variables tab, add:

```
WORKSPACE_ROOT=/app/workspace
DOCKER_IMAGE_NAME=orca-executor:latest
CONTAINER_MEMORY_LIMIT=2g
CONTAINER_CPU_LIMIT=2
```

### 3. Docker Access Setup

Railway doesn't have a "Docker Socket" toggle. You need to set up Docker access:

**Option 1: Docker Service (Recommended)**

1. Create a new service in Railway
2. Use Docker image: `docker:dind`
3. Enable private networking
4. Name it: `docker-service`
5. In your backend service, add variable:
   ```
   DOCKER_HOST=tcp://docker-service:2375
   ```

**Option 2: Check if Railway auto-mounts socket**

Some Railway plans auto-mount Docker socket. Check logs for:
- "Connected to Docker via /var/run/docker.sock"

If you see this, no additional setup needed!

### 4. Build Executor Image

The backend needs the `orca-executor:latest` image to create user containers.

**Quick method (Docker Hub):**

1. Build locally:
   ```bash
   cd docker/executor
   docker build -t your-username/orca-executor:latest .
   docker push your-username/orca-executor:latest
   ```

2. Update environment variable:
   ```
   DOCKER_IMAGE_NAME=your-username/orca-executor:latest
   ```

### 5. Deploy

Railway will automatically:
- Build from `backend/Dockerfile`
- Deploy when you push to GitHub
- Or use `railway up` from CLI

### 6. Test

```bash
# Get your Railway URL
railway domain

# Test health
curl https://your-app.railway.app/health

# Test execution (will fail if Docker not set up)
curl -X POST https://your-app.railway.app/execute \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "code": "print(1+1)"}'
```

## Common Issues

### Build fails: "Dockerfile not found"
- **Fix**: Set Dockerfile Path to `backend/Dockerfile` (not just `Dockerfile`)

### App starts but Docker connection fails
- **Fix**: Set up Docker service (Option 1 above) or check if socket is auto-mounted

### "orca-executor:latest not found"
- **Fix**: Build and push executor image first (Step 4)

### Port binding error
- **Fix**: Railway sets `$PORT` automatically, the Dockerfile handles this

## Next Steps

Once basic deployment works:
1. Add Redis service (optional, for queue)
2. Deploy frontend to Vercel or Railway
3. Set up custom domain
4. Configure monitoring

