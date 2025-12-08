"""
Package manager integrations for ToolchainKit.

This package provides abstractions and implementations for integrating
C++ package managers like Conan and vcpkg with ToolchainKit's toolchain
management system.

Available Components:
--------------------
- PackageManager: Abstract base class for package manager implementations
- PackageManagerConfig: Configuration data for package managers
- PackageManagerDetector: Detect and manage package manager instances
- ConanIntegration: Conan 2.x package manager integration
- VcpkgIntegration: vcpkg package manager integration

Example Usage:
-------------
    from toolchainkit.packages import PackageManagerDetector
    from toolchainkit.packages.conan import ConanIntegration
    from toolchainkit.packages.vcpkg import VcpkgIntegration
    from pathlib import Path

    # Set up detector
    project_root = Path('/path/to/project')
    detector = PackageManagerDetector(project_root)

    # Register available package managers
    detector.register(ConanIntegration(project_root))
    detector.register(VcpkgIntegration(project_root))

    # Detect which managers are used
    managers = detector.detect_all()
    for manager in managers:
        print(f"Detected: {manager.get_name()}")
        manager.install_dependencies()
"""

from toolchainkit.packages.base import (
    PackageManager,
    PackageManagerConfig,
    PackageManagerDetector,
)

from toolchainkit.core.exceptions import (
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerDetectionError,
    PackageManagerInstallError,
)

# Import specific implementations (lazy import to avoid import errors)
try:
    from toolchainkit.packages.conan import ConanIntegration

    _conan_available = True
except ImportError:
    _conan_available = False
    ConanIntegration = None  # type: ignore[assignment, misc]

try:
    from toolchainkit.packages.vcpkg import VcpkgIntegration

    _vcpkg_available = True
except ImportError:
    _vcpkg_available = False
    VcpkgIntegration = None  # type: ignore[assignment, misc]

__all__ = [
    "PackageManager",
    "PackageManagerConfig",
    "PackageManagerDetector",
    "PackageManagerError",
    "PackageManagerNotFoundError",
    "PackageManagerDetectionError",
    "PackageManagerInstallError",
]

# Add implementations to __all__ if available
if _conan_available:
    __all__.append("ConanIntegration")
if _vcpkg_available:
    __all__.append("VcpkgIntegration")
