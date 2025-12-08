"""
Concurrent access control for ToolchainKit.

This module provides file-based locking mechanisms to ensure safe concurrent
access to shared resources (registry, downloads, toolchain installations) across
multiple ToolchainKit processes.

Features:
- Cross-platform file locking (Windows, Linux, macOS)
- Cross-process locking (not just threading)
- Timeout support to prevent hanging
- Automatic cleanup on process death
- Fair queuing (first-come-first-served)
- Stale lock detection and cleanup

Usage:
    from toolchainkit.core.locking import LockManager, DownloadCoordinator

    # Basic locking
    lock_manager = LockManager()
    with lock_manager.registry_lock(timeout=30):
        # Safely modify registry
        pass

    # Download coordination
    coordinator = DownloadCoordinator(lock_manager)
    with coordinator.coordinate_download(toolchain_id, destination) as should_download:
        if should_download:
            # This process should perform the download
            download_toolchain(toolchain_id, destination)
"""

import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from filelock import FileLock, Timeout as LockTimeout

logger = logging.getLogger(__name__)


def get_global_cache_dir() -> Path:
    """
    Get the global cache directory for lock files.

    Returns:
        Path to global cache directory
    """
    import platform

    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local" / "toolchainkit"
    else:
        base = Path.home() / ".toolchainkit"

    return base


