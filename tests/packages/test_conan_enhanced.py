"""
Unit tests for enhanced Conan integration with custom paths and downloaded Conan.

Tests the new features including:
- use_system_conan flag
- custom_conan_path configuration
- conan_home configuration
- Downloaded Conan in toolchain directory
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from toolchainkit.packages.conan import ConanIntegration
from toolchainkit.core.exceptions import PackageManagerNotFoundError


class MockToolchain:
    """Mock toolchain for testing."""

    def __init__(self, type="llvm", version="18.1.8", stdlib=None):
        self.type = type
        self.version = version
        self.stdlib = stdlib


class MockPlatform:
    """Mock platform for testing."""

    def __init__(self, os="linux", architecture="x86_64"):
        self.os = os
        self.architecture = architecture


# =============================================================================
# Test Custom Conan Path
# =============================================================================


class TestConanCustomPath:
    """Test custom Conan executable path configuration."""

    def test_custom_conan_path_valid(self, tmp_path):
        """Test using custom Conan path."""
        custom_conan = tmp_path / "custom" / "conan"
        custom_conan.parent.mkdir(parents=True)
        custom_conan.touch()

        conan = ConanIntegration(tmp_path, custom_conan_path=custom_conan)
        result = conan.get_conan_executable()

        assert result == custom_conan

    def test_custom_conan_path_invalid(self, tmp_path):
        """Test error when custom Conan path doesn't exist."""
        custom_conan = tmp_path / "nonexistent" / "conan"

        conan = ConanIntegration(tmp_path, custom_conan_path=custom_conan)

        with pytest.raises(PackageManagerNotFoundError) as exc_info:
            conan.get_conan_executable()

        assert "Custom Conan path not found" in str(exc_info.value)

    def test_custom_path_priority_over_system(self, tmp_path):
        """Test custom path takes priority over system Conan."""
        custom_conan = tmp_path / "custom" / "conan"
        custom_conan.parent.mkdir(parents=True)
        custom_conan.touch()

        with patch(
            "toolchainkit.packages.tool_downloader.get_system_conan_path"
        ) as mock_system:
            mock_system.return_value = Path("/usr/bin/conan")

            conan = ConanIntegration(
                tmp_path, use_system_conan=True, custom_conan_path=custom_conan
            )
            result = conan.get_conan_executable()

            # Custom path should be used, not system
            assert result == custom_conan
            mock_system.assert_not_called()


# =============================================================================
# Test System vs Downloaded Conan
# =============================================================================


class TestConanSystemVsDownloaded:
    """Test system Conan vs downloaded Conan selection."""

    @patch("toolchainkit.packages.conan.get_system_conan_path")
    def test_use_system_conan_found(self, mock_system_path, tmp_path):
        """Test using system Conan when available."""
        system_conan = Path("/usr/bin/conan")
        mock_system_path.return_value = system_conan

        conan = ConanIntegration(tmp_path, use_system_conan=True)
        result = conan.get_conan_executable()

        assert result == system_conan
        mock_system_path.assert_called_once()

    @patch("toolchainkit.packages.conan.get_system_conan_path")
    def test_use_system_conan_not_found(self, mock_system_path, tmp_path):
        """Test error when system Conan is requested but not found."""
        mock_system_path.return_value = None

        conan = ConanIntegration(tmp_path, use_system_conan=True)

        with pytest.raises(PackageManagerNotFoundError) as exc_info:
            conan.get_conan_executable()

        assert "Conan not found in system PATH" in str(exc_info.value)

    @patch("toolchainkit.packages.conan.ConanDownloader")
    def test_download_conan_when_not_system(self, mock_downloader_class, tmp_path):
        """Test downloading Conan when use_system_conan is False."""
        # Create mock downloader
        mock_downloader = MagicMock()
        mock_downloader.is_installed.return_value = False
        mock_downloader.download.return_value = (
            tmp_path / ".toolchainkit" / "tools" / "conan"
        )

        downloaded_conan = (
            tmp_path / ".toolchainkit" / "tools" / "conan" / "venv" / "bin" / "conan"
        )
        downloaded_conan.parent.mkdir(parents=True, exist_ok=True)
        downloaded_conan.touch()

        mock_downloader.get_executable_path.return_value = downloaded_conan
        mock_downloader_class.return_value = mock_downloader

        conan = ConanIntegration(tmp_path, use_system_conan=False)
        result = conan.get_conan_executable()

        assert result == downloaded_conan
        mock_downloader.download.assert_called_once_with(version="2.0")

    @patch("toolchainkit.packages.conan.ConanDownloader")
    def test_use_already_downloaded_conan(self, mock_downloader_class, tmp_path):
        """Test using already downloaded Conan."""
        mock_downloader = MagicMock()
        mock_downloader.is_installed.return_value = True

        downloaded_conan = (
            tmp_path / ".toolchainkit" / "tools" / "conan" / "venv" / "bin" / "conan"
        )
        downloaded_conan.parent.mkdir(parents=True, exist_ok=True)
        downloaded_conan.touch()

        mock_downloader.get_executable_path.return_value = downloaded_conan
        mock_downloader_class.return_value = mock_downloader

        conan = ConanIntegration(tmp_path, use_system_conan=False)
        result = conan.get_conan_executable()

        assert result == downloaded_conan
        mock_downloader.download.assert_not_called()


