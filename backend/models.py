"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel
from typing import Optional


class ExecuteRequest(BaseModel):
    code: str
    timeout: int = 30  # seconds
    session_id: Optional[str] = None  # If provided, use kernel; otherwise use subprocess


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    success: bool


class SessionCreateResponse(BaseModel):
    session_id: str
    message: str


class SessionExecuteRequest(BaseModel):
    session_id: str
    code: str
    timeout: int = 30


class SessionExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    result: Optional[str] = None
    success: bool