class LockManager:
    """
    Manages locks for ToolchainKit resources.

    Provides thread-safe and process-safe locking mechanisms for:
    - Registry modifications
    - Toolchain downloads/installations
    - Project-local state modifications

    Uses file-based locking with the `filelock` library for cross-platform
    compatibility and automatic cleanup on process death.

    Attributes:
        lock_dir: Directory where lock files are stored
    """

    def __init__(self, lock_dir: Optional[Path] = None):
        """
        Initialize lock manager.

        Args:
            lock_dir: Directory for lock files (default: global cache/lock/)
        """
        if lock_dir is None:
            lock_dir = get_global_cache_dir() / "lock"

        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def registry_lock(self, timeout: int = 30):
        """
        Acquire registry lock for safe modifications.

        This lock protects the global registry.json file from concurrent
        modifications by multiple ToolchainKit processes.

        Args:
            timeout: Maximum wait time in seconds (default: 30)

        Yields:
            None

        Raises:
            LockTimeout: If lock can't be acquired within timeout

        Example:
            >>> lock_manager = LockManager()
            >>> with lock_manager.registry_lock(timeout=30):
            ...     # Safely modify registry
            ...     registry = load_registry()
            ...     registry['new_toolchain'] = {...}
            ...     save_registry(registry)
        """
        lock_path = self.lock_dir / "registry.lock"
        lock = FileLock(lock_path, timeout=timeout)

        try:
            with lock:
                logger.debug(f"Acquired registry lock: {lock_path}")
                yield
                logger.debug(f"Released registry lock: {lock_path}")
        except LockTimeout as e:
            logger.error(
                f"Could not acquire registry lock after {timeout}s. "
                "Another ToolchainKit process may be running."
            )
            raise LockTimeout(
                f"Could not acquire registry lock after {timeout}s. "
                "Another ToolchainKit process may be running."
            ) from e

    @contextmanager
    def toolchain_lock(self, toolchain_id: str, timeout: int = 300):
        """
        Acquire lock for specific toolchain (for download/installation).

        This lock prevents multiple processes from downloading or installing
        the same toolchain simultaneously.

        Args:
            toolchain_id: Unique toolchain identifier (e.g., 'llvm-18.1.8-linux-x64')
            timeout: Maximum wait time in seconds (default: 300 for long downloads)

        Yields:
            None

        Raises:
            LockTimeout: If lock can't be acquired within timeout

        Example:
            >>> lock_manager = LockManager()
            >>> with lock_manager.toolchain_lock('llvm-18-linux-x64', timeout=300):
            ...     # Download and extract toolchain
            ...     download_toolchain('llvm-18', destination)
        """
        # Sanitize toolchain_id to create valid filename
        safe_id = toolchain_id.replace("/", "-").replace("\\", "-").replace(":", "-")
        lock_path = self.lock_dir / f"toolchain-{safe_id}.lock"
        lock = FileLock(lock_path, timeout=timeout)

        try:
            with lock:
                logger.debug(f"Acquired toolchain lock: {lock_path}")
                yield
                logger.debug(f"Released toolchain lock: {lock_path}")
        except LockTimeout as e:
            logger.error(
                f"Could not acquire toolchain lock for {toolchain_id} after {timeout}s. "
                "Another process may be downloading this toolchain."
            )
            raise LockTimeout(
                f"Could not acquire toolchain lock for {toolchain_id} after {timeout}s. "
                "Another process may be downloading this toolchain."
            ) from e

    @contextmanager
    def project_lock(self, project_path: Path, timeout: int = 10):
        """
        Acquire lock for project-local state modifications.

        This lock protects project-specific state files from concurrent
        modifications.

        Args:
            project_path: Project root directory
            timeout: Maximum wait time in seconds (default: 10)

        Yields:
            None

        Raises:
            LockTimeout: If lock can't be acquired within timeout

        Example:
            >>> lock_manager = LockManager()
            >>> with lock_manager.project_lock(Path('/path/to/project'), timeout=10):
            ...     # Safely modify project state
            ...     state = load_project_state()
            ...     state['last_build'] = datetime.now()
            ...     save_project_state(state)
        """
        lock_path = project_path / ".toolchainkit" / "project.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock = FileLock(lock_path, timeout=timeout)

        try:
            with lock:
                logger.debug(f"Acquired project lock: {lock_path}")
                yield
                logger.debug(f"Released project lock: {lock_path}")
        except LockTimeout as e:
            logger.error(f"Could not acquire project lock after {timeout}s.")
            raise LockTimeout(
                f"Could not acquire project lock after {timeout}s."
            ) from e

    def cleanup_stale_locks(self, max_age_hours: int = 24) -> int:
        """
        Remove lock files older than max_age_hours.

        This handles cases where processes died without cleaning up locks.
        The filelock library handles this automatically in most cases, but
        this provides explicit cleanup for edge cases.

        Args:
            max_age_hours: Maximum age in hours before lock is considered stale

        Returns:
            Number of stale locks removed

        Example:
            >>> lock_manager = LockManager()
            >>> removed = lock_manager.cleanup_stale_locks(max_age_hours=24)
            >>> print(f"Removed {removed} stale locks")
        """
        if not self.lock_dir.exists():
            return 0

        current_time = time.time()
        removed_count = 0

        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                age_hours = (current_time - lock_file.stat().st_mtime) / 3600

                if age_hours > max_age_hours:
                    lock_file.unlink()
                    logger.info(f"Removed stale lock file: {lock_file}")
                    removed_count += 1
            except OSError as e:
                # Lock may be in use or already deleted
                logger.debug(f"Could not remove lock {lock_file}: {e}")

        return removed_count


@contextmanager
def try_lock(lock_path: Path, timeout: int = 0):
    """
    Try to acquire lock without blocking (or with short timeout).

    This is useful for "try-and-skip" patterns where you want to attempt
    an operation but skip it if another process is already working on it.

    Args:
        lock_path: Path to lock file
        timeout: 0 for immediate (non-blocking), or seconds to wait

    Yields:
        bool: True if lock acquired, False otherwise

    Example:
        >>> with try_lock(Path('/tmp/my.lock'), timeout=0) as acquired:
        ...     if acquired:
        ...         print("Got the lock, doing work...")
        ...         do_work()
        ...     else:
        ...         print("Someone else is working, skipping...")
    """
    lock = FileLock(lock_path, timeout=timeout)

    acquired = False
    try:
        lock.acquire(timeout=timeout)
        acquired = True
        logger.debug(f"Acquired lock (try_lock): {lock_path}")
        yield True
    except LockTimeout:
        logger.debug(f"Could not acquire lock (try_lock): {lock_path}")
        yield False
    finally:
        if acquired:
            lock.release()
            logger.debug(f"Released lock (try_lock): {lock_path}")


