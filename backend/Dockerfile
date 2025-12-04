# Simple test server Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY models.py .
COPY routers/ ./routers/

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Run the server
# Railway sets PORT env var, use it or default to 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

