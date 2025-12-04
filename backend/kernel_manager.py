"""
Jupyter kernel manager for session-based code execution.
Manages kernel lifecycle and communication.
"""
import uuid
import asyncio
import time
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
    
    def __init__(self, workspace_root: str = "workspace", max_sessions_per_machine: int = 5):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        self.kernels: Dict[str, AsyncKernelManager] = {}
        self.kernel_clients: Dict[str, any] = {}
        self.max_sessions_per_machine = max_sessions_per_machine
        self._startup_lock = asyncio.Lock()  # Prevent concurrent kernel startups
        
        # Initialize session registry for distributed scaling
        self.registry = SessionRegistry() if SessionRegistry else None
    
    async def create_session(self) -> str:
        """Create a new session and spawn a kernel."""
        # Check session limit
        if len(self.kernels) >= self.max_sessions_per_machine:
            raise Exception(
                f"Maximum sessions per machine reached ({self.max_sessions_per_machine}). "
                f"Please wait for other sessions to end or scale to more machines."
            )
        
        session_id = str(uuid.uuid4())
        km = None
        kc = None
        
        # Use lock to prevent concurrent kernel startups (can cause issues)
        async with self._startup_lock:
            try:
                # Create workspace directory for this session
                session_dir = self.workspace_root / session_id
                session_dir.mkdir(exist_ok=True, parents=True)
                
                # Create kernel manager with explicit timeout
                print(f"Creating kernel for session {session_id}...", file=__import__('sys').stderr)
                km = AsyncKernelManager(kernel_name='python3')
                
                # Start kernel with timeout
                try:
                    await asyncio.wait_for(km.start_kernel(cwd=str(session_dir)), timeout=15)
                except asyncio.TimeoutError:
                    raise Exception("Kernel startup timed out after 15 seconds")
                
                print(f"Kernel started, getting client...", file=__import__('sys').stderr)
                
                # Get kernel client for communication
                kc = km.client()
                kc.start_channels()
                
                print(f"Waiting for kernel to be ready...", file=__import__('sys').stderr)
                
                # Wait for kernel to be ready with timeout
                # Try a longer timeout, and if it fails, try a simple test execution instead
                try:
                    await asyncio.wait_for(kc.wait_for_ready(), timeout=20)
                    print(f"Kernel ready check passed", file=__import__('sys').stderr)
                except asyncio.TimeoutError:
                    print(f"Ready check timed out, but continuing anyway (kernel will be tested on first execution)...", file=__import__('sys').stderr)
                    # Ready check can be flaky - kernel might still work
                    # We'll test it on the first actual code execution
                
                print(f"Kernel ready for session {session_id}", file=__import__('sys').stderr)
                
                self.kernels[session_id] = km
                self.kernel_clients[session_id] = kc
                
                # Register session in Redis (for distributed scaling)
                if self.registry:
                    self.registry.register_session(session_id)
                
                return session_id
            except Exception as e:
                # Clean up on failure
                print(f"Error creating session {session_id}: {str(e)}", file=__import__('sys').stderr)
                if km is not None:
                    try:
                        await km.shutdown_kernel(now=True)
                    except Exception as cleanup_error:
                        print(f"Cleanup error: {cleanup_error}", file=__import__('sys').stderr)
                if session_id in self.kernels:
                    del self.kernels[session_id]
                if session_id in self.kernel_clients:
                    del self.kernel_clients[session_id]
                raise Exception(f"Failed to create kernel: {str(e)}")
    
    async def execute_code(self, session_id: str, code: str, timeout: int = 30, forward_if_needed: bool = True):
        """
        Execute code in a session's kernel.
        
        Args:
            session_id: Session ID
            code: Code to execute
            timeout: Execution timeout
            forward_if_needed: If True, automatically forward to correct machine if session is remote
        """
        # Ensure timeout is an integer
        timeout_int = int(timeout) if isinstance(timeout, (str, float)) else timeout
        
        # Check if session exists locally
        if session_id not in self.kernel_clients:
            # Check if session exists on another machine (if Redis available)
            if self.registry and forward_if_needed:
                machine_id = self.registry.get_session_machine(session_id)
                if machine_id and machine_id != self.registry.machine_id:
                    # Session is on another machine - forward the request via public URL
                    # Import here to avoid circular dependencies
                    from machine_forwarder import MachineForwarder
                    forwarder = MachineForwarder()
                    # Use the sessions/execute endpoint for forwarding
                    result = await forwarder.forward_execute_request(
                        machine_id=machine_id,
                        session_id=session_id,
                        code=code,
                        timeout=timeout_int
                    )
                    # Convert SessionExecuteResponse format to kernel result format
                    return {
                        'stdout': result.get('stdout', ''),
                        'stderr': result.get('stderr', ''),
                        'result': result.get('result'),
                        'success': result.get('success', False)
                    }
                elif machine_id is None:
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
        # We'll also wait for the shell reply to check for errors
        try:
            execution_complete = False
            start_time = time.time()
            
            # Collect messages until execution completes
            while not execution_complete:
                # Check if we've exceeded timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout_int:
                    raise TimeoutError(f"Code execution timed out after {timeout_int} seconds")
                
                # Try to get iopub message (with short timeout)
                try:
                    msg = await asyncio.wait_for(
                        kc.get_iopub_msg(),
                        timeout=1.0  # Short timeout to check for completion
                    )
                    
                    msg_type = msg.get('msg_type', '')
                    content = msg.get('content', {})
                    
                    if msg_type == 'stream':
                        if content.get('name') == 'stdout':
                            stdout.append(content.get('text', ''))
                        elif content.get('name') == 'stderr':
                            stderr.append(content.get('text', ''))
                    
                    elif msg_type == 'execute_result':
                        result = content.get('data', {}).get('text/plain', '')
                    
                    elif msg_type == 'status' and content.get('execution_state') == 'idle':
                        # Execution completed
                        execution_complete = True
                        break
                    
                    elif msg_type == 'error':
                        stderr.append('\n'.join(content.get('traceback', [])))
                        execution_complete = True
                        break
                        
                except asyncio.TimeoutError:
                    # No iopub message, check shell channel for completion
                    try:
                        shell_msg = await asyncio.wait_for(
                            kc.get_shell_msg(msg_id),
                            timeout=0.1  # Very short timeout
                        )
                        # Got shell reply, execution is complete
                        if shell_msg['content'].get('status') == 'error':
                            error_content = shell_msg['content']
                            stderr.append('\n'.join(error_content.get('traceback', [])))
                        execution_complete = True
                        break
                    except asyncio.TimeoutError:
                        # No shell reply yet, continue collecting iopub messages
                        continue
                    
        except TimeoutError:
            # Re-raise timeout errors
            raise
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

