"""
Configuration settings for the backend.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Docker
    docker_image_name: str = os.getenv("DOCKER_IMAGE_NAME", "orca-executor:latest")
    container_memory_limit: str = os.getenv("CONTAINER_MEMORY_LIMIT", "2g")
    container_cpu_limit: str = os.getenv("CONTAINER_CPU_LIMIT", "2")
    container_idle_timeout: int = int(os.getenv("CONTAINER_IDLE_TIMEOUT", "1800"))
    
    # Workspace
    workspace_root: str = os.getenv("WORKSPACE_ROOT", "./workspace")
    
    class Config:
        env_file = ".env"


settings = Settings()

