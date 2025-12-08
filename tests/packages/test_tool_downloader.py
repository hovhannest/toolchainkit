"""
Unit tests for package manager tool downloader.

Tests the ConanDownloader and VcpkgDownloader classes for downloading
package managers into the toolchain directory.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from toolchainkit.packages.tool_downloader import (
    ConanDownloader,
    VcpkgDownloader,
    ToolDownloadError,
    get_system_conan_path,
    get_system_vcpkg_path,
)
from toolchainkit.core.platform import PlatformInfo


# =============================================================================
# Test ConanDownloader
# =============================================================================


class TestConanDownloader:
    """Test Conan downloader functionality."""

    def test_init(self, tmp_path):
        """Test ConanDownloader initialization."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(tools_dir)

        assert downloader.tools_dir == tools_dir
        assert downloader.conan_dir == tools_dir / "conan"

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test getting executable path when Conan is not installed."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(tools_dir)

        assert downloader.get_executable_path() is None

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(tools_dir)

        assert downloader.is_installed() is False

    @patch("subprocess.run")
    def test_download_creates_venv(self, mock_run, tmp_path):
        """Test that download creates a virtual environment."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful subprocess calls
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Create fake conan executable after "installation"
        def create_conan_exe(*args, **kwargs):
            conan_exe = downloader.conan_dir / "venv" / "bin" / "conan"
            conan_exe.parent.mkdir(parents=True, exist_ok=True)
            conan_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = create_conan_exe

        result = downloader.download(version="2.0")

        assert result == downloader.conan_dir
        assert mock_run.call_count == 2  # venv creation + pip install

    @patch("subprocess.run")
    def test_download_failure_cleanup(self, mock_run, tmp_path):
        """Test that download cleans up on failure."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(tools_dir)

        # Mock failed subprocess call
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

        with pytest.raises(ToolDownloadError):
            downloader.download(version="2.0")

        # Directory should not exist after cleanup
        assert not downloader.conan_dir.exists()

    def test_download_already_installed(self, tmp_path):
        """Test download skips when already installed."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        conan_dir = tools_dir / "conan"
        venv_dir = conan_dir / "venv" / "bin"
        venv_dir.mkdir(parents=True, exist_ok=True)
        (venv_dir / "conan").touch()

        result = downloader.download(version="2.0")

        assert result == conan_dir

    @patch("subprocess.run")
    def test_download_force_reinstall(self, mock_run, tmp_path):
        """Test force reinstall removes existing installation."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake existing installation
        conan_dir = tools_dir / "conan"
        conan_dir.mkdir(parents=True, exist_ok=True)
        (conan_dir / "old_file").touch()

        # Mock successful subprocess calls
        def create_new_install(*args, **kwargs):
            conan_exe = downloader.conan_dir / "venv" / "bin" / "conan"
            conan_exe.parent.mkdir(parents=True, exist_ok=True)
            conan_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = create_new_install

        result = downloader.download(version="2.0", force=True)

        assert result == conan_dir
        assert not (conan_dir / "old_file").exists()


# =============================================================================
# Test VcpkgDownloader
# =============================================================================


