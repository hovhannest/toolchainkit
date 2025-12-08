"""
Integration tests for shared cache registry.

Tests concurrent access, persistence, and real-world scenarios.
"""

import pytest
import multiprocessing
from pathlib import Path

from toolchainkit.core.cache_registry import ToolchainCacheRegistry


def _worker_add_references(registry_path, toolchain_id, worker_id, count):
    """Worker function for concurrent reference addition."""
    registry = ToolchainCacheRegistry(registry_path)
    for i in range(count):
        project_path = Path(f"/project-{worker_id}-{i}")
        registry.add_project_reference(toolchain_id, project_path)


def _worker_register_toolchains(registry_path, worker_id, count):
    """Worker function for concurrent toolchain registration."""
    registry = ToolchainCacheRegistry(registry_path)
    for i in range(count):
        toolchain_id = f"toolchain-{worker_id}-{i}"
        registry.register_toolchain(
            toolchain_id,
            Path(f"/toolchains/{toolchain_id}"),
            100.0 + i,
            f"sha256:hash{worker_id}{i}",
            f"http://example.com/{toolchain_id}",
        )


def _worker_mixed_ops(registry_path, worker_id):
    """Worker function for mixed operations."""
    registry = ToolchainCacheRegistry(registry_path)

    # Mix of operations
    for i in range(5):
        # Read operation
        _toolchains = registry.list_toolchains()

        # Write operation - add reference
        registry.add_project_reference(
            "tc1" if i % 2 == 0 else "tc2", Path(f"/project-{worker_id}-{i}")
        )

        # Read operation
        _stats = registry.get_cache_stats()


