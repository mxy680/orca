"""
Executor - Executes Python code in user's Docker container.

Connects to Jupyter kernel inside container and executes code,
capturing all outputs (stdout, stderr, plots, results).
"""
import logging
from typing import Dict, Any, List
from jupyter_client import BlockingKernelClient
import json
import time

logger = logging.getLogger(__name__)


class Executor:
    """Executes code in user's Docker container via Jupyter kernel."""
    
    def __init__(self, container_manager):
        self.container_manager = container_manager
        self.kernel_clients = {}  # Cache kernel clients per container
        
    async def execute(
        self,
        user_id: str,
        code: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Execute Python code in user's container.
        
        Args:
            user_id: User identifier
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with stdout, stderr, plots, results, success
        """
        try:
            # Get or create container for user
            container = self.container_manager.get_or_create_container(user_id)
            
            # Get kernel client (connect to kernel in container)
            kernel_client = self._get_kernel_client(container)
            
            # Execute code
            result = self._execute_code(kernel_client, code, timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing code for user {user_id}: {str(e)}")
            return {
                'stdout': '',
                'stderr': f'Execution error: {str(e)}',
                'plots': [],
                'results': [],
                'success': False
            }
    
    def _get_kernel_client(self, container) -> BlockingKernelClient:
        """
        Get or create kernel client for container.
        
        Args:
            container: Docker container object
            
        Returns:
            BlockingKernelClient connected to kernel
        """
        container_id = container.id
        
        # Check if we already have a client for this container
        if container_id in self.kernel_clients:
            client = self.kernel_clients[container_id]
            # Test if connection is still alive
            try:
                client.get_shell_msg(timeout=0.1)
                return client
            except:
                # Connection dead, create new one
                del self.kernel_clients[container_id]
        
        # Get connection info from container
        connection_info = self.container_manager.get_container_connection_info(container)
        connection_file = connection_info['connection_file']
        
        # Load connection file and create kernel client
        kernel_client = BlockingKernelClient()
        kernel_client.load_connection_file(connection_file)
        kernel_client.start_channels()
        
        # Verify connection works
        try:
            # Send a test message to verify kernel is responsive
            kernel_client.kernel_info()
        except Exception as e:
            logger.error(f"Failed to connect to kernel: {str(e)}")
            raise Exception(f"Kernel connection failed: {str(e)}")
        
        # Cache client
        self.kernel_clients[container_id] = kernel_client
        
        logger.info(f"Connected to kernel in container {container_id}")
        return kernel_client
    
    def _execute_code(
        self,
        kernel_client: BlockingKernelClient,
        code: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute code and collect outputs.
        
        Args:
            kernel_client: Connected kernel client
            code: Python code to execute
            timeout: Maximum execution time
            
        Returns:
            Dictionary with execution results
        """
        stdout = ""
        stderr = ""
        plots = []
        results = []
        
        start_time = time.time()
        
        try:
            # Send code to kernel
            msg_id = kernel_client.execute(code)
            
            # Collect outputs until execution completes
            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    kernel_client.interrupt()
                    stderr += f"\nExecution timeout after {timeout} seconds"
                    break
                
                try:
                    # Get message from kernel (with timeout)
                    msg = kernel_client.get_iopub_msg(timeout=1)
                    msg_type = msg['msg_type']
                    content = msg.get('content', {})
                    
                    if msg_type == 'stream':
                        # Text output (print statements)
                        name = content.get('name', '')
                        text = content.get('text', '')
                        
                        if name == 'stdout':
                            stdout += text
                        elif name == 'stderr':
                            stderr += text
                    
                    elif msg_type == 'display_data':
                        # Plots, images, HTML output
                        data = content.get('data', {})
                        
                        if 'image/png' in data:
                            plots.append({
                                'type': 'image',
                                'format': 'png',
                                'data': data['image/png']
                            })
                        elif 'image/jpeg' in data:
                            plots.append({
                                'type': 'image',
                                'format': 'jpeg',
                                'data': data['image/jpeg']
                            })
                        elif 'text/html' in data:
                            plots.append({
                                'type': 'html',
                                'data': data['text/html']
                            })
                    
                    elif msg_type == 'execute_result':
                        # Return values from code
                        results.append(content.get('data', {}))
                    
                    elif msg_type == 'status':
                        execution_state = content.get('execution_state', '')
                        if execution_state == 'idle':
                            # Execution complete
                            break
                    
                    elif msg_type == 'error':
                        # Execution error
                        error_name = content.get('ename', 'Error')
                        error_value = content.get('evalue', '')
                        traceback = '\n'.join(content.get('traceback', []))
                        stderr += f"{error_name}: {error_value}\n{traceback}"
                        break
                
                except Exception as e:
                    # Timeout or other error getting message
                    if "timeout" in str(e).lower():
                        continue
                    else:
                        logger.warning(f"Error getting message: {str(e)}")
                        break
            
            # Get final execution result
            try:
                final_msg = kernel_client.get_shell_msg(msg_id, timeout=1)
                success = final_msg['content'].get('status') == 'ok'
            except:
                success = len(stderr) == 0
            
        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            stderr += f"\nExecution error: {str(e)}"
            success = False
        
        return {
            'stdout': stdout,
            'stderr': stderr,
            'plots': plots,
            'results': results,
            'success': success
        }

