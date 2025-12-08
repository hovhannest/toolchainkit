"""
Tests for toolchainkit.toolchain.cleanup module.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json

from toolchainkit.toolchain.cleanup import (
    ToolchainInfo,
    CleanupResult,
    ToolchainCleanupManager,
    ReferenceCounter,
)
from toolchainkit.core.cache_registry import ToolchainCacheRegistry


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory with registry."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    registry_path = cache_dir / "registry.json"
    registry_data = {
        "version": 1,
        "toolchains": {},
        "total_size_mb": 0.0,
        "last_cleanup": None,
    }

    with open(registry_path, "w") as f:
        json.dump(registry_data, f)

    return cache_dir


@pytest.fixture
def mock_registry(temp_cache_dir):
    """Create mock registry instance."""
    return ToolchainCacheRegistry(registry_path=temp_cache_dir / "registry.json")


@pytest.fixture
def cleanup_manager(mock_registry):
    """Create cleanup manager with mock registry."""
    return ToolchainCleanupManager(cache_registry=mock_registry)


@pytest.fixture
def reference_counter(mock_registry):
    """Create reference counter with mock registry."""
    return ReferenceCounter(cache_registry=mock_registry)


# Test ToolchainInfo dataclass
class TestToolchainInfo:
    def test_toolchain_info_creation(self):
        """Test ToolchainInfo dataclass creation."""
        now = datetime.now()
        info = ToolchainInfo(
            id="gcc-13.2.0",
            path=Path("/toolchains/gcc-13.2.0"),
            size=1024 * 1024 * 100,  # 100 MB
            last_access=now,
            ref_count=0,
            name="GCC",
            version="13.2.0",
        )

        assert info.id == "gcc-13.2.0"
        assert info.path == Path("/toolchains/gcc-13.2.0")
        assert info.size == 1024 * 1024 * 100
        assert info.last_access == now
        assert info.ref_count == 0
        assert info.name == "GCC"
        assert info.version == "13.2.0"


# Test CleanupResult dataclass
class TestCleanupResult:
    def test_cleanup_result_default(self):
        """Test CleanupResult default values."""
        result = CleanupResult()

        assert result.removed == []
        assert result.skipped == []
        assert result.failed == []
        assert result.space_reclaimed == 0
        assert result.errors == []

    def test_cleanup_result_with_values(self):
        """Test CleanupResult with values."""
        result = CleanupResult(
            removed=["gcc-13.2.0"],
            skipped=["llvm-16.0.0"],
            failed=["broken-tc"],
            space_reclaimed=1024 * 1024 * 100,
            errors=["Error message"],
        )

        assert result.removed == ["gcc-13.2.0"]
        assert result.skipped == ["llvm-16.0.0"]
        assert result.failed == ["broken-tc"]
        assert result.space_reclaimed == 1024 * 1024 * 100
        assert result.errors == ["Error message"]


# Test ReferenceCounter
class TestReferenceCounter:
    def test_init_default_registry(self):
        """Test ReferenceCounter initialization with default registry."""
        counter = ReferenceCounter()
        assert counter.registry is not None
        assert isinstance(counter.registry, ToolchainCacheRegistry)

    def test_init_custom_registry(self, mock_registry):
        """Test ReferenceCounter initialization with custom registry."""
        counter = ReferenceCounter(cache_registry=mock_registry)
        assert counter.registry == mock_registry

    def test_increment_new_project(self, reference_counter, temp_cache_dir, tmp_path):
        """Test incrementing reference count for new project."""
        # Setup: Add toolchain to registry
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 0,
                "projects": [],
            }
            reference_counter.registry._save_registry(data)

        # Increment reference
        project_path = tmp_path / "project1"
        count = reference_counter.increment(toolchain_id, project_path)

        assert count == 1

        # Verify registry updated
        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            tc_data = data["toolchains"][toolchain_id]
            assert tc_data["ref_count"] == 1
            assert str(project_path.resolve()) in tc_data["projects"]
            assert "last_access" in tc_data

    def test_increment_existing_project(
        self, reference_counter, temp_cache_dir, tmp_path
    ):
        """Test incrementing reference count for existing project (should not double-count)."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        project_path = tmp_path / "project1"

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 1,
                "projects": [str(project_path.resolve())],
            }
            reference_counter.registry._save_registry(data)

        # Increment again with same project
        count = reference_counter.increment(toolchain_id, project_path)

        assert count == 1  # Should not increment again

    def test_increment_nonexistent_toolchain(self, reference_counter, tmp_path):
        """Test incrementing reference for non-existent toolchain."""
        with pytest.raises(ValueError, match="Toolchain not found"):
            reference_counter.increment("nonexistent", tmp_path / "project")

    def test_decrement(self, reference_counter, temp_cache_dir, tmp_path):
        """Test decrementing reference count."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        project_path = tmp_path / "project1"

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 1,
                "projects": [str(project_path.resolve())],
            }
            reference_counter.registry._save_registry(data)

        # Decrement
        count = reference_counter.decrement(toolchain_id, project_path)

        assert count == 0

        # Verify registry updated
        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            tc_data = data["toolchains"][toolchain_id]
            assert tc_data["ref_count"] == 0
            assert str(project_path.resolve()) not in tc_data["projects"]

    def test_decrement_nonexistent_project(
        self, reference_counter, temp_cache_dir, tmp_path
    ):
        """Test decrementing reference for project not in list."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 1,
                "projects": ["/other/project"],
            }
            reference_counter.registry._save_registry(data)

        # Decrement with different project
        project_path = tmp_path / "project1"
        count = reference_counter.decrement(toolchain_id, project_path)

        assert count == 1  # Should remain unchanged

    def test_decrement_prevents_negative(
        self, reference_counter, temp_cache_dir, tmp_path
    ):
        """Test decrement doesn't go below zero."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        project_path = tmp_path / "project1"

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 0,
                "projects": [str(project_path.resolve())],
            }
            reference_counter.registry._save_registry(data)

        # Decrement when already zero
        count = reference_counter.decrement(toolchain_id, project_path)

        assert count == 0  # Should not go negative

    def test_get_count(self, reference_counter, temp_cache_dir):
        """Test getting reference count."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        with reference_counter.registry._lock():
            data = reference_counter.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 5,
                "projects": [],
            }
            reference_counter.registry._save_registry(data)

        count = reference_counter.get_count(toolchain_id)
        assert count == 5

    def test_get_count_nonexistent_toolchain(self, reference_counter):
        """Test getting count for non-existent toolchain."""
        with pytest.raises(ValueError, match="Toolchain not found"):
            reference_counter.get_count("nonexistent")


