"""
Regression tests for state file format compatibility.

Ensures state files remain compatible across versions.
"""

import pytest
import json
from pathlib import Path
from toolchainkit.core.state import (
    StateManager,
    ProjectState,
    CachingState,
    StateError,
)


@pytest.mark.regression
class TestLegacyStateFileCompatibility:
    """Test backward compatibility with legacy state formats."""

    def test_load_minimal_state_file(self, tmp_path):
        """Verify minimal state file loads correctly."""
        # Minimal valid state
        state_data = {
            "version": 1,
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data, indent=2))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.version == 1
        assert state.active_toolchain is None
        assert state.config_hash is None

    def test_load_complete_state_file(self, tmp_path):
        """Verify complete state file with all fields loads correctly."""
        state_data = {
            "version": 1,
            "active_toolchain": "llvm-18.1.8-linux-x64",
            "toolchain_hash": "sha256:abc123def456",
            "config_hash": "sha256:config789",
            "cmake_configured": True,
            "last_bootstrap": "2024-01-01T00:00:00Z",
            "last_configure": "2024-01-01T01:00:00Z",
            "package_manager": "conan",
            "package_manager_configured": True,
            "build_directory": "build",
            "caching": {
                "enabled": True,
                "tool": "ccache",
                "configured": True,
            },
            "modules": ["core", "cmake"],
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data, indent=2))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.version == 1
        assert state.active_toolchain == "llvm-18.1.8-linux-x64"
        assert state.toolchain_hash == "sha256:abc123def456"
        assert state.config_hash == "sha256:config789"
        assert state.cmake_configured is True
        assert state.last_bootstrap == "2024-01-01T00:00:00Z"
        assert state.package_manager == "conan"
        assert state.build_directory == "build"
        assert state.caching.enabled is True
        assert state.caching.tool == "ccache"
        assert state.modules == ["core", "cmake"]

    def test_load_state_with_missing_optional_fields(self, tmp_path):
        """Verify state with missing optional fields loads with defaults."""
        # Only required version field
        state_data = {
            "version": 1,
            "active_toolchain": "llvm-18",
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.version == 1
        assert state.active_toolchain == "llvm-18"
        # Check defaults
        assert state.config_hash is None
        assert state.cmake_configured is False
        assert state.last_bootstrap is None
        assert state.build_directory == "build"
        assert state.caching.enabled is False
        assert state.modules == ["core", "cmake"]

    def test_load_state_with_extra_fields(self, tmp_path):
        """Verify unknown fields in state don't break parsing."""
        # State with future fields
        state_data = {
            "version": 1,
            "active_toolchain": "llvm-18",
            "future_field": "future_value",  # Unknown field
            "nested": {"unknown": "data"},  # Unknown nested structure
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        # Should parse successfully, ignoring unknown fields
        assert state.version == 1
        assert state.active_toolchain == "llvm-18"

    def test_load_state_without_caching_section(self, tmp_path):
        """Verify state without caching section uses default."""
        state_data = {
            "version": 1,
            "active_toolchain": "llvm-18",
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        # Caching should have defaults
        assert state.caching.enabled is False
        assert state.caching.tool is None
        assert state.caching.configured is False


@pytest.mark.regression
class TestStateFileDefaultValues:
    """Test that state file defaults remain consistent."""

    def test_default_version(self, tmp_path):
        """Verify default version is 1."""
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()

        # No state file - should get defaults
        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.version == 1

    def test_default_build_directory(self, tmp_path):
        """Verify default build directory is 'build'."""
        state_data = {"version": 1}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.build_directory == "build"

    def test_default_modules(self, tmp_path):
        """Verify default modules are ['core', 'cmake']."""
        state_data = {"version": 1}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.modules == ["core", "cmake"]

    def test_default_cmake_configured(self, tmp_path):
        """Verify cmake_configured defaults to False."""
        state_data = {"version": 1}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.cmake_configured is False

    def test_default_package_manager_configured(self, tmp_path):
        """Verify package_manager_configured defaults to False."""
        state_data = {"version": 1}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.package_manager_configured is False


@pytest.mark.regression
class TestStateFileRoundTrip:
    """Test state file write/read round-trips."""

    def test_state_round_trip_preserves_data(self, tmp_path):
        """Verify writing and reading state preserves all data."""
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()

        manager = StateManager(tmp_path)

        # Create state with all fields
        original_state = ProjectState(
            version=1,
            active_toolchain="llvm-18.1.8",
            toolchain_hash="sha256:abc123",
            config_hash="sha256:def456",
            cmake_configured=True,
            last_bootstrap="2024-01-01T00:00:00Z",
            last_configure="2024-01-02T00:00:00Z",
            package_manager="vcpkg",
            package_manager_configured=True,
            build_directory="custom_build",
            caching=CachingState(enabled=True, tool="sccache", configured=True),
            modules=["core", "cmake", "custom"],
        )

        # Save
        manager.save(original_state)

        # Clear cache and reload
        manager._state = None
        loaded_state = manager.load()

        # Verify all data preserved
        assert loaded_state.version == original_state.version
        assert loaded_state.active_toolchain == original_state.active_toolchain
        assert loaded_state.toolchain_hash == original_state.toolchain_hash
        assert loaded_state.config_hash == original_state.config_hash
        assert loaded_state.cmake_configured == original_state.cmake_configured
        assert loaded_state.last_bootstrap == original_state.last_bootstrap
        assert loaded_state.last_configure == original_state.last_configure
        assert loaded_state.package_manager == original_state.package_manager
        assert (
            loaded_state.package_manager_configured
            == original_state.package_manager_configured
        )
        assert loaded_state.build_directory == original_state.build_directory
        assert loaded_state.caching.enabled == original_state.caching.enabled
        assert loaded_state.caching.tool == original_state.caching.tool
        assert loaded_state.caching.configured == original_state.caching.configured
        assert loaded_state.modules == original_state.modules

    def test_multiple_save_load_cycles(self, tmp_path):
        """Verify multiple save/load cycles preserve data integrity."""
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()

        manager = StateManager(tmp_path)

        # Cycle 1: Save initial state
        state1 = ProjectState(active_toolchain="llvm-18", config_hash="hash1")
        manager.save(state1)

        # Cycle 2: Update and save
        manager._state = None
        state2 = manager.load()
        state2.toolchain_hash = "newhash"
        manager.save(state2)

        # Cycle 3: Load and verify
        manager._state = None
        state3 = manager.load()

        assert state3.active_toolchain == "llvm-18"
        assert state3.config_hash == "hash1"
        assert state3.toolchain_hash == "newhash"


@pytest.mark.regression
class TestStateFileErrorHandling:
    """Test error handling remains consistent."""

    def test_nonexistent_state_file_returns_defaults(self, tmp_path):
        """Verify nonexistent state file returns default state."""
        # .toolchainkit directory doesn't exist yet
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()  # Create directory but no state.json

        manager = StateManager(tmp_path)
        state = manager.load()

        # Should get default state without error
        assert state.version == 1
        assert state.active_toolchain is None

    def test_corrupted_state_file_returns_defaults(self, tmp_path):
        """Verify corrupted state file returns default state with warning."""
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"

        # Write invalid JSON
        state_file.write_text("{ invalid json syntax }")

        manager = StateManager(tmp_path)
        state = manager.load()

        # Should recover gracefully with defaults
        assert state.version == 1
        assert state.active_toolchain is None

    def test_empty_state_file_returns_defaults(self, tmp_path):
        """Verify empty state file returns default state."""
        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"

        # Empty file
        state_file.write_text("")

        manager = StateManager(tmp_path)
        state = manager.load()

        # Should recover with defaults
        assert state.version == 1

    def test_state_file_with_null_values(self, tmp_path):
        """Verify state file with null values loads correctly."""
        state_data = {
            "version": 1,
            "active_toolchain": None,
            "toolchain_hash": None,
            "config_hash": None,
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        state = manager.load()

        assert state.version == 1
        assert state.active_toolchain is None
        assert state.toolchain_hash is None
        assert state.config_hash is None

    def test_nonexistent_project_root_raises_error(self):
        """Verify StateManager raises error for nonexistent project root."""
        with pytest.raises(StateError, match="Project root does not exist"):
            StateManager(Path("/nonexistent/project"))

    def test_project_root_as_file_raises_error(self, tmp_path):
        """Verify StateManager raises error if project root is a file."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("I am a file")

        with pytest.raises(StateError, match="not a directory"):
            StateManager(file_path)


@pytest.mark.regression
class TestStateVersionMigration:
    """Test state version migration handling."""

    def test_unsupported_version_logs_warning(self, tmp_path):
        """Verify unsupported versions log warning and use migration."""
        state_data = {
            "version": 999,  # Future version
            "active_toolchain": "llvm-18",
        }

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)
        # Should load with migration (logged warning not asserted in test)
        state = manager.load()

        # Should still have basic data
        assert state is not None


@pytest.mark.regression
class TestStateCaching:
    """Test state caching behavior."""

    def test_state_cached_after_first_load(self, tmp_path):
        """Verify state is cached after first load."""
        state_data = {"version": 1, "active_toolchain": "llvm-18"}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)

        # First load
        state1 = manager.load()
        assert state1.active_toolchain == "llvm-18"

        # Modify file on disk
        state_data["active_toolchain"] = "gcc-13"
        state_file.write_text(json.dumps(state_data))

        # Second load should return cached state
        state2 = manager.load()

        # Should still have original cached value (same instance)
        assert state1 is state2
        assert state2.active_toolchain == "llvm-18"  # Not "gcc-13"

    def test_state_reloaded_after_cache_clear(self, tmp_path):
        """Verify clearing cache forces reload from disk."""
        state_data = {"version": 1, "active_toolchain": "llvm-18"}

        state_dir = tmp_path / ".toolchainkit"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(tmp_path)

        # First load
        state1 = manager.load()
        assert state1.active_toolchain == "llvm-18"

        # Modify file on disk
        state_data["active_toolchain"] = "gcc-13"
        state_file.write_text(json.dumps(state_data))

        # Clear cache and reload
        manager._state = None
        state2 = manager.load()

        # Should be new state from disk (different from cached state1)
        assert state1 is not state2
        assert state2.active_toolchain == "gcc-13"


@pytest.mark.regression
def test_project_state_to_dict_completeness(tmp_path):
    """
    Verify ProjectState.to_dict() includes all fields.

    This ensures serialization doesn't lose data.
    """
    state = ProjectState(
        version=1,
        active_toolchain="llvm-18",
        toolchain_hash="hash1",
        config_hash="hash2",
        cmake_configured=True,
        last_bootstrap="2024-01-01T00:00:00Z",
        last_configure="2024-01-02T00:00:00Z",
        package_manager="conan",
        package_manager_configured=True,
        build_directory="build",
        caching=CachingState(enabled=True, tool="ccache", configured=True),
        modules=["core", "cmake"],
    )

    data = state.to_dict()

    # Verify all fields present
    assert "version" in data
    assert "active_toolchain" in data
    assert "toolchain_hash" in data
    assert "config_hash" in data
    assert "cmake_configured" in data
    assert "last_bootstrap" in data
    assert "last_configure" in data
    assert "package_manager" in data
    assert "package_manager_configured" in data
    assert "build_directory" in data
    assert "caching" in data
    assert "modules" in data

    # Verify caching nested structure
    assert "enabled" in data["caching"]
    assert "tool" in data["caching"]
    assert "configured" in data["caching"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
