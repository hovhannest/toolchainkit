"""
Regression tests for directory structure creation.

Ensures directory layout remains stable across versions.
"""

import pytest
import os
import stat
from pathlib import Path
from toolchainkit.core import directory


@pytest.mark.regression
class TestDirectoryStructureRegression:
    """Regression tests for directory structure."""

    def test_global_cache_directory_structure(self, tmp_path, monkeypatch):
        """Verify global cache directory structure remains consistent."""
        # Mock the home directory to use tmp_path
        monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))

        # Create global cache structure
        cache_dir = directory.ensure_global_cache_structure()

        # Verify expected structure
        assert cache_dir.exists()
        assert (cache_dir / "toolchains").exists()
        assert (cache_dir / "lock").exists()
        assert (cache_dir / "registry.json").exists()

        # Verify registry.json is valid empty JSON
        registry_content = (cache_dir / "registry.json").read_text()
        assert registry_content == "{}"

    def test_project_local_directory_structure(self, tmp_path):
        """Verify project-local directory structure remains consistent."""
        # Create project structure
        project_local = directory.ensure_project_structure(tmp_path)

        # Verify expected structure
        assert project_local.exists()
        assert project_local.name == ".toolchainkit"
        assert (project_local / "packages").exists()
        assert (project_local / "cmake").exists()
        assert (project_local / "cmake" / "toolchainkit").exists()
        assert (project_local / "state.json").exists()

        # Verify state.json is valid empty JSON
        state_content = (project_local / "state.json").read_text()
        assert state_content == "{}"

    def test_hidden_directory_naming(self, tmp_path):
        """Verify .toolchainkit directories are named with dot prefix."""
        directory.ensure_project_structure(tmp_path)

        toolchain_dir = tmp_path / ".toolchainkit"
        assert toolchain_dir.exists()
        assert toolchain_dir.name.startswith(".")

    def test_directory_structure_idempotent(self, tmp_path):
        """Verify calling initialization multiple times is safe."""
        # Create structure twice
        project_local1 = directory.ensure_project_structure(tmp_path)
        project_local2 = directory.ensure_project_structure(tmp_path)

        # Should return same path
        assert project_local1 == project_local2

        # Should still have correct structure
        assert (project_local1 / "packages").exists()
        assert (project_local1 / "state.json").exists()

    def test_existing_directory_preserved(self, tmp_path):
        """Verify existing directory contents are preserved."""
        # Create directory with file first
        project_local = tmp_path / ".toolchainkit"
        project_local.mkdir()
        marker_file = project_local / "existing_file.txt"
        marker_file.write_text("preserved")

        # Initialize structure
        directory.ensure_project_structure(tmp_path)

        # Verify file still exists
        assert marker_file.exists()
        assert marker_file.read_text() == "preserved"

    def test_nested_directory_creation(self, tmp_path):
        """Verify nested directories are created correctly."""
        project_local = directory.ensure_project_structure(tmp_path)

        # Verify nested cmake/toolchainkit structure
        cmake_toolchain_dir = project_local / "cmake" / "toolchainkit"
        assert cmake_toolchain_dir.exists()
        assert cmake_toolchain_dir.is_dir()

        # Verify all parent directories exist
        assert (project_local / "cmake").exists()

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only permission test")
    def test_directory_permissions_unix(self, tmp_path):
        """Verify directories have correct permissions on Unix."""
        project_local = directory.ensure_project_structure(tmp_path)

        # .toolchainkit should be readable/writable by owner
        mode = project_local.stat().st_mode

        # Check owner has read, write, execute
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR
        assert mode & stat.S_IXUSR

    def test_directory_verification(self, tmp_path):
        """Verify directory writability check works."""
        # Create writable directory
        writable_dir = tmp_path / "writable"
        writable_dir.mkdir()

        assert directory.verify_directory_writable(writable_dir)

        # Non-existent directory
        non_existent = tmp_path / "nonexistent"
        assert not directory.verify_directory_writable(non_existent)


