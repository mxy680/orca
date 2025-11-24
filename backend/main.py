"""
Orca Backend - Code Execution Service

This backend handles only code execution in isolated Docker containers.
All other logic (chat, LLM, code generation) happens in the Next.js frontend.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

from services.container_manager import ContainerManager
from services.executor import Executor
from services.file_storage import FileStorage

load_dotenv()

app = FastAPI(title="Orca Backend", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (Docker connection is lazy - only connects when needed)
container_manager = ContainerManager()
executor = Executor(container_manager)
file_storage = FileStorage()


class ExecuteRequest(BaseModel):
    user_id: str
    code: str
    timeout: Optional[int] = 300


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    plots: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    success: bool


@app.get("/")
async def root():
    return {"message": "Orca Backend API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """
    Execute Python code in user's Docker container.
    
    - Gets or creates Docker container for user
    - Connects to Jupyter kernel inside container
    - Executes code and captures outputs
    - Returns results
    """
    try:
        result = await executor.execute(
            user_id=request.user_id,
            code=request.code,
            timeout=request.timeout
        )
        return ExecuteResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_file(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a file (dataset) for a user.
    Files are stored and mounted into user's container.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Store file using file storage service
        result = file_storage.store_file(
            user_id=user_id,
            file_content=file_content,
            filename=file.filename or 'uploaded_file'
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{user_id}")
async def get_user_files(user_id: str):
    """
    Get list of files for a user.
    """
    files = file_storage.get_user_files(user_id)
    return {"files": files}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", 8000)))

