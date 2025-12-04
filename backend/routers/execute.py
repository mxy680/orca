"""
Code execution endpoint.
Supports both stateless (subprocess) and stateful (Jupyter kernel) execution.
"""
from fastapi import APIRouter, HTTPException
import sys
import subprocess
import uuid
from pathlib import Path

# Import models - works when running from backend directory
try:
    from models import ExecuteRequest, ExecuteResponse
    from kernel_manager import KernelManager
except ImportError:
    # Fallback for when running as a package
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import ExecuteRequest, ExecuteResponse
    from kernel_manager import KernelManager

router = APIRouter(prefix="/execute", tags=["execute"])

# Import shared kernel manager instance
try:
    from kernel_manager_instance import kernel_manager
except ImportError:
    # Fallback
    from kernel_manager import KernelManager
    kernel_manager = KernelManager()


@router.post("", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """
    Execute Python code and return the results.
    
    If session_id is provided, code runs in a persistent Jupyter kernel (stateful).
    If session_id is None, code runs in a subprocess (stateless, backward compatible).
    """
    # If session_id provided, use kernel-based execution
    if request.session_id:
        try:
            result = await kernel_manager.execute_code(
                session_id=request.session_id,
                code=request.code,
                timeout=request.timeout,
                forward_if_needed=True  # Automatically forward to correct machine
            )
            
            # Result might be from local execution or forwarded request
            # Handle both formats
            if isinstance(result, dict):
                # Check if it's already in ExecuteResponse format (from forwarding)
                if 'returncode' in result:
                    return ExecuteResponse(**result)
                # Otherwise, convert from kernel result format
                return ExecuteResponse(
                    stdout=result.get('stdout', ''),
                    stderr=result.get('stderr', ''),
                    returncode=0 if result.get('success', False) else 1,
                    success=result.get('success', False)
                )
            else:
                # Fallback
                return ExecuteResponse(
                    stdout=str(result),
                    stderr='',
                    returncode=0,
                    success=True
                )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except TimeoutError as e:
            raise HTTPException(status_code=408, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Kernel execution error: {str(e)}"
            )
    
    # Otherwise, use subprocess execution (stateless, backward compatible)
    temp_dir = Path("/tmp")
    temp_dir.mkdir(exist_ok=True)
    
    temp_file = temp_dir / f"execute_{uuid.uuid4().hex}.py"
    
    try:
        # Write code to temporary file
        temp_file.write_text(request.code, encoding="utf-8")
        
        # Execute the code
        try:
            result = subprocess.run(
                [sys.executable, str(temp_file)],
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd=temp_dir
            )
            
            return ExecuteResponse(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                success=result.returncode == 0
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=408,
                detail=f"Code execution timed out after {request.timeout} seconds"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Execution error: {str(e)}"
            )
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()

