#!/bin/bash
# Start Jupyter kernel in the container

# Create kernel connection file directory
mkdir -p /app/kernel

# Start IPython kernel
# The kernel will listen on a port and create a connection file
python -m ipykernel_launcher \
    --ip=0.0.0.0 \
    --port=8888 \
    --KernelManager.transport=tcp \
    --KernelManager.ip=0.0.0.0 \
    --KernelManager.port=8888 \
    --KernelApp.connection_file=/app/kernel/connection.json

# Keep container running
tail -f /dev/null

