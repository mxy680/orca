#!/bin/sh
# Start Docker daemon and then the FastAPI app
# For Railway Docker-in-Docker setup

# Start Docker daemon in background
dockerd-entrypoint.sh &
DOCKER_PID=$!

# Wait for Docker to be ready
echo "Waiting for Docker daemon to start..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if docker info > /dev/null 2>&1; then
        echo "Docker daemon is ready!"
        break
    fi
    echo "Attempt $i/10: Docker not ready yet..."
    sleep 1
done

# Build the executor image if it doesn't exist
if ! docker images | grep -q "orca-executor"; then
    echo "Building orca-executor image..."
    # This would need the executor Dockerfile context
    # For now, we'll assume it's pre-built or available
    echo "Note: orca-executor image should be pre-built"
fi

# Start the FastAPI app
echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

