# Deploying via Docker Image (Recommended)

Instead of building from GitHub, you can build the Docker image locally (or via CI/CD) and connect it directly to Railway.

## Advantages

✅ **Faster deployments** - No build time on Railway
✅ **More control** - Build once, deploy anywhere
✅ **Easier debugging** - Test image locally before deploying
✅ **Version control** - Tag images with versions
✅ **Simpler setup** - No need to configure build paths

## Steps

### 1. Build the Docker Image

```bash
cd backend
docker build -t orca-backend:latest .
```

### 2. Tag for Railway Registry (or Docker Hub)

**Option A: Railway Registry**
```bash
# Login to Railway registry
railway login
railway link

# Tag for Railway
docker tag orca-backend:latest railway.app/orca-backend:latest

# Push to Railway
docker push railway.app/orca-backend:latest
```

**Option B: Docker Hub**
```bash
docker tag orca-backend:latest your-username/orca-backend:latest
docker push your-username/orca-backend:latest
```

### 3. Connect Image to Railway

In Railway Dashboard:
1. Go to your service
2. **Source** → **Connect Image**
3. Enter image name:
   - Railway: `railway.app/orca-backend:latest`
   - Docker Hub: `your-username/orca-backend:latest`
4. Railway will pull and deploy the image

### 4. Set Environment Variables

Same as before:
```
WORKSPACE_ROOT=/app/workspace
DOCKER_IMAGE_NAME=orca-executor:latest
CONTAINER_MEMORY_LIMIT=2g
CONTAINER_CPU_LIMIT=2
PORT=8000
```

### 5. Configure Deploy Settings

- **Start Command**: Leave empty (uses Dockerfile CMD)
- **Healthcheck Path**: `/health`
- **Resource Limits**: Set as needed

## Updating the Image

When you make changes:

```bash
# Rebuild
docker build -t orca-backend:latest .

# Retag and push
docker tag orca-backend:latest railway.app/orca-backend:latest
docker push railway.app/orca-backend:latest

# Railway will automatically redeploy
```

Or use version tags:
```bash
docker tag orca-backend:latest railway.app/orca-backend:v1.0.0
docker push railway.app/orca-backend:v1.0.0
```

Then update the image name in Railway to use the new version.

## CI/CD Integration

You can automate this with GitHub Actions:

```yaml
# .github/workflows/docker-build.yml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push
        run: |
          docker build -t orca-backend:latest ./backend
          docker tag orca-backend:latest railway.app/orca-backend:latest
          docker push railway.app/orca-backend:latest
```

## Comparison

| Method | Pros | Cons |
|--------|------|------|
| **GitHub Repo** | Auto-deploy on push, Railway builds | Slower (builds on Railway), more config |
| **Docker Image** | Faster, more control, test locally | Manual push, need CI/CD for automation |

## Recommendation

For development: **Docker Image** (faster iterations)
For production: **GitHub Repo with CI/CD** (automated deployments)

Or use both: Build image via CI/CD, then connect image to Railway for best of both worlds!