@pytest.mark.integration
class TestConcurrentAccess:
    """Test concurrent registry access."""

    def test_concurrent_registration(self, tmp_path):
        """Test multiple processes registering toolchains concurrently."""
        registry_path = tmp_path / "registry.json"

        # Create initial registry
        registry = ToolchainCacheRegistry(registry_path)
        data = registry._load_registry()
        registry._save_registry(data)

        # Spawn multiple processes to register toolchains
        num_workers = 4
        toolchains_per_worker = 5

        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=_worker_register_toolchains,
                args=(registry_path, worker_id, toolchains_per_worker),
            )
            p.start()
            processes.append(p)

        # Wait for all workers
        for p in processes:
            p.join()

        # Verify all toolchains were registered
        registry = ToolchainCacheRegistry(registry_path)
        toolchains = registry.list_toolchains()

        expected_count = num_workers * toolchains_per_worker
        assert len(toolchains) == expected_count

    def test_concurrent_reference_addition(self, tmp_path):
        """Test multiple processes adding project references."""
        registry_path = tmp_path / "registry.json"

        # Register a toolchain
        registry = ToolchainCacheRegistry(registry_path)
        registry.register_toolchain(
            "shared-toolchain",
            Path("/toolchains/shared"),
            1000.0,
            "sha256:abc123",
            "http://example.com/toolchain",
        )

        # Spawn multiple processes to add references
        num_workers = 4
        refs_per_worker = 10

        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=_worker_add_references,
                args=(registry_path, "shared-toolchain", worker_id, refs_per_worker),
            )
            p.start()
            processes.append(p)

        # Wait for all workers
        for p in processes:
            p.join()

        # Verify all references were added
        registry = ToolchainCacheRegistry(registry_path)
        info = registry.get_toolchain_info("shared-toolchain")

        expected_count = num_workers * refs_per_worker
        assert len(info["projects"]) == expected_count

    def test_concurrent_mixed_operations(self, tmp_path):
        """Test concurrent reads and writes."""
        registry_path = tmp_path / "registry.json"

        # Initial setup
        registry = ToolchainCacheRegistry(registry_path)
        registry.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")
        registry.register_toolchain("tc2", Path("/tc2"), 200.0, "sha256:b", "http://b")

        # Spawn workers
        processes = []
        for worker_id in range(4):
            p = multiprocessing.Process(
                target=_worker_mixed_ops, args=(registry_path, worker_id)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        # Verify registry is consistent
        registry = ToolchainCacheRegistry(registry_path)
        toolchains = registry.list_toolchains()
        assert "tc1" in toolchains
        assert "tc2" in toolchains


@pytest.mark.integration
class TestPersistence:
    """Test registry persistence across process restarts."""

    def test_registry_survives_restart(self, tmp_path):
        """Test registry data persists across process restarts."""
        registry_path = tmp_path / "registry.json"

        # First process: create and populate registry
        registry1 = ToolchainCacheRegistry(registry_path)
        registry1.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")
        registry1.add_project_reference("tc1", Path("/project1"))

        # Simulate process restart by creating new registry instance
        registry2 = ToolchainCacheRegistry(registry_path)

        # Verify data persisted
        info = registry2.get_toolchain_info("tc1")
        assert info is not None
        assert len(info["projects"]) == 1

    def test_multiple_registries_same_file(self, tmp_path):
        """Test multiple registry instances can access same file."""
        registry_path = tmp_path / "registry.json"

        # Create two separate instances
        registry1 = ToolchainCacheRegistry(registry_path)
        registry2 = ToolchainCacheRegistry(registry_path)

        # Write from first instance
        registry1.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")

        # Read from second instance
        info = registry2.get_toolchain_info("tc1")
        assert info is not None


@pytest.mark.integration
class TestRealPaths:
    """Test with real filesystem paths."""

    def test_absolute_path_resolution(self, tmp_path):
        """Test paths are resolved to absolute form."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        # Use relative path for toolchain
        toolchain_dir = tmp_path / "toolchains" / "llvm"
        toolchain_dir.mkdir(parents=True)

        registry.register_toolchain(
            "llvm-18", toolchain_dir, 1000.0, "sha256:abc", "http://example.com"
        )

        info = registry.get_toolchain_info("llvm-18")
        stored_path = Path(info["path"])

        assert stored_path.is_absolute()
        assert stored_path == toolchain_dir.resolve()

    def test_project_path_normalization(self, tmp_path):
        """Test project paths are normalized."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        registry.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")

        # Add reference with relative path
        project_dir = tmp_path / "projects" / "my-project"
        project_dir.mkdir(parents=True)

        registry.add_project_reference("tc1", project_dir)

        info = registry.get_toolchain_info("tc1")
        stored_project = info["projects"][0]

        assert Path(stored_project).is_absolute()


