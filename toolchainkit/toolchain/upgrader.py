"""
Toolchain upgrade orchestration.

This module provides functionality to upgrade toolchains and ToolchainKit itself
to the latest available versions. It handles version checking, downloading,
verification, and safe replacement of existing installations.
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import requests

from .metadata_registry import ToolchainMetadataRegistry
from .downloader import ToolchainDownloader
from .verifier import ToolchainVerifier, VerificationLevel
from ..core.cache_registry import ToolchainCacheRegistry
from ..core.directory import get_global_cache_dir
from ..core.locking import LockManager
from ..core.exceptions import ToolchainMetadataNotFoundError

logger = logging.getLogger(__name__)


class UpgradeError(Exception):
    """Base exception for upgrade errors."""

    pass


class VersionComparisonError(UpgradeError):
    """Error comparing versions."""

    pass


class UpdateCheckError(UpgradeError):
    """Error checking for updates."""

    pass


class Version:
    """
    Semantic version parser and comparator.

    Supports semantic versioning in format: major.minor.patch
    Examples: "18.1.8", "13.2.0", "1.0.0"

    Example:
        >>> v1 = Version("18.1.8")
        >>> v2 = Version("18.1.10")
        >>> v2 > v1
        True
    """

    def __init__(self, version_string: str):
        """
        Parse version string.

        Args:
            version_string: Version in format "major.minor.patch" or "major.minor"

        Raises:
            VersionComparisonError: If version format is invalid
        """
        self.original = version_string
        self.major, self.minor, self.patch = self._parse(version_string)

    def _parse(self, version_string: str) -> tuple[int, int, int]:
        """
        Parse version string into components.

        Args:
            version_string: Version string to parse

        Returns:
            Tuple of (major, minor, patch)

        Raises:
            VersionComparisonError: If format is invalid
        """
        # Remove leading 'v' if present
        version_string = version_string.lstrip("v")

        # Split by dots
        parts = version_string.split(".")

        if len(parts) < 2 or len(parts) > 3:
            raise VersionComparisonError(
                f"Invalid version format: {version_string}. "
                f"Expected format: major.minor.patch or major.minor"
            )

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2]) if len(parts) == 3 else 0
        except ValueError as e:
            raise VersionComparisonError(
                f"Invalid version format: {version_string}. "
                f"Version parts must be integers."
            ) from e

        return major, minor, patch

    def __lt__(self, other: "Version") -> bool:
        """Less than comparison."""
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: "Version") -> bool:
        """Less than or equal comparison."""
        return (self.major, self.minor, self.patch) <= (
            other.major,
            other.minor,
            other.patch,
        )

    def __gt__(self, other: "Version") -> bool:
        """Greater than comparison."""
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: "Version") -> bool:
        """Greater than or equal comparison."""
        return (self.major, self.minor, self.patch) >= (
            other.major,
            other.minor,
            other.patch,
        )

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    def __ne__(self, other: object) -> bool:
        """Inequality comparison."""
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__eq__(other)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Version('{self}')"


@dataclass
class UpdateInfo:
    """Information about an available update."""

    current_version: str
    """Currently installed version"""

    latest_version: str
    """Latest available version"""

    download_url: str
    """Download URL for latest version"""

    sha256: str
    """SHA256 checksum"""

    size_mb: int
    """Download size in megabytes"""


@dataclass
class UpgradeResult:
    """Result of an upgrade operation."""

    toolchain_id: str
    """Toolchain identifier"""

    old_version: str
    """Previous version"""

    new_version: str
    """New version after upgrade"""

    success: bool
    """Whether upgrade succeeded"""

    error: Optional[str] = None
    """Error message if failed"""


class ToolchainUpgrader:
    """
    Orchestrates toolchain upgrade operations.

    Handles version checking, downloading, verification, and safe replacement
    of existing toolchain installations. Preserves project references and
    ensures atomic upgrades.

    Example:
        >>> upgrader = ToolchainUpgrader()
        >>>
        >>> # Check for updates
        >>> update = upgrader.check_for_updates("llvm-18.1.8-linux-x64")
        >>> if update:
        >>>     print(f"Update available: {update.latest_version}")
        >>>
        >>> # Upgrade toolchain
        >>> result = upgrader.upgrade_toolchain("llvm-18.1.8-linux-x64")
        >>> if result.success:
        >>>     print(f"Upgraded to {result.new_version}")
    """

    def __init__(self):
        """Initialize toolchain upgrader."""
        self.metadata_registry = ToolchainMetadataRegistry()
        self.cache_registry = ToolchainCacheRegistry(
            get_global_cache_dir() / "registry.json"
        )
        self.downloader = ToolchainDownloader()
        self.verifier = ToolchainVerifier()
        self.lock_manager = LockManager()
        logger.debug("ToolchainUpgrader initialized")

    def check_for_updates(self, toolchain_id: str) -> Optional[UpdateInfo]:
        """
        Check if update is available for toolchain.

        Args:
            toolchain_id: Toolchain identifier (e.g., "llvm-18.1.8-linux-x64")

        Returns:
            UpdateInfo if update available, None if already latest

        Raises:
            UpdateCheckError: If unable to check for updates
        """
        logger.debug(f"Checking for updates: {toolchain_id}")

        # Get current toolchain info from cache registry
        with self.cache_registry.lock():
            current_info = self.cache_registry.get_toolchain_info(toolchain_id)

        if not current_info:
            raise UpdateCheckError(f"Toolchain not found: {toolchain_id}")

        # Parse toolchain ID to extract type and current version
        # Format: <type>-<version>-<platform>
        parts = toolchain_id.split("-")
        if len(parts) < 3:
            raise UpdateCheckError(f"Invalid toolchain ID format: {toolchain_id}")

        toolchain_type = parts[0]  # e.g., "llvm"
        current_version = parts[1]  # e.g., "18.1.8"
        platform_parts = parts[2:]  # e.g., ["linux", "x64"]
        platform = "-".join(platform_parts)

        # Query metadata registry for latest version
        try:
            # Get all versions for this toolchain type
            versions = self.metadata_registry.list_versions(toolchain_type)

            if not versions:
                logger.debug(f"No versions found for {toolchain_type}")
                return None

            # Check which versions are available for this platform
            available_versions = []
            for ver in versions:
                if self.metadata_registry.is_compatible(toolchain_type, ver, platform):
                    available_versions.append(ver)

            if not available_versions:
                logger.debug(
                    f"No versions available for {toolchain_type} on {platform}"
                )
                return None

            # Find latest version
            latest_version = max(available_versions, key=Version)

            # Compare versions
            current_ver = Version(current_version)
            latest_ver = Version(latest_version)

            if latest_ver <= current_ver:
                logger.debug(f"{toolchain_id} is up to date")
                return None

            # Get metadata for latest version
            metadata = self.metadata_registry.lookup(
                toolchain_type, latest_version, platform
            )

            return UpdateInfo(
                current_version=current_version,
                latest_version=latest_version,
                download_url=metadata.url,
                sha256=metadata.sha256,
                size_mb=metadata.size_mb,
            )

        except ToolchainMetadataNotFoundError as e:
            raise UpdateCheckError(f"Failed to check for updates: {e}") from e
        except VersionComparisonError as e:
            raise UpdateCheckError(f"Failed to compare versions: {e}") from e

    def upgrade_toolchain(
        self, toolchain_id: str, force: bool = False, progress_callback=None
    ) -> UpgradeResult:
        """
        Upgrade a specific toolchain to latest version.

        Args:
            toolchain_id: Toolchain to upgrade (e.g., "llvm-18.1.8-linux-x64")
            force: Force re-download even if already latest
            progress_callback: Optional progress callback function

        Returns:
            UpgradeResult with upgrade details

        Raises:
            UpgradeError: If upgrade fails
        """
        logger.info(f"Upgrading toolchain: {toolchain_id}")

        # Parse toolchain ID
        parts = toolchain_id.split("-")
        if len(parts) < 3:
            return UpgradeResult(
                toolchain_id=toolchain_id,
                old_version="unknown",
                new_version="unknown",
                success=False,
                error=f"Invalid toolchain ID format: {toolchain_id}",
            )

        toolchain_type = parts[0]
        current_version = parts[1]
        platform = "-".join(parts[2:])

        try:
            # Check for updates
            if not force:
                update_info = self.check_for_updates(toolchain_id)
                if not update_info:
                    logger.info(f"{toolchain_id} is already up to date")
                    return UpgradeResult(
                        toolchain_id=toolchain_id,
                        old_version=current_version,
                        new_version=current_version,
                        success=True,
                    )
            else:
                # Force upgrade - get latest version
                versions = self.metadata_registry.list_versions(toolchain_type)
                if not versions:
                    raise UpgradeError(f"No versions available for {toolchain_type}")

                # Filter by platform compatibility
                available_versions = [
                    ver
                    for ver in versions
                    if self.metadata_registry.is_compatible(
                        toolchain_type, ver, platform
                    )
                ]
                if not available_versions:
                    raise UpgradeError(
                        f"No versions available for {toolchain_type} on {platform}"
                    )

                latest_version = max(available_versions, key=Version)
                metadata = self.metadata_registry.lookup(
                    toolchain_type, latest_version, platform
                )

                update_info = UpdateInfo(
                    current_version=current_version,
                    latest_version=latest_version,
                    download_url=metadata.url,
                    sha256=metadata.sha256,
                    size_mb=metadata.size_mb,
                )

            new_toolchain_id = (
                f"{toolchain_type}-{update_info.latest_version}-{platform}"
            )

            # Download and install new version
            logger.info(f"Downloading {new_toolchain_id}...")
            toolchain_path = self.downloader.download_and_install(
                toolchain_id=new_toolchain_id,
                url=update_info.download_url,
                checksum=f"sha256:{update_info.sha256}",
                progress_callback=progress_callback,
            )

            # Verify new installation
            logger.info(f"Verifying {new_toolchain_id}...")
            verification = self.verifier.verify(
                toolchain_path=toolchain_path,
                toolchain_type=toolchain_type,
                expected_version=update_info.latest_version,
                level=VerificationLevel.STANDARD,
            )

            if not verification.success:
                raise UpgradeError(
                    f"Verification failed: {verification.error}. "
                    f"Issues: {', '.join(verification.issues)}"
                )

            # Get project references from old toolchain
            with self.cache_registry.lock():
                old_info = self.cache_registry.get_toolchain_info(toolchain_id)
                if old_info:
                    # Transfer references to new toolchain
                    new_info = self.cache_registry.get_toolchain_info(new_toolchain_id)
                    if new_info and old_info.get("projects"):
                        for project_path in old_info["projects"]:
                            self.cache_registry.add_project_reference(
                                toolchain_id=new_toolchain_id,
                                project_path=Path(project_path),
                            )

                    # Remove old toolchain if no longer referenced
                    if not old_info.get("projects"):
                        logger.info(f"Removing old version: {toolchain_id}")
                        self.cache_registry.unregister_toolchain(toolchain_id)

                        # Delete old toolchain directory
                        old_path = Path(old_info["path"])
                        if old_path.exists():
                            from ..core.filesystem import safe_rmtree

                            safe_rmtree(old_path, require_prefix=get_global_cache_dir())

            logger.info(f"Successfully upgraded to {new_toolchain_id}")

            return UpgradeResult(
                toolchain_id=toolchain_id,
                old_version=current_version,
                new_version=update_info.latest_version,
                success=True,
            )

        except Exception as e:
            error_msg = f"Upgrade failed: {str(e)}"
            logger.error(error_msg)
            return UpgradeResult(
                toolchain_id=toolchain_id,
                old_version=current_version,
                new_version="unknown",
                success=False,
                error=error_msg,
            )

    def upgrade_all_toolchains(
        self, force: bool = False, progress_callback=None
    ) -> List[UpgradeResult]:
        """
        Upgrade all installed toolchains.

        Args:
            force: Force re-download even if already latest
            progress_callback: Optional progress callback function

        Returns:
            List of UpgradeResult for each toolchain
        """
        logger.info("Checking all toolchains for updates...")

        # Get all installed toolchains
        with self.cache_registry.lock():
            toolchain_ids = self.cache_registry.list_toolchains()

        if not toolchain_ids:
            logger.info("No toolchains installed")
            return []

        results = []

        for toolchain_id in toolchain_ids:
            # Check for updates
            try:
                if not force:
                    update_info = self.check_for_updates(toolchain_id)
                    if not update_info:
                        logger.debug(f"{toolchain_id} is up to date")
                        continue

                # Upgrade this toolchain
                result = self.upgrade_toolchain(
                    toolchain_id=toolchain_id,
                    force=force,
                    progress_callback=progress_callback,
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to upgrade {toolchain_id}: {e}")
                results.append(
                    UpgradeResult(
                        toolchain_id=toolchain_id,
                        old_version="unknown",
                        new_version="unknown",
                        success=False,
                        error=str(e),
                    )
                )

        return results


def check_toolchainkit_updates() -> Optional[tuple[str, str]]:
    """
    Check if ToolchainKit update is available on PyPI.

    Returns:
        Tuple of (current_version, latest_version) if update available,
        None if already latest or unable to check
    """
    try:
        # Get current version
        try:
            from importlib.metadata import version

            current_version = version("toolchainkit")
        except Exception:
            current_version = "0.1.0"

        # Query PyPI JSON API
        url = "https://pypi.org/pypi/toolchainkit/json"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"Failed to check PyPI: {e}")
            return None

        latest_version = data["info"]["version"]

        # Compare versions
        try:
            current_ver = Version(current_version)
            latest_ver = Version(latest_version)

            if latest_ver > current_ver:
                return (current_version, latest_version)
        except VersionComparisonError:
            logger.warning(
                f"Unable to compare versions: {current_version} vs {latest_version}"
            )

        return None

    except Exception as e:
        logger.debug(f"Error checking for ToolchainKit updates: {e}")
        return None


def upgrade_toolchainkit() -> bool:
    """
    Upgrade ToolchainKit using pip.

    Returns:
        True if upgrade successful, False otherwise
    """
    try:
        logger.info("Upgrading ToolchainKit...")

        # Run pip upgrade
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "toolchainkit"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info("ToolchainKit upgraded successfully")
            return True
        else:
            logger.error(f"Upgrade failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Upgrade timed out")
        return False
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        return False
