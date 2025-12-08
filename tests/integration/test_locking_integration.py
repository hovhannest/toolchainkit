"""
Integration tests for locking with multiple processes.

These tests use multiprocessing to verify that locks work correctly
across different processes, not just threads.
"""

import pytest
import time
import multiprocessing

from toolchainkit.core.locking import (
    LockManager,
    DownloadCoordinator,
)


def worker_acquire_registry_lock(lock_dir, result_queue, sleep_duration=1):
    """
    Worker function that acquires registry lock and holds it.

    Args:
        lock_dir: Directory for lock files
        result_queue: Queue to communicate success/failure
        sleep_duration: How long to hold the lock
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        with manager.registry_lock(timeout=10):
            result_queue.put(("acquired", time.time()))
            time.sleep(sleep_duration)
            result_queue.put(("released", time.time()))
    except Exception as e:
        result_queue.put(("error", str(e)))


def worker_try_acquire_registry_lock(lock_dir, result_queue, timeout=1):
    """
    Worker function that tries to acquire registry lock with timeout.

    Args:
        lock_dir: Directory for lock files
        result_queue: Queue to communicate success/failure
        timeout: Lock timeout in seconds
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        with manager.registry_lock(timeout=timeout):
            result_queue.put(("acquired", time.time()))
    except Exception:
        result_queue.put(("timeout", time.time()))


def worker_coordinate_download(lock_dir, toolchain_id, destination, result_queue):
    """
    Worker function that coordinates a download.

    Args:
        lock_dir: Directory for lock files
        toolchain_id: Toolchain identifier
        destination: Download destination path
        result_queue: Queue to communicate results
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        coordinator = DownloadCoordinator(manager)

        with coordinator.coordinate_download(
            toolchain_id, destination
        ) as should_download:
            result_queue.put(("coordinated", should_download, time.time()))

            if should_download:
                # Simulate download
                time.sleep(0.5)
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "file.txt").write_text("content")
                result_queue.put(("downloaded", time.time()))
    except Exception as e:
        result_queue.put(("error", str(e)))


def worker_toolchain_lock(lock_dir, toolchain_id, result_queue):
    """
    Worker function for toolchain lock testing.

    Args:
        lock_dir: Directory for lock files
        toolchain_id: Toolchain identifier
        result_queue: Queue to communicate results
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        with manager.toolchain_lock(toolchain_id, timeout=5):
            result_queue.put(("acquired", toolchain_id, time.time()))
            time.sleep(1)
            result_queue.put(("released", toolchain_id, time.time()))
    except Exception as e:
        result_queue.put(("error", str(e)))


def worker_project_lock(lock_dir, project_path, result_queue):
    """
    Worker function for project lock testing.

    Args:
        lock_dir: Directory for lock files
        project_path: Project root path
        result_queue: Queue to communicate results
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        with manager.project_lock(project_path, timeout=5):
            result_queue.put(("acquired", str(project_path), time.time()))
            time.sleep(1)
            result_queue.put(("released", str(project_path), time.time()))
    except Exception as e:
        result_queue.put(("error", str(e)))


def cleanup_worker(lock_dir, result_queue):
    """
    Worker function for stale lock cleanup testing.

    Args:
        lock_dir: Directory for lock files
        result_queue: Queue to communicate results
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        removed = manager.cleanup_stale_locks(max_age_hours=24)
        result_queue.put(("cleaned", removed))
    except Exception as e:
        result_queue.put(("error", str(e)))


def rapid_worker(lock_dir, iterations, result_queue):
    """
    Worker function for rapid lock acquisition testing.

    Args:
        lock_dir: Directory for lock files
        iterations: Number of lock cycles
        result_queue: Queue to communicate results
    """
    try:
        manager = LockManager(lock_dir=lock_dir)
        for i in range(iterations):
            with manager.registry_lock(timeout=5):
                pass  # Immediately release
        result_queue.put(("completed", iterations))
    except Exception as e:
        result_queue.put(("error", str(e)))


