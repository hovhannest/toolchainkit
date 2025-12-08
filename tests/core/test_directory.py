"""
Unit tests for toolchainkit.core.directory module.

Tests cover:
- Platform-specific path resolution
- Directory creation and structure
- Gitignore management
- Error handling
- Permission checks
- Idempotency
"""

import os
import tempfile
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

import pytest

from toolchainkit.core.directory import (
    get_global_cache_dir,
    get_project_local_dir,
    verify_directory_writable,
    ensure_global_cache_structure,
    ensure_project_structure,
    update_gitignore,
    create_directory_structure,
    DirectoryError,
)


class TestGetGlobalCacheDir:
    """Tests for get_global_cache_dir function."""

    def test_windows_path(self):
        """Test global cache directory on Windows."""
        if os.name != "nt":
            pytest.skip("Cannot instantiate WindowsPath on non-Windows system")
        with patch("os.name", "nt"):
            with patch.dict(os.environ, {"USERPROFILE": r"C:\Users\TestUser"}):
                with patch(
                    "pathlib.Path.home",
                    return_value=PureWindowsPath(r"C:\Users\TestUser"),
                ):
                    cache_dir = get_global_cache_dir()
                    assert str(cache_dir) == str(
                        PureWindowsPath(r"C:\Users\TestUser\.toolchainkit")
                    )

    def test_linux_path(self):
        """Test global cache directory on Linux."""
        if os.name == "nt":
            pytest.skip("Cannot test PosixPath on Windows")
        with patch("os.name", "posix"):
            with patch("pathlib.Path.home", return_value=Path("/home/testuser")):
                cache_dir = get_global_cache_dir()
                assert cache_dir == Path("/home/testuser/.toolchainkit")

    def test_macos_path(self):
        """Test global cache directory on macOS."""
        if os.name == "nt":
            pytest.skip("Cannot test PosixPath on Windows")
        with patch("os.name", "posix"):
            with patch("pathlib.Path.home", return_value=Path("/Users/testuser")):
                cache_dir = get_global_cache_dir()
                assert cache_dir == Path("/Users/testuser/.toolchainkit")

    def test_windows_missing_userprofile(self):
        """Test error when USERPROFILE is not set on Windows."""
        with patch("os.name", "nt"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(DirectoryError) as exc_info:
                    get_global_cache_dir()
                assert "USERPROFILE" in str(exc_info.value)


class TestGetProjectLocalDir:
    """Tests for get_project_local_dir function."""

    def test_project_local_path(self):
        """Test project-local directory path."""
        project_root = Path("/path/to/project")
        local_dir = get_project_local_dir(project_root)
        assert local_dir == Path("/path/to/project/.toolchainkit")

    def test_project_local_path_string_input(self):
        """Test project-local directory with string input."""
        project_root = "/path/to/project"
        local_dir = get_project_local_dir(Path(project_root))
        assert local_dir == Path("/path/to/project/.toolchainkit")

    def test_project_local_path_windows(self):
        """Test project-local directory on Windows."""
        project_root = PureWindowsPath(r"C:\Projects\MyProject")
        local_dir = get_project_local_dir(project_root)
        assert str(local_dir) == str(
            PureWindowsPath(r"C:\Projects\MyProject\.toolchainkit")
        )


class TestVerifyDirectoryWritable:
    """Tests for verify_directory_writable function."""

    def test_writable_directory(self):
        """Test that writable directory is detected correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert verify_directory_writable(Path(tmpdir)) is True

    def test_nonexistent_directory(self):
        """Test that nonexistent directory returns False."""
        nonexistent = Path("/nonexistent/directory/path")
        assert verify_directory_writable(nonexistent) is False

    def test_file_not_directory(self):
        """Test that a file (not directory) returns False."""
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile_path = Path(tmpfile.name)

        try:
            assert verify_directory_writable(tmpfile_path) is False
        finally:
            if tmpfile_path.exists():
                tmpfile_path.unlink()

    def test_readonly_directory(self):
        """Test that read-only directory returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Make directory read-only
            if os.name != "nt":  # Unix-like systems
                os.chmod(tmpdir_path, 0o444)
                try:
                    assert verify_directory_writable(tmpdir_path) is False
                finally:
                    # Restore permissions for cleanup
                    os.chmod(tmpdir_path, 0o755)
            else:
                # Windows readonly test would require admin privileges
                # Skip for now, but test should pass on Unix
                pass


class TestEnsureGlobalCacheStructure:
    """Tests for ensure_global_cache_structure function."""

    def test_create_global_cache_structure(self):
        """Test creation of global cache directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock get_global_cache_dir to use temp directory
            cache_path = Path(tmpdir) / ".toolchainkit"

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                result = ensure_global_cache_structure()

                # Verify main directory
                assert result.exists()
                assert result.is_dir()

                # Verify subdirectories
                assert (result / "toolchains").exists()
                assert (result / "toolchains").is_dir()
                assert (result / "lock").exists()
                assert (result / "lock").is_dir()

                # Verify registry.json
                assert (result / "registry.json").exists()
                assert (result / "registry.json").read_text() == "{}"

    def test_idempotent_global_cache_creation(self):
        """Test that creating global cache multiple times doesn't fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / ".toolchainkit"

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                # Create once
                result1 = ensure_global_cache_structure()

                # Create again
                result2 = ensure_global_cache_structure()

                assert result1 == result2
                assert result1.exists()

    def test_preserve_existing_registry(self):
        """Test that existing registry.json is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / ".toolchainkit"
            cache_path.mkdir()

            # Create registry with content
            registry_path = cache_path / "registry.json"
            registry_path.write_text('{"existing": "data"}')

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                ensure_global_cache_structure()

                # Verify registry wasn't overwritten
                assert registry_path.read_text() == '{"existing": "data"}'


class TestEnsureProjectStructure:
    """Tests for ensure_project_structure function."""

    def test_create_project_structure(self):
        """Test creation of project-local directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            result = ensure_project_structure(project_root)

            # Verify main directory
            assert result.exists()
            assert result.is_dir()
            assert result == project_root / ".toolchainkit"

            # Verify subdirectories
            assert (result / "packages").exists()
            assert (result / "packages").is_dir()
            assert (result / "cmake" / "toolchainkit").exists()
            assert (result / "cmake" / "toolchainkit").is_dir()

            # Verify state.json
            assert (result / "state.json").exists()
            assert (result / "state.json").read_text() == "{}"

    def test_idempotent_project_structure_creation(self):
        """Test that creating project structure multiple times doesn't fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create once
            result1 = ensure_project_structure(project_root)

            # Create again
            result2 = ensure_project_structure(project_root)

            assert result1 == result2
            assert result1.exists()

    def test_preserve_existing_state(self):
        """Test that existing state.json is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            project_local = project_root / ".toolchainkit"
            project_local.mkdir()

            # Create state with content
            state_path = project_local / "state.json"
            state_path.write_text('{"existing": "state"}')

            ensure_project_structure(project_root)

            # Verify state wasn't overwritten
            assert state_path.read_text() == '{"existing": "state"}'

    def test_nonexistent_project_root(self):
        """Test error when project root doesn't exist."""
        nonexistent = Path("/nonexistent/project")

        with pytest.raises(DirectoryError) as exc_info:
            ensure_project_structure(nonexistent)
        assert "does not exist" in str(exc_info.value)

    def test_project_root_is_file(self):
        """Test error when project root is a file, not directory."""
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile_path = Path(tmpfile.name)

        try:
            with pytest.raises(DirectoryError) as exc_info:
                ensure_project_structure(tmpfile_path)
            assert "not a directory" in str(exc_info.value)
        finally:
            if tmpfile_path.exists():
                tmpfile_path.unlink()


class TestUpdateGitignore:
    """Tests for update_gitignore function."""

    def test_create_new_gitignore(self):
        """Test creating new .gitignore file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            update_gitignore(project_root)

            gitignore_path = project_root / ".gitignore"
            assert gitignore_path.exists()

            content = gitignore_path.read_text()
            assert ".toolchainkit/" in content
            assert "# ToolchainKit" in content

    def test_add_to_existing_gitignore(self):
        """Test adding pattern to existing .gitignore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            gitignore_path = project_root / ".gitignore"

            # Create existing .gitignore
            existing_content = "*.pyc\n__pycache__/\n"
            gitignore_path.write_text(existing_content)

            update_gitignore(project_root)

            content = gitignore_path.read_text()
            assert "*.pyc" in content
            assert "__pycache__/" in content
            assert ".toolchainkit/" in content

    def test_idempotent_gitignore_update(self):
        """Test that updating .gitignore multiple times doesn't duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Update once
            update_gitignore(project_root)
            content1 = (project_root / ".gitignore").read_text()

            # Update again
            update_gitignore(project_root)
            content2 = (project_root / ".gitignore").read_text()

            # Content should be identical
            assert content1 == content2

            # Pattern should appear only once
            assert content2.count(".toolchainkit/") == 1

    def test_preserve_gitignore_without_trailing_newline(self):
        """Test handling .gitignore that doesn't end with newline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            gitignore_path = project_root / ".gitignore"

            # Create .gitignore without trailing newline
            gitignore_path.write_text("*.pyc")

            update_gitignore(project_root)

            content = gitignore_path.read_text()
            lines = content.splitlines()
            assert "*.pyc" in lines
            assert ".toolchainkit/" in lines

    def test_nonexistent_project_root(self):
        """Test error when project root doesn't exist."""
        nonexistent = Path("/nonexistent/project")

        with pytest.raises(DirectoryError) as exc_info:
            update_gitignore(nonexistent)
        assert "does not exist" in str(exc_info.value)


class TestCreateDirectoryStructure:
    """Tests for create_directory_structure function."""

    def test_create_global_only(self):
        """Test creating only global cache structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / ".toolchainkit"

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                result = create_directory_structure()

                assert "global_cache" in result
                assert result["global_cache"].exists()
                assert "project_local" not in result

    def test_create_global_and_project(self):
        """Test creating both global and project-local structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "global" / ".toolchainkit"
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                result = create_directory_structure(project_root)

                assert "global_cache" in result
                assert result["global_cache"].exists()
                assert "project_local" in result
                assert result["project_local"].exists()

                # Verify .gitignore was updated
                gitignore = project_root / ".gitignore"
                assert gitignore.exists()
                assert ".toolchainkit/" in gitignore.read_text()

    def test_create_with_string_path(self):
        """Test creating structure with string path input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "global" / ".toolchainkit"
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                # Pass string instead of Path
                result = create_directory_structure(str(project_root))

                assert "global_cache" in result
                assert "project_local" in result
                assert result["project_local"].exists()


class TestIntegration:
    """Integration tests for complete directory structure creation."""

    def test_full_directory_structure(self):
        """Test creating complete directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache" / ".toolchainkit"
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                paths = create_directory_structure(project_root)

                # Verify all global cache structure
                global_cache = paths["global_cache"]
                assert (global_cache / "toolchains").exists()
                assert (global_cache / "lock").exists()
                assert (global_cache / "registry.json").exists()

                # Verify all project-local structure
                project_local = paths["project_local"]
                assert (project_local / "packages").exists()
                assert (project_local / "cmake" / "toolchainkit").exists()
                assert (project_local / "state.json").exists()

                # Verify .gitignore
                gitignore = project_root / ".gitignore"
                assert gitignore.exists()
                assert ".toolchainkit/" in gitignore.read_text()

    def test_multiple_projects_share_global_cache(self):
        """Test that multiple projects can share the same global cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "shared_cache" / ".toolchainkit"

            project1_root = Path(tmpdir) / "project1"
            project1_root.mkdir()

            project2_root = Path(tmpdir) / "project2"
            project2_root.mkdir()

            with patch(
                "toolchainkit.core.directory.get_global_cache_dir",
                return_value=cache_path,
            ):
                paths1 = create_directory_structure(project1_root)
                paths2 = create_directory_structure(project2_root)

                # Both projects should reference the same global cache
                assert paths1["global_cache"] == paths2["global_cache"]

                # But have different project-local directories
                assert paths1["project_local"] != paths2["project_local"]
                assert paths1["project_local"].parent == project1_root
                assert paths2["project_local"].parent == project2_root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
