"""
Regression tests for Unix platform compatibility (Linux/macOS).

These tests run only on Unix systems.
"""

import pytest
import sys
import os
import stat
from pathlib import Path
import subprocess


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Unix-only tests")


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixPathHandling:
    """Test Unix path handling."""

    def test_forward_slash_paths_work(self, tmp_path):
        """Verify forward slash paths work correctly."""
        from toolchainkit.core.directory import ensure_project_structure

        # Unix-style path
        project_path = tmp_path / "project"
        project_path.mkdir()

        ensure_project_structure(project_path)

        assert (project_path / ".toolchainkit").exists()

    def test_absolute_paths_start_with_slash(self, tmp_path):
        """Verify absolute paths start with /."""
        abs_path = tmp_path.resolve()

        assert str(abs_path).startswith("/")

    def test_home_directory_expansion(self, tmp_path, monkeypatch):
        """Verify ~ expands to home directory."""
        home = Path.home()

        # Test path with tilde
        tilde_path = Path("~/project").expanduser()

        assert str(home) in str(tilde_path)

    def test_relative_paths_with_dot(self, tmp_path, monkeypatch):
        """Verify ./path and ../path work."""
        monkeypatch.chdir(tmp_path)

        # Create structure
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("test")

        # Relative paths
        assert Path("./file.txt").exists()

        monkeypatch.chdir(tmp_path / "subdir")
        assert Path("../file.txt").exists()

    def test_path_separator_is_forward_slash(self, tmp_path):
        """Verify Unix path separator is forward slash."""
        assert os.sep == "/"
        assert os.pathsep == ":"

    def test_hidden_files_start_with_dot(self, tmp_path):
        """Verify hidden files start with dot."""
        hidden_file = tmp_path / ".hidden"
        hidden_file.write_text("secret")

        assert hidden_file.exists()
        assert hidden_file.name.startswith(".")


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixFilePermissions:
    """Test Unix file permission handling."""

    def test_executable_bit_set(self, tmp_path):
        """Verify executable bit can be set and detected."""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/bash\necho 'test'")

        # Make executable
        script.chmod(script.stat().st_mode | stat.S_IXUSR)

        # Check executable
        mode = script.stat().st_mode
        assert mode & stat.S_IXUSR
        assert os.access(script, os.X_OK)

    def test_read_only_files(self, tmp_path):
        """Verify read-only files can be created."""
        readonly = tmp_path / "readonly.txt"
        readonly.write_text("content")

        # Make read-only (remove write permission)
        readonly.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        # Should not be writable
        assert not os.access(readonly, os.W_OK)

    def test_permission_octal_notation(self, tmp_path):
        """Verify octal permission notation works."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        # Set permissions using octal (rw-r--r--)
        file.chmod(0o644)

        mode = file.stat().st_mode & 0o777

        assert mode == 0o644

    def test_directory_permissions(self, tmp_path):
        """Verify directory permissions work."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Set permissions (rwxr-xr-x)
        subdir.chmod(0o755)

        mode = subdir.stat().st_mode

        # Check owner has rwx
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR
        assert mode & stat.S_IXUSR

    def test_default_file_permissions(self, tmp_path):
        """Verify default file permissions are reasonable."""
        file = tmp_path / "newfile.txt"
        file.write_text("content")

        mode = file.stat().st_mode & 0o777

        # Default should be at least owner readable/writable
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR


@pytest.mark.regression
@pytest.mark.platform_linux
class TestSymbolicLinks:
    """Test symbolic link handling."""

    def test_create_symlink(self, tmp_path):
        """Verify symbolic links can be created."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        link = tmp_path / "link.txt"
        link.symlink_to(target)

        assert link.exists()
        assert link.is_symlink()
        assert link.read_text() == "content"

    def test_symlink_to_directory(self, tmp_path):
        """Verify directory symlinks work."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()
        (target_dir / "file.txt").write_text("test")

        link_dir = tmp_path / "link_dir"
        link_dir.symlink_to(target_dir)

        assert link_dir.is_symlink()
        assert (link_dir / "file.txt").exists()

    def test_broken_symlink_detection(self, tmp_path):
        """Verify broken symlinks are detected."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        link = tmp_path / "link.txt"
        link.symlink_to(target)

        # Remove target
        target.unlink()

        # Link should be broken
        assert link.is_symlink()
        assert not link.exists()  # exists() follows symlinks

    def test_resolve_symlink(self, tmp_path):
        """Verify symlinks can be resolved to real path."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        link = tmp_path / "link.txt"
        link.symlink_to(target)

        resolved = link.resolve()

        assert resolved == target
        assert str(resolved) == str(target)


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixShellCommands:
    """Test Unix shell command execution."""

    def test_execute_bash_command(self, tmp_path):
        """Verify bash commands can be executed."""
        result = subprocess.run(
            ["bash", "-c", "echo test"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "test" in result.stdout

    def test_execute_sh_command(self, tmp_path):
        """Verify sh commands can be executed."""
        result = subprocess.run(
            ["sh", "-c", "echo test"], capture_output=True, text=True, cwd=tmp_path
        )

        assert result.returncode == 0
        assert "test" in result.stdout

    def test_shell_script_execution(self, tmp_path):
        """Verify shell scripts can be executed."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho 'Hello from script'")
        script.chmod(0o755)

        result = subprocess.run([str(script)], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Hello from script" in result.stdout

    def test_which_command_works(self, tmp_path):
        """Verify 'which' command finds executables."""
        # Look for bash (should exist on Unix)
        result = subprocess.run(
            ["which", "bash"], capture_output=True, text=True, cwd=tmp_path
        )

        assert result.returncode == 0
        assert "bash" in result.stdout

    def test_environment_variables_in_shell(self, tmp_path):
        """Verify environment variables work in shell."""
        result = subprocess.run(
            ["bash", "-c", "echo $HOME"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0

    def test_pipe_commands(self, tmp_path):
        """Verify Unix pipe commands work."""
        result = subprocess.run(
            ["bash", "-c", "echo 'line1\nline2\nline3' | grep line2"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "line2" in result.stdout
        assert "line1" not in result.stdout


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixEnvironment:
    """Test Unix environment handling."""

    def test_path_environment_variable(self):
        """Verify PATH uses colon separator."""
        path = os.environ.get("PATH", "")

        assert ":" in path  # Unix uses colon separator

    def test_home_directory_set(self):
        """Verify HOME environment variable is set."""
        home = os.environ.get("HOME")

        assert home is not None
        assert len(home) > 0
        assert Path(home).exists()

    def test_shell_environment_variable(self):
        """Verify SHELL environment variable is set."""
        shell = os.environ.get("SHELL")

        # SHELL might not be set in all environments
        if shell:
            assert "sh" in shell or "bash" in shell or "zsh" in shell

    def test_user_environment_variable(self):
        """Verify USER environment variable is set."""
        user = os.environ.get("USER") or os.environ.get("LOGNAME")

        assert user is not None
        assert len(user) > 0


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixFileSystem:
    """Test Unix file system behavior."""

    def test_case_sensitivity_default(self, tmp_path):
        """Verify file system is case-sensitive (typical for Linux)."""
        # Create lowercase file
        lower = tmp_path / "test.txt"
        lower.write_text("lower")

        # Create uppercase file
        upper = tmp_path / "TEST.txt"

        # On case-sensitive FS, these should be different files
        # Note: macOS can be case-insensitive, so this might fail there
        upper.write_text("upper")

        # Check if they are the same file (case-insensitive)
        if lower.read_text() == "upper":
            pytest.skip("File system is case-insensitive")

        # If we got here, FS is case-sensitive
        assert lower.read_text() == "lower"
        assert upper.read_text() == "upper"

    def test_dev_null_exists(self):
        """Verify /dev/null exists."""
        dev_null = Path("/dev/null")

        assert dev_null.exists()

    def test_tmp_directory_exists(self):
        """Verify /tmp directory exists."""
        tmp = Path("/tmp")

        assert tmp.exists()
        assert tmp.is_dir()

    def test_root_directory(self):
        """Verify root directory is /."""
        root = Path("/")

        assert root.exists()
        assert root.is_dir()
        assert str(root) == "/"


@pytest.mark.regression
@pytest.mark.platform_linux
class TestUnixToolchainCompatibility:
    """Test toolchain operations on Unix."""

    def test_compiler_executables_pattern(self, tmp_path):
        """Verify Unix compiler executable patterns."""
        # Unix compilers typically have no extension
        compiler_names = ["gcc", "g++", "clang", "clang++"]

        for name in compiler_names:
            # Just verify pattern is valid (don't require actual compilers)
            path = tmp_path / name
            path.touch()
            path.chmod(0o755)

            assert path.exists()
            assert not path.suffix  # No file extension

    def test_library_extensions(self, tmp_path):
        """Verify Unix library file extensions."""
        # Static libraries: .a
        static_lib = tmp_path / "libtest.a"
        static_lib.touch()
        assert static_lib.suffix == ".a"

        # Shared libraries: .so
        shared_lib = tmp_path / "libtest.so"
        shared_lib.touch()
        assert shared_lib.suffix == ".so"

        # Shared libraries with version: .so.1.2.3
        versioned_lib = tmp_path / "libtest.so.1.2.3"
        versioned_lib.touch()
        assert "so" in versioned_lib.name

    def test_standard_include_paths_pattern(self):
        """Verify standard Unix include path patterns."""
        # Standard Unix include locations
        standard_paths = [
            "/usr/include",
            "/usr/local/include",
        ]

        # This is informational - verify the path patterns are Unix-style
        for path in standard_paths:
            assert path.startswith("/")


@pytest.mark.regression
def test_unix_specific_modules_available():
    """
    Verify Unix-specific Python modules are available.

    This ensures platform detection works correctly.
    """
    # These should be available on Unix
    import pwd  # noqa: F401
    import grp  # noqa: F401

    # Verify we can use pwd module
    try:
        pwd.getpwuid(os.getuid())
    except Exception:
        pytest.fail("Unix pwd module not working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