@pytest.mark.integration
class TestMultiprocessLocking:
    """Integration tests for multiprocess locking."""

    def test_registry_lock_blocks_other_process(self, tmp_path):
        """Test registry lock blocks another process from acquiring."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        result_queue = multiprocessing.Queue()

        # Start first process that holds lock for 5 seconds
        p1 = multiprocessing.Process(
            target=worker_acquire_registry_lock, args=(lock_dir, result_queue, 5)
        )
        p1.start()

        # Wait for first process to acquire lock
        event = result_queue.get(timeout=10)
        assert event[0] == "acquired"
        acquire_time_1 = event[1]

        # Start second process that tries to acquire with short timeout
        p2 = multiprocessing.Process(
            target=worker_try_acquire_registry_lock, args=(lock_dir, result_queue, 0.5)
        )
        p2.start()

        # Second process should timeout
        event = result_queue.get(timeout=10)
        assert event[0] == "timeout"

        # Wait for first process to release
        event = result_queue.get(timeout=10)
        assert event[0] == "released"
        release_time_1 = event[1]

        # Verify lock was held for approximately 5 seconds
        lock_duration = release_time_1 - acquire_time_1
        assert 4.5 <= lock_duration <= 6.0  # Allow some tolerance

        p1.join(timeout=10)
        p2.join(timeout=10)

    def test_registry_lock_sequential_access(self, tmp_path):
        """Test processes can acquire lock sequentially."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        result_queue = multiprocessing.Queue()

        # Start two processes that each hold lock briefly
        processes = []
        for i in range(2):
            p = multiprocessing.Process(
                target=worker_acquire_registry_lock, args=(lock_dir, result_queue, 0.5)
            )
            p.start()
            processes.append(p)

        # Collect results
        events = []
        for _ in range(4):  # 2 processes × 2 events each (acquired, released)
            event = result_queue.get(timeout=10)
            events.append(event)

        # Both processes should have acquired and released
        acquired_events = [e for e in events if e[0] == "acquired"]
        released_events = [e for e in events if e[0] == "released"]

        assert len(acquired_events) == 2
        assert len(released_events) == 2

        for p in processes:
            p.join(timeout=5)

    def test_toolchain_lock_different_toolchains(self, tmp_path):
        """Test different toolchain locks don't interfere."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        result_queue = multiprocessing.Queue()

        # Start two processes with different toolchain locks
        p1 = multiprocessing.Process(
            target=worker_toolchain_lock, args=(lock_dir, "llvm-18", result_queue)
        )
        p2 = multiprocessing.Process(
            target=worker_toolchain_lock, args=(lock_dir, "gcc-13", result_queue)
        )

        p1.start()
        p2.start()

        # Both should acquire locks successfully (different toolchains)
        events = []
        for _ in range(4):  # 2 processes × 2 events each
            event = result_queue.get(timeout=10)
            events.append(event)

        acquired_events = [e for e in events if e[0] == "acquired"]
        assert len(acquired_events) == 2

        # Check both toolchains were locked
        toolchains = [e[1] for e in acquired_events]
        assert "llvm-18" in toolchains
        assert "gcc-13" in toolchains

        p1.join(timeout=5)
        p2.join(timeout=5)

    def test_download_coordinator_multiple_processes(self, tmp_path):
        """Test download coordinator with multiple processes."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        destination = tmp_path / "toolchain"
        toolchain_id = "test-toolchain"

        result_queue = multiprocessing.Queue()

        # Start 3 processes trying to download same toolchain
        processes = []
        for i in range(3):
            p = multiprocessing.Process(
                target=worker_coordinate_download,
                args=(lock_dir, toolchain_id, destination, result_queue),
            )
            p.start()
            processes.append(p)
            time.sleep(0.1)  # Slight stagger to ensure ordering

        # Collect results
        coordinated_events = []
        downloaded_events = []

        # First process should download
        for _ in range(6):  # Up to 3 coordinated + 3 downloaded events
            try:
                event = result_queue.get(timeout=5)
                if event[0] == "coordinated":
                    coordinated_events.append(event)
                elif event[0] == "downloaded":
                    downloaded_events.append(event)
            except Exception:
                break

        # Exactly one process should have downloaded
        should_download_count = sum(1 for e in coordinated_events if e[1] is True)
        assert (
            should_download_count == 1
        ), f"Expected 1 download, got {should_download_count}"

        # All processes should have coordinated
        assert len(coordinated_events) >= 3

        # Destination should exist and be valid
        assert destination.exists()
        assert (destination / "file.txt").exists()

        for p in processes:
            p.join(timeout=5)

    def test_project_lock_different_projects(self, tmp_path):
        """Test project locks for different projects don't interfere."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        result_queue = multiprocessing.Queue()

        # Start two processes with different project locks
        p1 = multiprocessing.Process(
            target=worker_project_lock, args=(lock_dir, project1, result_queue)
        )
        p2 = multiprocessing.Process(
            target=worker_project_lock, args=(lock_dir, project2, result_queue)
        )

        p1.start()
        p2.start()

        # Both should acquire locks successfully (different projects)
        events = []
        for _ in range(4):
            event = result_queue.get(timeout=10)
            events.append(event)

        acquired_events = [e for e in events if e[0] == "acquired"]
        assert len(acquired_events) == 2

        p1.join(timeout=5)
        p2.join(timeout=5)

    def test_stale_lock_cleanup_across_processes(self, tmp_path):
        """Test stale lock cleanup works across processes."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        # Create stale lock file
        old_lock = lock_dir / "stale.lock"
        old_lock.touch()

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        import os

        os.utime(old_lock, (old_time, old_time))

        result_queue = multiprocessing.Queue()

        p = multiprocessing.Process(
            target=cleanup_worker, args=(lock_dir, result_queue)
        )
        p.start()

        event = result_queue.get(timeout=5)
        assert event[0] == "cleaned"
        assert event[1] >= 1  # At least one stale lock removed

        p.join(timeout=5)

        # Verify lock was removed
        assert not old_lock.exists()


