"""
Build cache management for ToolchainKit.

This package provides build cache detection, installation, and configuration
for accelerating C++ compilation through result caching using sccache or ccache.

Modules:
    detection: Detect and install build cache tools (sccache, ccache)
    launcher: Configure compiler launcher for CMake integration
    remote: Configure remote cache backends (S3, Redis)
"""

from .detection import (
    BuildCacheConfig,
    BuildCacheDetector,
    BuildCacheInstaller,
    BuildCacheManager,
)
from .launcher import (
    CacheStats,
    CompilerLauncherConfig,
)
from .remote import (
    RemoteCacheConfig,
    RemoteCacheConfigurator,
    SecureCredentialHandler,
)

__all__ = [
    "BuildCacheConfig",
    "BuildCacheDetector",
    "BuildCacheInstaller",
    "BuildCacheManager",
    "CacheStats",
    "CompilerLauncherConfig",
    "RemoteCacheConfig",
    "RemoteCacheConfigurator",
    "SecureCredentialHandler",
]
