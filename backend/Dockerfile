# Simple test server Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/main.py .
COPY backend/models.py .
COPY backend/kernel_manager.py .
COPY backend/kernel_manager_instance.py .
COPY backend/session_registry.py .
COPY backend/machine_forwarder.py .
COPY backend/routers/ ./routers/

# Expose port (Fly.io/Railway sets PORT env var)
EXPOSE 8000

# Run the server
# Fly.io/Railway sets PORT env var, use it or default to 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

