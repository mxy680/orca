"""
Shared kernel manager instance for the application.
This ensures all routers use the same kernel manager.
"""
from kernel_manager import KernelManager

# Global kernel manager instance
kernel_manager = KernelManager()

