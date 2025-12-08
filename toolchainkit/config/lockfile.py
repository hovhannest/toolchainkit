"""
Lock file generation and verification for ToolchainKit.

This module provides lock file generation that records exact versions and
cryptographic hashes of all dependencies (toolchains, build tools, packages)
for reproducible builds and supply chain security.

Example:
    >>> from pathlib import Path
    >>> from toolchainkit.config.lockfile import LockFileManager
    >>>
    >>> # Generate lock file
    >>> manager = LockFileManager(Path('/path/to/project'))
    >>> lock = manager.generate(config, platform_info, toolchain_info)
    >>> manager.save(lock)
    >>>
    >>> # Verify installation
    >>> lock = manager.load()
    >>> verified, issues = manager.verify(lock)
    >>> if not verified:
    >>>     for issue in issues:
    >>>         print(f"⚠ {issue}")
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class LockFileError(Exception):
    """Base exception for lock file errors."""

    pass


class LockFileVerificationError(LockFileError):
    """Raised when lock file verification fails."""

    pass


@dataclass
class LockedComponent:
    """
    A locked component (toolchain, build tool, or package).

    Attributes:
        url: Download URL for the component
        sha256: SHA256 hash of the component
        size_bytes: Size in bytes
        version: Component version (optional)
        verified: Whether component has been verified
        verification_date: ISO 8601 timestamp of verification
    """

    url: str
    sha256: str
    size_bytes: int
    version: Optional[str] = None
    verified: bool = False
    verification_date: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        data = {
            "url": self.url,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }
        if self.version is not None:
            data["version"] = self.version
        if self.verified:
            data["verified"] = self.verified
        if self.verification_date is not None:
            data["verification_date"] = self.verification_date
        return data

    @staticmethod
    def from_dict(data: dict) -> "LockedComponent":
        """Create from dictionary loaded from YAML."""
        return LockedComponent(
            url=data["url"],
            sha256=data["sha256"],
            size_bytes=data["size_bytes"],
            version=data.get("version"),
            verified=data.get("verified", False),
            verification_date=data.get("verification_date"),
        )


@dataclass
class LockFile:
    """
    Complete lock file structure.

    Attributes:
        version: Lock file format version (currently 1)
        generated: ISO 8601 timestamp of generation
        platform: Platform string (e.g., 'linux-x64-glibc')
        toolchains: Dict of toolchain_id -> LockedComponent
        build_tools: Dict of tool_name -> LockedComponent
        packages: Dict of package_name -> package info
        metadata: Additional metadata
    """

    version: int = 1
    generated: Optional[str] = None
    platform: Optional[str] = None
    toolchains: Dict[str, LockedComponent] = field(default_factory=dict)
    build_tools: Dict[str, LockedComponent] = field(default_factory=dict)
    packages: Dict[str, dict] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        data = {
            "version": self.version,
            "generated": self.generated,
            "platform": self.platform,
            "toolchains": {},
            "build_tools": {},
            "packages": self.packages,
            "metadata": self.metadata,
        }

        # Convert toolchains
        for name, component in self.toolchains.items():
            data["toolchains"][name] = component.to_dict()  # type: ignore[index]

        # Convert build tools
        for name, component in self.build_tools.items():
            data["build_tools"][name] = component.to_dict()  # type: ignore[index]

        return data

    @staticmethod
    def from_dict(data: dict) -> "LockFile":
        """Create from dictionary loaded from YAML."""
        # Parse toolchains
        toolchains = {}
        for name, comp_data in data.get("toolchains", {}).items():
            toolchains[name] = LockedComponent.from_dict(comp_data)

        # Parse build tools
        build_tools = {}
        for name, comp_data in data.get("build_tools", {}).items():
            build_tools[name] = LockedComponent.from_dict(comp_data)

        return LockFile(
            version=data.get("version", 1),
            generated=data.get("generated"),
            platform=data.get("platform"),
            toolchains=toolchains,
            build_tools=build_tools,
            packages=data.get("packages", {}),
            metadata=data.get("metadata", {}),
        )


class LockFileManager:
    """
    Manages toolchainkit.lock file generation and verification.

    LockFileManager provides high-level API for creating and verifying lock files
    that record exact versions and hashes of all dependencies for reproducible builds.

    Example:
        >>> from pathlib import Path
        >>> from toolchainkit.config.lockfile import LockFileManager
        >>>
        >>> # Initialize
        >>> manager = LockFileManager(Path('/path/to/project'))
        >>>
        >>> # Generate lock file
        >>> lock = manager.generate(config, platform, toolchain_info)
        >>> manager.save(lock)
        >>>
        >>> # Verify installation
        >>> lock = manager.load()
        >>> verified, issues = manager.verify(lock)

    Attributes:
        project_root: Project root directory
        lock_file_path: Path to toolchainkit.lock file
    """

    def __init__(self, project_root: Path):
        """
        Initialize lock file manager.

        Args:
            project_root: Project root directory

        Raises:
            LockFileError: If project_root is not a valid directory
        """
        if not isinstance(project_root, Path):
            project_root = Path(project_root)

        if not project_root.exists():
            raise LockFileError(
                f"Project root does not exist: {project_root}. "
                f"Ensure the directory exists before initializing LockFileManager."
            )

        if not project_root.is_dir():
            raise LockFileError(
                f"Project root is not a directory: {project_root}. "
                f"Expected a valid directory path."
            )

        self.project_root = project_root.resolve()
        self.lock_file_path = self.project_root / "toolchainkit.lock"

    def generate(
        self,
        config,  # ToolchainKitConfig
        platform,  # PlatformInfo
        toolchain_info: Dict[str, dict],
        build_tools_info: Optional[Dict[str, dict]] = None,
    ) -> LockFile:
        """
        Generate lock file from current configuration.

        Args:
            config: Parsed configuration (ToolchainKitConfig)
            platform: Current platform info (PlatformInfo)
            toolchain_info: Dict of toolchain_id -> component info
                           (must include: url, sha256, size_bytes, version)
            build_tools_info: Dict of tool_name -> component info (optional)

        Returns:
            Generated lock file

        Example:
            >>> toolchain_info = {
            ...     'llvm-18.1.8': {
            ...         'url': 'https://...',
            ...         'sha256': 'abc123...',
            ...         'size_bytes': 2147483648,
            ...         'version': '18.1.8'
            ...     }
            ... }
            >>> lock = manager.generate(config, platform, toolchain_info)
        """
        lock = LockFile(
            version=1,
            generated=datetime.now().isoformat(),
            platform=self._get_platform_string(platform),
        )

        # Add toolchains
        for toolchain_id, info in toolchain_info.items():
            lock.toolchains[toolchain_id] = LockedComponent(
                url=info["url"],
                sha256=info["sha256"],
                size_bytes=info["size_bytes"],
                version=info.get("version"),
                verified=True,
                verification_date=datetime.now().isoformat(),
            )
            logger.debug(f"Added toolchain to lock file: {toolchain_id}")

        # Add build tools
        if build_tools_info:
            for tool_name, info in build_tools_info.items():
                lock.build_tools[tool_name] = LockedComponent(
                    url=info["url"],
                    sha256=info["sha256"],
                    size_bytes=info["size_bytes"],
                    version=info.get("version"),
                    verified=True,
                    verification_date=datetime.now().isoformat(),
                )
                logger.debug(f"Added build tool to lock file: {tool_name}")

        # Add metadata
        lock.metadata = {
            "generator": "ToolchainKit 0.1.0",
            "config_hash": self._compute_config_hash(),
            "python_version": self._get_python_version(),
        }

        logger.info(
            f"Generated lock file with {len(lock.toolchains)} toolchains, "
            f"{len(lock.build_tools)} build tools"
        )

        return lock

    def save(self, lock: LockFile):
        """
        Save lock file to disk in YAML format.

        Args:
            lock: Lock file to save

        Example:
            >>> lock = manager.generate(config, platform, toolchain_info)
            >>> manager.save(lock)
        """
        # Convert to dict
        data = lock.to_dict()

        # Write to file
        with open(self.lock_file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Lock file saved: {self.lock_file_path}")

    def load(self) -> Optional[LockFile]:
        """
        Load lock file from disk.

        Returns:
            Loaded lock file, or None if doesn't exist

        Raises:
            LockFileError: If lock file is corrupted

        Example:
            >>> lock = manager.load()
            >>> if lock:
            ...     print(f"Platform: {lock.platform}")
        """
        if not self.lock_file_path.exists():
            logger.debug(f"Lock file not found: {self.lock_file_path}")
            return None

        try:
            with open(self.lock_file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            lock = LockFile.from_dict(data)
            logger.debug(f"Loaded lock file: {self.lock_file_path}")
            return lock

        except (yaml.YAMLError, TypeError, KeyError) as e:
            raise LockFileError(
                f"Failed to load lock file {self.lock_file_path}: {e}. "
                f"The lock file may be corrupted or in an invalid format."
            ) from e

    def verify(self, lock: LockFile) -> tuple[bool, list[str]]:
        """
        Verify current installation matches lock file.

        Args:
            lock: Lock file to verify against

        Returns:
            Tuple of (verified: bool, issues: list[str])

        Example:
            >>> lock = manager.load()
            >>> verified, issues = manager.verify(lock)
            >>> if not verified:
            ...     for issue in issues:
            ...         print(f"⚠ {issue}")
        """
        issues = []

        # Verify toolchains
        for toolchain_id, expected in lock.toolchains.items():
            try:
                from toolchainkit.core.cache_registry import ToolchainCacheRegistry
                from toolchainkit.core.directory import get_global_cache_dir

                # Get installed toolchain
                cache_dir = get_global_cache_dir()
                registry_file = cache_dir / "registry.json"
                registry = ToolchainCacheRegistry(registry_file)

                info = registry.get_toolchain_info(toolchain_id)

                if not info:
                    issues.append(
                        f"Toolchain not installed: {toolchain_id}. "
                        f"Expected from lock file but not found in registry."
                    )
                    continue

                # Verify hash if available
                installed_hash = info.get("hash", "")
                if installed_hash and installed_hash != expected.sha256:
                    issues.append(
                        f"Toolchain hash mismatch: {toolchain_id}\n"
                        f"  Expected: {expected.sha256}\n"
                        f"  Got: {installed_hash}\n"
                        f"  This may indicate tampering or incorrect installation."
                    )

            except ImportError:
                logger.warning(
                    "Registry module not available, skipping toolchain verification"
                )
            except Exception as e:
                logger.warning(f"Error verifying toolchain {toolchain_id}: {e}")

        # Verify build tools
        for tool_name, expected in lock.build_tools.items():
            tool_path = self._find_tool_path(tool_name)

            if not tool_path:
                issues.append(
                    f"Build tool not installed: {tool_name}. "
                    f"Expected from lock file but not found."
                )
                continue

            # Verify hash
            try:
                from toolchainkit.core.verification import compute_file_hash

                actual_hash = compute_file_hash(tool_path, algorithm="sha256")
                if (
                    f"sha256:{actual_hash}" != expected.sha256
                    and actual_hash != expected.sha256
                ):
                    # Handle both 'sha256:...' and plain hash formats
                    expected_hash_clean = expected.sha256.replace("sha256:", "")
                    if actual_hash != expected_hash_clean:
                        issues.append(
                            f"Build tool hash mismatch: {tool_name}\n"
                            f"  Expected: {expected.sha256}\n"
                            f"  Got: sha256:{actual_hash}\n"
                            f"  This may indicate tampering or incorrect installation."
                        )
            except Exception as e:
                logger.warning(f"Error verifying build tool {tool_name}: {e}")

        verified = len(issues) == 0
        if verified:
            logger.info("Lock file verification passed")
        else:
            logger.warning(f"Lock file verification failed with {len(issues)} issues")

        return verified, issues

    def diff(self, old_lock: LockFile, new_lock: LockFile) -> dict:
        """
        Compute differences between two lock files.

        Args:
            old_lock: Old lock file
            new_lock: New lock file

        Returns:
            Dict describing changes with keys: toolchains, build_tools
            Each containing: added, removed, modified lists

        Example:
            >>> old_lock = manager.load()
            >>> new_lock = manager.generate(config, platform, new_toolchain_info)
            >>> changes = manager.diff(old_lock, new_lock)
            >>> print(f"Added: {changes['toolchains']['added']}")
        """
        changes: Dict[str, Dict[str, list]] = {
            "toolchains": {"added": [], "removed": [], "modified": []},
            "build_tools": {"added": [], "removed": [], "modified": []},
        }

        # Check toolchains
        old_ids = set(old_lock.toolchains.keys())
        new_ids = set(new_lock.toolchains.keys())

        changes["toolchains"]["added"] = list(new_ids - old_ids)
        changes["toolchains"]["removed"] = list(old_ids - new_ids)

        for tc_id in old_ids & new_ids:
            old_comp = old_lock.toolchains[tc_id]
            new_comp = new_lock.toolchains[tc_id]
            if old_comp.sha256 != new_comp.sha256:
                changes["toolchains"]["modified"].append(
                    {
                        "name": tc_id,
                        "old_version": old_comp.version,
                        "new_version": new_comp.version,
                        "old_hash": old_comp.sha256,
                        "new_hash": new_comp.sha256,
                    }
                )

        # Check build tools
        old_tools = set(old_lock.build_tools.keys())
        new_tools = set(new_lock.build_tools.keys())

        changes["build_tools"]["added"] = list(new_tools - old_tools)
        changes["build_tools"]["removed"] = list(old_tools - new_tools)

        for tool in old_tools & new_tools:
            old_comp = old_lock.build_tools[tool]
            new_comp = new_lock.build_tools[tool]
            if old_comp.sha256 != new_comp.sha256:
                changes["build_tools"]["modified"].append(
                    {
                        "name": tool,
                        "old_version": old_comp.version,
                        "new_version": new_comp.version,
                        "old_hash": old_comp.sha256,
                        "new_hash": new_comp.sha256,
                    }
                )

        logger.debug(
            f"Lock file diff: {len(changes['toolchains']['added'])} toolchains added, "
            f"{len(changes['toolchains']['removed'])} removed, "
            f"{len(changes['toolchains']['modified'])} modified"
        )

        return changes

    def _find_tool_path(self, tool_name: str) -> Optional[Path]:
        """
        Find path to installed build tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Path to tool if found, None otherwise
        """
        # Check .toolchainkit/tools/
        tools_dir = self.project_root / ".toolchainkit" / "tools"

        if os.name == "nt":
            tool_path = tools_dir / f"{tool_name}.exe"
        else:
            tool_path = tools_dir / tool_name

        if tool_path.exists():
            return tool_path

        # Check global cache
        try:
            from toolchainkit.core.directory import get_global_cache_dir

            global_tools = get_global_cache_dir() / "tools"
            if os.name == "nt":
                tool_path = global_tools / f"{tool_name}.exe"
            else:
                tool_path = global_tools / tool_name

            if tool_path.exists():
                return tool_path
        except ImportError:
            pass

        return None

    def _get_platform_string(self, platform) -> str:
        """Get platform string from PlatformInfo."""
        if hasattr(platform, "platform_string"):
            return platform.platform_string()
        return str(platform)

    def _compute_config_hash(self) -> str:
        """Compute hash of configuration file."""
        try:
            from toolchainkit.core.state import compute_config_hash

            config_file = self.project_root / "toolchainkit.yaml"
            return compute_config_hash(config_file)
        except ImportError:
            return "unknown"

    def _get_python_version(self) -> str:
        """Get Python version string."""
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
