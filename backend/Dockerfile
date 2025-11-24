# Backend Dockerfile for cloud deployment
FROM python:3.12-slim

# Install Docker CLI (for Docker-in-Docker or Docker socket mounting)
# Railway: Docker socket may be mounted at /var/run/docker.sock
RUN apt-get update && apt-get install -y \
    docker.io \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
RUN mkdir -p /app/workspace

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create workspace directory
RUN mkdir -p /app/workspace

# Expose port
EXPOSE 8000

# Run the application
# Railway sets $PORT automatically, but we default to 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

