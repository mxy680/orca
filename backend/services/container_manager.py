"""
Container Manager - Manages Docker containers per user.

Each user gets their own isolated Docker container with a Jupyter kernel.
Containers are created on first use and cleaned up after idle timeout.
"""
import docker
import redis
import os
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ContainerManager:
    """Manages Docker container lifecycle for user code execution."""
    
    def __init__(self):
        # Lazy initialization - don't connect to Docker until needed
        # This allows the app to start even if Docker isn't available
        self.docker_client = None
        self._docker_initialized = False
        
        # Redis connection (optional)
        try:
            self.redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379")
            )
            # Test Redis connection (non-blocking)
            self.redis_client.ping()
        except redis.ConnectionError:
            # Redis is optional for MVP, just log warning
            logger.warning("Redis not available, some features may not work")
            self.redis_client = None
        
        # Configuration
        self.image_name = os.getenv("DOCKER_IMAGE_NAME", "orca-executor:latest")
        self.memory_limit = os.getenv("CONTAINER_MEMORY_LIMIT", "2g")
        self.cpu_limit = os.getenv("CONTAINER_CPU_LIMIT", "2")
        self.idle_timeout = int(os.getenv("CONTAINER_IDLE_TIMEOUT", "1800"))  # 30 min
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "./workspace")
    
    def _ensure_docker_client(self):
        """Lazy initialization of Docker client."""
        if self._docker_initialized:
            return
        
        try:
            # Try to get Docker socket path (Railway-aware)
            socket_path = None
            docker_host = os.getenv('DOCKER_HOST', '')
            
            # Railway: Check for TCP Docker host (Docker service)
            if docker_host and docker_host.startswith('tcp://'):
                # Railway Docker service via TCP
                self.docker_client = docker.DockerClient(base_url=docker_host)
                self.docker_client.ping()
                logger.info(f"Connected to Railway Docker service via {docker_host}")
                self._docker_initialized = True
                return
            
            # Try cloud_config for socket path detection
            try:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from cloud_config import get_docker_socket_path
                socket_path = get_docker_socket_path()
            except Exception as e:
                logger.debug(f"cloud_config import failed, trying fallback: {e}")
            
            # Fallback: Try common socket paths
            if not socket_path:
                socket_paths = [
                    '/var/run/docker.sock',  # Standard Linux / Railway mounted socket
                    '/var/run/docker.sock.raw',  # Alternative Railway location
                    os.path.expanduser('~/.docker/run/docker.sock'),  # Docker Desktop
                ]
                for path in socket_paths:
                    if os.path.exists(path):
                        socket_path = path
                        break
            
            # Connect via Unix socket
            if socket_path:
                base_url = f'unix://{socket_path}'
                self.docker_client = docker.DockerClient(base_url=base_url)
                self.docker_client.ping()
                logger.info(f"Connected to Docker via {socket_path}")
            elif docker_host and docker_host.startswith('unix://'):
                # Use DOCKER_HOST if set
                self.docker_client = docker.DockerClient(base_url=docker_host)
                self.docker_client.ping()
                logger.info(f"Connected to Docker via DOCKER_HOST: {docker_host}")
            else:
                # Last resort: from_env (may fail with http+docker error)
                # This is a fallback that might not work in Railway
                logger.warning("No Docker socket found, trying from_env() (may fail)")
                self.docker_client = docker.from_env()
                self.docker_client.ping()
                logger.info("Connected to Docker via from_env()")
            
            self._docker_initialized = True
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise Exception(f"Docker connection failed. Make sure Docker is available. For Railway, ensure Docker socket is mounted or Docker service is configured. Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Docker: {e}")
            raise Exception(f"Docker connection failed: {e}")
    
    def get_or_create_container(self, user_id: str):
        """
        Get existing container for user or create a new one.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Docker container object
        """
        # Ensure Docker client is initialized
        self._ensure_docker_client()
        
        # Check if user already has a container
        container_id = None
        if self.redis_client:
            container_id_bytes = self.redis_client.get(f"user:{user_id}:container")
            if container_id_bytes:
                container_id = container_id_bytes.decode()
        
        if container_id:
            container_id = container_id.decode()
            try:
                container = self.docker_client.containers.get(container_id)
                if container.status == 'running':
                    # Update last used timestamp (if Redis available)
                    if self.redis_client:
                        self.redis_client.setex(
                            f"container:{container_id}:last_used",
                            self.idle_timeout,
                            datetime.now().isoformat()
                        )
                    logger.info(f"Reusing container {container_id} for user {user_id}")
                    return container
                else:
                    # Container exists but not running, remove from cache
                    logger.info(f"Container {container_id} not running, creating new one")
                    if self.redis_client:
                        self.redis_client.delete(f"user:{user_id}:container")
            except docker.errors.NotFound:
                # Container was removed, create new one
                logger.info(f"Container {container_id} not found, creating new one")
                if self.redis_client:
                    self.redis_client.delete(f"user:{user_id}:container")
        
        # Create new container
        logger.info(f"Creating new container for user {user_id}")
        container = self._create_container(user_id)
        
        # Store mapping in Redis (if available)
        if self.redis_client:
            self.redis_client.set(f"user:{user_id}:container", container.id)
            self.redis_client.setex(
                f"container:{container.id}:last_used",
                self.idle_timeout,
                datetime.now().isoformat()
            )
        
        return container
    
    def _create_container(self, user_id: str):
        """
        Create a new Docker container for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Docker container object
        """
        # Ensure user workspace directory exists
        user_workspace = os.path.join(self.workspace_root, user_id)
        os.makedirs(user_workspace, exist_ok=True)
        
        # Create kernel directory for connection file (mounted from host)
        kernel_dir = os.path.join(self.workspace_root, user_id, 'kernel')
        os.makedirs(kernel_dir, exist_ok=True)
        
        # Create container with volume mounts
        container = self.docker_client.containers.run(
            self.image_name,
            detach=True,
            name=f"orca-user-{user_id}",
            mem_limit=self.memory_limit,
            cpus=self.cpu_limit,
            volumes={
                os.path.abspath(user_workspace): {
                    'bind': '/data',
                    'mode': 'rw'
                },
                os.path.abspath(kernel_dir): {
                    'bind': '/app/kernel',
                    'mode': 'rw'
                }
            },
            network_mode='bridge',
            remove=False,  # Don't auto-remove on stop
            environment={
                'USER_ID': user_id
            },
            # Expose kernel ports (will be configured in Dockerfile)
            ports={
                '8888/tcp': None,  # Jupyter kernel port (random host port)
            }
        )
        
        # Wait for container to be ready
        self._wait_for_kernel_ready(container)
        
        logger.info(f"Container {container.id} created and ready for user {user_id}")
        return container
    
    def _wait_for_kernel_ready(self, container, max_wait: int = 30):
        """
        Wait for Jupyter kernel to be ready inside container.
        
        Args:
            container: Docker container object
            max_wait: Maximum seconds to wait
        """
        import time
        
        for i in range(max_wait):
            if self._is_kernel_ready(container):
                return
            time.sleep(1)
        
        raise Exception(f"Kernel failed to start in container {container.id}")
    
    def _is_kernel_ready(self, container) -> bool:
        """
        Check if kernel is ready in container.
        
        Args:
            container: Docker container object
            
        Returns:
            True if kernel is ready
        """
        # Check if container is running
        container.reload()
        if container.status != 'running':
            return False
        
        # Check if connection file exists
        # The kernel creates /app/kernel/connection.json which is mounted to host
        try:
            # Get user_id from container name or environment
            container_name = container.name
            user_id = container_name.replace('orca-user-', '')
            connection_file = os.path.join(
                self.workspace_root,
                user_id,
                'kernel',
                'connection.json'
            )
            
            if os.path.exists(connection_file):
                # Verify file is valid JSON
                import json
                with open(connection_file, 'r') as f:
                    json.load(f)
                return True
        except Exception as e:
            logger.debug(f"Kernel not ready yet: {str(e)}")
        
        return False
    
    def get_container_connection_info(self, container) -> dict:
        """
        Get kernel connection information from container.
        
        Reads the connection file created by the Jupyter kernel.
        
        Args:
            container: Docker container object
            
        Returns:
            Dictionary with connection file path
        """
        # Ensure Docker client is initialized
        self._ensure_docker_client()
        
        # Get user_id from container name
        container_name = container.name
        user_id = container_name.replace('orca-user-', '')
        
        # Connection file is mounted at workspace/user_id/kernel/connection.json
        connection_file = os.path.join(
            self.workspace_root,
            user_id,
            'kernel',
            'connection.json'
        )
        
        if not os.path.exists(connection_file):
            raise Exception(f"Connection file not found: {connection_file}")
        
        return {
            'connection_file': connection_file,
            'container_id': container.id,
            'user_id': user_id
        }
    
    def cleanup_idle_containers(self):
        """
        Background task to cleanup containers that haven't been used.
        Should be called periodically (e.g., every 5 minutes).
        """
        # Get all container mappings from Redis
        # Check last_used timestamp
        # Stop and remove idle containers
        # TODO: Implement cleanup logic
        pass

