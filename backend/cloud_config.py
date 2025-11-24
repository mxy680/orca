"""
Cloud-specific configuration adjustments.

This file helps adapt the backend for different cloud environments.
"""
import os
import logging

logger = logging.getLogger(__name__)


def get_docker_socket_path():
    """
    Get Docker socket path based on environment.
    
    Cloud platforms may mount Docker socket at different locations.
    Railway-specific: Railway may mount Docker socket or require Docker-in-Docker.
    """
    # Railway-specific: Check for Railway environment
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Railway may mount Docker socket at standard location
        # Or use Docker-in-Docker service
        railway_socket_paths = [
            '/var/run/docker.sock',  # Standard location if mounted
            '/var/run/docker.sock.raw',  # Alternative Railway location
        ]
        for path in railway_socket_paths:
            if os.path.exists(path):
                return path
        
        # Railway Docker-in-Docker: Check if DOCKER_HOST is set by Railway
        docker_host = os.getenv('DOCKER_HOST', '')
        if docker_host:
            if docker_host.startswith('unix://'):
                socket_path = docker_host.replace('unix://', '')
                if os.path.exists(socket_path):
                    return socket_path
            elif docker_host.startswith('tcp://'):
                # Railway might use TCP connection to Docker service
                # This would need different handling
                logger.warning(f"Railway Docker via TCP: {docker_host}")
    
    # Common Docker socket locations
    socket_paths = [
        '/var/run/docker.sock',  # Standard Linux
        '/var/run/docker.sock.raw',  # Some cloud platforms
        os.path.expanduser('~/.docker/run/docker.sock'),  # Docker Desktop
    ]
    
    # Check if DOCKER_HOST is set
    docker_host = os.getenv('DOCKER_HOST', '')
    if docker_host and docker_host.startswith('unix://'):
        socket_path = docker_host.replace('unix://', '')
        if os.path.exists(socket_path):
            return socket_path
    
    # Try common paths
    for path in socket_paths:
        if os.path.exists(path):
            return path
    
    return None


def is_cloud_environment():
    """Check if running in a cloud environment."""
    cloud_indicators = [
        'RAILWAY_ENVIRONMENT',
        'RENDER',
        'FLY_APP_NAME',
        'HEROKU_APP_NAME',
        'AWS_EXECUTION_ENV',
        'GOOGLE_CLOUD_PROJECT',
    ]
    
    return any(os.getenv(indicator) for indicator in cloud_indicators)


def get_workspace_root():
    """Get workspace root path, adjusted for cloud environments."""
    default = os.getenv('WORKSPACE_ROOT', './workspace')
    
    # In cloud, use absolute path
    if is_cloud_environment():
        if not os.path.isabs(default):
            return os.path.join('/app', default.lstrip('./'))
    
    return default

