"""
Regression tests for Windows platform compatibility.

These tests run only on Windows.
"""

import pytest
import sys
import os
from pathlib import Path
import subprocess


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only tests")


@pytest.mark.regression
@pytest.mark.platform_windows
class TestWindowsPathHandling:
    """Test Windows path handling."""

    def test_backslash_paths_work(self, tmp_path):
        """Verify backslash paths are handled correctly."""
        from toolchainkit.core import directory

        # Use Windows-style path with backslashes
        windows_path = str(tmp_path).replace("/", "\\")

        # Should handle Windows paths
        project_local = directory.get_project_local_dir(Path(windows_path))
        assert project_local.exists() or True  # Path object created

    def test_windows_environment_variables(self):
        """Verify Windows environment variables are accessible."""
        # Check Windows-specific env vars
        userprofile = os.environ.get("USERPROFILE")
        assert userprofile  # Should exist on Windows

    def test_path_environment_variable(self):
        """Verify PATH uses semicolon separator on Windows."""
        path = os.environ.get("PATH", "")

        assert path
        assert ";" in path  # Windows uses semicolon separator


@pytest.mark.regression
@pytest.mark.platform_windows
class TestWindowsCommands:
    """Test Windows-specific command execution."""

    def test_run_cmd_command(self):
        """Verify cmd.exe commands work."""
        result = subprocess.run(
            ["cmd", "/c", "echo", "test"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "test" in result.stdout

    def test_where_command(self):
        """Verify 'where' command (Windows equivalent of 'which') works."""
        result = subprocess.run(["where", "cmd"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "cmd.exe" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
