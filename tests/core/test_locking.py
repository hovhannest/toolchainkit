"""
Unit tests for the locking module.

Tests cover:
- Lock acquisition and release
- Timeout behavior
- Exception handling and cleanup
- Stale lock detection and cleanup
- Try-lock patterns
- Download coordination
"""

import pytest
import time
from pathlib import Path
from unittest.mock import patch

from filelock import Timeout as LockTimeout

from toolchainkit.core.locking import (
    LockManager,
    DownloadCoordinator,
    try_lock,
    get_global_cache_dir,
)


class TestLockManager:
    """Tests for LockManager class."""

    def test_init_default_lock_dir(self, tmp_path):
        """Test initialization with default lock directory."""
        with patch(
            "toolchainkit.core.locking.get_global_cache_dir", return_value=tmp_path
        ):
            manager = LockManager()

            expected_lock_dir = tmp_path / "lock"
            assert manager.lock_dir == expected_lock_dir
            assert expected_lock_dir.exists()

    def test_init_custom_lock_dir(self, tmp_path):
        """Test initialization with custom lock directory."""
        custom_dir = tmp_path / "custom_locks"
        manager = LockManager(lock_dir=custom_dir)

        assert manager.lock_dir == custom_dir
        assert custom_dir.exists()

    def test_registry_lock_acquire_and_release(self, tmp_path):
        """Test acquiring and releasing registry lock."""
        manager = LockManager(lock_dir=tmp_path)

        # Lock should not exist initially
        lock_file = tmp_path / "registry.lock"

        # Acquire and release lock
        with manager.registry_lock(timeout=5):
            # Lock file should exist while locked
            assert lock_file.exists()

        # Note: filelock may or may not delete the lock file after release
        # This is implementation-dependent, so we just verify the lock is released
        # by being able to acquire it again
        with manager.registry_lock(timeout=1):
            pass  # Should succeed, proving lock was released

    def test_registry_lock_timeout(self, tmp_path):
        """Test registry lock timeout when already locked."""
        manager = LockManager(lock_dir=tmp_path)

        # First lock succeeds
        with manager.registry_lock(timeout=5):
            # Try to acquire again from same thread - should timeout
            with pytest.raises(LockTimeout) as exc_info:
                with manager.registry_lock(timeout=0.1):
                    pass

            assert "Could not acquire registry lock" in str(exc_info.value)

    def test_toolchain_lock_acquire_and_release(self, tmp_path):
        """Test acquiring and releasing toolchain lock."""
        manager = LockManager(lock_dir=tmp_path)
        toolchain_id = "llvm-18.1.8-linux-x64"

        with manager.toolchain_lock(toolchain_id, timeout=5):
            # Lock file should exist
            lock_file = tmp_path / f"toolchain-{toolchain_id}.lock"
            assert lock_file.exists()

    def test_toolchain_lock_sanitizes_id(self, tmp_path):
        """Test toolchain lock sanitizes toolchain ID for filename."""
        manager = LockManager(lock_dir=tmp_path)

        # ID with special characters
        toolchain_id = "llvm/18:1.8\\windows-x64"
        expected_safe_id = "llvm-18-1.8-windows-x64"

        with manager.toolchain_lock(toolchain_id, timeout=5):
            lock_file = tmp_path / f"toolchain-{expected_safe_id}.lock"
            assert lock_file.exists()

    def test_toolchain_lock_timeout(self, tmp_path):
        """Test toolchain lock timeout."""
        manager = LockManager(lock_dir=tmp_path)
        toolchain_id = "gcc-13.2.0"

        with manager.toolchain_lock(toolchain_id, timeout=5):
            # Try to acquire again - should timeout
            with pytest.raises(LockTimeout) as exc_info:
                with manager.toolchain_lock(toolchain_id, timeout=0.1):
                    pass

            assert f"Could not acquire toolchain lock for {toolchain_id}" in str(
                exc_info.value
            )

    def test_project_lock_acquire_and_release(self, tmp_path):
        """Test acquiring and releasing project lock."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = LockManager(lock_dir=tmp_path / "locks")

        with manager.project_lock(project_path, timeout=5):
            lock_file = project_path / ".toolchainkit" / "project.lock"
            assert lock_file.exists()

    def test_project_lock_creates_toolchainkit_dir(self, tmp_path):
        """Test project lock creates .toolchainkit directory if needed."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = LockManager(lock_dir=tmp_path / "locks")

        # .toolchainkit should not exist initially
        toolchainkit_dir = project_path / ".toolchainkit"
        assert not toolchainkit_dir.exists()

        with manager.project_lock(project_path, timeout=5):
            # Should be created
            assert toolchainkit_dir.exists()

    def test_project_lock_timeout(self, tmp_path):
        """Test project lock timeout."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = LockManager(lock_dir=tmp_path / "locks")

        with manager.project_lock(project_path, timeout=5):
            # Try to acquire again - should timeout
            with pytest.raises(LockTimeout) as exc_info:
                with manager.project_lock(project_path, timeout=0.1):
                    pass

            assert "Could not acquire project lock" in str(exc_info.value)

    def test_lock_released_on_exception(self, tmp_path):
        """Test lock is released even when exception occurs."""
        manager = LockManager(lock_dir=tmp_path)

        # Raise exception inside lock context
        try:
            with manager.registry_lock(timeout=5):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Lock should be released, so we can acquire it again
        with manager.registry_lock(timeout=1):
            pass  # Should succeed without timeout

    def test_cleanup_stale_locks_no_locks(self, tmp_path):
        """Test cleanup when no locks exist."""
        manager = LockManager(lock_dir=tmp_path)

        removed = manager.cleanup_stale_locks(max_age_hours=24)
        assert removed == 0

    def test_cleanup_stale_locks_fresh_locks(self, tmp_path):
        """Test cleanup doesn't remove fresh locks."""
        manager = LockManager(lock_dir=tmp_path)

        # Create fresh lock file
        lock_file = tmp_path / "test.lock"
        lock_file.touch()

        removed = manager.cleanup_stale_locks(max_age_hours=24)
        assert removed == 0
        assert lock_file.exists()

    def test_cleanup_stale_locks_old_locks(self, tmp_path):
        """Test cleanup removes old locks."""
        manager = LockManager(lock_dir=tmp_path)

        # Create old lock file
        lock_file = tmp_path / "old.lock"
        lock_file.touch()

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        import os

        os.utime(lock_file, (old_time, old_time))

        removed = manager.cleanup_stale_locks(max_age_hours=24)
        assert removed == 1
        assert not lock_file.exists()

    def test_cleanup_stale_locks_multiple_files(self, tmp_path):
        """Test cleanup handles multiple lock files."""
        manager = LockManager(lock_dir=tmp_path)

        # Create mix of old and fresh locks
        old_lock = tmp_path / "old.lock"
        old_lock.touch()
        old_time = time.time() - (25 * 3600)
        import os

        os.utime(old_lock, (old_time, old_time))

        fresh_lock = tmp_path / "fresh.lock"
        fresh_lock.touch()

        removed = manager.cleanup_stale_locks(max_age_hours=24)
        assert removed == 1
        assert not old_lock.exists()
        assert fresh_lock.exists()

    def test_cleanup_stale_locks_nonexistent_dir(self, tmp_path):
        """Test cleanup handles nonexistent lock directory."""
        manager = LockManager(lock_dir=tmp_path / "nonexistent")

        removed = manager.cleanup_stale_locks(max_age_hours=24)
        assert removed == 0