@pytest.mark.integration
class TestLockBehavior:
    """Test file lock behavior."""

    def test_lock_released_after_operation(self, tmp_path):
        """Test lock is properly released after operations."""
        registry_path = tmp_path / "registry.json"
        registry1 = ToolchainCacheRegistry(registry_path)
        registry2 = ToolchainCacheRegistry(registry_path)

        # Perform operation with first instance
        registry1.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")

        # Second instance should be able to acquire lock immediately
        registry2.register_toolchain("tc2", Path("/tc2"), 100.0, "sha256:b", "http://b")

        # Verify both toolchains registered
        toolchains = registry1.list_toolchains()
        assert len(toolchains) == 2

    def test_lock_timeout_behavior(self, tmp_path):
        """Test lock timeout raises appropriate exception."""
        registry_path = tmp_path / "registry.json"

        # Create registry with very short timeout
        registry = ToolchainCacheRegistry(registry_path, lock_timeout=1)

        # This test just verifies the timeout parameter is accepted
        # Actual timeout testing is in unit tests with mocks
        registry.register_toolchain("tc1", Path("/tc1"), 100.0, "sha256:a", "http://a")

        info = registry.get_toolchain_info("tc1")
        assert info is not None


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_project_lifecycle(self, tmp_path):
        """Test complete project lifecycle with registry."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        # Step 1: Install toolchain
        registry.register_toolchain(
            "llvm-18.1.8",
            Path("/toolchains/llvm-18.1.8"),
            2048.5,
            "sha256:abc123def456",
            "https://github.com/llvm/releases/llvm-18.1.8.tar.gz",
        )

        # Step 2: Project starts using toolchain
        project1 = Path("/home/user/project1")
        registry.add_project_reference("llvm-18.1.8", project1)

        # Step 3: Another project starts using same toolchain
        project2 = Path("/home/user/project2")
        registry.add_project_reference("llvm-18.1.8", project2)

        # Verify reference count
        info = registry.get_toolchain_info("llvm-18.1.8")
        assert len(info["projects"]) == 2

        # Step 4: First project stops using toolchain
        registry.remove_project_reference("llvm-18.1.8", project1)

        info = registry.get_toolchain_info("llvm-18.1.8")
        assert len(info["projects"]) == 1

        # Step 5: Try to cleanup - should fail (still in use)
        unused = registry.get_unused_toolchains()
        assert "llvm-18.1.8" not in unused

        # Step 6: Second project stops using toolchain
        registry.remove_project_reference("llvm-18.1.8", project2)

        # Now it's unused
        unused = registry.get_unused_toolchains()
        assert "llvm-18.1.8" in unused

        # Step 7: Safe to unregister and delete
        registry.unregister_toolchain("llvm-18.1.8")

        # Verify removed
        info = registry.get_toolchain_info("llvm-18.1.8")
        assert info is None

    def test_multi_toolchain_project(self, tmp_path):
        """Test project using multiple toolchains."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        # Register multiple toolchains
        registry.register_toolchain(
            "llvm-18", Path("/llvm"), 2000.0, "sha256:a", "http://a"
        )
        registry.register_toolchain(
            "gcc-13", Path("/gcc"), 1500.0, "sha256:b", "http://b"
        )
        registry.register_toolchain(
            "cmake-3.28", Path("/cmake"), 200.0, "sha256:c", "http://c"
        )

        # Project uses all three
        project = Path("/home/user/cross-platform-project")
        registry.add_project_reference("llvm-18", project)
        registry.add_project_reference("gcc-13", project)
        registry.add_project_reference("cmake-3.28", project)

        # Verify all referenced
        assert (
            str(project.resolve()) in registry.get_toolchain_info("llvm-18")["projects"]
        )
        assert (
            str(project.resolve()) in registry.get_toolchain_info("gcc-13")["projects"]
        )
        assert (
            str(project.resolve())
            in registry.get_toolchain_info("cmake-3.28")["projects"]
        )

        # Check statistics
        stats = registry.get_cache_stats()
        assert stats["total_toolchains"] == 3
        assert stats["unused_toolchains"] == 0  # All in use

    def test_cleanup_workflow(self, tmp_path):
        """Test toolchain cleanup workflow."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        # Register several toolchains
        for i in range(5):
            registry.register_toolchain(
                f"toolchain-{i}",
                Path(f"/toolchains/tc{i}"),
                500.0,
                f"sha256:hash{i}",
                f"http://example.com/tc{i}",
            )

        # Only some are used
        registry.add_project_reference("toolchain-1", Path("/project1"))
        registry.add_project_reference("toolchain-3", Path("/project2"))

        # Find unused toolchains
        unused = registry.get_unused_toolchains()
        assert len(unused) == 3
        assert "toolchain-0" in unused
        assert "toolchain-2" in unused
        assert "toolchain-4" in unused

        # Calculate reclaimable space
        stats = registry.get_cache_stats()
        assert stats["reclaimable_size_mb"] == 1500.0  # 3 * 500

        # Clean up unused toolchains
        for tc_id in unused:
            registry.unregister_toolchain(tc_id)
            # In real scenario, would also delete files here

        # Mark cleanup timestamp
        registry.mark_cleanup()

        # Verify cleanup
        stats = registry.get_cache_stats()
        assert stats["total_toolchains"] == 2
        assert stats["unused_toolchains"] == 0
        assert stats["last_cleanup"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
