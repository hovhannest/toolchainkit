"""
Core functionality for ToolchainKit.

This package contains the foundational modules that other components depend on.
"""

from .directory import (
    get_global_cache_dir,
    get_project_local_dir,
    ensure_global_cache_structure,
    ensure_project_structure,
    update_gitignore,
    verify_directory_writable,
    create_directory_structure,
    DirectoryError,
)

from .locking import (
    LockManager,
    DownloadCoordinator,
    try_lock,
    LockTimeout,
)

from .platform import (
    PlatformInfo,
    detect_platform,
    is_supported_platform,
    get_supported_platforms,
    clear_platform_cache,
)

from .cache_registry import (
    ToolchainCacheRegistry,
)

from .exceptions import (
    ToolchainKitError,
    RegistryError,
    ToolchainInUseError,
    RegistryLockTimeout,
    ToolchainError,
    ToolchainNotFoundError,
    ToolchainNotInCacheError,
    ToolchainRegistryError,
    ToolchainMetadataNotFoundError,
    InvalidVersionError,
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerDetectionError,
    PackageManagerInstallError,
    BuildBackendError,
    BackendNotAvailableError,
    BuildConfigurationError,
    PluginError,
    PluginLoadError,
    PluginValidationError,
)

__all__ = [
    "get_global_cache_dir",
    "get_project_local_dir",
    "ensure_global_cache_structure",
    "ensure_project_structure",
    "update_gitignore",
    "verify_directory_writable",
    "create_directory_structure",
    "DirectoryError",
    "LockManager",
    "DownloadCoordinator",
    "try_lock",
    "LockTimeout",
    "PlatformInfo",
    "detect_platform",
    "is_supported_platform",
    "get_supported_platforms",
    "clear_platform_cache",
    "ToolchainCacheRegistry",
    "ToolchainKitError",
    "RegistryError",
    "ToolchainInUseError",
    "RegistryLockTimeout",
    "ToolchainError",
    "ToolchainNotFoundError",
    "ToolchainNotInCacheError",
    "ToolchainRegistryError",
    "ToolchainMetadataNotFoundError",
    "InvalidVersionError",
    "PackageManagerError",
    "PackageManagerNotFoundError",
    "PackageManagerDetectionError",
    "PackageManagerInstallError",
    "BuildBackendError",
    "BackendNotAvailableError",
    "BuildConfigurationError",
    "PluginError",
    "PluginLoadError",
    "PluginValidationError",
]
