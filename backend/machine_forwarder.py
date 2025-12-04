"""
Machine-to-machine request forwarding for session affinity.
Forwards requests to the correct machine when session is on a different machine.
"""
import httpx
from typing import Dict, Any, Optional
import json


class MachineForwarder:
    """Handles forwarding requests between machines."""
    
    async def forward_execute_request(
        self,
        machine_address: str,
        session_id: str,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Forward an execute request to another machine.
        
        Args:
            machine_address: Internal address of the target machine
            session_id: Session ID
            code: Code to execute
            timeout: Request timeout
            
        Returns:
            Execution result dictionary (SessionExecuteResponse format)
        """
        url = f"{machine_address}/sessions/execute"
        
        payload = {
            "session_id": session_id,
            "code": code,
            "timeout": timeout
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout + 5) as client:
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
            raise Exception(f"Failed to forward request to {machine_address}: {str(e)}")
    
    async def forward_execute_request_legacy(
        self,
        machine_address: str,
        session_id: str,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Forward a legacy /execute request to another machine.
        Returns ExecuteResponse format.
        """
        url = f"{machine_address}/execute"
        
        payload = {
            "session_id": session_id,
            "code": code,
            "timeout": timeout
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout + 5) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                # Ensure result is in ExecuteResponse format
                return {
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                    'returncode': result.get('returncode', 0),
                    'success': result.get('success', False)
                }
        except httpx.HTTPError as e:
            raise Exception(f"Failed to forward request to {machine_address}: {str(e)}")

