from __future__ import annotations

import time
import uuid
from threading import Lock
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from jupyter_client import KernelManager as JKernalManager
from jupyter_client.blocking import BlockingKernelClient
from ipykernel.kernelspec import make_ipkernel_cmd


class KernelCreateRequest(BaseModel):
    runtime: Optional[str] = Field(default="python3", description="Kernel name to launch")


class ExecuteRequest(BaseModel):
    cell_id: str
    code: str
    timeout: Optional[float] = Field(default=60.0, description="Seconds to wait for execution")


class ExecuteResult(BaseModel):
    cell_id: str
    outputs: List[Dict[str, Any]]
    execution_count: Optional[int] = None
    status: str = "ok"


class _KernelHandle(BaseModel):
    id: str
    km: Any
    client: Any
    last_activity: float


class KernelManager:
    """Simple in-process kernel manager for development.

    Uses jupyter_client to launch a local Python kernel per session and keeps
    a mapping of kernel_id -> client/manager handles.
    """

    def __init__(self) -> None:
        self._kernels: Dict[str, _KernelHandle] = {}
        self._lock = Lock()

    def has_kernel(self, kernel_id: str) -> bool:
        with self._lock:
            return kernel_id in self._kernels

    def create_kernel(self, req: KernelCreateRequest) -> str:
        kernel_name = (req.runtime or "python3").strip()
        km = JKernalManager(kernel_name=kernel_name)
        try:
            # Try to start by kernelspec name (e.g., 'python3')
            km.start_kernel()
        except Exception:
            # Fallback: launch ipykernel directly without requiring a kernelspec installation
            cmd = make_ipkernel_cmd(None)
            km = JKernalManager(kernel_cmd=cmd)
            km.start_kernel()
        client: BlockingKernelClient = km.client()
        client.start_channels()
        # Wait for kernel to be ready
        client.wait_for_ready(timeout=30)

        kernel_id = str(uuid.uuid4())
        handle = _KernelHandle(id=kernel_id, km=km, client=client, last_activity=time.time())
        with self._lock:
            self._kernels[kernel_id] = handle
        return kernel_id

    def shutdown_kernel(self, kernel_id: str) -> bool:
        with self._lock:
            handle = self._kernels.pop(kernel_id, None)
        if not handle:
            return False
        try:
            handle.client.stop_channels()
        except Exception:
            pass
        try:
            handle.km.shutdown_kernel(now=True)
        except Exception:
            pass
        return True

    def execute(self, kernel_id: str, body: ExecuteRequest) -> ExecuteResult:
        with self._lock:
            handle = self._kernels.get(kernel_id)
        if not handle:
            raise KeyError("kernel not found")

        client: BlockingKernelClient = handle.client
        msg_id = client.execute(body.code)
        outputs: List[Dict[str, Any]] = []
        execution_count: Optional[int] = None

        # Collect IOPub messages until we see 'idle'
        # Stop if timeout is exceeded
        deadline = time.time() + float(body.timeout or 60.0)
        while True:
            if time.time() > deadline:
                break
            msg = client.get_iopub_msg(timeout=1)
            if not msg:
                continue
            msg_type = msg["header"]["msg_type"]
            content = msg.get("content", {})

            if msg_type == "status" and content.get("execution_state") == "idle":
                break
            if msg_type in {"execute_result", "display_data", "stream", "error"}:
                outputs.append({
                    "msg_type": msg_type,
                    "content": content,
                })
                if execution_count is None and "execution_count" in content:
                    execution_count = content.get("execution_count")

        handle.last_activity = time.time()
        return ExecuteResult(cell_id=body.cell_id, outputs=outputs, execution_count=execution_count)
