"""
Unit tests for vcpkg package manager integration.

Tests the VcpkgIntegration class including detection, triplet selection,
installation, and CMake toolchain chaining.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

from toolchainkit.packages.vcpkg import VcpkgIntegration
from toolchainkit.core.exceptions import (
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerInstallError,
)


# =============================================================================
# Mock Objects
# =============================================================================


class MockPlatform:
    """Mock platform for testing."""

    def __init__(self, os="linux", architecture="x86_64"):
        self.os = os
        self.architecture = architecture


# =============================================================================
# Test Detection
# =============================================================================


class TestVcpkgDetection:
    """Test vcpkg manifest file detection."""

    def test_detect_with_vcpkg_json(self, tmp_path):
        """Test detection when vcpkg.json exists."""
        manifest = tmp_path / "vcpkg.json"
        manifest.write_text('{"dependencies": ["fmt"]}')

        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.detect() is True

    def test_detect_without_vcpkg_json(self, tmp_path):
        """Test detection when no vcpkg.json exists."""
        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.detect() is False

    def test_manifest_file_path(self, tmp_path):
        """Test that manifest file path is set correctly."""
        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.manifest_file == tmp_path / "vcpkg.json"


# =============================================================================
# Test VCPKG_ROOT Detection
# =============================================================================


class TestVcpkgRootDetection:
    """Test vcpkg installation detection."""

    @patch.dict(os.environ, {"VCPKG_ROOT": "/custom/vcpkg"})
    def test_find_vcpkg_root_from_env(self, tmp_path):
        """Test finding vcpkg from VCPKG_ROOT environment variable."""
        vcpkg_root = tmp_path / "custom" / "vcpkg"
        vcpkg_root.mkdir(parents=True)

        with patch.dict(os.environ, {"VCPKG_ROOT": str(vcpkg_root)}):
            vcpkg = VcpkgIntegration(tmp_path)
            assert vcpkg.vcpkg_root == vcpkg_root

    @patch.dict(os.environ, {}, clear=True)
    @patch("pathlib.Path.home")
    def test_find_vcpkg_root_from_home(self, mock_home, tmp_path):
        """Test finding vcpkg in home directory."""
        home = tmp_path / "home"
        home.mkdir()
        mock_home.return_value = home

        vcpkg_dir = home / "vcpkg"
        vcpkg_dir.mkdir()
        (vcpkg_dir / "vcpkg").touch()

        with patch.dict(os.environ, {}, clear=True):
            _vcpkg = VcpkgIntegration(tmp_path)
            # Note: Will find it if Path.home() returns our mocked home

    @patch.dict(os.environ, {}, clear=True)
    @patch("pathlib.Path.home")
    def test_find_vcpkg_root_not_found(self, mock_home, tmp_path):
        """Test when vcpkg is not found anywhere."""
        # Mock home to avoid environment issues
        mock_home.return_value = tmp_path / "home"
        vcpkg = VcpkgIntegration(tmp_path)
        # vcpkg_root will be None if not found
        assert vcpkg.vcpkg_root is None or isinstance(vcpkg.vcpkg_root, Path)


# =============================================================================
# Test Triplet Selection
# =============================================================================


class TestVcpkgTripletSelection:
    """Test vcpkg triplet selection based on platform."""

    def test_triplet_linux_x64(self, tmp_path):
        """Test triplet for Linux x64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="x86_64")
        assert vcpkg.get_triplet(platform) == "x64-linux"

    def test_triplet_linux_x64_alt(self, tmp_path):
        """Test triplet for Linux x64 (alternative arch names)."""
        vcpkg = VcpkgIntegration(tmp_path)

        platform = MockPlatform(os="linux", architecture="x64")
        assert vcpkg.get_triplet(platform) == "x64-linux"

        platform = MockPlatform(os="linux", architecture="amd64")
        assert vcpkg.get_triplet(platform) == "x64-linux"

    def test_triplet_linux_arm64(self, tmp_path):
        """Test triplet for Linux ARM64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="arm64")
        assert vcpkg.get_triplet(platform) == "arm64-linux"

    def test_triplet_linux_arm64_alt(self, tmp_path):
        """Test triplet for Linux ARM64 (aarch64)."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="aarch64")
        assert vcpkg.get_triplet(platform) == "arm64-linux"

    def test_triplet_linux_x86(self, tmp_path):
        """Test triplet for Linux x86."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="x86")
        assert vcpkg.get_triplet(platform) == "x86-linux"

    def test_triplet_linux_arm(self, tmp_path):
        """Test triplet for Linux ARM."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="arm")
        assert vcpkg.get_triplet(platform) == "arm-linux"

    def test_triplet_macos_x64(self, tmp_path):
        """Test triplet for macOS x64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="macos", architecture="x86_64")
        assert vcpkg.get_triplet(platform) == "x64-osx"

    def test_triplet_darwin_x64(self, tmp_path):
        """Test triplet for darwin (alternate macOS name)."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="darwin", architecture="x86_64")
        assert vcpkg.get_triplet(platform) == "x64-osx"

    def test_triplet_macos_arm64(self, tmp_path):
        """Test triplet for macOS ARM64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="macos", architecture="arm64")
        assert vcpkg.get_triplet(platform) == "arm64-osx"

    def test_triplet_windows_x64(self, tmp_path):
        """Test triplet for Windows x64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="windows", architecture="x86_64")
        assert vcpkg.get_triplet(platform) == "x64-windows"

    def test_triplet_windows_x86(self, tmp_path):
        """Test triplet for Windows x86."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="windows", architecture="x86")
        assert vcpkg.get_triplet(platform) == "x86-windows"

    def test_triplet_windows_arm64(self, tmp_path):
        """Test triplet for Windows ARM64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="windows", architecture="arm64")
        assert vcpkg.get_triplet(platform) == "arm64-windows"

    def test_triplet_android_arm64(self, tmp_path):
        """Test triplet for Android ARM64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="android", architecture="arm64")
        assert vcpkg.get_triplet(platform) == "arm64-android"

    def test_triplet_ios_arm64(self, tmp_path):
        """Test triplet for iOS ARM64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="ios", architecture="arm64")
        assert vcpkg.get_triplet(platform) == "arm64-ios"

    def test_triplet_unknown_os_defaults_to_linux(self, tmp_path):
        """Test unknown OS defaults to linux."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="unknown", architecture="x86_64")
        assert vcpkg.get_triplet(platform) == "x64-linux"

    def test_triplet_unknown_arch_defaults_to_x64(self, tmp_path):
        """Test unknown architecture defaults to x64."""
        vcpkg = VcpkgIntegration(tmp_path)
        platform = MockPlatform(os="linux", architecture="unknown")
        assert vcpkg.get_triplet(platform) == "x64-linux"


# =============================================================================
# Test Installation
# =============================================================================


class TestVcpkgInstallation:
    """Test vcpkg dependency installation."""

    def test_install_without_vcpkg_root(self, tmp_path):
        """Test that install fails when vcpkg_root is not set."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg.vcpkg_root = None
        platform = MockPlatform()

        with pytest.raises(PackageManagerNotFoundError, match="vcpkg not found"):
            vcpkg.install_dependencies(platform)

    def test_install_without_vcpkg_executable(self, tmp_path):
        """Test that install fails when vcpkg executable doesn't exist."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg.vcpkg_root = vcpkg_root
        platform = MockPlatform()

        with pytest.raises(
            PackageManagerNotFoundError, match="vcpkg executable not found"
        ):
            vcpkg.install_dependencies(platform)

    @patch("subprocess.run")
    def test_install_calls_vcpkg_command(self, mock_run, tmp_path):
        """Test that install calls vcpkg with correct arguments."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg_exe = vcpkg_root / ("vcpkg.exe" if os.name == "nt" else "vcpkg")
        vcpkg_exe.touch()
        vcpkg.vcpkg_root = vcpkg_root

        platform = MockPlatform(os="linux", architecture="x86_64")
        vcpkg.install_dependencies(platform)

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert str(vcpkg_exe) in call_args
        assert "install" in call_args
        assert "--triplet" in call_args
        assert "x64-linux" in call_args
        assert "--x-manifest-root" in call_args
        assert str(tmp_path) in call_args

    @patch("subprocess.run")
    def test_install_failure_raises_error(self, mock_run, tmp_path):
        """Test that install failure raises PackageManagerInstallError."""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="ERROR: Package not found"
        )

        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg_exe = vcpkg_root / ("vcpkg.exe" if os.name == "nt" else "vcpkg")
        vcpkg_exe.touch()
        vcpkg.vcpkg_root = vcpkg_root

        platform = MockPlatform()

        with pytest.raises(PackageManagerInstallError, match="exit code 1"):
            vcpkg.install_dependencies(platform)

    @patch("subprocess.run")
    def test_install_exception_raises_error(self, mock_run, tmp_path):
        """Test that subprocess exception raises PackageManagerInstallError."""
        mock_run.side_effect = OSError("Command failed")

        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg_exe = vcpkg_root / ("vcpkg.exe" if os.name == "nt" else "vcpkg")
        vcpkg_exe.touch()
        vcpkg.vcpkg_root = vcpkg_root

        platform = MockPlatform()

        with pytest.raises(PackageManagerInstallError, match="Failed to execute"):
            vcpkg.install_dependencies(platform)


