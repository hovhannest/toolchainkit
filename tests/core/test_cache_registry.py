"""
Unit tests for shared cache registry.

Tests registry operations, reference counting, and thread-safety.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from toolchainkit.core.cache_registry import ToolchainCacheRegistry
from toolchainkit.core.exceptions import (
    RegistryError,
    ToolchainNotInCacheError,
    ToolchainInUseError,
    RegistryLockTimeout,
)


class TestRegistryBasics:
    """Test basic registry operations."""

    def test_create_registry(self, tmp_path):
        """Test creating new registry."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        assert registry.registry_path == registry_path
        assert registry.lock_path.name == "registry.lock"

    def test_load_empty_registry(self, tmp_path):
        """Test loading non-existent registry creates default structure."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        data = registry._load_registry()

        assert data["version"] == 1
        assert data["toolchains"] == {}
        assert data["total_size_mb"] == 0.0
        assert data["last_cleanup"] is None

    def test_save_and_load_registry(self, tmp_path):
        """Test saving and loading registry."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        test_data = {
            "version": 1,
            "toolchains": {
                "test-toolchain": {
                    "path": "/test/path",
                    "size_mb": 100.0,
                    "projects": [],
                }
            },
            "total_size_mb": 100.0,
            "last_cleanup": None,
        }

        registry._save_registry(test_data)
        loaded = registry._load_registry()

        assert loaded["version"] == 1
        assert "test-toolchain" in loaded["toolchains"]
        assert loaded["total_size_mb"] == 100.0

    def test_registry_file_created(self, tmp_path):
        """Test registry file is created on save."""
        registry_path = tmp_path / "registry.json"
        registry = ToolchainCacheRegistry(registry_path)

        data = registry._load_registry()
        registry._save_registry(data)

        assert registry_path.exists()


class TestToolchainRegistration:
    """Test toolchain registration and unregistration."""

    def test_register_toolchain(self, tmp_path):
        """Test registering a new toolchain."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "llvm-18.1.8",
            Path("/toolchains/llvm-18.1.8"),
            2048.5,
            "sha256:abc123",
            "https://example.com/llvm.tar.gz",
        )

        info = registry.get_toolchain_info("llvm-18.1.8")

        assert info is not None
        assert info["size_mb"] == 2048.5
        assert info["hash"] == "sha256:abc123"
        assert info["source_url"] == "https://example.com/llvm.tar.gz"
        assert info["verified"] is True
        assert len(info["projects"]) == 0

    def test_register_multiple_toolchains(self, tmp_path):
        """Test registering multiple toolchains."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "llvm-18", Path("/llvm"), 2000.0, "sha256:aaa", "http://a"
        )
        registry.register_toolchain(
            "gcc-13", Path("/gcc"), 1500.0, "sha256:bbb", "http://b"
        )
        registry.register_toolchain(
            "msvc-19", Path("/msvc"), 3000.0, "sha256:ccc", "http://c"
        )

        toolchains = registry.list_toolchains()

        assert len(toolchains) == 3
        assert "llvm-18" in toolchains
        assert "gcc-13" in toolchains
        assert "msvc-19" in toolchains

    def test_register_updates_total_size(self, tmp_path):
        """Test total size is updated when registering toolchains."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain("tc1", Path("/tc1"), 1000.0, "sha256:a", "http://a")
        registry.register_toolchain("tc2", Path("/tc2"), 500.0, "sha256:b", "http://b")

        stats = registry.get_cache_stats()

        assert stats["total_size_mb"] == 1500.0

    def test_unregister_toolchain(self, tmp_path):
        """Test unregistering unused toolchain."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.unregister_toolchain("test-tc")

        info = registry.get_toolchain_info("test-tc")
        assert info is None

    def test_unregister_in_use_toolchain_fails(self, tmp_path):
        """Test cannot unregister toolchain with project references."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project"))

        with pytest.raises(ToolchainInUseError):
            registry.unregister_toolchain("test-tc")

    def test_unregister_nonexistent_toolchain(self, tmp_path):
        """Test unregistering nonexistent toolchain is safe."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        # Should not raise exception
        registry.unregister_toolchain("nonexistent")

    def test_unregister_updates_total_size(self, tmp_path):
        """Test total size is updated when unregistering."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain("tc1", Path("/tc1"), 1000.0, "sha256:a", "http://a")
        registry.register_toolchain("tc2", Path("/tc2"), 500.0, "sha256:b", "http://b")
        registry.unregister_toolchain("tc1")

        stats = registry.get_cache_stats()
        assert stats["total_size_mb"] == 500.0


class TestProjectReferences:
    """Test project reference tracking."""

    def test_add_project_reference(self, tmp_path):
        """Test adding project reference."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project1"))

        info = registry.get_toolchain_info("test-tc")
        assert len(info["projects"]) == 1
        assert str(Path("/project1").resolve()) in info["projects"]

    def test_add_multiple_project_references(self, tmp_path):
        """Test adding multiple project references."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project1"))
        registry.add_project_reference("test-tc", Path("/project2"))
        registry.add_project_reference("test-tc", Path("/project3"))

        info = registry.get_toolchain_info("test-tc")
        assert len(info["projects"]) == 3

    def test_add_duplicate_reference_ignored(self, tmp_path):
        """Test adding same project reference twice is ignored."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project1"))
        registry.add_project_reference("test-tc", Path("/project1"))

        info = registry.get_toolchain_info("test-tc")
        assert len(info["projects"]) == 1

    def test_add_reference_to_nonexistent_toolchain(self, tmp_path):
        """Test adding reference to nonexistent toolchain raises error."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        with pytest.raises(ToolchainNotInCacheError):
            registry.add_project_reference("nonexistent", Path("/project"))

    def test_remove_project_reference(self, tmp_path):
        """Test removing project reference."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project1"))
        registry.remove_project_reference("test-tc", Path("/project1"))

        info = registry.get_toolchain_info("test-tc")
        assert len(info["projects"]) == 0

    def test_remove_one_of_multiple_references(self, tmp_path):
        """Test removing one project reference among several."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        registry.add_project_reference("test-tc", Path("/project1"))
        registry.add_project_reference("test-tc", Path("/project2"))
        registry.remove_project_reference("test-tc", Path("/project1"))

        info = registry.get_toolchain_info("test-tc")
        assert len(info["projects"]) == 1
        assert str(Path("/project2").resolve()) in info["projects"]

    def test_remove_nonexistent_reference(self, tmp_path):
        """Test removing nonexistent reference is safe."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )

        # Should not raise exception
        registry.remove_project_reference("test-tc", Path("/nonexistent"))


