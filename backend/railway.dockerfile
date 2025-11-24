# Alternative Dockerfile for Railway with Docker-in-Docker support
# Use this if Railway doesn't mount Docker socket

FROM docker:dind

# Install Python
RUN apk add --no-cache python3 py3-pip python3-dev gcc musl-dev

# Install Docker Python SDK
RUN pip3 install --no-cache-dir docker==6.1.3

# Copy requirements and install
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create workspace directory
RUN mkdir -p /app/workspace

# Start Docker daemon and then the app
# Note: This requires privileged mode in Railway
COPY railway-start.sh /app/railway-start.sh
RUN chmod +x /app/railway-start.sh

EXPOSE 8000

CMD ["/app/railway-start.sh"]

