"""
Jupyter kernel manager for session-based code execution.
Manages kernel lifecycle and communication.
"""
import uuid
import asyncio
from typing import Dict, Optional
from jupyter_client import AsyncKernelManager, AsyncKernelClient
from pathlib import Path
import json

# Import session registry for distributed sessions
try:
    from session_registry import SessionRegistry
except ImportError:
    SessionRegistry = None


class KernelManager:
    """Manages Jupyter kernels for user sessions."""
    
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        self.kernels: Dict[str, AsyncKernelManager] = {}
        self.kernel_clients: Dict[str, any] = {}
        
        # Initialize session registry for distributed scaling
        self.registry = SessionRegistry() if SessionRegistry else None
    
    async def create_session(self) -> str:
        """Create a new session and spawn a kernel."""
        session_id = str(uuid.uuid4())
        
        # Create workspace directory for this session
        session_dir = self.workspace_root / session_id
        session_dir.mkdir(exist_ok=True)
        
        # Create kernel manager
        km = AsyncKernelManager(kernel_name='python3')
        await km.start_kernel(cwd=str(session_dir))
        
        # Get kernel client for communication
        kc = km.client()
        kc.start_channels()
        
        # Wait for kernel to be ready
        await asyncio.wait_for(kc.wait_for_ready(), timeout=10)
        
        self.kernels[session_id] = km
        self.kernel_clients[session_id] = kc
        
        # Register session in Redis (for distributed scaling)
        if self.registry:
            self.registry.register_session(session_id)
        
        return session_id
    
    async def execute_code(self, session_id: str, code: str, timeout: int = 30, forward_if_needed: bool = True):
        """
        Execute code in a session's kernel.
        
        Args:
            session_id: Session ID
            code: Code to execute
            timeout: Execution timeout
            forward_if_needed: If True, automatically forward to correct machine if session is remote
        """
        # Check if session exists locally
        if session_id not in self.kernel_clients:
            # Check if session exists on another machine (if Redis available)
            if self.registry and forward_if_needed:
                machine_address = self.registry.get_session_machine_address(session_id)
                if machine_address and machine_address != self.registry.machine_address:
                    # Session is on another machine - forward the request
                    # Import here to avoid circular dependencies
                    from machine_forwarder import MachineForwarder
                    forwarder = MachineForwarder()
                    # Use the sessions/execute endpoint for forwarding
                    result = await forwarder.forward_execute_request(
                        machine_address=machine_address,
                        session_id=session_id,
                        code=code,
                        timeout=timeout
                    )
                    # Convert SessionExecuteResponse format to kernel result format
                    return {
                        'stdout': result.get('stdout', ''),
                        'stderr': result.get('stderr', ''),
                        'result': result.get('result'),
                        'success': result.get('success', False)
                    }
                elif machine_address is None:
                    # Session not found in registry
                    raise ValueError(f"Session {session_id} not found")
                else:
                    # Session should be local but kernel not found
                    raise ValueError(f"Session {session_id} registered but kernel not found locally")
            raise ValueError(f"Session {session_id} not found")
        
        # Extend session TTL on each request
        if self.registry:
            self.registry.extend_session_ttl(session_id)
        
        kc = self.kernel_clients[session_id]
        
        # Send code to kernel
        msg_id = kc.execute(code)
        
        # Collect output
        stdout = []
        stderr = []
        result = None
        
        # Collect iopub messages (stdout, stderr, results) until execution completes
        try:
            # Wait for execute_reply on shell channel (indicates completion)
            # This is more reliable than waiting for status messages
            execute_reply = await asyncio.wait_for(
                kc.get_shell_msg(msg_id),
                timeout=timeout
            )
            
            # Check if execution had errors
            if execute_reply['content'].get('status') == 'error':
                error_content = execute_reply['content']
                stderr.append('\n'.join(error_content.get('traceback', [])))
            
            # Collect all iopub messages (with shorter timeout per message)
            # These contain stdout, stderr, and execute_results
            message_timeout = min(5, timeout)
            while True:
                try:
                    msg = await asyncio.wait_for(
                        kc.get_iopub_msg(),
                        timeout=message_timeout
                    )
                    
                    msg_type = msg['msg_type']
                    content = msg['content']
                    
                    if msg_type == 'stream':
                        if content['name'] == 'stdout':
                            stdout.append(content['text'])
                        elif content['name'] == 'stderr':
                            stderr.append(content['text'])
                    
                    elif msg_type == 'execute_result':
                        result = content.get('data', {}).get('text/plain', '')
                    
                    elif msg_type == 'status' and content.get('execution_state') == 'idle':
                        # All messages received
                        break
                        
                except asyncio.TimeoutError:
                    # No more iopub messages, execution is complete
                    break
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"Code execution timed out after {timeout} seconds")
        except Exception as e:
            raise Exception(f"Kernel communication error: {str(e)}")
        
        return {
            'stdout': ''.join(stdout),
            'stderr': ''.join(stderr),
            'result': result,
            'success': len(stderr) == 0
        }
    
    async def delete_session(self, session_id: str):
        """Delete a session and shutdown its kernel."""
        if session_id in self.kernels:
            km = self.kernels[session_id]
            await km.shutdown_kernel(now=True)
            del self.kernels[session_id]
            del self.kernel_clients[session_id]
        
        # Unregister from Redis
        if self.registry:
            self.registry.unregister_session(session_id)
        
        # Clean up workspace
        session_dir = self.workspace_root / session_id
        if session_dir.exists():
            # Optionally delete workspace files
            pass
    
    def list_sessions(self):
        """List all active sessions."""
        return list(self.kernels.keys())

