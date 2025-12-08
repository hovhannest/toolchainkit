"""
Shared cache registry for tracking toolchain installations and project references.

This module provides thread-safe registry management for the global toolchain cache,
enabling multiple projects to share toolchains while tracking usage through reference counting.
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from filelock import FileLock, Timeout

from toolchainkit.core.directory import get_global_cache_dir
from toolchainkit.core.filesystem import atomic_write
from toolchainkit.core.exceptions import (
    RegistryError,
    ToolchainNotInCacheError,
    ToolchainInUseError,
    RegistryLockTimeout,
)

logger = logging.getLogger(__name__)


class ToolchainCacheRegistry:
    """
    Manages global toolchain cache registry with thread-safe access.

    The registry tracks toolchain installations, project references, and metadata
    to enable shared caching and safe cleanup of unused toolchains.

    Example:
        >>> registry = ToolchainCacheRegistry()
        >>> registry.register_toolchain(
        ...     'llvm-18.1.8-linux-x64',
        ...     Path('/home/user/.toolchainkit/toolchains/llvm-18.1.8'),
        ...     2048.5,
        ...     'sha256:abc123...',
        ...     'https://github.com/llvm/...'
        ... )
        >>> registry.add_project_reference('llvm-18.1.8-linux-x64', Path('/home/user/project1'))
    """

    def __init__(self, registry_path: Optional[Path] = None, lock_timeout: int = 30):
        """
        Initialize toolchain registry.

        Args:
            registry_path: Path to registry.json (default: global cache dir)
            lock_timeout: Timeout in seconds for acquiring file lock
        """
        if registry_path is None:
            cache_dir = get_global_cache_dir()
            registry_path = cache_dir / "registry.json"

        self.registry_path = Path(registry_path)
        self.lock_path = self.registry_path.parent / "lock" / "registry.lock"
        self.lock_timeout = lock_timeout

        logger.debug(f"Initialized registry at {self.registry_path}")

    def _load_registry(self) -> dict:
        """
        Load registry from disk.

        Returns:
            Registry data dictionary
        """
        if not self.registry_path.exists():
            logger.debug("Registry file not found, creating new registry")
            return {
                "version": 1,
                "toolchains": {},
                "total_size_mb": 0.0,
                "last_cleanup": None,
            }

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate registry format
            if "version" not in data or "toolchains" not in data:
                logger.warning("Invalid registry format, resetting")
                return {
                    "version": 1,
                    "toolchains": {},
                    "total_size_mb": 0.0,
                    "last_cleanup": None,
                }

            return data

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load registry: {e}")
            raise RegistryError(f"Failed to load registry: {e}") from e

    def _save_registry(self, data: dict):
        """
        Save registry to disk atomically.

        Args:
            data: Registry data dictionary to save
        """
        try:
            # Ensure parent directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write to prevent corruption
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
            atomic_write(self.registry_path, json_content)

            logger.debug(f"Saved registry with {len(data['toolchains'])} toolchains")

        except OSError as e:
            logger.error(f"Failed to save registry: {e}")
            raise RegistryError(f"Failed to save registry: {e}") from e

    @contextmanager
    def _lock(self):
        """
        Context manager for registry locking.

        Acquires exclusive file lock to ensure thread-safe operations.

        Yields:
            None

        Raises:
            RegistryLockTimeout: If lock cannot be acquired within timeout
        """
        # Ensure lock directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock = FileLock(self.lock_path, timeout=self.lock_timeout)

        try:
            with lock:
                logger.debug("Acquired registry lock")
                yield
            logger.debug("Released registry lock")

        except Timeout as e:
            logger.error(f"Failed to acquire registry lock within {self.lock_timeout}s")
            raise RegistryLockTimeout(
                f"Could not acquire registry lock within {self.lock_timeout} seconds"
            ) from e

    def register_toolchain(
        self,
        toolchain_id: str,
        path: Path,
        size_mb: float,
        hash_value: str,
        source_url: str,
        verified: bool = True,
    ):
        """
        Register new toolchain installation.

        Args:
            toolchain_id: Unique identifier for toolchain
            path: Path to toolchain installation
            size_mb: Size in megabytes
            hash_value: Hash of toolchain archive (e.g., 'sha256:abc...')
            source_url: URL where toolchain was downloaded from
            verified: Whether toolchain hash has been verified

        Example:
            >>> registry.register_toolchain(
            ...     'llvm-18.1.8-linux-x64',
            ...     Path('/home/user/.toolchainkit/toolchains/llvm-18.1.8'),
            ...     2048.5,
            ...     'sha256:abc123...',
            ...     'https://github.com/llvm/...'
            ... )
        """
        with self._lock():
            data = self._load_registry()

            now = datetime.now().isoformat()

            data["toolchains"][toolchain_id] = {
                "path": str(path.resolve()),
                "size_mb": size_mb,
                "projects": [],
                "installed": now,
                "last_used": now,
                "hash": hash_value,
                "source_url": source_url,
                "verified": verified,
            }

            # Recalculate total size
            data["total_size_mb"] = sum(
                tc["size_mb"] for tc in data["toolchains"].values()
            )

            self._save_registry(data)

            logger.info(f"Registered toolchain: {toolchain_id} ({size_mb:.1f} MB)")

    def add_project_reference(self, toolchain_id: str, project_path: Path):
        """
        Add project reference to toolchain.

        Tracks that a project is using this toolchain. This increments
        the reference count and updates the last used timestamp.

        Args:
            toolchain_id: Toolchain identifier
            project_path: Path to project using the toolchain

        Raises:
            ToolchainNotFoundError: If toolchain_id is not registered

        Example:
            >>> registry.add_project_reference(
            ...     'llvm-18.1.8-linux-x64',
            ...     Path('/home/user/my-project')
            ... )
        """
        with self._lock():
            data = self._load_registry()

            if toolchain_id not in data["toolchains"]:
                raise ToolchainNotInCacheError(toolchain_id)

            project_str = str(project_path.resolve())
            projects = data["toolchains"][toolchain_id]["projects"]

            if project_str not in projects:
                projects.append(project_str)
                data["toolchains"][toolchain_id][
                    "last_used"
                ] = datetime.now().isoformat()
                self._save_registry(data)

                logger.info(f"Added project reference: {toolchain_id} <- {project_str}")
            else:
                logger.debug(
                    f"Project already references {toolchain_id}: {project_str}"
                )

    def remove_project_reference(self, toolchain_id: str, project_path: Path):
        """
        Remove project reference from toolchain.

        Removes a project from the toolchain's reference list. This decrements
        the reference count and may enable cleanup if count reaches zero.

        Args:
            toolchain_id: Toolchain identifier
            project_path: Path to project no longer using the toolchain

        Example:
            >>> registry.remove_project_reference(
            ...     'llvm-18.1.8-linux-x64',
            ...     Path('/home/user/my-project')
            ... )
        """
        with self._lock():
            data = self._load_registry()

            if toolchain_id in data["toolchains"]:
                project_str = str(project_path.resolve())
                projects = data["toolchains"][toolchain_id]["projects"]

                if project_str in projects:
                    projects.remove(project_str)
                    self._save_registry(data)

                    logger.info(
                        f"Removed project reference: {toolchain_id} -x- {project_str}"
                    )
                else:
                    logger.debug(f"Project not found in references: {project_str}")
            else:
                logger.warning(
                    f"Toolchain not found for reference removal: {toolchain_id}"
                )

    def get_toolchain_info(self, toolchain_id: str) -> Optional[Dict]:
        """
        Get toolchain metadata.

        Args:
            toolchain_id: Toolchain identifier

        Returns:
            Toolchain metadata dictionary, or None if not found

        Example:
            >>> info = registry.get_toolchain_info('llvm-18.1.8-linux-x64')
            >>> print(f"Path: {info['path']}")
            >>> print(f"Size: {info['size_mb']} MB")
            >>> print(f"Projects: {len(info['projects'])}")
        """
        data = self._load_registry()
        return data["toolchains"].get(toolchain_id)

    def list_toolchains(self) -> List[str]:
        """
        Get list of all registered toolchain IDs.

        Returns:
            List of toolchain identifiers

        Example:
            >>> toolchains = registry.list_toolchains()
            >>> for tc_id in toolchains:
            ...     print(f"- {tc_id}")
        """
        data = self._load_registry()
        return list(data["toolchains"].keys())

    def get_unused_toolchains(self, older_than_days: Optional[int] = None) -> List[str]:
        """
        Get toolchains with no project references.

        Args:
            older_than_days: Optional filter for toolchains unused for N days

        Returns:
            List of unused toolchain IDs

        Example:
            >>> # Get all unused toolchains
            >>> unused = registry.get_unused_toolchains()
            >>>
            >>> # Get toolchains unused for >30 days
            >>> old_unused = registry.get_unused_toolchains(older_than_days=30)
        """
        data = self._load_registry()
        unused = []

        for toolchain_id, info in data["toolchains"].items():
            if len(info["projects"]) == 0:
                if older_than_days is not None:
                    try:
                        last_used = datetime.fromisoformat(info["last_used"])
                        age_days = (datetime.now() - last_used).days

                        if age_days >= older_than_days:
                            unused.append(toolchain_id)
                    except (ValueError, KeyError):
                        # Invalid timestamp or missing field - include in unused
                        unused.append(toolchain_id)
                else:
                    unused.append(toolchain_id)

        return unused

    def update_last_used(self, toolchain_id: str):
        """
        Update last used timestamp for toolchain.

        Args:
            toolchain_id: Toolchain identifier

        Example:
            >>> registry.update_last_used('llvm-18.1.8-linux-x64')
        """
        with self._lock():
            data = self._load_registry()

            if toolchain_id in data["toolchains"]:
                data["toolchains"][toolchain_id][
                    "last_used"
                ] = datetime.now().isoformat()
                self._save_registry(data)

                logger.debug(f"Updated last used timestamp: {toolchain_id}")
            else:
                logger.warning(
                    f"Toolchain not found for timestamp update: {toolchain_id}"
                )

    def unregister_toolchain(self, toolchain_id: str):
        """
        Remove toolchain from registry.

        Performs safety check to ensure no projects reference the toolchain
        before allowing unregistration.

        Args:
            toolchain_id: Toolchain identifier

        Raises:
            ToolchainInUseError: If toolchain still has project references

        Example:
            >>> try:
            ...     registry.unregister_toolchain('llvm-18.1.8-linux-x64')
            ... except ToolchainInUseError:
            ...     print("Toolchain still in use by projects")
        """
        with self._lock():
            data = self._load_registry()

            if toolchain_id not in data["toolchains"]:
                logger.warning(
                    f"Toolchain not found for unregistration: {toolchain_id}"
                )
                return

            # Safety check: ensure no projects reference it
            if len(data["toolchains"][toolchain_id]["projects"]) > 0:
                projects = data["toolchains"][toolchain_id]["projects"]
                raise ToolchainInUseError(
                    f"Cannot unregister '{toolchain_id}': still referenced by {len(projects)} project(s)"
                )

            del data["toolchains"][toolchain_id]

            # Recalculate total size
            data["total_size_mb"] = sum(
                tc["size_mb"] for tc in data["toolchains"].values()
            )

            self._save_registry(data)

            logger.info(f"Unregistered toolchain: {toolchain_id}")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - total_toolchains: Number of registered toolchains
            - total_size_mb: Total size in megabytes
            - unused_toolchains: Number of unused toolchains
            - reclaimable_size_mb: Size that could be freed by removing unused
            - last_cleanup: Timestamp of last cleanup (if any)

        Example:
            >>> stats = registry.get_cache_stats()
            >>> print(f"Total size: {stats['total_size_mb']} MB")
            >>> print(f"Unused: {stats['unused_toolchains']}")
            >>> print(f"Reclaimable: {stats['reclaimable_size_mb']} MB")
        """
        data = self._load_registry()

        total_toolchains = len(data["toolchains"])
        total_size = data["total_size_mb"]

        unused = self.get_unused_toolchains()
        unused_count = len(unused)

        # Calculate space that could be freed
        reclaimable_size = sum(data["toolchains"][tc]["size_mb"] for tc in unused)

        return {
            "total_toolchains": total_toolchains,
            "total_size_mb": total_size,
            "unused_toolchains": unused_count,
            "reclaimable_size_mb": reclaimable_size,
            "last_cleanup": data.get("last_cleanup"),
        }

    def mark_cleanup(self):
        """
        Mark that cleanup was performed.

        Updates the last_cleanup timestamp in the registry.

        Example:
            >>> registry.mark_cleanup()
        """
        with self._lock():
            data = self._load_registry()
            data["last_cleanup"] = datetime.now().isoformat()
            self._save_registry(data)

            logger.info("Marked cleanup timestamp")
