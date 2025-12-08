"""
Centralized exception hierarchy for ToolchainKit.

This module defines all custom exceptions used across the codebase
to eliminate duplication and provide clear exception semantics.
"""


# ============================================================================
# Base Exceptions
# ============================================================================


class ToolchainKitError(Exception):
    """Base exception for all ToolchainKit errors."""

    pass


# ============================================================================
# Registry Exceptions
# ============================================================================


class RegistryError(ToolchainKitError):
    """Base exception for registry-related errors."""

    pass


class ToolchainInUseError(RegistryError):
    """Raised when attempting to unregister toolchain that's still in use."""

    pass


class RegistryLockTimeout(RegistryError):
    """Raised when registry lock cannot be acquired within timeout."""

    pass


# ============================================================================
# Toolchain-related Exceptions
# ============================================================================


class ToolchainError(ToolchainKitError):
    """Base exception for toolchain-related errors."""

    pass


class ToolchainNotFoundError(ToolchainError):
    """Base exception when a toolchain cannot be found."""

    pass


class ToolchainNotInCacheError(ToolchainNotFoundError):
    """Raised when a toolchain is not found in the cache registry."""

    def __init__(self, toolchain_id: str):
        self.toolchain_id = toolchain_id
        super().__init__(f"Toolchain not found in cache: {toolchain_id}")


class ToolchainRegistryError(ToolchainError):
    """Base exception for toolchain metadata registry errors."""

    pass


class ToolchainMetadataNotFoundError(ToolchainRegistryError):
    """Raised when toolchain metadata cannot be found."""

    def __init__(self, toolchain_name: str, version: str = ""):
        self.toolchain_name = toolchain_name
        self.version = version
        msg = f"Metadata not found for toolchain: {toolchain_name}"
        if version:
            msg += f" version {version}"
        super().__init__(msg)


class InvalidVersionError(ToolchainRegistryError):
    """Invalid version format or pattern."""

    pass


# ============================================================================
# Package Manager Exceptions
# ============================================================================


class PackageManagerError(ToolchainKitError):
    """Base exception for package manager errors."""

    pass


class PackageManagerNotFoundError(PackageManagerError):
    """Package manager not found or not installed."""

    pass


class PackageManagerDetectionError(PackageManagerError):
    """Error occurred during package manager detection."""

    pass


class PackageManagerInstallError(PackageManagerError):
    """Error occurred during dependency installation."""

    pass


# ============================================================================
# Build Backend Exceptions
# ============================================================================


class BuildBackendError(ToolchainKitError):
    """Base exception for build backend errors."""

    pass


class BackendNotAvailableError(BuildBackendError):
    """Raised when requested backend is not available."""

    pass


class BuildConfigurationError(BuildBackendError):
    """Raised when build configuration fails."""

    pass


# ============================================================================
# Plugin Exceptions (keep existing, but inherit from base)
# ============================================================================


class PluginError(ToolchainKitError):
    """Base exception for plugin-related errors."""

    pass


class PluginLoadError(PluginError):
    """Raised when plugin loading fails."""

    pass


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""

    pass