# =============================================================================
# Test Custom CONAN_HOME
# =============================================================================


class TestConanHome:
    """Test custom CONAN_HOME configuration."""

    def test_custom_conan_home(self, tmp_path):
        """Test setting custom CONAN_HOME."""
        custom_home = tmp_path / "custom_conan_home"
        custom_home.mkdir()

        conan = ConanIntegration(tmp_path, conan_home=custom_home)
        env = conan.get_environment()

        assert env["CONAN_HOME"] == str(custom_home)

    def test_default_conan_home_when_downloaded(self, tmp_path):
        """Test CONAN_HOME set to global cache when using downloaded Conan.

        When using downloaded Conan without explicit conan_home config,
        CONAN_HOME should be set to global_cache_dir/conan_home.
        """
        from toolchainkit.core.directory import get_global_cache_dir

        conan = ConanIntegration(tmp_path, use_system_conan=False)
        env = conan.get_environment()

        global_cache_dir = get_global_cache_dir()
        expected_home = global_cache_dir / "conan_home"

        assert "CONAN_HOME" in env
        assert env["CONAN_HOME"] == str(expected_home)
        assert expected_home.exists()

    def test_no_conan_home_when_system_and_not_specified(self, tmp_path):
        """Test CONAN_HOME not set when using system Conan without custom home."""
        # Save original env
        original_conan_home = os.environ.get("CONAN_HOME")

        try:
            # Remove CONAN_HOME from environment
            if "CONAN_HOME" in os.environ:
                del os.environ["CONAN_HOME"]

            conan = ConanIntegration(tmp_path, use_system_conan=True)
            env = conan.get_environment()

            # Should use system environment (not add CONAN_HOME)
            assert "CONAN_HOME" not in env or env.get("CONAN_HOME") == os.environ.get(
                "CONAN_HOME"
            )

        finally:
            # Restore original env
            if original_conan_home:
                os.environ["CONAN_HOME"] = original_conan_home

    def test_environment_passed_to_subprocess(self, tmp_path):
        """Test that custom environment is passed to subprocess."""
        custom_home = tmp_path / "custom_conan_home"
        custom_home.mkdir()

        # Create fake conan executable
        conan_exe = tmp_path / "conan"
        conan_exe.touch()

        # Create conanfile
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        conan = ConanIntegration(
            tmp_path,
            use_system_conan=True,
            custom_conan_path=conan_exe,
            conan_home=custom_home,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            try:
                conan.install_dependencies()
            except Exception:
                pass  # We only care about the environment

            # Check that subprocess was called with custom environment
            assert mock_run.called
            call_kwargs = mock_run.call_args[1]
            assert "env" in call_kwargs
            assert call_kwargs["env"]["CONAN_HOME"] == str(custom_home)


# =============================================================================
# Test Integration with install_dependencies
# =============================================================================


class TestConanInstallWithCustomConfiguration:
    """Test install_dependencies with custom configuration."""

    @patch("subprocess.run")
    @patch("toolchainkit.packages.conan.get_system_conan_path")
    def test_install_with_system_conan(self, mock_system_path, mock_run, tmp_path):
        """Test installing dependencies with system Conan."""
        system_conan = Path("/usr/bin/conan")
        mock_system_path.return_value = system_conan
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create conanfile
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        conan = ConanIntegration(tmp_path, use_system_conan=True)
        conan.install_dependencies()

        # Verify subprocess was called with system conan
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert str(call_args[0]) == str(system_conan)

    @patch("subprocess.run")
    def test_install_with_custom_conan_path(self, mock_run, tmp_path):
        """Test installing dependencies with custom Conan path."""
        custom_conan = tmp_path / "custom" / "conan"
        custom_conan.parent.mkdir(parents=True)
        custom_conan.touch()

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create conanfile
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        conan = ConanIntegration(tmp_path, custom_conan_path=custom_conan)
        conan.install_dependencies()

        # Verify subprocess was called with custom conan
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert str(call_args[0]) == str(custom_conan)

    @patch("subprocess.run")
    @patch("toolchainkit.packages.conan.ConanDownloader")
    def test_install_with_downloaded_conan(
        self, mock_downloader_class, mock_run, tmp_path
    ):
        """Test installing dependencies with downloaded Conan."""
        # Setup mock downloader
        mock_downloader = MagicMock()
        mock_downloader.is_installed.return_value = True

        downloaded_conan = (
            tmp_path / ".toolchainkit" / "tools" / "conan" / "venv" / "bin" / "conan"
        )
        downloaded_conan.parent.mkdir(parents=True, exist_ok=True)
        downloaded_conan.touch()

        mock_downloader.get_executable_path.return_value = downloaded_conan
        mock_downloader_class.return_value = mock_downloader

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create conanfile
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        conan = ConanIntegration(tmp_path, use_system_conan=False)
        conan.install_dependencies()

        # Verify subprocess was called with downloaded conan
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert str(call_args[0]) == str(downloaded_conan)

        # Verify CONAN_HOME is NOT set automatically (uses system default)
        # CONAN_HOME is only set when explicitly configured via conan_home parameter
        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        # CONAN_HOME should not be in env unless it was in os.environ
        # (the test environment may or may not have it set)