class DownloadCoordinator:
    """
    Coordinate downloads across multiple processes.

    If one process is downloading a toolchain, other processes should wait
    for the download to complete rather than starting duplicate downloads.

    This implements a wait-and-notify pattern where:
    1. First process acquires lock and downloads
    2. Other processes wait and periodically check if download completed
    3. All processes proceed once download is complete

    Attributes:
        lock_manager: LockManager instance for acquiring locks
    """

    def __init__(self, lock_manager: LockManager):
        """
        Initialize download coordinator.

        Args:
            lock_manager: LockManager instance for acquiring locks
        """
        self.lock_manager = lock_manager

    @contextmanager
    def coordinate_download(self, toolchain_id: str, destination: Path):
        """
        Coordinate toolchain download across processes.

        This context manager determines whether the current process should
        download the toolchain or wait for another process to complete it.

        If destination already exists, no download is needed.
        If destination doesn't exist, try to acquire lock:
        - If lock acquired: this process should download
        - If lock timeout: another process is downloading, wait for completion

        Args:
            toolchain_id: Unique toolchain identifier
            destination: Destination path where toolchain will be extracted

        Yields:
            bool: True if this process should download, False if no download needed

        Raises:
            TimeoutError: If waiting for another process's download times out

        Example:
            >>> coordinator = DownloadCoordinator(lock_manager)
            >>> with coordinator.coordinate_download('llvm-18', dest_path) as should_download:
            ...     if should_download:
            ...         print("This process will download")
            ...         download_and_extract(url, dest_path)
            ...     else:
            ...         print("Another process downloaded, or already exists")
        """
        # Quick check without lock - if destination exists, no download needed
        if destination.exists() and self._is_valid_installation(destination):
            logger.debug(
                f"Destination already exists, no download needed: {destination}"
            )
            yield False
            return

        # Try to acquire lock for download
        try:
            with self.lock_manager.toolchain_lock(toolchain_id, timeout=300):
                # Check again after acquiring lock (another process may have completed)
                if destination.exists() and self._is_valid_installation(destination):
                    logger.info(f"Another process completed download: {destination}")
                    yield False
                else:
                    logger.info(f"This process will download: {toolchain_id}")
                    yield True
        except LockTimeout:
            # Another process is downloading, wait and check periodically
            logger.info(f"Another process is downloading {toolchain_id}, waiting...")
            self._wait_for_download(destination, timeout=600)
            yield False

    def _is_valid_installation(self, destination: Path) -> bool:
        """
        Check if destination contains a valid toolchain installation.

        Basic heuristic: directory exists and is not empty.
        Future: Could check for specific files (e.g., bin/clang, bin/gcc).

        Args:
            destination: Path to check

        Returns:
            True if installation appears valid
        """
        if not destination.is_dir():
            return False

        # Check if directory is not empty
        try:
            next(destination.iterdir())
            return True
        except StopIteration:
            return False

    def _wait_for_download(self, destination: Path, timeout: int):
        """
        Wait for another process to complete download.

        Polls the destination path periodically until it exists or timeout.

        Args:
            destination: Expected destination path
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If download doesn't complete within timeout
        """
        start_time = time.time()
        check_interval = 1  # Check every 1 second for more responsive testing

        while time.time() - start_time < timeout:
            if destination.exists() and self._is_valid_installation(destination):
                logger.info(f"Download completed by another process: {destination}")
                return

            elapsed = time.time() - start_time
            logger.debug(
                f"Waiting for download to complete... " f"({elapsed:.0f}s / {timeout}s)"
            )
            time.sleep(check_interval)

        raise TimeoutError(
            f"Timeout waiting for download to complete: {destination}. "
            f"Waited {timeout}s but file was not created."
        )


__all__ = [
    "LockManager",
    "DownloadCoordinator",
    "try_lock",
    "LockTimeout",
    "get_global_cache_dir",
]
