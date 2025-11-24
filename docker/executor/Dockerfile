# Docker image for user code execution
# Contains Python, Jupyter kernel, and ML libraries

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python ML libraries
RUN pip install --no-cache-dir \
    jupyter-client==8.6.0 \
    ipykernel==6.26.0 \
    pandas==2.1.3 \
    numpy==1.26.2 \
    scikit-learn==1.3.2 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    plotly==5.18.0

# Create directory for kernel connection files
RUN mkdir -p /app/kernel

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV JUPYTER_RUNTIME_DIR=/app/kernel

# Expose kernel port (will be configured dynamically)
EXPOSE 8888

# Start Jupyter kernel when container starts
# The kernel will be started by a startup script
COPY start_kernel.sh /app/start_kernel.sh
RUN chmod +x /app/start_kernel.sh

CMD ["/app/start_kernel.sh"]