@pytest.mark.regression
class TestGitignoreIntegration:
    """Test .gitignore update functionality."""

    def test_gitignore_created_if_missing(self, tmp_path):
        """Verify .gitignore is created if it doesn't exist."""
        directory.update_gitignore(tmp_path)

        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert ".toolchainkit/" in content

    def test_gitignore_updated_if_exists(self, tmp_path):
        """Verify .gitignore is updated if it already exists."""
        # Create existing .gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("*.pyc\n__pycache__/\n")

        directory.update_gitignore(tmp_path)

        content = gitignore_path.read_text()
        assert "*.pyc" in content  # Preserved
        assert "__pycache__/" in content  # Preserved
        assert ".toolchainkit/" in content  # Added

    def test_gitignore_not_duplicated(self, tmp_path):
        """Verify .toolchainkit/ is not added multiple times."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".toolchainkit/\n")

        # Update multiple times
        directory.update_gitignore(tmp_path)
        directory.update_gitignore(tmp_path)

        content = gitignore_path.read_text()
        # Count occurrences
        count = content.count(".toolchainkit/")
        assert count == 1


@pytest.mark.regression
class TestPathResolution:
    """Test path resolution across platforms."""

    def test_global_cache_path_windows(self, monkeypatch):
        """Verify Windows global cache path."""
        if os.name != "nt":
            pytest.skip("Windows-only test")

        monkeypatch.setenv("USERPROFILE", r"C:\Users\TestUser")
        cache_dir = directory.get_global_cache_dir()

        assert str(cache_dir) == r"C:\Users\TestUser\.toolchainkit"

    def test_global_cache_path_unix(self, tmp_path, monkeypatch):
        """Verify Unix global cache path."""
        if os.name == "nt":
            pytest.skip("Unix-only test")

        monkeypatch.setenv("HOME", str(tmp_path))
        cache_dir = directory.get_global_cache_dir()

        assert cache_dir == tmp_path / ".toolchainkit"

    def test_project_local_path(self, tmp_path):
        """Verify project-local path resolution."""
        project_dir = directory.get_project_local_dir(tmp_path)

        assert project_dir == tmp_path / ".toolchainkit"

    def test_path_with_string_input(self, tmp_path):
        """Verify Path and string inputs both work."""
        # Path object
        path_obj = directory.get_project_local_dir(tmp_path)

        # String path
        path_str = directory.get_project_local_dir(str(tmp_path))

        assert path_obj == path_str


@pytest.mark.regression
class TestCompleteStructureCreation:
    """Test complete directory structure creation."""

    def test_create_global_only(self, tmp_path, monkeypatch):
        """Verify creating only global cache structure."""
        monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))

        paths = directory.create_directory_structure()

        assert "global_cache" in paths
        assert paths["global_cache"].exists()
        assert "project_local" not in paths

    def test_create_global_and_project(self, tmp_path, monkeypatch):
        """Verify creating both global and project structures."""
        monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))

        project_root = tmp_path / "project"
        project_root.mkdir()

        paths = directory.create_directory_structure(project_root)

        assert "global_cache" in paths
        assert "project_local" in paths
        assert paths["global_cache"].exists()
        assert paths["project_local"].exists()
        assert (project_root / ".gitignore").exists()


@pytest.mark.regression
def test_directory_structure_matches_specification(tmp_path, monkeypatch):
    """
    Critical regression test: Verify directory structure matches specification.

    This test fails if the documented directory structure changes unexpectedly.
    """
    monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))

    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create complete structure
    paths = directory.create_directory_structure(project_root)

    # Global cache structure (as documented)
    global_cache = paths["global_cache"]
    expected_global_structure = {
        "toolchains": {},
        "lock": {},
        "registry.json": None,  # File, not directory
    }

    for name, children in expected_global_structure.items():
        item_path = global_cache / name
        assert item_path.exists(), f"Missing: {name}"

        if children is None:
            assert item_path.is_file(), f"{name} should be a file"
        else:
            assert item_path.is_dir(), f"{name} should be a directory"

    # Project-local structure (as documented)
    project_local = paths["project_local"]
    expected_project_structure = {
        "packages": {},
        "cmake": {"toolchainkit": {}},
        "state.json": None,  # File, not directory
    }

    def verify_structure(base_path: Path, expected: dict):
        """Recursively verify directory structure."""
        for name, children in expected.items():
            item_path = base_path / name
            assert item_path.exists(), f"Missing: {item_path}"

            if children is None:
                assert item_path.is_file(), f"{item_path} should be a file"
            elif isinstance(children, dict):
                assert item_path.is_dir(), f"{item_path} should be a directory"
                if children:  # Has nested structure
                    verify_structure(item_path, children)

    verify_structure(project_local, expected_project_structure)


@pytest.mark.regression
def test_error_handling_nonexistent_project():
    """Verify appropriate error for nonexistent project root."""
    nonexistent = Path("/nonexistent/path/to/project")

    with pytest.raises(directory.DirectoryError, match="does not exist"):
        directory.ensure_project_structure(nonexistent)


@pytest.mark.regression
def test_error_handling_file_not_directory(tmp_path):
    """Verify appropriate error when project root is a file."""
    file_path = tmp_path / "not_a_directory.txt"
    file_path.write_text("I am a file")

    with pytest.raises(directory.DirectoryError, match="not a directory"):
        directory.ensure_project_structure(file_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
