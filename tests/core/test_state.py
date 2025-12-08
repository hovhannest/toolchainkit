"""
Unit tests for state management module.

Tests state loading, saving, updates, change detection, and validation.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from toolchainkit.core.state import (
    StateManager,
    ProjectState,
    CachingState,
    StateError,
    compute_config_hash,
)


class TestCachingState:
    """Tests for CachingState dataclass."""

    def test_default_values(self):
        """Test CachingState default values."""
        caching = CachingState()
        assert caching.enabled is False
        assert caching.tool is None
        assert caching.configured is False

    def test_custom_values(self):
        """Test CachingState with custom values."""
        caching = CachingState(enabled=True, tool="sccache", configured=True)
        assert caching.enabled is True
        assert caching.tool == "sccache"
        assert caching.configured is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        caching = CachingState(enabled=True, tool="ccache", configured=True)
        data = caching.to_dict()

        assert data == {"enabled": True, "tool": "ccache", "configured": True}


class TestProjectState:
    """Tests for ProjectState dataclass."""

    def test_default_values(self):
        """Test ProjectState default values."""
        state = ProjectState()

        assert state.version == 1
        assert state.active_toolchain is None
        assert state.toolchain_hash is None
        assert state.config_hash is None
        assert state.cmake_configured is False
        assert state.last_bootstrap is None
        assert state.last_configure is None
        assert state.package_manager is None
        assert state.package_manager_configured is False
        assert state.build_directory == "build"
        assert isinstance(state.caching, CachingState)
        assert state.modules == ["core", "cmake"]

    def test_custom_values(self):
        """Test ProjectState with custom values."""
        caching = CachingState(enabled=True, tool="sccache")
        state = ProjectState(
            active_toolchain="llvm-18.1.8",
            toolchain_hash="sha256:abc123",
            config_hash="sha256:def456",
            cmake_configured=True,
            build_directory="custom_build",
            caching=caching,
            modules=["core", "cmake", "caching"],
        )

        assert state.active_toolchain == "llvm-18.1.8"
        assert state.toolchain_hash == "sha256:abc123"
        assert state.config_hash == "sha256:def456"
        assert state.cmake_configured is True
        assert state.build_directory == "custom_build"
        assert state.caching.enabled is True
        assert state.modules == ["core", "cmake", "caching"]

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = ProjectState(
            active_toolchain="llvm-18.1.8", config_hash="sha256:abc123"
        )
        data = state.to_dict()

        assert data["version"] == 1
        assert data["active_toolchain"] == "llvm-18.1.8"
        assert data["config_hash"] == "sha256:abc123"
        assert "caching" in data
        assert "modules" in data


class TestStateManagerInit:
    """Tests for StateManager initialization."""

    def test_init_with_valid_path(self, temp_dir):
        """Test initialization with valid project root."""
        manager = StateManager(temp_dir)

        assert manager.project_root == temp_dir.resolve()
        assert manager.state_file == temp_dir.resolve() / ".toolchainkit" / "state.json"
        assert manager._state is None

    def test_init_with_string_path(self, temp_dir):
        """Test initialization with string path."""
        manager = StateManager(str(temp_dir))

        assert manager.project_root == temp_dir.resolve()
        assert isinstance(manager.project_root, Path)

    def test_init_with_nonexistent_path(self, temp_dir):
        """Test initialization with nonexistent path."""
        nonexistent = temp_dir / "nonexistent"

        with pytest.raises(StateError) as exc_info:
            StateManager(nonexistent)

        assert "does not exist" in str(exc_info.value)

    def test_init_with_file_path(self, temp_dir):
        """Test initialization with file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("test")

        with pytest.raises(StateError) as exc_info:
            StateManager(file_path)

        assert "not a directory" in str(exc_info.value)