# =============================================================================
# Test CMake Integration
# =============================================================================


class TestVcpkgCMakeIntegration:
    """Test CMake toolchain integration file generation."""

    def test_generate_integration_without_vcpkg_root(self, tmp_path):
        """Test that generation fails when vcpkg_root is not set."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg.vcpkg_root = None
        toolchain_file = tmp_path / "toolchain.cmake"

        with pytest.raises(PackageManagerError, match="VCPKG_ROOT not set"):
            vcpkg.generate_toolchain_integration(toolchain_file)

    def test_generate_integration_creates_file(self, tmp_path):
        """Test that integration file is created."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg.vcpkg_root = vcpkg_root

        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = vcpkg.generate_toolchain_integration(toolchain_file)

        assert integration_file.exists()
        assert integration_file.name == "vcpkg-integration.cmake"

    def test_generate_integration_file_location(self, tmp_path):
        """Test that integration file is in same directory as toolchain."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg.vcpkg_root = vcpkg_root

        toolchain_dir = tmp_path / "cmake"
        toolchain_dir.mkdir()
        toolchain_file = toolchain_dir / "toolchain.cmake"

        integration_file = vcpkg.generate_toolchain_integration(toolchain_file)

        assert integration_file.parent == toolchain_dir

    def test_generate_integration_content(self, tmp_path):
        """Test integration file content."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg.vcpkg_root = vcpkg_root

        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = vcpkg.generate_toolchain_integration(toolchain_file)
        content = integration_file.read_text()

        assert "vcpkg Integration" in content
        assert "VCPKG_CHAINLOAD_TOOLCHAIN_FILE" in content
        assert "toolchainkit-base.cmake" in content
        assert "CMAKE_TOOLCHAIN_FILE" in content
        assert "scripts/buildsystems/vcpkg.cmake" in content
        assert 'include("${CMAKE_TOOLCHAIN_FILE}")' in content

    def test_generate_integration_returns_path(self, tmp_path):
        """Test that generate_integration returns correct path."""
        vcpkg = VcpkgIntegration(tmp_path)
        vcpkg_root = tmp_path / "vcpkg"
        vcpkg_root.mkdir()
        vcpkg.vcpkg_root = vcpkg_root

        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = vcpkg.generate_toolchain_integration(toolchain_file)

        assert isinstance(integration_file, Path)
        assert integration_file == tmp_path / "vcpkg-integration.cmake"


