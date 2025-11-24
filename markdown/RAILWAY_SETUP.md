# Railway Setup Instructions

## Service Configuration

Based on your Railway service settings, configure the following:

### 1. Source
- **Connect Repo**: Connect your GitHub repository
- **Root Directory**: Set to `/` (root of repo)

### 2. Build Settings

**Dockerfile Path**: Change from `Dockerfile` to:
```
backend/Dockerfile
```

**Why**: The Dockerfile is in the `backend/` directory, not the root.

### 3. Deploy Settings

**Start Command**: Set to:
```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Or if Railway auto-detects, it should use the CMD from the Dockerfile.

### 4. Environment Variables

Add these in Railway Dashboard → Variables:

```
WORKSPACE_ROOT=/app/workspace
DOCKER_IMAGE_NAME=orca-executor:latest
CONTAINER_MEMORY_LIMIT=2g
CONTAINER_CPU_LIMIT=2
PORT=8000
```

**Optional (if using Redis):**
```
REDIS_URL=redis://your-redis-service.railway.internal:6379
```

### 5. Docker Socket Access

Railway doesn't expose Docker socket in the UI settings. You have two options:

#### Option A: Use Railway's Docker Service (Recommended)

1. **Create a separate Docker service:**
   - Add new service in Railway
   - Use image: `docker:dind` (Docker-in-Docker)
   - Enable private networking
   - Name it: `docker-service`

2. **Set environment variable in your backend:**
   ```
   DOCKER_HOST=tcp://docker-service:2375
   ```

3. **The backend will automatically detect and use TCP connection**

#### Option B: Use Subprocess Execution (Simpler for MVP)

If Docker-in-Docker is too complex, we can modify the backend to execute Python code directly via subprocess instead of containers. This is less secure but simpler.

### 6. Healthcheck Path

Set to:
```
/health
```

This will check if your backend is running before marking deployment as successful.

### 7. Resource Limits

For MVP, you can use:
- **CPU**: 2 vCPU (minimum)
- **Memory**: 2 GB (minimum)

For production with multiple users:
- **CPU**: 4-8 vCPU
- **Memory**: 4-8 GB

### 8. Build the Executor Image

Before the backend can create user containers, you need to build the executor image:

1. **Option 1: Build in Railway**
   - Create a separate service
   - Use `docker/executor/Dockerfile`
   - Build and push to Railway registry
   - Reference as `orca-executor:latest`

2. **Option 2: Build locally and push**
   ```bash
   cd docker/executor
   docker build -t orca-executor:latest .
   docker tag orca-executor:latest your-registry/orca-executor:latest
   docker push your-registry/orca-executor:latest
   ```

3. **Option 3: Use Docker Hub**
   - Build and push to Docker Hub
   - Update `DOCKER_IMAGE_NAME` to `your-dockerhub-username/orca-executor:latest`

## Quick Setup Checklist

- [ ] Connect GitHub repo
- [ ] Set Dockerfile path to `backend/Dockerfile`
- [ ] Set start command (or use Dockerfile CMD)
- [ ] Add environment variables
- [ ] Set healthcheck to `/health`
- [ ] Build executor image (`orca-executor:latest`)
- [ ] Configure Docker access (socket or service)
- [ ] Test deployment

## Testing

Once deployed, test with:

```bash
# Health check
curl https://your-app.railway.app/health

# Execute code
curl -X POST https://your-app.railway.app/execute \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "code": "print(1+1)"}'
```

## Troubleshooting

### "Docker connection failed"
- Check if Docker service is running (if using Option A)
- Verify `DOCKER_HOST` is set correctly
- Check Railway logs for connection errors

### "Connection file not found"
- Kernel may not have started yet
- Check container logs
- Verify volume mounts

### Build fails
- Check Dockerfile path is correct: `backend/Dockerfile`
- Verify root directory is `/`
- Check build logs for errors