class TestVcpkgDownloader:
    """Test vcpkg downloader functionality."""

    def test_init(self, tmp_path):
        """Test VcpkgDownloader initialization."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        assert downloader.tools_dir == tools_dir
        assert downloader.vcpkg_dir == tools_dir / "vcpkg"

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test getting executable path when vcpkg is not installed."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        assert downloader.get_executable_path() is None

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        assert downloader.is_installed() is False

    @patch("subprocess.run")
    def test_download_clones_and_bootstraps(self, mock_run, tmp_path):
        """Test that download clones repository and runs bootstrap."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful subprocess calls
        def mock_subprocess(*args, **kwargs):
            cmd = args[0]
            if "git" in cmd[0]:
                # Create fake vcpkg directory
                vcpkg_dir = tools_dir / "vcpkg"
                vcpkg_dir.mkdir(parents=True, exist_ok=True)
                (vcpkg_dir / "bootstrap-vcpkg.sh").touch()
            elif "bootstrap" in cmd[0]:
                # Create fake vcpkg executable
                vcpkg_exe = tools_dir / "vcpkg" / "vcpkg"
                vcpkg_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = downloader.download()

        assert result == downloader.vcpkg_dir
        assert mock_run.call_count == 2  # git clone + bootstrap

    @patch("subprocess.run")
    def test_download_failure_cleanup(self, mock_run, tmp_path):
        """Test that download cleans up on failure."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        # Mock failed subprocess call
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Git clone failed")

        with pytest.raises(ToolDownloadError):
            downloader.download()

        # Directory should not exist after cleanup
        assert not downloader.vcpkg_dir.exists()


# =============================================================================
# Test System Tool Detection
# =============================================================================


class TestSystemToolDetection:
    """Test system-installed tool detection."""

    @patch("shutil.which")
    def test_get_system_conan_path_found(self, mock_which):
        """Test finding system Conan."""
        mock_which.return_value = "/usr/bin/conan"

        result = get_system_conan_path()

        assert result == Path("/usr/bin/conan")
        mock_which.assert_called_once_with("conan")

    @patch("shutil.which")
    def test_get_system_conan_path_not_found(self, mock_which):
        """Test when system Conan is not found."""
        mock_which.return_value = None

        result = get_system_conan_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_vcpkg_path_found(self, mock_which):
        """Test finding system vcpkg."""
        mock_which.return_value = "/usr/local/bin/vcpkg"

        result = get_system_vcpkg_path()

        assert result == Path("/usr/local/bin/vcpkg")
        mock_which.assert_called_once_with("vcpkg")

    @patch("shutil.which")
    def test_get_system_vcpkg_path_not_found(self, mock_which):
        """Test when system vcpkg is not found."""
        mock_which.return_value = None

        result = get_system_vcpkg_path()

        assert result is None


# =============================================================================
# Test CMakeDownloader
# =============================================================================


class TestCMakeDownloader:
    """Test CMake downloader functionality."""

    def test_init(self, tmp_path):
        """Test CMakeDownloader initialization."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(tools_dir, version="3.28.1")

        assert downloader.tools_dir == tools_dir
        assert downloader.version == "3.28.1"
        assert downloader.install_dir == tools_dir / "cmake" / "3.28.1"

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test getting executable path when CMake is not installed."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(tools_dir)

        assert downloader.get_executable_path() is None

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(tools_dir)

        assert downloader.is_installed() is False

    def test_is_installed_true_linux(self, tmp_path):
        """Test is_installed returns True when CMake is installed on Linux."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        cmake_exe = downloader.install_dir / "bin" / "cmake"
        cmake_exe.parent.mkdir(parents=True, exist_ok=True)
        cmake_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == cmake_exe

    def test_is_installed_true_windows(self, tmp_path):
        """Test is_installed returns True when CMake is installed on Windows."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        # Create fake installation
        cmake_exe = downloader.install_dir / "bin" / "cmake.exe"
        cmake_exe.parent.mkdir(parents=True, exist_ok=True)
        cmake_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == cmake_exe

    def test_get_download_url_linux_x64(self, tmp_path):
        """Test CMake download URL for Linux x64."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/Kitware/CMake/releases/download/v3.28.1/cmake-3.28.1-linux-x86_64.tar.gz"
        )

    def test_get_download_url_macos(self, tmp_path):
        """Test CMake download URL for macOS."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("macos", "arm64", "14.0", "", ""),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/Kitware/CMake/releases/download/v3.28.1/cmake-3.28.1-macos-universal.tar.gz"
        )

    def test_get_download_url_windows_x64(self, tmp_path):
        """Test CMake download URL for Windows x64."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/Kitware/CMake/releases/download/v3.28.1/cmake-3.28.1-windows-x86_64.zip"
        )

    def test_get_download_url_unsupported_os(self, tmp_path):
        """Test CMake download URL with unsupported OS."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("freebsd", "x86_64", "13.0", "", ""),
        )

        with pytest.raises(ToolDownloadError, match="Unsupported OS"):
            downloader._get_download_url()

    @patch("toolchainkit.core.filesystem.extract_archive")
    @patch("toolchainkit.core.download.download_file")
    def test_download_success(self, mock_download, mock_extract, tmp_path):
        """Test successful CMake download."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful download and extraction
        def mock_download_side_effect(url, dest_path):
            # Create the archive file that would be downloaded
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.touch()

        def mock_extract_side_effect(archive_path, extract_dir):
            # Create extracted directory structure
            extracted = extract_dir / "cmake-3.28.1-linux-x86_64"
            cmake_exe = extracted / "bin" / "cmake"
            cmake_exe.parent.mkdir(parents=True, exist_ok=True)
            cmake_exe.touch()

        mock_download.side_effect = mock_download_side_effect
        mock_extract.side_effect = mock_extract_side_effect

        result = downloader.download()

        assert result == downloader.install_dir
        assert downloader.is_installed()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_download_already_installed(self, tmp_path):
        """Test download skips when already installed."""
        from toolchainkit.packages.tool_downloader import CMakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = CMakeDownloader(
            tools_dir,
            version="3.28.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        cmake_exe = downloader.install_dir / "bin" / "cmake"
        cmake_exe.parent.mkdir(parents=True, exist_ok=True)
        cmake_exe.touch()

        result = downloader.download(force=False)

        assert result == downloader.install_dir


# =============================================================================
# Test NinjaDownloader
# =============================================================================


class TestNinjaDownloader:
    """Test Ninja downloader functionality."""

    def test_init(self, tmp_path):
        """Test NinjaDownloader initialization."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(tools_dir, version="1.11.1")

        assert downloader.tools_dir == tools_dir
        assert downloader.version == "1.11.1"
        assert downloader.install_dir == tools_dir / "ninja" / "1.11.1"

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test getting executable path when Ninja is not installed."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(tools_dir)

        assert downloader.get_executable_path() is None

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(tools_dir)

        assert downloader.is_installed() is False

    def test_is_installed_true_linux(self, tmp_path):
        """Test is_installed returns True when Ninja is installed on Linux."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        ninja_exe = downloader.install_dir / "ninja"
        ninja_exe.parent.mkdir(parents=True, exist_ok=True)
        ninja_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == ninja_exe

    def test_is_installed_true_windows(self, tmp_path):
        """Test is_installed returns True when Ninja is installed on Windows."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        # Create fake installation
        ninja_exe = downloader.install_dir / "ninja.exe"
        ninja_exe.parent.mkdir(parents=True, exist_ok=True)
        ninja_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == ninja_exe

    def test_get_download_url_linux(self, tmp_path):
        """Test Ninja download URL for Linux."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-linux.zip"
        )

    def test_get_download_url_macos(self, tmp_path):
        """Test Ninja download URL for macOS."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("macos", "arm64", "14.0", "", ""),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-mac.zip"
        )

    def test_get_download_url_windows(self, tmp_path):
        """Test Ninja download URL for Windows."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-win.zip"
        )

    def test_get_download_url_unsupported_os(self, tmp_path):
        """Test Ninja download URL with unsupported OS."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("freebsd", "x86_64", "13.0", "", ""),
        )

        with pytest.raises(ToolDownloadError, match="Unsupported OS"):
            downloader._get_download_url()

    @patch("toolchainkit.core.filesystem.extract_archive")
    @patch("toolchainkit.core.download.download_file")
    def test_download_success(self, mock_download, mock_extract, tmp_path):
        """Test successful Ninja download."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful download and extraction
        def mock_download_side_effect(url, dest_path):
            # Create the archive file that would be downloaded
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.touch()

        def mock_extract_side_effect(archive_path, extract_dir):
            # Create ninja executable
            ninja_exe = extract_dir / "ninja"
            ninja_exe.touch()

        mock_download.side_effect = mock_download_side_effect
        mock_extract.side_effect = mock_extract_side_effect

        result = downloader.download()

        assert result == downloader.install_dir
        assert downloader.is_installed()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_download_already_installed(self, tmp_path):
        """Test download skips when already installed."""
        from toolchainkit.packages.tool_downloader import NinjaDownloader

        tools_dir = tmp_path / "tools"
        downloader = NinjaDownloader(
            tools_dir,
            version="1.11.1",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        ninja_exe = downloader.install_dir / "ninja"
        ninja_exe.parent.mkdir(parents=True, exist_ok=True)
        ninja_exe.touch()

        result = downloader.download(force=False)

        assert result == downloader.install_dir


# =============================================================================
# Test System Detection Functions
# =============================================================================


class TestSystemDetection:
    """Test system tool detection functions."""

    @patch("shutil.which")
    def test_get_system_cmake_path_found(self, mock_which):
        """Test when system CMake is found."""
        from toolchainkit.packages.tool_downloader import get_system_cmake_path

        mock_which.return_value = "/usr/bin/cmake"

        result = get_system_cmake_path()

        assert result == Path("/usr/bin/cmake")
        mock_which.assert_called_once_with("cmake")

    @patch("shutil.which")
    def test_get_system_cmake_path_not_found(self, mock_which):
        """Test when system CMake is not found."""
        from toolchainkit.packages.tool_downloader import get_system_cmake_path

        mock_which.return_value = None

        result = get_system_cmake_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_ninja_path_found(self, mock_which):
        """Test when system Ninja is found."""
        from toolchainkit.packages.tool_downloader import get_system_ninja_path

        mock_which.return_value = "/usr/bin/ninja"

        result = get_system_ninja_path()

        assert result == Path("/usr/bin/ninja")
        mock_which.assert_called_once_with("ninja")

    @patch("shutil.which")
    def test_get_system_ninja_path_not_found(self, mock_which):
        """Test when system Ninja is not found."""
        from toolchainkit.packages.tool_downloader import get_system_ninja_path

        mock_which.return_value = None

        result = get_system_ninja_path()

        assert result is None


# =============================================================================
# Test SccacheDownloader
# =============================================================================


class TestSccacheDownloader:
    """Test sccache downloader functionality."""

    def test_init(self, tmp_path):
        """Test SccacheDownloader initialization."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(tools_dir, version="0.7.4")

        assert downloader.tools_dir == tools_dir
        assert downloader.version == "0.7.4"
        assert downloader.install_dir == tools_dir / "sccache" / "0.7.4"

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test getting executable path when sccache is not installed."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(tools_dir)

        assert downloader.get_executable_path() is None

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(tools_dir)

        assert downloader.is_installed() is False

    def test_is_installed_true_linux(self, tmp_path):
        """Test is_installed returns True when sccache is installed on Linux."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        sccache_exe = downloader.install_dir / "sccache"
        sccache_exe.parent.mkdir(parents=True, exist_ok=True)
        sccache_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == sccache_exe

    def test_is_installed_true_windows(self, tmp_path):
        """Test is_installed returns True when sccache is installed on Windows."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        # Create fake installation
        sccache_exe = downloader.install_dir / "sccache.exe"
        sccache_exe.parent.mkdir(parents=True, exist_ok=True)
        sccache_exe.touch()

        assert downloader.is_installed() is True
        assert downloader.get_executable_path() == sccache_exe

    def test_get_download_url_linux(self, tmp_path):
        """Test sccache download URL for Linux."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/mozilla/sccache/releases/download/v0.7.4/sccache-v0.7.4-x86_64-unknown-linux-musl.tar.gz"
        )

    def test_get_download_url_macos_x64(self, tmp_path):
        """Test sccache download URL for macOS x64."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("macos", "x86_64", "14.0", "", ""),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/mozilla/sccache/releases/download/v0.7.4/sccache-v0.7.4-x86_64-apple-darwin.tar.gz"
        )

    def test_get_download_url_macos_arm64(self, tmp_path):
        """Test sccache download URL for macOS ARM64."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("macos", "arm64", "14.0", "", ""),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/mozilla/sccache/releases/download/v0.7.4/sccache-v0.7.4-aarch64-apple-darwin.tar.gz"
        )

    def test_get_download_url_windows(self, tmp_path):
        """Test sccache download URL for Windows."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/mozilla/sccache/releases/download/v0.7.4/sccache-v0.7.4-x86_64-pc-windows-msvc.zip"
        )

    def test_get_download_url_unsupported_platform(self, tmp_path):
        """Test sccache download URL with unsupported platform."""
        from toolchainkit.packages.tool_downloader import (
            SccacheDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("freebsd", "x86_64", "13.0", "", ""),
        )

        with pytest.raises(ToolDownloadError, match="Unsupported platform"):
            downloader._get_download_url()

    @patch("toolchainkit.core.filesystem.extract_archive")
    @patch("toolchainkit.core.download.download_file")
    def test_download_success(self, mock_download, mock_extract, tmp_path):
        """Test successful sccache download."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful download and extraction
        def mock_download_side_effect(url, dest_path):
            # Create the archive file that would be downloaded
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.touch()

        def mock_extract_side_effect(archive_path, extract_dir):
            # Create sccache executable
            sccache_dir = extract_dir / "sccache-v0.7.4-x86_64-unknown-linux-musl"
            sccache_exe = sccache_dir / "sccache"
            sccache_exe.parent.mkdir(parents=True, exist_ok=True)
            sccache_exe.touch()

        mock_download.side_effect = mock_download_side_effect
        mock_extract.side_effect = mock_extract_side_effect

        result = downloader.download()

        assert result == downloader.install_dir
        assert downloader.is_installed()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_download_already_installed(self, tmp_path):
        """Test download skips when already installed."""
        from toolchainkit.packages.tool_downloader import SccacheDownloader

        tools_dir = tmp_path / "tools"
        downloader = SccacheDownloader(
            tools_dir,
            version="0.7.4",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        sccache_exe = downloader.install_dir / "sccache"
        sccache_exe.parent.mkdir(parents=True, exist_ok=True)
        sccache_exe.touch()

        result = downloader.download(force=False)

        assert result == downloader.install_dir


# =============================================================================
# Test Caching Tool System Detection
# =============================================================================


class TestCachingToolDetection:
    """Test system caching tool detection functions."""

    @patch("shutil.which")
    def test_get_system_sccache_path_found(self, mock_which):
        """Test when system sccache is found."""
        from toolchainkit.packages.tool_downloader import get_system_sccache_path

        mock_which.return_value = "/usr/bin/sccache"

        result = get_system_sccache_path()

        assert result == Path("/usr/bin/sccache")
        mock_which.assert_called_once_with("sccache")

    @patch("shutil.which")
    def test_get_system_sccache_path_not_found(self, mock_which):
        """Test when system sccache is not found."""
        from toolchainkit.packages.tool_downloader import get_system_sccache_path

        mock_which.return_value = None

        result = get_system_sccache_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_ccache_path_found(self, mock_which):
        """Test when system ccache is found."""
        from toolchainkit.packages.tool_downloader import get_system_ccache_path

        mock_which.return_value = "/usr/bin/ccache"

        result = get_system_ccache_path()

        assert result == Path("/usr/bin/ccache")
        mock_which.assert_called_once_with("ccache")

    @patch("shutil.which")
    def test_get_system_ccache_path_not_found(self, mock_which):
        """Test when system ccache is not found."""
        from toolchainkit.packages.tool_downloader import get_system_ccache_path

        mock_which.return_value = None

        result = get_system_ccache_path()

        assert result is None


# =============================================================================
# Test PythonDownloader
# =============================================================================


class TestPythonDownloader:
    """Test Python downloader functionality."""

    def test_init(self, tmp_path):
        """Test PythonDownloader initialization."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(tools_dir, version="3.12.7")

        assert downloader.tools_dir == tools_dir
        assert downloader.version == "3.12.7"
        assert downloader.install_dir == tools_dir / "python" / "3.12.7"

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(tools_dir, version="3.12.7")

        assert downloader.is_installed() is False

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test get_executable_path returns None when not installed."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(tools_dir, version="3.12.7")

        assert downloader.get_executable_path() is None

    def test_get_download_url_windows(self, tmp_path):
        """Test download URL generation for Windows."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(
            tools_dir,
            version="3.12.7",
            platform=PlatformInfo("windows", "x86_64", "10.0.19045", "", ""),
        )

        url = downloader._get_download_url()

        assert "python.org/ftp/python/3.12.7" in url
        assert "python-3.12.7-embed-amd64.zip" in url

    def test_get_download_url_linux_x64(self, tmp_path):
        """Test download URL generation for Linux x64."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(
            tools_dir,
            version="3.12.7",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        url = downloader._get_download_url()

        assert "github.com/indygreg/python-build-standalone" in url
        assert "cpython-3.12.7" in url
        assert "x86_64-unknown-linux-gnu" in url
        assert "install_only.tar.gz" in url

    def test_get_download_url_macos_x64(self, tmp_path):
        """Test download URL generation for macOS x64."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(
            tools_dir,
            version="3.12.7",
            platform=PlatformInfo("macos", "x86_64", "13.0.0", "", ""),
        )

        url = downloader._get_download_url()

        assert "github.com/indygreg/python-build-standalone" in url
        assert "cpython-3.12.7" in url
        assert "x86_64-apple-darwin" in url

    def test_get_download_url_macos_arm64(self, tmp_path):
        """Test download URL generation for macOS ARM64."""
        from toolchainkit.packages.tool_downloader import PythonDownloader

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(
            tools_dir,
            version="3.12.7",
            platform=PlatformInfo("macos", "arm64", "13.0.0", "", ""),
        )

        url = downloader._get_download_url()

        assert "github.com/indygreg/python-build-standalone" in url
        assert "cpython-3.12.7" in url
        assert "aarch64-apple-darwin" in url

    def test_get_download_url_unsupported_platform(self, tmp_path):
        """Test download URL generation for unsupported platform."""
        from toolchainkit.packages.tool_downloader import (
            PythonDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = PythonDownloader(
            tools_dir,
            version="3.12.7",
            platform=PlatformInfo("freebsd", "x86_64", "13.0", "", ""),
        )

        with pytest.raises(ToolDownloadError, match="Unsupported platform"):
            downloader._get_download_url()


# =============================================================================
# Test MakeDownloader
# =============================================================================


class TestMakeDownloader:
    """Test Make downloader functionality."""

    def test_init(self, tmp_path):
        """Test MakeDownloader initialization."""
        from toolchainkit.packages.tool_downloader import MakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(tools_dir, version="2.4.0")

        assert downloader.tools_dir == tools_dir
        assert downloader.version == "2.4.0"
        assert downloader.install_dir == tools_dir / "make" / "2.4.0"

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when not installed."""
        from toolchainkit.packages.tool_downloader import MakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(tools_dir, version="2.4.0")

        assert downloader.is_installed() is False

    def test_get_executable_path_not_installed(self, tmp_path):
        """Test get_executable_path returns None when not installed."""
        from toolchainkit.packages.tool_downloader import MakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(tools_dir, version="2.4.0")

        assert downloader.get_executable_path() is None

    def test_get_download_url_windows(self, tmp_path):
        """Test download URL generation for Windows."""
        from toolchainkit.packages.tool_downloader import MakeDownloader

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(
            tools_dir,
            version="2.4.0",
            platform=PlatformInfo("windows", "x86_64", "10.0.19045", "", ""),
        )

        url = downloader._get_download_url()

        assert "github.com/skeeto/w64devkit" in url
        assert "v2.4.0" in url
        assert "w64devkit-x64-2.4.0.7z.exe" in url

    def test_get_download_url_non_windows(self, tmp_path):
        """Test download URL generation fails for non-Windows."""
        from toolchainkit.packages.tool_downloader import (
            MakeDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(
            tools_dir,
            version="2.0.0",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        with pytest.raises(ToolDownloadError, match="only supported on Windows"):
            downloader._get_download_url()

    def test_download_non_windows_raises_error(self, tmp_path):
        """Test download raises error on non-Windows platforms."""
        from toolchainkit.packages.tool_downloader import (
            MakeDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = MakeDownloader(
            tools_dir,
            version="2.0.0",
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        with pytest.raises(ToolDownloadError, match="only needed on Windows"):
            downloader.download()


# =============================================================================
# Test System Detection for Python and Make
# =============================================================================


class TestPythonMakeDetection:
    """Test system Python and Make detection functions."""

    @patch("shutil.which")
    def test_get_system_python_path_found_python3(self, mock_which):
        """Test when system python3 is found."""
        from toolchainkit.packages.tool_downloader import get_system_python_path

        mock_which.return_value = "/usr/bin/python3"

        result = get_system_python_path()

        assert result == Path("/usr/bin/python3")
        mock_which.assert_called_once_with("python3")

    @patch("shutil.which")
    def test_get_system_python_path_found_python(self, mock_which):
        """Test when system python is found (fallback)."""
        from toolchainkit.packages.tool_downloader import get_system_python_path

        # python3 not found, python found
        mock_which.side_effect = [None, "/usr/bin/python"]

        result = get_system_python_path()

        assert result == Path("/usr/bin/python")
        assert mock_which.call_count == 2

    @patch("shutil.which")
    def test_get_system_python_path_not_found(self, mock_which):
        """Test when system python is not found."""
        from toolchainkit.packages.tool_downloader import get_system_python_path

        mock_which.return_value = None

        result = get_system_python_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_make_path_found_make(self, mock_which):
        """Test when system make is found."""
        from toolchainkit.packages.tool_downloader import get_system_make_path

        mock_which.return_value = "/usr/bin/make"

        result = get_system_make_path()

        assert result == Path("/usr/bin/make")
        mock_which.assert_called_once_with("make")

    @patch("shutil.which")
    def test_get_system_make_path_found_gmake(self, mock_which):
        """Test when system gmake is found."""
        from toolchainkit.packages.tool_downloader import get_system_make_path

        # make not found, gmake found
        mock_which.side_effect = [None, "/usr/bin/gmake", None]

        result = get_system_make_path()

        assert result == Path("/usr/bin/gmake")

    @patch("shutil.which")
    def test_get_system_make_path_found_mingw32_make(self, mock_which):
        """Test when system mingw32-make is found."""
        from toolchainkit.packages.tool_downloader import get_system_make_path

        # make not found, gmake not found, mingw32-make found
        mock_which.side_effect = [None, None, "C:\\MinGW\\bin\\mingw32-make.exe"]

        result = get_system_make_path()

        assert result == Path("C:\\MinGW\\bin\\mingw32-make.exe")

    @patch("shutil.which")
    def test_get_system_make_path_not_found(self, mock_which):
        """Test when system make is not found."""
        from toolchainkit.packages.tool_downloader import get_system_make_path

        mock_which.return_value = None

        result = get_system_make_path()

        assert result is None


class TestGitDownloader:
    """Test GitDownloader functionality."""

    def test_init_windows(self, tmp_path):
        """Test GitDownloader initialization on Windows."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        assert downloader.platform.os == "windows"
        assert downloader.install_dir == tools_dir
        assert downloader.version == "2.47.1"
        assert downloader.tool_dir == tools_dir / "git" / "2.47.1"

    def test_init_linux(self, tmp_path):
        """Test GitDownloader initialization on Linux."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        assert downloader.platform.os == "linux"
        assert downloader.install_dir == tools_dir
        assert downloader.version == "2.47.1"

    def test_is_installed_not_installed(self, tmp_path):
        """Test is_installed returns False when git not present."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        assert not downloader.is_installed()

    def test_is_installed_windows_installed(self, tmp_path):
        """Test is_installed returns True when git is present on Windows."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        # Create git executable
        git_dir = downloader.tool_dir / "MinGit-2.47.1-64-bit" / "cmd"
        git_dir.mkdir(parents=True)
        git_exe = git_dir / "git.exe"
        git_exe.touch()

        assert downloader.is_installed()

    def test_get_executable_path_windows(self, tmp_path):
        """Test get_executable_path on Windows."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        # Create git executable
        git_dir = downloader.tool_dir / "MinGit-2.47.1-64-bit" / "cmd"
        git_dir.mkdir(parents=True)
        git_exe = git_dir / "git.exe"
        git_exe.touch()

        exe_path = downloader.get_executable_path()
        assert exe_path == git_exe
        assert exe_path.exists()

    @patch("shutil.which")
    def test_get_executable_path_linux(self, mock_which, tmp_path):
        """Test get_executable_path on Linux uses system git."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        mock_which.return_value = "/usr/bin/git"

        exe_path = downloader.get_executable_path()
        assert exe_path == Path("/usr/bin/git")

    def test_get_download_url_windows(self, tmp_path):
        """Test git download URL for Windows."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/MinGit-2.47.1-64-bit.zip"
        )

    def test_get_download_url_linux_raises(self, tmp_path):
        """Test git download URL raises on Linux."""
        from toolchainkit.packages.tool_downloader import (
            GitDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        with pytest.raises(
            ToolDownloadError, match="Git download only supported on Windows"
        ):
            downloader._get_download_url()

    def test_download_linux_raises(self, tmp_path):
        """Test download raises on Linux."""
        from toolchainkit.packages.tool_downloader import (
            GitDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        with pytest.raises(
            ToolDownloadError, match="Git download only supported on Windows"
        ):
            downloader.download()

    @patch("toolchainkit.core.filesystem.extract_archive")
    @patch("toolchainkit.core.download.download_file")
    def test_download_windows_success(self, mock_download, mock_extract, tmp_path):
        """Test successful git download on Windows."""
        from toolchainkit.packages.tool_downloader import GitDownloader

        tools_dir = tmp_path / "tools"
        downloader = GitDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.47.1",
        )

        # Mock download to create archive file
        def create_archive(url, archive_path):
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_path.touch()

        mock_download.side_effect = create_archive

        # Mock extraction to create git executable
        def create_git_exe(archive_path, extract_dir):
            git_dir = downloader.tool_dir / "MinGit-2.47.1-64-bit" / "cmd"
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / "git.exe").touch()

        mock_extract.side_effect = create_git_exe

        result = downloader.download()

        assert result.exists()
        assert result.name == "git.exe"
        mock_download.assert_called_once()
        mock_extract.assert_called_once()


class TestGitDetection:
    """Test system git detection functions."""

    @patch("shutil.which")
    def test_get_system_git_path_found(self, mock_which):
        """Test when system git is found."""
        from toolchainkit.packages.tool_downloader import get_system_git_path

        mock_which.return_value = "/usr/bin/git"

        result = get_system_git_path()

        assert result == Path("/usr/bin/git")
        mock_which.assert_called_once_with("git")

    @patch("shutil.which")
    def test_get_system_git_path_not_found(self, mock_which):
        """Test when system git is not found."""
        from toolchainkit.packages.tool_downloader import get_system_git_path

        mock_which.return_value = None

        result = get_system_git_path()

        assert result is None


class TestClangToolsDownloader:
    """Test ClangToolsDownloader functionality."""

    def test_init_windows(self, tmp_path):
        """Test ClangToolsDownloader initialization on Windows."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        assert downloader.platform.os == "windows"
        assert downloader.install_dir == tools_dir
        assert downloader.version == "18.1.8"
        assert downloader.tool_dir == tools_dir / "clang-tools" / "18.1.8"

    def test_is_installed_not_installed(self, tmp_path):
        """Test is_installed returns False when tools not present."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        assert not downloader.is_installed()

    def test_is_installed_windows_installed(self, tmp_path):
        """Test is_installed returns True when tools are present on Windows."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        # Create executables
        bin_dir = downloader.tool_dir / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "clang-tidy.exe").touch()
        (bin_dir / "clang-format.exe").touch()

        assert downloader.is_installed()

    def test_get_clang_tidy_path_windows(self, tmp_path):
        """Test get_clang_tidy_path on Windows."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        # Create executable
        bin_dir = downloader.tool_dir / "bin"
        bin_dir.mkdir(parents=True)
        tidy_exe = bin_dir / "clang-tidy.exe"
        tidy_exe.touch()

        exe_path = downloader.get_clang_tidy_path()
        assert exe_path == tidy_exe
        assert exe_path.exists()

    def test_get_clang_format_path_linux(self, tmp_path):
        """Test get_clang_format_path on Linux."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        # Create executable
        bin_dir = downloader.tool_dir / "bin"
        bin_dir.mkdir(parents=True)
        format_exe = bin_dir / "clang-format"
        format_exe.touch()

        exe_path = downloader.get_clang_format_path()
        assert exe_path == format_exe
        assert exe_path.exists()

    def test_get_download_url_windows(self, tmp_path):
        """Test clang tools download URL for Windows."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/LLVM-18.1.8-win64.exe"
        )

    def test_get_download_url_linux(self, tmp_path):
        """Test clang tools download URL for Linux."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-linux-gnu-ubuntu-18.04.tar.xz"
        )

    def test_get_download_url_macos_arm64(self, tmp_path):
        """Test clang tools download URL for macOS ARM64."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("macos", "arm64", "14.0", "", "clang"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/clang+llvm-18.1.8-arm64-apple-darwin22.0.tar.xz"
        )

    @patch("toolchainkit.core.filesystem.extract_archive")
    @patch("toolchainkit.core.download.download_file")
    def test_download_windows_success(self, mock_download, mock_extract, tmp_path):
        """Test successful clang tools download on Windows."""
        from toolchainkit.packages.tool_downloader import ClangToolsDownloader

        tools_dir = tmp_path / "tools"
        downloader = ClangToolsDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="18.1.8",
        )

        # Mock download to create archive file
        def create_archive(url, archive_path):
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_path.touch()

        mock_download.side_effect = create_archive

        # Mock extraction to create executables
        def create_executables(archive_path, extract_dir):
            bin_dir = downloader.tool_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            (bin_dir / "clang-tidy.exe").touch()
            (bin_dir / "clang-format.exe").touch()

        mock_extract.side_effect = create_executables

        tidy_path, format_path = downloader.download()

        assert tidy_path.exists()
        assert tidy_path.name == "clang-tidy.exe"
        assert format_path.exists()
        assert format_path.name == "clang-format.exe"
        mock_download.assert_called_once()
        mock_extract.assert_called_once()


class TestCppcheckDownloader:
    """Test CppcheckDownloader functionality."""

    def test_init_windows(self, tmp_path):
        """Test CppcheckDownloader initialization on Windows."""
        from toolchainkit.packages.tool_downloader import CppcheckDownloader

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        assert downloader.platform.os == "windows"
        assert downloader.install_dir == tools_dir
        assert downloader.version == "2.16.2"
        assert downloader.tool_dir == tools_dir / "cppcheck" / "2.16.2"

    def test_is_installed_not_installed(self, tmp_path):
        """Test is_installed returns False when cppcheck not present."""
        from toolchainkit.packages.tool_downloader import CppcheckDownloader

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        assert not downloader.is_installed()

    def test_is_installed_windows_installed(self, tmp_path):
        """Test is_installed returns True when cppcheck is present on Windows."""
        from toolchainkit.packages.tool_downloader import CppcheckDownloader

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        # Create executable
        bin_dir = downloader.tool_dir / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "cppcheck.exe").touch()

        assert downloader.is_installed()

    def test_get_executable_path_windows(self, tmp_path):
        """Test get_executable_path on Windows."""
        from toolchainkit.packages.tool_downloader import CppcheckDownloader

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        # Create executable
        bin_dir = downloader.tool_dir / "bin"
        bin_dir.mkdir(parents=True)
        cppcheck_exe = bin_dir / "cppcheck.exe"
        cppcheck_exe.touch()

        exe_path = downloader.get_executable_path()
        assert exe_path == cppcheck_exe
        assert exe_path.exists()

    def test_get_download_url_windows(self, tmp_path):
        """Test cppcheck download URL for Windows."""
        from toolchainkit.packages.tool_downloader import CppcheckDownloader

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("windows", "x86_64", "10", "", "msvc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        url = downloader._get_download_url()
        assert (
            url
            == "https://github.com/danmar/cppcheck/releases/download/2.16.2/cppcheck-2.16.2-x64-Setup.msi"
        )

    def test_get_download_url_linux_raises(self, tmp_path):
        """Test cppcheck download URL raises on Linux."""
        from toolchainkit.packages.tool_downloader import (
            CppcheckDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        with pytest.raises(
            ToolDownloadError, match="Cppcheck download not supported on Linux"
        ):
            downloader._get_download_url()

    def test_download_linux_raises(self, tmp_path):
        """Test download raises on Linux."""
        from toolchainkit.packages.tool_downloader import (
            CppcheckDownloader,
            ToolDownloadError,
        )

        tools_dir = tmp_path / "tools"
        downloader = CppcheckDownloader(
            platform=PlatformInfo("linux", "x86_64", "5.15", "debian", "gcc"),
            install_dir=tools_dir,
            version="2.16.2",
        )

        with pytest.raises(
            ToolDownloadError, match="Cppcheck download not supported on Linux"
        ):
            downloader.download()


class TestAnalysisToolsDetection:
    """Test system analysis tools detection functions."""

    @patch("shutil.which")
    def test_get_system_clang_tidy_path_found(self, mock_which):
        """Test when system clang-tidy is found."""
        from toolchainkit.packages.tool_downloader import get_system_clang_tidy_path

        mock_which.return_value = "/usr/bin/clang-tidy"

        result = get_system_clang_tidy_path()

        assert result == Path("/usr/bin/clang-tidy")
        mock_which.assert_called_once_with("clang-tidy")

    @patch("shutil.which")
    def test_get_system_clang_tidy_path_not_found(self, mock_which):
        """Test when system clang-tidy is not found."""
        from toolchainkit.packages.tool_downloader import get_system_clang_tidy_path

        mock_which.return_value = None

        result = get_system_clang_tidy_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_clang_format_path_found(self, mock_which):
        """Test when system clang-format is found."""
        from toolchainkit.packages.tool_downloader import get_system_clang_format_path

        mock_which.return_value = "/usr/bin/clang-format"

        result = get_system_clang_format_path()

        assert result == Path("/usr/bin/clang-format")
        mock_which.assert_called_once_with("clang-format")

    @patch("shutil.which")
    def test_get_system_clang_format_path_not_found(self, mock_which):
        """Test when system clang-format is not found."""
        from toolchainkit.packages.tool_downloader import get_system_clang_format_path

        mock_which.return_value = None

        result = get_system_clang_format_path()

        assert result is None

    @patch("shutil.which")
    def test_get_system_cppcheck_path_found(self, mock_which):
        """Test when system cppcheck is found."""
        from toolchainkit.packages.tool_downloader import get_system_cppcheck_path

        mock_which.return_value = "/usr/bin/cppcheck"

        result = get_system_cppcheck_path()

        assert result == Path("/usr/bin/cppcheck")
        mock_which.assert_called_once_with("cppcheck")

    @patch("shutil.which")
    def test_get_system_cppcheck_path_not_found(self, mock_which):
        """Test when system cppcheck is not found."""
        from toolchainkit.packages.tool_downloader import get_system_cppcheck_path

        mock_which.return_value = None

        result = get_system_cppcheck_path()

        assert result is None


# =============================================================================
# Additional Edge Case Tests for Missing Coverage
# =============================================================================


class TestConanDownloaderEdgeCases:
    """Edge cases for ConanDownloader to improve coverage."""

    @patch("subprocess.run")
    def test_download_with_specific_version(self, mock_run, tmp_path):
        """Test downloading specific Conan version."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        def create_conan_exe(*args, **kwargs):
            conan_exe = downloader.conan_dir / "venv" / "bin" / "conan"
            conan_exe.parent.mkdir(parents=True, exist_ok=True)
            conan_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = create_conan_exe

        result = downloader.download(version="2.0.13")

        assert result == downloader.conan_dir
        # Should have been called with specific version
        pip_call = [call for call in mock_run.call_args_list if "pip" in str(call)]
        assert len(pip_call) > 0

    @patch("subprocess.run")
    def test_download_hermetic_python(self, mock_run, tmp_path):
        """Test downloading Conan with hermetic Python."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        with patch(
            "toolchainkit.packages.tool_downloader.PythonDownloader"
        ) as mock_python:
            mock_python_instance = Mock()
            mock_python_instance.is_installed.return_value = True
            mock_python_instance.get_executable_path.return_value = Path(
                "/tools/python/bin/python"
            )
            mock_python.return_value = mock_python_instance

            def create_conan_exe(*args, **kwargs):
                conan_exe = downloader.conan_dir / "venv" / "bin" / "conan"
                conan_exe.parent.mkdir(parents=True, exist_ok=True)
                conan_exe.touch()
                return Mock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = create_conan_exe

            result = downloader.download(version="2.0", use_hermetic_python=True)

            assert result == downloader.conan_dir
            mock_python_instance.is_installed.assert_called_once()

    @patch("subprocess.run")
    def test_download_hermetic_python_not_installed(self, mock_run, tmp_path):
        """Test downloading Conan when hermetic Python needs to be downloaded."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        with patch(
            "toolchainkit.packages.tool_downloader.PythonDownloader"
        ) as mock_python:
            mock_python_instance = Mock()
            mock_python_instance.is_installed.return_value = False
            mock_python_instance.download.return_value = Path("/tools/python")
            mock_python_instance.get_executable_path.return_value = Path(
                "/tools/python/bin/python"
            )
            mock_python.return_value = mock_python_instance

            def create_conan_exe(*args, **kwargs):
                conan_exe = downloader.conan_dir / "venv" / "bin" / "conan"
                conan_exe.parent.mkdir(parents=True, exist_ok=True)
                conan_exe.touch()
                return Mock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = create_conan_exe

            result = downloader.download(version="2.0", use_hermetic_python=True)

            assert result == downloader.conan_dir
            mock_python_instance.download.assert_called_once()

    @patch("subprocess.run")
    def test_download_hermetic_python_unavailable(self, mock_run, tmp_path):
        """Test error when hermetic Python cannot be obtained."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        with patch(
            "toolchainkit.packages.tool_downloader.PythonDownloader"
        ) as mock_python:
            mock_python_instance = Mock()
            mock_python_instance.is_installed.return_value = True
            mock_python_instance.get_executable_path.return_value = None
            mock_python.return_value = mock_python_instance

            with pytest.raises(
                ToolDownloadError, match="Failed to get hermetic Python"
            ):
                downloader.download(version="2.0", use_hermetic_python=True)

    @patch("subprocess.run")
    def test_download_venv_creation_timeout(self, mock_run, tmp_path):
        """Test timeout during venv creation."""
        import subprocess

        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        mock_run.side_effect = subprocess.TimeoutExpired("python", 120)

        with pytest.raises(ToolDownloadError, match="Installation timed out"):
            downloader.download(version="2.0")

    @patch("subprocess.run")
    def test_download_pip_install_timeout(self, mock_run, tmp_path):
        """Test timeout during pip install."""
        import subprocess

        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        call_count = [0]

        def timeout_on_second_call(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (venv creation) succeeds
                return Mock(returncode=0, stdout="", stderr="")
            # Second call (pip install) times out
            raise subprocess.TimeoutExpired("pip", 300)

        mock_run.side_effect = timeout_on_second_call

        with pytest.raises(ToolDownloadError, match="Installation timed out"):
            downloader.download(version="2.0")

    @patch("subprocess.run")
    def test_download_conan_exe_not_created(self, mock_run, tmp_path):
        """Test error when Conan executable is not created after installation."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Mock successful subprocess but don't create the executable
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with pytest.raises(
            ToolDownloadError, match="Conan executable not found after installation"
        ):
            downloader.download(version="2.0")

    @patch("subprocess.run")
    def test_download_cleanup_failure_doesnt_hide_main_error(self, mock_run, tmp_path):
        """Test that cleanup failure doesn't hide the main error."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Venv failed")

        # Create directory to trigger cleanup attempt
        downloader.conan_dir.mkdir(parents=True)
        (downloader.conan_dir / "file.txt").touch()

        with patch(
            "toolchainkit.packages.tool_downloader.safe_rmtree",
            side_effect=Exception("Cleanup error"),
        ):
            with pytest.raises(ToolDownloadError, match="Failed to install Conan"):
                downloader.download(version="2.0", force=True)

    def test_get_executable_path_windows(self, tmp_path):
        """Test getting executable path on Windows."""
        tools_dir = tmp_path / "tools"
        downloader = ConanDownloader(
            tools_dir, platform=PlatformInfo("windows", "x86_64", "10", "", "msvc")
        )

        # Create Windows executable structure
        conan_exe = downloader.conan_dir / "venv" / "Scripts" / "conan.exe"
        conan_exe.parent.mkdir(parents=True, exist_ok=True)
        conan_exe.touch()

        result = downloader.get_executable_path()

        assert result == conan_exe
        assert downloader.is_installed()


class TestVcpkgDownloaderEdgeCases:
    """Edge cases for VcpkgDownloader to improve coverage."""

    @patch("subprocess.run")
    def test_download_specific_version(self, mock_run, tmp_path):
        """Test downloading specific vcpkg version."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        def mock_subprocess(*args, **kwargs):
            cmd = args[0]
            if "git" in cmd[0]:
                # Verify version tag is passed
                assert "--branch" in cmd
                assert "2024.10.21" in cmd
                vcpkg_dir = tools_dir / "vcpkg"
                vcpkg_dir.mkdir(parents=True, exist_ok=True)
                (vcpkg_dir / "bootstrap-vcpkg.sh").touch()
            elif "bootstrap" in cmd[0]:
                vcpkg_exe = tools_dir / "vcpkg" / "vcpkg"
                vcpkg_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = downloader.download(version="2024.10.21")

        assert result == downloader.vcpkg_dir

    @patch("subprocess.run")
    def test_download_git_clone_timeout(self, mock_run, tmp_path):
        """Test timeout during git clone."""
        import subprocess

        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        mock_run.side_effect = subprocess.TimeoutExpired("git", 300)

        with pytest.raises(ToolDownloadError, match="Installation timed out"):
            downloader.download()

    @patch("subprocess.run")
    def test_download_bootstrap_timeout(self, mock_run, tmp_path):
        """Test timeout during bootstrap."""
        import subprocess

        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        call_count = [0]

        def timeout_on_second_call(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (git clone) succeeds
                vcpkg_dir = tools_dir / "vcpkg"
                vcpkg_dir.mkdir(parents=True, exist_ok=True)
                (vcpkg_dir / "bootstrap-vcpkg.sh").touch()
                return Mock(returncode=0, stdout="", stderr="")
            # Second call (bootstrap) times out
            raise subprocess.TimeoutExpired("bootstrap", 600)

        mock_run.side_effect = timeout_on_second_call

        with pytest.raises(ToolDownloadError, match="Installation timed out"):
            downloader.download()

    @patch("subprocess.run")
    def test_download_bootstrap_script_missing(self, mock_run, tmp_path):
        """Test error when bootstrap script is not found."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        def mock_git_clone(*args, **kwargs):
            vcpkg_dir = tools_dir / "vcpkg"
            vcpkg_dir.mkdir(parents=True, exist_ok=True)
            # Don't create bootstrap script
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_git_clone

        with pytest.raises(ToolDownloadError, match="Bootstrap script not found"):
            downloader.download()

    @patch("subprocess.run")
    def test_download_bootstrap_failure(self, mock_run, tmp_path):
        """Test error when bootstrap script fails."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        call_count = [0]

        def bootstrap_fails(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Git clone succeeds
                vcpkg_dir = tools_dir / "vcpkg"
                vcpkg_dir.mkdir(parents=True, exist_ok=True)
                (vcpkg_dir / "bootstrap-vcpkg.sh").touch()
                return Mock(returncode=0, stdout="", stderr="")
            # Bootstrap fails
            return Mock(returncode=1, stdout="", stderr="Bootstrap failed")

        mock_run.side_effect = bootstrap_fails

        with pytest.raises(ToolDownloadError, match="Failed to bootstrap vcpkg"):
            downloader.download()

    @patch("subprocess.run")
    def test_download_cleanup_on_generic_exception(self, mock_run, tmp_path):
        """Test cleanup when generic exception occurs."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(tools_dir)

        mock_run.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(ToolDownloadError, match="Failed to install vcpkg"):
            downloader.download()

        # Directory should be cleaned up
        assert not downloader.vcpkg_dir.exists()

    @patch("subprocess.run")
    def test_download_windows_uses_bat_script(self, mock_run, tmp_path):
        """Test that Windows uses .bat bootstrap script."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir, platform=PlatformInfo("windows", "x86_64", "10", "", "msvc")
        )

        def mock_subprocess(*args, **kwargs):
            cmd = args[0]
            if "git" in cmd[0]:
                vcpkg_dir = tools_dir / "vcpkg"
                vcpkg_dir.mkdir(parents=True, exist_ok=True)
                (vcpkg_dir / "bootstrap-vcpkg.bat").touch()
            elif "bootstrap-vcpkg.bat" in cmd[0]:
                vcpkg_exe = tools_dir / "vcpkg" / "vcpkg.exe"
                vcpkg_exe.touch()
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = downloader.download()

        assert result == downloader.vcpkg_dir
        # Verify .bat script was used
        bootstrap_calls = [
            call for call in mock_run.call_args_list if "bootstrap" in str(call)
        ]
        assert any("bootstrap-vcpkg.bat" in str(call) for call in bootstrap_calls)

    def test_get_executable_path_windows(self, tmp_path):
        """Test getting executable path on Windows."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir, platform=PlatformInfo("windows", "x86_64", "10", "", "msvc")
        )

        # Create Windows executable
        vcpkg_exe = downloader.vcpkg_dir / "vcpkg.exe"
        vcpkg_exe.parent.mkdir(parents=True, exist_ok=True)
        vcpkg_exe.touch()

        result = downloader.get_executable_path()

        assert result == vcpkg_exe
        assert downloader.is_installed()

    @patch("subprocess.run")
    def test_download_already_installed_no_force(self, mock_run, tmp_path):
        """Test that download is skipped when already installed and not forcing."""
        tools_dir = tmp_path / "tools"
        downloader = VcpkgDownloader(
            tools_dir,
            platform=PlatformInfo("linux", "x86_64", "5.15.0", "", "glibc-2.31"),
        )

        # Create fake installation
        vcpkg_dir = tools_dir / "vcpkg"
        vcpkg_dir.mkdir(parents=True, exist_ok=True)
        (vcpkg_dir / "vcpkg").touch()

        result = downloader.download(force=False)

        assert result == vcpkg_dir
        # Should not have called subprocess
        mock_run.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