class TestTryLock:
    """Tests for try_lock context manager."""

    def test_try_lock_immediate_success(self, tmp_path):
        """Test try_lock succeeds when lock is available."""
        lock_path = tmp_path / "test.lock"

        with try_lock(lock_path, timeout=0) as acquired:
            assert acquired is True

    def test_try_lock_immediate_failure(self, tmp_path):
        """Test try_lock fails immediately when lock is held."""
        from filelock import FileLock

        lock_path = tmp_path / "test.lock"

        # Hold the lock
        lock = FileLock(lock_path)
        lock.acquire()

        try:
            # Try to acquire with timeout=0 (immediate)
            with try_lock(lock_path, timeout=0) as acquired:
                assert acquired is False
        finally:
            lock.release()

    def test_try_lock_with_timeout_success(self, tmp_path):
        """Test try_lock succeeds within timeout."""
        lock_path = tmp_path / "test.lock"

        with try_lock(lock_path, timeout=1) as acquired:
            assert acquired is True

    def test_try_lock_with_timeout_failure(self, tmp_path):
        """Test try_lock fails when timeout expires."""
        from filelock import FileLock

        lock_path = tmp_path / "test.lock"

        # Hold the lock
        lock = FileLock(lock_path)
        lock.acquire()

        try:
            # Try to acquire with short timeout
            with try_lock(lock_path, timeout=0.1) as acquired:
                assert acquired is False
        finally:
            lock.release()

    def test_try_lock_releases_on_success(self, tmp_path):
        """Test try_lock releases lock after context exit."""
        lock_path = tmp_path / "test.lock"

        # Acquire and release
        with try_lock(lock_path, timeout=0) as acquired:
            assert acquired is True

        # Should be able to acquire again
        with try_lock(lock_path, timeout=0) as acquired:
            assert acquired is True


