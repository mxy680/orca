# Simple test server Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Run the server (use exec form for better compatibility)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

