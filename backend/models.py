"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    code: str
    timeout: int = 30  # seconds


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    success: bool

