"""
Build backends for ToolchainKit.
"""

from toolchainkit.backends.cmake import CMakeBackend
from toolchainkit.plugins.registry import get_global_registry

# Auto-register the CMake backend
_registry = get_global_registry()
if not _registry.has_backend("cmake"):
    _registry.register_backend("cmake", CMakeBackend())

__all__ = ["CMakeBackend"]
