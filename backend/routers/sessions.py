"""
Session management endpoints for Jupyter kernel-based execution.
"""
from fastapi import APIRouter, HTTPException
from models import SessionCreateResponse, SessionExecuteRequest, SessionExecuteResponse
from typing import Optional

# Import shared kernel manager instance
try:
    from kernel_manager_instance import kernel_manager
except ImportError:
    # Fallback
    from kernel_manager import KernelManager
    kernel_manager = KernelManager()

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
async def create_session():
    """
    Create a new session with a dedicated Jupyter kernel.
    Each session maintains its own Python state (variables, imports, etc.)
    """
    try:
        session_id = await kernel_manager.create_session()
        return SessionCreateResponse(
            session_id=session_id,
            message=f"Session {session_id} created successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.post("/execute", response_model=SessionExecuteResponse)
async def execute_code(request: SessionExecuteRequest):
    """
    Execute code in a session's kernel.
    Code runs in the same Python process, so variables persist between calls.
    Automatically forwards to correct machine if session is on another machine.
    """
    try:
        result = await kernel_manager.execute_code(
            session_id=request.session_id,
            code=request.code,
            timeout=request.timeout,
            forward_if_needed=True  # Automatically forward to correct machine
        )
        
        # Result might be from local execution or forwarded request
        if isinstance(result, dict):
            # Check if it's already in SessionExecuteResponse format (from forwarding)
            if 'result' in result:
                return SessionExecuteResponse(**result)
            # Otherwise, convert from kernel result format
            return SessionExecuteResponse(
                stdout=result.get('stdout', ''),
                stderr=result.get('stderr', ''),
                result=result.get('result'),
                success=result.get('success', False)
            )
        else:
            # Fallback
            return SessionExecuteResponse(
                stdout=str(result),
                stderr='',
                result=None,
                success=True
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution error: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and shutdown its kernel."""
    try:
        await kernel_manager.delete_session(session_id)
        return {"message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("")
async def list_sessions():
    """List all active sessions."""
    sessions = kernel_manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}

