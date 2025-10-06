from __future__ import annotations

"""
K8sKernelManager skeleton.

This stub matches the interface of the local KernelManager so the API can select
between backends via ORCA_KERNEL_BACKEND without import-time Kubernetes deps.

Implementation plan (later):
- Use kubernetes_asyncio or kubernetes client to create a Pod per kernel
- Store kernel_id -> pod_name and optional service/port-forward proxy
- Proxy IOPub/execute via a sidecar or direct TCP/WS if exposed
- Implement idle culling by checking Pod annotations/last-activity
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class KernelCreateRequest(BaseModel):
    runtime: Optional[str] = Field(default="python3")


class ExecuteRequest(BaseModel):
    cell_id: str
    code: str
    timeout: Optional[float] = Field(default=60.0)


class ExecuteResult(BaseModel):
    cell_id: str
    outputs: List[Dict[str, Any]]
    execution_count: Optional[int] = None
    status: str = "ok"


class K8sKernelManager:
    def __init__(self) -> None:
        # Minimal state placeholder; real impl will track kernel_id -> pod refs
        self._kernels: Dict[str, Any] = {}

    def has_kernel(self, kernel_id: str) -> bool:
        return kernel_id in self._kernels

    def create_kernel(self, req: KernelCreateRequest) -> str:
        raise NotImplementedError("K8s backend not implemented yet")

    def shutdown_kernel(self, kernel_id: str) -> bool:
        raise NotImplementedError("K8s backend not implemented yet")

    def execute(self, kernel_id: str, body: ExecuteRequest) -> ExecuteResult:
        raise NotImplementedError("K8s backend not implemented yet")

    def get_iopub_msg(self, kernel_id: str, timeout: float = 1.0):
        # For skeleton, no streaming
        return None

    def cull_idle(self, idle_seconds: float) -> list[str]:
        # No-op until implemented
        return []