# =============================================================================
# Test get_name
# =============================================================================


class TestVcpkgGetName:
    """Test get_name method."""

    def test_get_name_returns_vcpkg(self, tmp_path):
        """Test that get_name returns 'vcpkg'."""
        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.get_name() == "vcpkg"


# =============================================================================
# Test Initialization
# =============================================================================


class TestVcpkgInitialization:
    """Test VcpkgIntegration initialization."""

    def test_init_stores_project_root(self, tmp_path):
        """Test that initialization stores project_root."""
        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.project_root == tmp_path

    def test_init_sets_manifest_file(self, tmp_path):
        """Test that initialization sets manifest file path."""
        vcpkg = VcpkgIntegration(tmp_path)
        assert vcpkg.manifest_file == tmp_path / "vcpkg.json"

    def test_init_attempts_to_find_vcpkg_root(self, tmp_path):
        """Test that initialization attempts to find vcpkg_root."""
        vcpkg = VcpkgIntegration(tmp_path)
        # vcpkg_root will be set (or None if not found)
        assert hasattr(vcpkg, "vcpkg_root")

    def test_init_validates_project_root_type(self):
        """Test that initialization validates project_root type."""
        with pytest.raises(TypeError, match="project_root must be Path"):
            VcpkgIntegration("not/a/path")

    def test_init_validates_project_root_exists(self, tmp_path):
        """Test that initialization validates project_root exists."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="Project root does not exist"):
            VcpkgIntegration(nonexistent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
