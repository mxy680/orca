from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict

from .kernel_manager import KernelManager, KernelCreateRequest, ExecuteRequest

app = FastAPI(title="Orca Control API", version="0.1.0")

# Single, in-process manager for dev
manager = KernelManager()


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/kernels")
def create_kernel(req: KernelCreateRequest):
    kernel_id = manager.create_kernel(req)
    return {"kernel_id": kernel_id, "mode": "dev"}


@app.delete("/kernels/{kernel_id}")
def delete_kernel(kernel_id: str):
    if not manager.shutdown_kernel(kernel_id):
        raise HTTPException(status_code=404, detail="kernel not found")
    return JSONResponse(status_code=204, content=None)


@app.post("/kernels/{kernel_id}/execute")
def execute(kernel_id: str, body: ExecuteRequest):
    if not manager.has_kernel(kernel_id):
        raise HTTPException(status_code=404, detail="kernel not found")
    # For now, execute synchronously and return collected outputs
    result = manager.execute(kernel_id, body)
    return result


# NOTE: For dev, we’ll add WS/SSE streaming in a follow-up step.
# Keeping API surface stable:
# GET /kernels/{kernel_id}/stream -> WS/SSE to be implemented.
