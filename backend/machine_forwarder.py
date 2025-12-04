"""
Machine-to-machine request forwarding for session affinity.
Forwards requests to the correct machine when session is on a different machine.
Uses public URL for simplicity and reliability.
"""
import httpx
import os
from typing import Dict, Any
import sys


class MachineForwarder:
    """Handles forwarding requests between machines using public URL."""
    
    async def forward_execute_request(
        self,
        machine_id: str,  # We only need machine_id to know it's not local
        session_id: str,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Forward an execute request to another machine via public URL.
        
        Args:
            machine_id: Machine ID where the session is running (for logging)
            session_id: Session ID
            code: Code to execute
            timeout: Request timeout
            
        Returns:
            Execution result dictionary (SessionExecuteResponse format)
        """
        # Get app name from environment or use default
        app_name = os.getenv("FLY_APP_NAME", "orca-67")
        public_url = f"https://{app_name}.fly.dev"
        url = f"{public_url}/sessions/execute"
        
        payload = {
            "session_id": session_id,
            "code": code,
            "timeout": timeout
        }
        
        # Use longer timeout for forwarding
        timeout_obj = httpx.Timeout(timeout + 10, connect=10.0)
        
        print(f"Forwarding request for session {session_id} to machine {machine_id} via {url}", file=sys.stderr)
        
        try:
            async with httpx.AsyncClient(
                timeout=timeout_obj,
                verify=True,  # Use HTTPS for public URL
                follow_redirects=True
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                # Ensure result is in the expected format
                return {
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                    'result': result.get('result'),
                    'success': result.get('success', False)
                }
        except httpx.HTTPError as e:
            raise Exception(f"Failed to forward request to {url}: {str(e)}")

