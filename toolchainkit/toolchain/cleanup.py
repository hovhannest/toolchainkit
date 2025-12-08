"""
toolchainkit/toolchain/cleanup.py

Toolchain cleanup with reference counting for safe removal.

This module provides functionality to safely remove unused toolchains from the
shared cache while tracking which projects reference them to prevent accidental
deletion of toolchains that are still in use.
"""

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from ..core.cache_registry import ToolchainCacheRegistry
from ..core.filesystem import safe_rmtree
from ..core.locking import LockManager

logger = logging.getLogger(__name__)


@dataclass
class ToolchainInfo:
    """Information about a toolchain for cleanup purposes."""

    id: str
    path: Path
    size: int
    last_access: datetime
    ref_count: int
    name: str
    version: str


@dataclass
class CleanupResult:
    """Result of cleanup operation."""

    removed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    space_reclaimed: int = 0
    errors: List[str] = field(default_factory=list)


class ToolchainCleanupManager:
    """Manages toolchain cleanup operations."""

    def __init__(
        self,
        cache_registry: Optional[ToolchainCacheRegistry] = None,
        lock_manager: Optional[LockManager] = None,
    ):
        """
        Initialize cleanup manager.

        Args:
            cache_registry: Toolchain registry instance (creates default if None)
            lock_manager: Lock manager instance (creates default if None)
        """
        self.registry = cache_registry or ToolchainCacheRegistry()
        self.lock_manager = lock_manager or LockManager()

    def list_unused(self, min_age_days: int = 30) -> List[ToolchainInfo]:
        """
        List toolchains unused for specified days.

        Args:
            min_age_days: Minimum age in days for toolchain to be considered unused

        Returns:
            List of unused toolchain information
        """
        unused = []
        cutoff = datetime.now() - timedelta(days=min_age_days)

        with self.registry._lock():
            data = self.registry._load_registry()
            toolchains = data.get("toolchains", {})

            for toolchain_id, tc_data in toolchains.items():
                # Check reference count and last access time
                ref_count = tc_data.get("ref_count", 0)
                last_access_str = tc_data.get("last_access")

                if last_access_str:
                    try:
                        last_access = datetime.fromisoformat(last_access_str)
                    except ValueError:
                        logger.warning(f"Invalid last_access format for {toolchain_id}")
                        continue
                else:
                    # No access time recorded, use install time
                    installed_str = tc_data.get("installed")
                    if installed_str:
                        try:
                            last_access = datetime.fromisoformat(installed_str)
                        except ValueError:
                            logger.warning(
                                f"Invalid installed format for {toolchain_id}"
                            )
                            continue
                    else:
                        # No timestamp at all, skip
                        continue

                # Include if unused and old enough
                if ref_count == 0 and last_access < cutoff:
                    toolchain_path = Path(tc_data["path"])
                    if toolchain_path.exists():
                        size = self._calculate_directory_size(toolchain_path)

                        info = ToolchainInfo(
                            id=toolchain_id,
                            path=toolchain_path,
                            size=size,
                            last_access=last_access,
                            ref_count=ref_count,
                            name=tc_data.get("name", toolchain_id),
                            version=tc_data.get("version", "Unknown"),
                        )
                        unused.append(info)

        # Sort by last access (oldest first)
        unused.sort(key=lambda x: x.last_access)

        logger.info(f"Found {len(unused)} unused toolchains")
        return unused

    def cleanup(self, toolchain_ids: List[str], dry_run: bool = False) -> CleanupResult:
        """
        Remove specified toolchains.

        Args:
            toolchain_ids: List of toolchain IDs to remove
            dry_run: If True, only simulate removal

        Returns:
            CleanupResult with removal details
        """
        result = CleanupResult()

        for toolchain_id in toolchain_ids:
            try:
                with self.registry._lock():
                    data = self.registry._load_registry()
                    toolchains = data.get("toolchains", {})

                    if toolchain_id not in toolchains:
                        logger.warning(f"Toolchain not found: {toolchain_id}")
                        result.skipped.append(toolchain_id)
                        continue

                    tc_data = toolchains[toolchain_id]
                    toolchain_path = Path(tc_data["path"])

                    if not toolchain_path.exists():
                        logger.warning(
                            f"Toolchain path doesn't exist: {toolchain_path}"
                        )
                        result.skipped.append(toolchain_id)
                        # Clean up registry entry for non-existent toolchain
                        if not dry_run:
                            del toolchains[toolchain_id]
                            self.registry._save_registry(data)
                        continue

                    # Check reference count
                    ref_count = tc_data.get("ref_count", 0)
                    if ref_count > 0:
                        logger.warning(
                            f"Skipping {toolchain_id}: still referenced by {ref_count} projects"
                        )
                        result.skipped.append(toolchain_id)
                        result.errors.append(
                            f"{toolchain_id}: Referenced by {ref_count} projects"
                        )
                        continue

                    # Calculate size
                    size = self._calculate_directory_size(toolchain_path)

                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would remove: {toolchain_id} ({size} bytes)"
                        )
                        result.removed.append(toolchain_id)
                        result.space_reclaimed += size
                    else:
                        # Remove toolchain directory
                        safe_rmtree(
                            toolchain_path, require_prefix=toolchain_path.parent
                        )

                        # Remove from registry
                        del toolchains[toolchain_id]
                        self.registry._save_registry(data)

                        logger.info(f"Removed toolchain: {toolchain_id} ({size} bytes)")
                        result.removed.append(toolchain_id)
                        result.space_reclaimed += size

            except Exception as e:
                logger.error(f"Failed to remove {toolchain_id}: {e}")
                result.failed.append(toolchain_id)
                result.errors.append(f"{toolchain_id}: {str(e)}")

        return result

    def auto_cleanup(
        self,
        max_age_days: int = 90,
        min_space_gb: Optional[float] = None,
        dry_run: bool = False,
    ) -> CleanupResult:
        """
        Automatically clean up old unused toolchains.

        Args:
            max_age_days: Maximum age before toolchain is eligible for cleanup
            min_space_gb: Minimum space to keep free (triggers cleanup if below)
            dry_run: If True, only simulate removal

        Returns:
            CleanupResult with cleanup details
        """
        # List unused toolchains
        unused = self.list_unused(min_age_days=max_age_days)

        if not unused:
            logger.info("No unused toolchains found")
            return CleanupResult()

        # If minimum space specified, check if cleanup needed
        if min_space_gb is not None:
            free_space_gb = self._get_free_space_gb()
            if free_space_gb >= min_space_gb:
                logger.info(
                    f"Sufficient free space ({free_space_gb:.2f} GB), "
                    f"skipping cleanup"
                )
                return CleanupResult()

        # Remove unused toolchains (oldest first)
        toolchain_ids = [tc.id for tc in unused]
        return self.cleanup(toolchain_ids, dry_run=dry_run)

    def get_statistics(self) -> dict:
        """Get toolchain cache statistics."""
        with self.registry._lock():
            data = self.registry._load_registry()
            toolchains = data.get("toolchains", {})

            total_size = 0
            unused_size = 0
            unused_count = 0

            for toolchain_id, tc_data in toolchains.items():
                toolchain_path = Path(tc_data["path"])
                if toolchain_path.exists():
                    size = self._calculate_directory_size(toolchain_path)
                    total_size += size

                    ref_count = tc_data.get("ref_count", 0)

                    if ref_count == 0:
                        unused_size += size
                        unused_count += 1

            return {
                "total_toolchains": len(toolchains),
                "total_size": total_size,
                "unused_toolchains": unused_count,
                "unused_size": unused_size,
                "free_space": self._get_free_space_gb() * 1024**3,  # Convert to bytes
            }

    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file() and not item.is_symlink():
                    total += item.stat().st_size
        except Exception as e:
            logger.debug(f"Error calculating size for {path}: {e}")
        return total

    def _get_free_space_gb(self) -> float:
        """Get free space in GB on toolchain cache filesystem."""
        # Get cache directory from registry
        cache_dir = self.registry.registry_path.parent

        if hasattr(os, "statvfs"):
            # Unix
            stat = os.statvfs(cache_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
        else:
            # Windows
            import ctypes

            free_bytes_obj = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(  # type: ignore
                str(cache_dir), ctypes.byref(free_bytes_obj), None, None
            )
            free_bytes = free_bytes_obj.value

        return free_bytes / (1024**3)


class ReferenceCounter:
    """Manages reference counting for toolchains."""

    def __init__(self, cache_registry: Optional[ToolchainCacheRegistry] = None):
        """
        Initialize reference counter.

        Args:
            cache_registry: Toolchain registry instance (creates default if None)
        """
        self.registry = cache_registry or ToolchainCacheRegistry()

    def increment(self, toolchain_id: str, project_path: Path) -> int:
        """
        Increment reference count for toolchain.

        Args:
            toolchain_id: Toolchain ID
            project_path: Project directory path

        Returns:
            New reference count
        """
        with self.registry._lock():
            data = self.registry._load_registry()
            toolchains = data.get("toolchains", {})

            if toolchain_id not in toolchains:
                raise ValueError(f"Toolchain not found: {toolchain_id}")

            tc_data = toolchains[toolchain_id]

            # Get current count
            ref_count = tc_data.get("ref_count", 0)

            # Track referencing projects
            projects = tc_data.get("projects", [])
            project_str = str(project_path.resolve())

            if project_str not in projects:
                projects.append(project_str)
                ref_count += 1

            # Update metadata
            tc_data["ref_count"] = ref_count
            tc_data["projects"] = projects
            tc_data["last_access"] = datetime.now().isoformat()

            self.registry._save_registry(data)

            logger.debug(f"Incremented ref count for {toolchain_id}: {ref_count}")
            return ref_count

    def decrement(self, toolchain_id: str, project_path: Path) -> int:
        """
        Decrement reference count for toolchain.

        Args:
            toolchain_id: Toolchain ID
            project_path: Project directory path

        Returns:
            New reference count
        """
        with self.registry._lock():
            data = self.registry._load_registry()
            toolchains = data.get("toolchains", {})

            if toolchain_id not in toolchains:
                raise ValueError(f"Toolchain not found: {toolchain_id}")

            tc_data = toolchains[toolchain_id]

            # Get current count
            ref_count = tc_data.get("ref_count", 0)
            projects = tc_data.get("projects", [])
            project_str = str(project_path.resolve())

            if project_str in projects:
                projects.remove(project_str)
                ref_count = max(0, ref_count - 1)

            # Update metadata
            tc_data["ref_count"] = ref_count
            tc_data["projects"] = projects

            self.registry._save_registry(data)

            logger.debug(f"Decremented ref count for {toolchain_id}: {ref_count}")
            return ref_count

    def get_count(self, toolchain_id: str) -> int:
        """
        Get current reference count.

        Args:
            toolchain_id: Toolchain ID

        Returns:
            Current reference count
        """
        with self.registry._lock():
            data = self.registry._load_registry()
            toolchains = data.get("toolchains", {})

            if toolchain_id not in toolchains:
                raise ValueError(f"Toolchain not found: {toolchain_id}")

            return toolchains[toolchain_id].get("ref_count", 0)


# Example usage
def example_usage():
    """Example: Clean up unused toolchains."""

    cleanup_mgr = ToolchainCleanupManager()

    # Get statistics
    stats = cleanup_mgr.get_statistics()
    print("Toolchain Cache Statistics:")
    print(f"  Total toolchains: {stats['total_toolchains']}")
    print(f"  Total size: {stats['total_size'] / 1024**3:.2f} GB")
    print(f"  Unused toolchains: {stats['unused_toolchains']}")
    print(f"  Unused size: {stats['unused_size'] / 1024**3:.2f} GB")
    print(f"  Free space: {stats['free_space'] / 1024**3:.2f} GB")

    # List unused toolchains
    unused = cleanup_mgr.list_unused(min_age_days=30)
    print("\nUnused toolchains (older than 30 days):")
    for tc in unused:
        print(f"  {tc.name} {tc.version}")
        print(f"    ID: {tc.id}")
        print(f"    Size: {tc.size / 1024**3:.2f} GB")
        print(f"    Last access: {tc.last_access}")

    # Dry run cleanup
    result = cleanup_mgr.cleanup([tc.id for tc in unused], dry_run=True)
    print(f"\n[DRY RUN] Would reclaim {result.space_reclaimed / 1024**3:.2f} GB")

    # Actual cleanup (commented out for safety)
    # result = cleanup_mgr.cleanup([tc.id for tc in unused], dry_run=False)
    # print(f"Reclaimed {result.space_reclaimed / 1024**3:.2f} GB")


if __name__ == "__main__":
    example_usage()
