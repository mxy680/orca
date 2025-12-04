"""
Code execution endpoint.
"""
from fastapi import APIRouter, HTTPException
import sys
import subprocess
import uuid
from pathlib import Path

# Import models - works when running from backend directory
try:
    from models import ExecuteRequest, ExecuteResponse
except ImportError:
    # Fallback for when running as a package
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import ExecuteRequest, ExecuteResponse

router = APIRouter(prefix="/execute", tags=["execute"])


@router.post("", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """
    Execute Python code and return the results.
    Code is executed in a subprocess with a timeout for safety.
    """
    # Create a temporary file for the code
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

