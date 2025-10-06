from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import anyio

from .kernel_manager import KernelManager, KernelCreateRequest, ExecuteRequest

app = FastAPI(title="Orca Control API", version="0.1.0")

# Single, in-process manager for dev
manager = KernelManager()


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/kernels")
async def create_kernel(req: KernelCreateRequest):
    try:
        kernel_id = await anyio.to_thread.run_sync(manager.create_kernel, req)
        return {"kernel_id": kernel_id, "mode": "dev"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to create kernel: {e}")


@app.delete("/kernels/{kernel_id}")
async def delete_kernel(kernel_id: str):
    ok = await anyio.to_thread.run_sync(manager.shutdown_kernel, kernel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="kernel not found")
    return JSONResponse(status_code=204, content=None)


@app.post("/kernels/{kernel_id}/execute")
async def execute(kernel_id: str, body: ExecuteRequest):
    if not manager.has_kernel(kernel_id):
        raise HTTPException(status_code=404, detail="kernel not found")
    try:
        # Offload blocking Jupyter client calls to a worker thread
        result = await anyio.to_thread.run_sync(manager.execute, kernel_id, body)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail="kernel not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"execution failed: {e}")


# NOTE: For dev, we’ll add WS/SSE streaming in a follow-up step.
# Keeping API surface stable:
# GET /kernels/{kernel_id}/stream -> WS/SSE to be implemented.