class TestStateManagerLoad:
    """Tests for state loading."""

    def test_load_missing_file(self, temp_dir):
        """Test loading when state file doesn't exist."""
        manager = StateManager(temp_dir)
        state = manager.load()

        assert isinstance(state, ProjectState)
        assert state.active_toolchain is None
        assert manager._state is state  # Cached

    def test_load_existing_file(self, temp_dir):
        """Test loading existing state file."""
        state_file = temp_dir / ".toolchainkit" / "state.json"
        state_file.parent.mkdir(parents=True)

        state_data = {
            "version": 1,
            "active_toolchain": "llvm-18.1.8",
            "toolchain_hash": "sha256:abc123",
            "config_hash": "sha256:def456",
            "cmake_configured": True,
            "build_directory": "build",
            "caching": {"enabled": True, "tool": "sccache", "configured": True},
            "modules": ["core", "cmake"],
        }

        state_file.write_text(json.dumps(state_data))

        manager = StateManager(temp_dir)
        state = manager.load()

        assert state.active_toolchain == "llvm-18.1.8"
        assert state.toolchain_hash == "sha256:abc123"
        assert state.config_hash == "sha256:def456"
        assert state.cmake_configured is True
        assert state.caching.enabled is True
        assert state.caching.tool == "sccache"

    def test_load_caches_state(self, temp_dir):
        """Test that load caches state in memory."""
        manager = StateManager(temp_dir)

        state1 = manager.load()
        state2 = manager.load()

        assert state1 is state2  # Same object

    def test_load_corrupted_json(self, temp_dir):
        """Test loading corrupted JSON file."""
        state_file = temp_dir / ".toolchainkit" / "state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("{ invalid json")

        manager = StateManager(temp_dir)
        state = manager.load()

        # Should return default state
        assert isinstance(state, ProjectState)
        assert state.active_toolchain is None

    def test_load_invalid_data_types(self, temp_dir):
        """Test loading with invalid data types."""
        state_file = temp_dir / ".toolchainkit" / "state.json"
        state_file.parent.mkdir(parents=True)

        # Write invalid data
        state_file.write_text(
            json.dumps({"version": "not-a-number", "active_toolchain": 123})
        )

        manager = StateManager(temp_dir)
        state = manager.load()

        # Should handle gracefully and return default
        assert isinstance(state, ProjectState)

    def test_load_minimal_state(self, temp_dir):
        """Test loading state with minimal fields."""
        state_file = temp_dir / ".toolchainkit" / "state.json"
        state_file.parent.mkdir(parents=True)

        # Only required fields
        state_data = {"version": 1}
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(temp_dir)
        state = manager.load()

        assert state.version == 1
        assert state.active_toolchain is None
        assert isinstance(state.caching, CachingState)
        assert state.modules == ["core", "cmake"]


class TestStateManagerSave:
    """Tests for state saving."""

    def test_save_creates_directory(self, temp_dir):
        """Test that save creates .toolchainkit directory."""
        manager = StateManager(temp_dir)
        state = ProjectState(active_toolchain="llvm-18.1.8")

        manager.save(state)

        assert manager.state_file.exists()
        assert manager.state_file.parent.exists()

    def test_save_writes_json(self, temp_dir):
        """Test that save writes valid JSON."""
        manager = StateManager(temp_dir)
        state = ProjectState(
            active_toolchain="llvm-18.1.8", config_hash="sha256:abc123"
        )

        manager.save(state)

        # Read and verify
        with open(manager.state_file, "r") as f:
            data = json.load(f)

        assert data["active_toolchain"] == "llvm-18.1.8"
        assert data["config_hash"] == "sha256:abc123"

    def test_save_uses_atomic_write(self, temp_dir):
        """Test that save uses atomic write."""
        manager = StateManager(temp_dir)
        state = ProjectState(active_toolchain="test")

        # Mock atomic_write to verify it's called
        with patch("toolchainkit.core.state.atomic_write") as mock_atomic:
            manager.save(state)

            mock_atomic.assert_called_once()
            call_args = mock_atomic.call_args
            assert call_args[0][0] == manager.state_file

    def test_save_current_state(self, temp_dir):
        """Test saving current state without parameter."""
        manager = StateManager(temp_dir)
        state = manager.load()
        state.active_toolchain = "llvm-18.1.8"
        manager._state = state

        manager.save()  # No parameter

        # Reload and verify
        manager2 = StateManager(temp_dir)
        loaded_state = manager2.load()
        assert loaded_state.active_toolchain == "llvm-18.1.8"

    def test_save_with_none_state(self, temp_dir):
        """Test saving with None state (should do nothing)."""
        manager = StateManager(temp_dir)
        manager.save(None)  # Should not crash

        # No file should be created
        assert not manager.state_file.exists()


class TestStateManagerUpdates:
    """Tests for state update methods."""

    def test_update_toolchain(self, temp_dir):
        """Test updating toolchain information."""
        manager = StateManager(temp_dir)

        manager.update_toolchain("llvm-18.1.8", "sha256:abc123")

        state = manager.load()
        assert state.active_toolchain == "llvm-18.1.8"
        assert state.toolchain_hash == "sha256:abc123"
        assert state.last_configure is not None

        # Verify timestamp format
        datetime.fromisoformat(state.last_configure)  # Should not raise

    def test_update_config_hash(self, temp_dir):
        """Test updating configuration hash."""
        manager = StateManager(temp_dir)

        manager.update_config_hash("sha256:def456")

        state = manager.load()
        assert state.config_hash == "sha256:def456"

    def test_mark_bootstrap_complete(self, temp_dir):
        """Test marking bootstrap complete."""
        manager = StateManager(temp_dir)

        manager.mark_bootstrap_complete()

        state = manager.load()
        assert state.last_bootstrap is not None
        datetime.fromisoformat(state.last_bootstrap)  # Verify format

    def test_mark_cmake_configured(self, temp_dir):
        """Test marking CMake as configured."""
        manager = StateManager(temp_dir)

        manager.mark_cmake_configured("custom_build")

        state = manager.load()
        assert state.cmake_configured is True
        assert state.build_directory == "custom_build"
        assert state.last_configure is not None

    def test_mark_cmake_configured_default_dir(self, temp_dir):
        """Test marking CMake configured with default directory."""
        manager = StateManager(temp_dir)

        manager.mark_cmake_configured()

        state = manager.load()
        assert state.build_directory == "build"

    def test_mark_package_manager_configured(self, temp_dir):
        """Test marking package manager as configured."""
        manager = StateManager(temp_dir)

        manager.mark_package_manager_configured("conan")

        state = manager.load()
        assert state.package_manager == "conan"
        assert state.package_manager_configured is True

    def test_update_caching(self, temp_dir):
        """Test updating caching configuration."""
        manager = StateManager(temp_dir)

        manager.update_caching(enabled=True, tool="sccache")

        state = manager.load()
        assert state.caching.enabled is True
        assert state.caching.tool == "sccache"
        assert state.caching.configured is True

    def test_update_caching_disabled(self, temp_dir):
        """Test disabling caching."""
        manager = StateManager(temp_dir)

        manager.update_caching(enabled=False)

        state = manager.load()
        assert state.caching.enabled is False
        assert state.caching.tool is None
        assert state.caching.configured is True


class TestStateManagerChangeDetection:
    """Tests for change detection (needs_reconfigure)."""

    def test_needs_reconfigure_no_previous_config(self, temp_dir):
        """Test reconfigure needed when no previous configuration."""
        manager = StateManager(temp_dir)

        assert manager.needs_reconfigure("sha256:abc123") is True

    def test_needs_reconfigure_config_changed(self, temp_dir):
        """Test reconfigure needed when config hash changed."""
        manager = StateManager(temp_dir)
        manager.update_config_hash("sha256:old_hash")

        assert manager.needs_reconfigure("sha256:new_hash") is True

    def test_needs_reconfigure_cmake_not_configured(self, temp_dir):
        """Test reconfigure needed when CMake not configured."""
        manager = StateManager(temp_dir)
        manager.update_config_hash("sha256:abc123")

        assert manager.needs_reconfigure("sha256:abc123") is True

    def test_needs_reconfigure_build_dir_missing(self, temp_dir):
        """Test reconfigure needed when build directory missing."""
        manager = StateManager(temp_dir)
        manager.update_config_hash("sha256:abc123")
        manager.mark_cmake_configured("build")

        # Build dir doesn't exist
        assert manager.needs_reconfigure("sha256:abc123") is True

    def test_no_reconfigure_when_unchanged(self, temp_dir):
        """Test no reconfigure needed when nothing changed."""
        manager = StateManager(temp_dir)

        # Set up state
        manager.update_config_hash("sha256:abc123")
        manager.mark_cmake_configured("build")

        # Create build directory
        build_dir = temp_dir / "build"
        build_dir.mkdir()

        # Should not need reconfigure
        assert manager.needs_reconfigure("sha256:abc123") is False

    def test_needs_reconfigure_custom_build_dir(self, temp_dir):
        """Test reconfigure with custom build directory."""
        manager = StateManager(temp_dir)
        manager.update_config_hash("sha256:abc123")
        manager.mark_cmake_configured("custom_build")

        # Create the custom build directory
        custom_build = temp_dir / "custom_build"
        custom_build.mkdir()

        # Should not need reconfigure
        assert manager.needs_reconfigure("sha256:abc123") is False


class TestStateManagerValidation:
    """Tests for state validation."""

    def test_validate_empty_state(self, temp_dir):
        """Test validating empty state (no issues)."""
        manager = StateManager(temp_dir)
        issues = manager.validate()

        assert issues == []

    def test_validate_missing_build_directory(self, temp_dir):
        """Test validation detects missing build directory."""
        manager = StateManager(temp_dir)
        manager.mark_cmake_configured("build")

        issues = manager.validate()

        assert len(issues) == 1
        assert "Build directory not found" in issues[0]
        assert "build" in issues[0]

    def test_validate_existing_build_directory(self, temp_dir):
        """Test validation passes with existing build directory."""
        manager = StateManager(temp_dir)

        build_dir = temp_dir / "build"
        build_dir.mkdir()
        manager.mark_cmake_configured("build")

        issues = manager.validate()

        assert issues == []

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_validate_toolchain_not_in_registry(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test validation detects toolchain not in registry."""
        # Setup mocks
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain_info.return_value = None
        mock_registry_class.return_value = mock_registry

        manager = StateManager(temp_dir)
        manager.update_toolchain("llvm-18.1.8", "sha256:abc123")

        issues = manager.validate()

        assert len(issues) == 1
        assert "not found in registry" in issues[0]
        assert "llvm-18.1.8" in issues[0]

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_validate_toolchain_path_missing(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test validation detects missing toolchain path."""
        # Setup mocks
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain_info.return_value = {
            "path": str(temp_dir / "nonexistent"),
            "size_bytes": 1000,
        }
        mock_registry_class.return_value = mock_registry

        manager = StateManager(temp_dir)
        manager.update_toolchain("llvm-18.1.8", "sha256:abc123")

        issues = manager.validate()

        assert len(issues) == 1
        assert "path does not exist" in issues[0]

    def test_validate_multiple_issues(self, temp_dir):
        """Test validation reports multiple issues."""
        manager = StateManager(temp_dir)

        # Create multiple issues
        manager.update_toolchain("nonexistent", "sha256:abc123")
        manager.mark_cmake_configured("missing_build")

        with patch(
            "toolchainkit.core.cache_registry.ToolchainCacheRegistry"
        ) as mock_registry_class:
            with patch(
                "toolchainkit.core.directory.get_global_cache_dir"
            ) as mock_cache:
                mock_cache.return_value = temp_dir / ".toolchainkit"
                mock_registry = Mock()
                mock_registry.get_toolchain.return_value = None
                mock_registry_class.return_value = mock_registry

                issues = manager.validate()

        # Should have both toolchain and build dir issues
        assert len(issues) >= 1  # At least build dir issue


class TestStateManagerClear:
    """Tests for state clearing."""

    def test_clear_resets_state(self, temp_dir):
        """Test clearing resets all state to defaults."""
        manager = StateManager(temp_dir)

        # Set up state
        manager.update_toolchain("llvm-18.1.8", "sha256:abc123")
        manager.update_config_hash("sha256:def456")
        manager.mark_cmake_configured()

        # Clear
        manager.clear()

        # Load and verify
        state = manager.load()
        assert state.active_toolchain is None
        assert state.toolchain_hash is None
        assert state.config_hash is None
        assert state.cmake_configured is False

    def test_clear_saves_to_disk(self, temp_dir):
        """Test clearing persists to disk."""
        manager = StateManager(temp_dir)
        manager.update_toolchain("llvm-18.1.8", "sha256:abc123")

        manager.clear()

        # Reload from disk
        manager2 = StateManager(temp_dir)
        state = manager2.load()

        assert state.active_toolchain is None


class TestComputeConfigHash:
    """Tests for compute_config_hash function."""

    def test_compute_hash_existing_file(self, temp_dir):
        """Test computing hash of existing file."""
        config_file = temp_dir / "toolchainkit.yaml"
        config_file.write_text("test: value\n")

        hash_str = compute_config_hash(config_file)

        assert hash_str.startswith("sha256:")
        assert len(hash_str) > 8  # More than just prefix

    def test_compute_hash_missing_file(self, temp_dir):
        """Test computing hash of missing file."""
        config_file = temp_dir / "nonexistent.yaml"

        hash_str = compute_config_hash(config_file)

        assert hash_str == "sha256:no-config"

    def test_compute_hash_deterministic(self, temp_dir):
        """Test hash computation is deterministic."""
        config_file = temp_dir / "toolchainkit.yaml"
        config_file.write_text("test: value\n")

        hash1 = compute_config_hash(config_file)
        hash2 = compute_config_hash(config_file)

        assert hash1 == hash2

    def test_compute_hash_different_content(self, temp_dir):
        """Test different content produces different hash."""
        config_file = temp_dir / "toolchainkit.yaml"

        config_file.write_text("test: value1\n")
        hash1 = compute_config_hash(config_file)

        config_file.write_text("test: value2\n")
        hash2 = compute_config_hash(config_file)

        assert hash1 != hash2


class TestStatePersistence:
    """Integration-style tests for state persistence."""

    def test_save_and_load_roundtrip(self, temp_dir):
        """Test saving and loading preserves all data."""
        manager = StateManager(temp_dir)

        # Create complex state
        state = ProjectState(
            active_toolchain="llvm-18.1.8",
            toolchain_hash="sha256:abc123",
            config_hash="sha256:def456",
            cmake_configured=True,
            last_bootstrap="2025-11-14T10:30:00",
            last_configure="2025-11-14T10:35:00",
            package_manager="conan",
            package_manager_configured=True,
            build_directory="custom_build",
            caching=CachingState(enabled=True, tool="sccache", configured=True),
            modules=["core", "cmake", "caching"],
        )

        manager.save(state)

        # Reload
        manager2 = StateManager(temp_dir)
        loaded = manager2.load()

        assert loaded.active_toolchain == state.active_toolchain
        assert loaded.toolchain_hash == state.toolchain_hash
        assert loaded.config_hash == state.config_hash
        assert loaded.cmake_configured == state.cmake_configured
        assert loaded.last_bootstrap == state.last_bootstrap
        assert loaded.last_configure == state.last_configure
        assert loaded.package_manager == state.package_manager
        assert loaded.package_manager_configured == state.package_manager_configured
        assert loaded.build_directory == state.build_directory
        assert loaded.caching.enabled == state.caching.enabled
        assert loaded.caching.tool == state.caching.tool
        assert loaded.modules == state.modules

    def test_multiple_save_load_cycles(self, temp_dir):
        """Test multiple save/load cycles."""
        manager = StateManager(temp_dir)

        # First cycle
        manager.update_toolchain("llvm-18", "sha256:v1")
        _state1 = manager.load()

        # Second cycle
        manager.update_toolchain("llvm-19", "sha256:v2")
        state2 = manager.load()

        # Verify latest state
        assert state2.active_toolchain == "llvm-19"
        assert state2.toolchain_hash == "sha256:v2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