@pytest.mark.integration
@pytest.mark.slow
class TestLockingStressTests:
    """Stress tests for locking under contention."""

    def test_many_processes_competing_for_lock(self, tmp_path):
        """Test many processes competing for same lock."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        result_queue = multiprocessing.Queue()

        # Start 10 processes trying to acquire same lock
        processes = []
        for i in range(10):
            p = multiprocessing.Process(
                target=worker_acquire_registry_lock, args=(lock_dir, result_queue, 0.2)
            )
            p.start()
            processes.append(p)

        # Collect results
        acquired_count = 0
        released_count = 0

        for _ in range(20):  # 10 processes × 2 events each
            try:
                event = result_queue.get(timeout=30)
                if event[0] == "acquired":
                    acquired_count += 1
                elif event[0] == "released":
                    released_count += 1
            except Exception:
                break

        # All processes should have acquired and released
        assert acquired_count == 10
        assert released_count == 10

        for p in processes:
            p.join(timeout=10)

    def test_rapid_lock_acquisition_release(self, tmp_path):
        """Test rapid lock acquisition and release cycles."""
        lock_dir = tmp_path / "locks"
        lock_dir.mkdir()

        result_queue = multiprocessing.Queue()
        iterations = 50

        # Start 3 processes doing rapid lock cycles
        processes = []
        for i in range(3):
            p = multiprocessing.Process(
                target=rapid_worker, args=(lock_dir, iterations, result_queue)
            )
            p.start()
            processes.append(p)

        # All processes should complete
        completed_count = 0
        for _ in range(3):
            event = result_queue.get(timeout=30)
            if event[0] == "completed":
                completed_count += 1
                assert event[1] == iterations

        assert completed_count == 3

        for p in processes:
            p.join(timeout=10)


if __name__ == "__main__":
    # Allow running integration tests directly
    pytest.main([__file__, "-v", "-m", "integration"])
