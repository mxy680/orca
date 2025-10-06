from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import anyio

from .kernel_manager import KernelManager, KernelCreateRequest, ExecuteRequest
from .k8s_manager import K8sKernelManager  # type: ignore
import os
import asyncio

app = FastAPI(title="Orca Control API", version="0.1.0")

BACKEND = os.environ.get("ORCA_KERNEL_BACKEND", "local").lower()

# Select backend manager
if BACKEND == "k8s":
    manager = K8sKernelManager()
else:
    # Default to local, in-process manager for development
    manager = KernelManager()

IDLE_SECS = float(os.environ.get("ORCA_KERNEL_IDLE_SECS", "600"))


@app.on_event("startup")
async def _start_culler():
    async def loop():
        while True:
            try:
                culled = await anyio.to_thread.run_sync(manager.cull_idle, IDLE_SECS)
            except Exception:
                culled = []
            # Optionally log culled IDs here
            await anyio.sleep(10)

    # Start background task
    asyncio.create_task(loop())


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
@app.websocket("/kernels/{kernel_id}/stream")
async def stream_kernel(websocket: WebSocket, kernel_id: str):
    await websocket.accept()
    if not manager.has_kernel(kernel_id):
        await websocket.send_json({"event": "error", "detail": "kernel not found"})
        await websocket.close(code=1008)
        return
    try:
        while True:
            # Offload blocking read to a worker thread
            msg = await anyio.to_thread.run_sync(manager.get_iopub_msg, kernel_id, 1.0)
            if not msg:
                # send periodic ping/status if needed; otherwise continue polling
                await anyio.sleep(0.05)
                continue
            msg_type = msg["header"]["msg_type"]
            content = msg.get("content", {})
            if msg_type == "status" and content.get("execution_state") == "idle":
                await websocket.send_json({"event": "status", "execution_state": "idle"})
                continue
            if msg_type in {"stream", "display_data", "execute_result", "error"}:
                await websocket.send_json({
                    "event": msg_type,
                    "content": content,
                })
    except WebSocketDisconnect:
        # Client disconnected
        return
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "detail": str(e)})
        finally:
            await websocket.close(code=1011)