# Test ToolchainCleanupManager
class TestToolchainCleanupManager:
    def test_init_default(self):
        """Test CleanupManager initialization with defaults."""
        mgr = ToolchainCleanupManager()
        assert mgr.registry is not None
        assert mgr.lock_manager is not None

    def test_init_custom(self, mock_registry):
        """Test CleanupManager initialization with custom registry."""
        from toolchainkit.core.locking import LockManager

        lock_mgr = LockManager()

        mgr = ToolchainCleanupManager(
            cache_registry=mock_registry, lock_manager=lock_mgr
        )
        assert mgr.registry == mock_registry
        assert mgr.lock_manager == lock_mgr

    def test_list_unused_empty(self, cleanup_manager):
        """Test listing unused toolchains when none exist."""
        unused = cleanup_manager.list_unused(min_age_days=30)
        assert unused == []

    def test_list_unused_with_old_toolchains(self, cleanup_manager, temp_cache_dir):
        """Test listing unused toolchains with old entries."""
        # Add old unused toolchain
        toolchain_id = "gcc-12.0.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        (tc_path / "bin" / "gcc").mkdir(parents=True)
        (tc_path / "bin" / "gcc" / "dummy.txt").write_text("test")

        old_date = datetime.now() - timedelta(days=60)

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "12.0.0",
                "ref_count": 0,
                "last_access": old_date.isoformat(),
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        unused = cleanup_manager.list_unused(min_age_days=30)

        assert len(unused) == 1
        assert unused[0].id == toolchain_id
        assert unused[0].ref_count == 0
        assert unused[0].name == "GCC"
        assert unused[0].version == "12.0.0"

    def test_list_unused_excludes_recent(self, cleanup_manager, temp_cache_dir):
        """Test listing excludes recently accessed toolchains."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        recent_date = datetime.now() - timedelta(days=15)

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 0,
                "last_access": recent_date.isoformat(),
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        unused = cleanup_manager.list_unused(min_age_days=30)
        assert len(unused) == 0

    def test_list_unused_excludes_referenced(self, cleanup_manager, temp_cache_dir):
        """Test listing excludes referenced toolchains."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        old_date = datetime.now() - timedelta(days=60)

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 2,  # Referenced
                "last_access": old_date.isoformat(),
                "projects": ["/project1", "/project2"],
            }
            cleanup_manager.registry._save_registry(data)

        unused = cleanup_manager.list_unused(min_age_days=30)
        assert len(unused) == 0

    def test_cleanup_dry_run(self, cleanup_manager, temp_cache_dir):
        """Test cleanup in dry-run mode."""
        toolchain_id = "gcc-12.0.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        (tc_path / "file.txt").write_text("test")

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "12.0.0",
                "ref_count": 0,
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        result = cleanup_manager.cleanup([toolchain_id], dry_run=True)

        assert toolchain_id in result.removed
        assert result.space_reclaimed > 0
        assert tc_path.exists()  # Should not be deleted in dry run

    def test_cleanup_removes_toolchain(self, cleanup_manager, temp_cache_dir):
        """Test cleanup actually removes toolchain."""
        toolchain_id = "gcc-12.0.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        (tc_path / "file.txt").write_text("test")

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "12.0.0",
                "ref_count": 0,
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        result = cleanup_manager.cleanup([toolchain_id], dry_run=False)

        assert toolchain_id in result.removed
        assert result.space_reclaimed > 0
        assert not tc_path.exists()  # Should be deleted

        # Verify removed from registry
        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            assert toolchain_id not in data["toolchains"]

    def test_cleanup_skips_referenced(self, cleanup_manager, temp_cache_dir):
        """Test cleanup skips referenced toolchains."""
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 2,
                "projects": ["/project1", "/project2"],
            }
            cleanup_manager.registry._save_registry(data)

        result = cleanup_manager.cleanup([toolchain_id], dry_run=False)

        assert toolchain_id in result.skipped
        assert len(result.errors) > 0
        assert tc_path.exists()  # Should not be deleted

    def test_cleanup_nonexistent_toolchain(self, cleanup_manager):
        """Test cleanup with non-existent toolchain."""
        result = cleanup_manager.cleanup(["nonexistent"], dry_run=False)
        assert "nonexistent" in result.skipped

    def test_cleanup_missing_path(self, cleanup_manager, temp_cache_dir):
        """Test cleanup when toolchain path doesn't exist."""
        toolchain_id = "gcc-missing"
        tc_path = temp_cache_dir / toolchain_id  # Don't create directory

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "missing",
                "ref_count": 0,
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        result = cleanup_manager.cleanup([toolchain_id], dry_run=False)

        assert toolchain_id in result.skipped

        # Registry entry should be cleaned up
        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            assert toolchain_id not in data["toolchains"]

    def test_auto_cleanup_no_unused(self, cleanup_manager):
        """Test auto cleanup with no unused toolchains."""
        result = cleanup_manager.auto_cleanup(max_age_days=90, dry_run=False)

        assert len(result.removed) == 0
        assert len(result.skipped) == 0

    def test_auto_cleanup_with_unused(self, cleanup_manager, temp_cache_dir):
        """Test auto cleanup removes old unused toolchains."""
        toolchain_id = "gcc-old"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        (tc_path / "file.txt").write_text("test")

        old_date = datetime.now() - timedelta(days=100)

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "old",
                "ref_count": 0,
                "last_access": old_date.isoformat(),
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        result = cleanup_manager.auto_cleanup(max_age_days=90, dry_run=False)

        assert toolchain_id in result.removed
        assert not tc_path.exists()

    def test_get_statistics(self, cleanup_manager, temp_cache_dir):
        """Test getting cache statistics."""
        # Add some toolchains
        tc1_path = temp_cache_dir / "gcc-13.2.0"
        tc1_path.mkdir()
        (tc1_path / "file.txt").write_text("test" * 100)

        tc2_path = temp_cache_dir / "llvm-16.0.0"
        tc2_path.mkdir()
        (tc2_path / "file.txt").write_text("test" * 100)

        with cleanup_manager.registry._lock():
            data = cleanup_manager.registry._load_registry()
            data["toolchains"]["gcc-13.2.0"] = {
                "path": str(tc1_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 1,
                "projects": ["/project1"],
            }
            data["toolchains"]["llvm-16.0.0"] = {
                "path": str(tc2_path),
                "name": "LLVM",
                "version": "16.0.0",
                "ref_count": 0,  # Unused
                "projects": [],
            }
            cleanup_manager.registry._save_registry(data)

        stats = cleanup_manager.get_statistics()

        assert stats["total_toolchains"] == 2
        assert stats["total_size"] > 0
        assert stats["unused_toolchains"] == 1
        assert stats["unused_size"] > 0
        assert "free_space" in stats


# Integration tests
class TestCleanupIntegration:
    def test_full_workflow(self, temp_cache_dir, tmp_path):
        """Test complete cleanup workflow."""
        registry = ToolchainCacheRegistry(
            registry_path=temp_cache_dir / "registry.json"
        )
        ref_counter = ReferenceCounter(cache_registry=registry)
        cleanup_mgr = ToolchainCleanupManager(cache_registry=registry)

        # Create toolchain
        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()
        (tc_path / "file.txt").write_text("test")

        with registry._lock():
            data = registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 0,
                "projects": [],
            }
            registry._save_registry(data)

        # Add project reference
        project_path = tmp_path / "project1"
        count = ref_counter.increment(toolchain_id, project_path)
        assert count == 1

        # Try cleanup - should skip (referenced)
        result = cleanup_mgr.cleanup([toolchain_id], dry_run=False)
        assert toolchain_id in result.skipped
        assert tc_path.exists()

        # Remove reference
        count = ref_counter.decrement(toolchain_id, project_path)
        assert count == 0

        # Cleanup should succeed now
        result = cleanup_mgr.cleanup([toolchain_id], dry_run=False)
        assert toolchain_id in result.removed
        assert not tc_path.exists()

    def test_multiple_projects_reference(self, temp_cache_dir, tmp_path):
        """Test toolchain referenced by multiple projects."""
        registry = ToolchainCacheRegistry(
            registry_path=temp_cache_dir / "registry.json"
        )
        ref_counter = ReferenceCounter(cache_registry=registry)

        toolchain_id = "gcc-13.2.0"
        tc_path = temp_cache_dir / toolchain_id
        tc_path.mkdir()

        with registry._lock():
            data = registry._load_registry()
            data["toolchains"][toolchain_id] = {
                "path": str(tc_path),
                "name": "GCC",
                "version": "13.2.0",
                "ref_count": 0,
                "projects": [],
            }
            registry._save_registry(data)

        # Add multiple project references
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project3 = tmp_path / "project3"

        count = ref_counter.increment(toolchain_id, project1)
        assert count == 1

        count = ref_counter.increment(toolchain_id, project2)
        assert count == 2

        count = ref_counter.increment(toolchain_id, project3)
        assert count == 3

        # Remove one reference
        count = ref_counter.decrement(toolchain_id, project1)
        assert count == 2

        # Check final count
        final_count = ref_counter.get_count(toolchain_id)
        assert final_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
