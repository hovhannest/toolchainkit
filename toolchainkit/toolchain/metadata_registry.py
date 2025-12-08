"""
Toolchain registry and metadata management.

This module provides a registry of available toolchains with download URLs,
versions, and platform compatibility information. It enables version resolution
and platform-specific toolchain lookups.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from toolchainkit.core.exceptions import (
    ToolchainRegistryError,
    InvalidVersionError,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolchainMetadata:
    """Metadata for a specific toolchain version/platform combination."""

    url: str
    """Download URL for the toolchain archive"""

    sha256: str
    """SHA256 checksum of the archive"""

    size_mb: int
    """Approximate size in megabytes"""

    stdlib: List[str] = field(default_factory=list)
    """Supported standard libraries (e.g., libc++, libstdc++)"""

    requires_installer: bool = False
    """Whether this is an installer executable (e.g., MSVC)"""

    def __post_init__(self):
        """Validate metadata after initialization."""
        if not self.url:
            raise ValueError("URL cannot be empty")
        if not self.sha256:
            raise ValueError("SHA256 cannot be empty")
        if self.size_mb <= 0:
            raise ValueError("Size must be positive")


class ToolchainMetadataRegistry:
    """
    Registry of available toolchains with version resolution and platform lookup.

    The registry loads toolchain metadata from an embedded JSON file and provides
    methods to query available toolchains, resolve version patterns, and lookup
    platform-specific download information.

    Example:
        >>> registry = ToolchainMetadataRegistry()
        >>> metadata = registry.lookup("llvm", "18.1.8", "linux-x64")
        >>> print(metadata.url)
        https://github.com/llvm/llvm-project/releases/...
    """

    def __init__(self, metadata_path: Optional[Path] = None):
        """
        Initialize toolchain registry.

        Args:
            metadata_path: Optional path to metadata JSON file.
                          If None, uses embedded toolchains.json

        Raises:
            ToolchainRegistryError: If metadata file cannot be loaded
        """
        self.metadata_path = metadata_path or self._get_default_metadata_path()
        self.metadata = self._load_metadata()
        logger.debug(f"Loaded registry with {len(self.list_toolchains())} toolchains")

    def _get_default_metadata_path(self) -> Path:
        """Get path to default embedded metadata file."""
        # Path relative to this module: ../data/toolchains.json
        return Path(__file__).parent.parent / "data" / "toolchains.json"

    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load toolchain metadata from JSON file.

        Returns:
            Parsed metadata dictionary

        Raises:
            ToolchainRegistryError: If file cannot be loaded or parsed
        """
        if not self.metadata_path.exists():
            raise ToolchainRegistryError(
                f"Metadata file not found: {self.metadata_path}\n"
                f"This file should contain toolchain definitions."
            )

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ToolchainRegistryError(
                f"Invalid JSON in metadata file: {e}\n" f"File: {self.metadata_path}"
            ) from e
        except Exception as e:
            raise ToolchainRegistryError(
                f"Failed to load metadata file: {e}\n" f"File: {self.metadata_path}"
            ) from e

        # Validate structure
        if "toolchains" not in data:
            raise ToolchainRegistryError(
                f"Invalid metadata structure: missing 'toolchains' key\n"
                f"File: {self.metadata_path}"
            )

        return data

    def lookup(
        self, toolchain_name: str, version: str, platform: str
    ) -> Optional[ToolchainMetadata]:
        """
        Look up toolchain metadata for specific version and platform.

        Args:
            toolchain_name: Name of toolchain (e.g., "llvm", "gcc")
            version: Version string or pattern (e.g., "18.1.8", "18", "latest")
            platform: Platform string (e.g., "linux-x64", "windows-x64")

        Returns:
            ToolchainMetadata if found, None otherwise

        Raises:
            InvalidVersionError: If version pattern is invalid

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> metadata = registry.lookup("llvm", "18", "linux-x64")
            >>> if metadata:
            ...     print(f"Found: {metadata.url}")
        """
        toolchains = self.metadata.get("toolchains", {})

        # Check if toolchain exists
        if toolchain_name not in toolchains:
            logger.debug(f"Toolchain not found: {toolchain_name}")
            return None

        tc = toolchains[toolchain_name]
        versions = tc.get("versions", {})

        # Try exact version first
        if version in versions:
            resolved_version = version
        else:
            # Try version resolution
            resolved_version = self.resolve_version(toolchain_name, version)
            if not resolved_version:
                logger.debug(f"Version not found: {toolchain_name} {version}")
                return None

        # Get platform-specific data
        platforms = versions.get(resolved_version, {})
        if platform not in platforms:
            logger.debug(
                f"Platform not found: {toolchain_name} {resolved_version} {platform}"
            )
            return None

        data = platforms[platform]

        # Create metadata object
        try:
            return ToolchainMetadata(
                url=data["url"],
                sha256=data["sha256"],
                size_mb=data["size_mb"],
                stdlib=data.get("stdlib", []),
                requires_installer=data.get("requires_installer", False),
            )
        except (KeyError, ValueError) as e:
            raise ToolchainRegistryError(
                f"Invalid metadata for {toolchain_name} {resolved_version} {platform}: {e}"
            ) from e

    def resolve_version(self, toolchain_name: str, pattern: str) -> Optional[str]:
        """
        Resolve version pattern to specific version.

        Supports:
        - Exact version: "18.1.8" → "18.1.8"
        - Major.minor: "18.1" → "18.1.8" (latest patch)
        - Major only: "18" → "18.1.8" (latest minor.patch)
        - Latest: "latest" → highest version

        Args:
            toolchain_name: Name of toolchain
            pattern: Version pattern to resolve

        Returns:
            Resolved version string or None if not found

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> registry.resolve_version("llvm", "18")
            '18.1.8'
        """
        versions = self.list_versions(toolchain_name)
        if not versions:
            return None

        # Handle "latest" keyword
        if pattern.lower() == "latest":
            return self._get_latest_version(versions)

        # Try exact match first
        if pattern in versions:
            return pattern

        # Parse version pattern
        parts = pattern.split(".")
        if not parts or not parts[0].isdigit():
            raise InvalidVersionError(
                f"Invalid version pattern: {pattern}\n"
                f"Expected format: X.Y.Z, X.Y, X, or 'latest'"
            )

        # Filter matching versions
        matching = []
        if len(parts) == 1:
            # Major only (e.g., "18")
            matching = [v for v in versions if v.startswith(f"{parts[0]}.")]
        elif len(parts) == 2:
            # Major.minor (e.g., "18.1")
            matching = [v for v in versions if v.startswith(f"{parts[0]}.{parts[1]}.")]

        if matching:
            return self._get_latest_version(matching)

        return None

    def _get_latest_version(self, versions: List[str]) -> str:
        """
        Get latest version from list using semantic versioning.

        Args:
            versions: List of version strings

        Returns:
            Latest version string
        """

        def version_key(v: str) -> tuple:
            """Convert version string to sortable tuple."""
            parts = v.split(".")
            try:
                return tuple(int(p) for p in parts)
            except ValueError:
                # Fallback for non-numeric parts
                return tuple(0 if not p.isdigit() else int(p) for p in parts)

        return max(versions, key=version_key)

    def list_versions(self, toolchain_name: str) -> List[str]:
        """
        List all available versions for a toolchain.

        Args:
            toolchain_name: Name of toolchain

        Returns:
            List of version strings, sorted

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> versions = registry.list_versions("llvm")
            >>> print(versions)
            ['18.1.8', '17.0.6', '16.0.6']
        """
        toolchains = self.metadata.get("toolchains", {})
        if toolchain_name not in toolchains:
            return []

        versions = list(toolchains[toolchain_name].get("versions", {}).keys())
        # Sort in descending order (newest first)
        versions.sort(
            key=lambda v: tuple(int(p) if p.isdigit() else 0 for p in v.split(".")),
            reverse=True,
        )
        return versions

    def list_toolchains(self) -> List[str]:
        """
        List all available toolchain names.

        Returns:
            List of toolchain names

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> toolchains = registry.list_toolchains()
            >>> print(toolchains)
            ['llvm', 'gcc']
        """
        return list(self.metadata.get("toolchains", {}).keys())

    def list_platforms(self, toolchain_name: str, version: str) -> List[str]:
        """
        List available platforms for a toolchain version.

        Args:
            toolchain_name: Name of toolchain
            version: Version string (resolved version)

        Returns:
            List of platform strings

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> platforms = registry.list_platforms("llvm", "18.1.8")
            >>> print(platforms)
            ['linux-x64', 'windows-x64', 'macos-x64', 'macos-arm64']
        """
        toolchains = self.metadata.get("toolchains", {})
        if toolchain_name not in toolchains:
            return []

        versions = toolchains[toolchain_name].get("versions", {})
        if version not in versions:
            return []

        return list(versions[version].keys())

    def is_compatible(self, toolchain_name: str, version: str, platform: str) -> bool:
        """
        Check if toolchain version is available for platform.

        Args:
            toolchain_name: Name of toolchain
            version: Version string or pattern
            platform: Platform string

        Returns:
            True if compatible, False otherwise

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> if registry.is_compatible("llvm", "18", "linux-x64"):
            ...     print("Compatible!")
        """
        return self.lookup(toolchain_name, version, platform) is not None

    def get_toolchain_type(self, toolchain_name: str) -> Optional[str]:
        """
        Get the type of a toolchain.

        Args:
            toolchain_name: Name of toolchain

        Returns:
            Type string (e.g., "clang", "gcc") or None

        Example:
            >>> registry = ToolchainMetadataRegistry()
            >>> registry.get_toolchain_type("llvm")
            'clang'
        """
        toolchains = self.metadata.get("toolchains", {})
        if toolchain_name not in toolchains:
            return None

        return toolchains[toolchain_name].get("type")


# Convenience function for quick lookups
def get_toolchain_metadata(
    toolchain_name: str, version: str, platform: str
) -> Optional[ToolchainMetadata]:
    """
    Convenience function to get toolchain metadata.

    This creates a registry instance and performs a lookup in one call.
    For multiple lookups, create a ToolchainMetadataRegistry instance and reuse it.

    Args:
        toolchain_name: Name of toolchain
        version: Version string or pattern
        platform: Platform string

    Returns:
        ToolchainMetadata if found, None otherwise

    Example:
        >>> from toolchainkit.toolchain.metadata_registry import get_toolchain_metadata
        >>> metadata = get_toolchain_metadata("llvm", "18", "linux-x64")
        >>> if metadata:
        ...     print(metadata.url)
    """
    registry = ToolchainMetadataRegistry()
    return registry.lookup(toolchain_name, version, platform)
