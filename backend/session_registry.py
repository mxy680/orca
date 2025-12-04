"""
Session registry for distributed kernel management.
Stores session -> machine mapping in Redis for scaling across multiple machines.
"""
import os
import json
import socket
from typing import Optional
import redis
from redis.exceptions import RedisError


class SessionRegistry:
    """Manages session-to-machine mapping in Redis."""
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
        except (RedisError, Exception) as e:
            print(f"Warning: Redis not available: {e}. Using in-memory fallback.")
            self.redis_client = None
        
        # Get current machine ID (use Fly.io machine ID or hostname)
        self.machine_id = os.getenv("FLY_MACHINE_ID", socket.gethostname())
        self.app_name = os.getenv("FLY_APP_NAME", "orca-67")
        
        # Get machine's private IP (for Fly.io internal networking)
        # Fly.io machines can be accessed via: http://[machine-id].vm.[app-name].internal
        self.machine_address = self._get_machine_address()
    
    def _get_machine_address(self) -> str:
        """Get the internal address for this machine."""
        # Fly.io internal networking format: http://[machine-id].vm.[app-name].internal:8000
        if os.getenv("FLY_MACHINE_ID"):
            return f"http://{self.machine_id}.vm.{self.app_name}.internal:8000"
        # Fallback for local development
        return "http://localhost:8000"
    
    def register_session(self, session_id: str, ttl: int = 3600):
        """
        Register a session on this machine.
        TTL = time to live in seconds (default 1 hour)
        """
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps({
                        "machine_id": self.machine_id,
                        "machine_address": self.machine_address,
                        "session_id": session_id
                    })
                )
                return True
            except RedisError:
                return False
        return False
    
    def get_session_machine(self, session_id: str) -> Optional[str]:
        """Get the machine ID where a session is running."""
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                data = self.redis_client.get(key)
                if data:
                    session_info = json.loads(data)
                    return session_info.get("machine_id")
            except (RedisError, json.JSONDecodeError):
                pass
        return None
    
    def get_session_machine_address(self, session_id: str) -> Optional[str]:
        """Get the machine address (for forwarding) where a session is running."""
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                data = self.redis_client.get(key)
                if data:
                    session_info = json.loads(data)
                    return session_info.get("machine_address")
            except (RedisError, json.JSONDecodeError):
                pass
        return None
    
    def is_session_local(self, session_id: str) -> bool:
        """Check if a session is running on this machine."""
        machine_id = self.get_session_machine(session_id)
        return machine_id == self.machine_id
    
    def unregister_session(self, session_id: str):
        """Remove session from registry."""
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.delete(key)
            except RedisError:
                pass
    
    def extend_session_ttl(self, session_id: str, ttl: int = 3600):
        """Extend session TTL (call on each request)."""
        if self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.expire(key, ttl)
            except RedisError:
                pass