class TestDownloadCoordinator:
    """Tests for DownloadCoordinator class."""

    def test_coordinate_download_destination_exists(self, tmp_path):
        """Test coordination when destination already exists."""
        manager = LockManager(lock_dir=tmp_path / "locks")
        coordinator = DownloadCoordinator(manager)

        # Create destination directory with content
        destination = tmp_path / "toolchain"
        destination.mkdir()
        (destination / "file.txt").write_text("content")

        with coordinator.coordinate_download(
            "test-toolchain", destination
        ) as should_download:
            assert should_download is False

    def test_coordinate_download_destination_empty(self, tmp_path):
        """Test coordination treats empty directory as invalid."""
        manager = LockManager(lock_dir=tmp_path / "locks")
        coordinator = DownloadCoordinator(manager)

        # Create empty destination directory
        destination = tmp_path / "toolchain"
        destination.mkdir()

        with coordinator.coordinate_download(
            "test-toolchain", destination
        ) as should_download:
            # Empty directory is not valid, should download
            assert should_download is True

    def test_coordinate_download_destination_not_exists(self, tmp_path):
        """Test coordination when destination doesn't exist."""
        manager = LockManager(lock_dir=tmp_path / "locks")
        coordinator = DownloadCoordinator(manager)

        destination = tmp_path / "toolchain"

        with coordinator.coordinate_download(
            "test-toolchain", destination
        ) as should_download:
            assert should_download is True

    def test_coordinate_download_is_valid_installation(self, tmp_path):
        """Test _is_valid_installation method."""
        coordinator = DownloadCoordinator(LockManager(tmp_path / "locks"))

        # Non-existent path
        assert coordinator._is_valid_installation(tmp_path / "nonexistent") is False

        # File (not directory)
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        assert coordinator._is_valid_installation(file_path) is False

        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert coordinator._is_valid_installation(empty_dir) is False

        # Directory with content
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        (valid_dir / "file.txt").write_text("content")
        assert coordinator._is_valid_installation(valid_dir) is True

    def test_wait_for_download_timeout(self, tmp_path):
        """Test _wait_for_download raises TimeoutError on timeout."""
        coordinator = DownloadCoordinator(LockManager(tmp_path / "locks"))
        destination = tmp_path / "toolchain"

        with pytest.raises(TimeoutError) as exc_info:
            coordinator._wait_for_download(destination, timeout=1)

        assert "Timeout waiting for download" in str(exc_info.value)

    def test_wait_for_download_success(self, tmp_path):
        """Test _wait_for_download succeeds when file appears."""
        coordinator = DownloadCoordinator(LockManager(tmp_path / "locks"))
        destination = tmp_path / "toolchain"

        # Simulate another process creating the directory
        import threading

        def create_destination():
            time.sleep(0.5)
            destination.mkdir()
            (destination / "file.txt").write_text("content")

        thread = threading.Thread(target=create_destination)
        thread.start()

        # Should wait and succeed
        coordinator._wait_for_download(destination, timeout=5)

        thread.join()
        assert destination.exists()


class TestGetGlobalCacheDir:
    """Tests for get_global_cache_dir function."""

    def test_get_global_cache_dir_windows(self):
        """Test global cache dir on Windows."""
        with patch("platform.system", return_value="Windows"):
            with patch("pathlib.Path.home", return_value=Path("C:/Users/TestUser")):
                cache_dir = get_global_cache_dir()

                assert cache_dir == Path("C:/Users/TestUser/AppData/Local/toolchainkit")

    def test_get_global_cache_dir_linux(self):
        """Test global cache dir on Linux."""
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.home", return_value=Path("/home/testuser")):
                cache_dir = get_global_cache_dir()

                assert cache_dir == Path("/home/testuser/.toolchainkit")

    def test_get_global_cache_dir_macos(self):
        """Test global cache dir on macOS."""
        with patch("platform.system", return_value="Darwin"):
            with patch("pathlib.Path.home", return_value=Path("/Users/testuser")):
                cache_dir = get_global_cache_dir()

                assert cache_dir == Path("/Users/testuser/.toolchainkit")


# Integration-style tests that would normally go in a separate file
# but are included here for completeness


class TestLockingIntegration:
    """Integration tests for locking (single-process tests)."""

    def test_multiple_lock_types_coexist(self, tmp_path):
        """Test different lock types can be held simultaneously."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        manager = LockManager(lock_dir=tmp_path / "locks")

        # Should be able to hold registry, toolchain, and project locks simultaneously
        with manager.registry_lock(timeout=5):
            with manager.toolchain_lock("llvm-18", timeout=5):
                with manager.project_lock(project_path, timeout=5):
                    # All three locks held
                    assert (tmp_path / "locks" / "registry.lock").exists()
                    assert (tmp_path / "locks" / "toolchain-llvm-18.lock").exists()
                    assert (project_path / ".toolchainkit" / "project.lock").exists()

    def test_sequential_lock_reacquisition(self, tmp_path):
        """Test lock can be reacquired after release."""
        manager = LockManager(lock_dir=tmp_path)

        # Acquire and release multiple times
        for i in range(3):
            with manager.registry_lock(timeout=5):
                pass  # Lock acquired successfully

    def test_download_coordinator_workflow(self, tmp_path):
        """Test complete download coordinator workflow."""
        manager = LockManager(lock_dir=tmp_path / "locks")
        coordinator = DownloadCoordinator(manager)

        destination = tmp_path / "toolchain"
        toolchain_id = "test-toolchain"

        # First coordination - should download
        with coordinator.coordinate_download(
            toolchain_id, destination
        ) as should_download:
            assert should_download is True

            # Simulate download
            destination.mkdir()
            (destination / "bin").mkdir()
            (destination / "bin" / "clang").write_text("#!/bin/sh")

        # Second coordination - should skip
        with coordinator.coordinate_download(
            toolchain_id, destination
        ) as should_download:
            assert should_download is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
