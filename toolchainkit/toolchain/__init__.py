"""
Toolchain management module for ToolchainKit.

This module provides functionality for:
- Toolchain metadata registry and lookup
- Toolchain download and extraction
- Toolchain verification
- System toolchain detection
"""

from toolchainkit.core.exceptions import (
    InvalidVersionError,
    ToolchainMetadataNotFoundError,
    ToolchainRegistryError,
)
from toolchainkit.toolchain.downloader import (
    ToolchainDownloader,
    ToolchainDownloadError,
    ToolchainExtractionError,
    DownloadResult,
    ProgressInfo,
    download_toolchain,
)

from toolchainkit.toolchain.metadata_registry import (
    ToolchainMetadata,
    ToolchainMetadataRegistry,
)
from toolchainkit.toolchain.system_detector import (
    SystemToolchainDetector,
    SystemToolchain,
    CompilerVersionExtractor,
    PathSearcher,
    StandardLocationSearcher,
    RegistrySearcher,
    PackageManagerSearcher,
)

from toolchainkit.toolchain.upgrader import (
    ToolchainUpgrader,
    UpdateCheckError,
    UpdateInfo,
    UpgradeError,
    UpgradeResult,
    Version,
    VersionComparisonError,
    check_toolchainkit_updates,
    upgrade_toolchainkit,
)
from toolchainkit.toolchain.verifier import (
    ABICheck,
    CheckResult,
    CompileTestCheck,
    ExecutabilityCheck,
    FilePresenceCheck,
    SymlinkCheck,
    ToolchainSpec,
    ToolchainVerifier,
    VerificationLevel,
    VerificationResult,
    VersionCheck,
    verify_toolchain,
)

# For backward compatibility, export ToolchainNotFoundError as an alias
ToolchainNotFoundError = ToolchainMetadataNotFoundError

__all__ = [
    # Registry
    "ToolchainMetadata",
    "ToolchainMetadataRegistry",
    "ToolchainRegistryError",
    "ToolchainNotFoundError",
    "InvalidVersionError",
    # Downloader
    "ToolchainDownloader",
    "ToolchainDownloadError",
    "ToolchainExtractionError",
    "DownloadResult",
    "ProgressInfo",
    "download_toolchain",
    # Verifier
    "ToolchainVerifier",
    "VerificationLevel",
    "VerificationResult",
    "CheckResult",
    "ToolchainSpec",
    "verify_toolchain",
    "FilePresenceCheck",
    "ExecutabilityCheck",
    "VersionCheck",
    "ABICheck",
    "SymlinkCheck",
    "CompileTestCheck",
    # System Detector
    "SystemToolchainDetector",
    "SystemToolchain",
    "CompilerVersionExtractor",
    "PathSearcher",
    "StandardLocationSearcher",
    "RegistrySearcher",
    "PackageManagerSearcher",
    # Upgrader
    "ToolchainUpgrader",
    "Version",
    "UpdateInfo",
    "UpgradeResult",
    "UpgradeError",
    "VersionComparisonError",
    "UpdateCheckError",
    "check_toolchainkit_updates",
    "upgrade_toolchainkit",
]