class TestUnusedDetection:
    """Test unused toolchain detection."""

    def test_get_unused_toolchains_empty(self, tmp_path):
        """Test getting unused toolchains from empty registry."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        unused = registry.get_unused_toolchains()

        assert len(unused) == 0

    def test_get_unused_toolchains(self, tmp_path):
        """Test detecting unused toolchains."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "used-tc", Path("/used"), 100.0, "sha256:a", "http://a"
        )
        registry.register_toolchain(
            "unused-tc", Path("/unused"), 100.0, "sha256:b", "http://b"
        )
        registry.add_project_reference("used-tc", Path("/project"))

        unused = registry.get_unused_toolchains()

        assert len(unused) == 1
        assert "unused-tc" in unused
        assert "used-tc" not in unused

    def test_get_unused_by_age(self, tmp_path):
        """Test getting unused toolchains older than N days."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        # Register toolchains
        registry.register_toolchain(
            "old-tc", Path("/old"), 100.0, "sha256:a", "http://a"
        )
        registry.register_toolchain(
            "new-tc", Path("/new"), 100.0, "sha256:b", "http://b"
        )

        # Manually set old timestamp
        data = registry._load_registry()
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        data["toolchains"]["old-tc"]["last_used"] = old_date
        registry._save_registry(data)

        # Get toolchains unused for >30 days
        unused = registry.get_unused_toolchains(older_than_days=30)

        assert "old-tc" in unused
        assert "new-tc" not in unused


class TestStatistics:
    """Test cache statistics."""

    def test_get_empty_stats(self, tmp_path):
        """Test getting stats from empty registry."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        stats = registry.get_cache_stats()

        assert stats["total_toolchains"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["unused_toolchains"] == 0
        assert stats["reclaimable_size_mb"] == 0.0

    def test_get_stats_with_toolchains(self, tmp_path):
        """Test calculating statistics."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain("tc1", Path("/tc1"), 1000.0, "sha256:a", "http://a")
        registry.register_toolchain("tc2", Path("/tc2"), 500.0, "sha256:b", "http://b")
        registry.register_toolchain("tc3", Path("/tc3"), 250.0, "sha256:c", "http://c")

        # tc1 is used
        registry.add_project_reference("tc1", Path("/project"))

        stats = registry.get_cache_stats()

        assert stats["total_toolchains"] == 3
        assert stats["total_size_mb"] == 1750.0
        assert stats["unused_toolchains"] == 2
        assert stats["reclaimable_size_mb"] == 750.0

    def test_mark_cleanup(self, tmp_path):
        """Test marking cleanup timestamp."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.mark_cleanup()

        stats = registry.get_cache_stats()
        assert stats["last_cleanup"] is not None


class TestTimestamps:
    """Test timestamp management."""

    def test_installed_timestamp_set(self, tmp_path):
        """Test installed timestamp is set on registration."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        before = datetime.now()
        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )
        after = datetime.now()

        info = registry.get_toolchain_info("test-tc")
        installed = datetime.fromisoformat(info["installed"])

        assert before <= installed <= after

    def test_last_used_updated_on_registration(self, tmp_path):
        """Test last_used is set on registration."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )

        info = registry.get_toolchain_info("test-tc")
        assert info["last_used"] is not None

    def test_update_last_used(self, tmp_path):
        """Test updating last_used timestamp."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )

        # Get initial timestamp
        info1 = registry.get_toolchain_info("test-tc")
        old_timestamp = info1["last_used"]

        # Wait a tiny bit and update
        import time

        time.sleep(0.01)
        registry.update_last_used("test-tc")

        # Check timestamp changed
        info2 = registry.get_toolchain_info("test-tc")
        new_timestamp = info2["last_used"]

        assert new_timestamp > old_timestamp

    def test_last_used_updated_on_add_reference(self, tmp_path):
        """Test last_used is updated when adding project reference."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )

        info1 = registry.get_toolchain_info("test-tc")
        old_timestamp = info1["last_used"]

        import time

        time.sleep(0.01)
        registry.add_project_reference("test-tc", Path("/project"))

        info2 = registry.get_toolchain_info("test-tc")
        new_timestamp = info2["last_used"]

        assert new_timestamp > old_timestamp


class TestAtomicity:
    """Test atomic operations."""

    def test_save_creates_parent_directory(self, tmp_path):
        """Test save creates parent directories."""
        nested_path = tmp_path / "nested" / "dir" / "registry.json"
        registry = ToolchainCacheRegistry(nested_path)

        data = registry._load_registry()
        registry._save_registry(data)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_registry_json_format(self, tmp_path):
        """Test registry is saved as valid JSON."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        registry.register_toolchain(
            "test-tc", Path("/test"), 100.0, "sha256:x", "http://x"
        )

        # Load directly as JSON
        with open(registry.registry_path, "r") as f:
            data = json.load(f)

        assert "version" in data
        assert "toolchains" in data
        assert "test-tc" in data["toolchains"]


class TestLocking:
    """Test file locking behavior."""

    def test_lock_context_manager(self, tmp_path):
        """Test lock context manager works."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        with registry._lock():
            # Lock should be acquired
            pass

        # Lock should be released

    def test_lock_timeout(self, tmp_path):
        """Test lock timeout raises exception."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json", lock_timeout=1)

        # Mock FileLock to raise Timeout
        from filelock import Timeout

        with patch("toolchainkit.core.cache_registry.FileLock") as mock_lock:
            mock_lock.return_value.__enter__.side_effect = Timeout("test.lock")

            with pytest.raises(RegistryLockTimeout):
                with registry._lock():
                    pass


class TestErrorHandling:
    """Test error handling."""

    def test_get_nonexistent_toolchain(self, tmp_path):
        """Test getting nonexistent toolchain returns None."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        info = registry.get_toolchain_info("nonexistent")

        assert info is None

    def test_list_toolchains_empty(self, tmp_path):
        """Test listing toolchains from empty registry."""
        registry = ToolchainCacheRegistry(tmp_path / "registry.json")

        toolchains = registry.list_toolchains()

        assert toolchains == []

    def test_corrupted_registry_handled(self, tmp_path):
        """Test corrupted registry file is handled gracefully."""
        registry_path = tmp_path / "registry.json"

        # Write invalid JSON
        registry_path.write_text("{ invalid json")

        registry = ToolchainCacheRegistry(registry_path)

        with pytest.raises(RegistryError):
            registry._load_registry()

    def test_invalid_registry_format_reset(self, tmp_path):
        """Test invalid registry format is reset."""
        registry_path = tmp_path / "registry.json"

        # Write JSON without required fields
        registry_path.write_text('{"invalid": "format"}')

        registry = ToolchainCacheRegistry(registry_path)
        data = registry._load_registry()

        # Should return default structure
        assert "version" in data
        assert "toolchains" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
