"""
Unit tests for Conan 2.x package manager integration.

Tests the ConanIntegration class including detection, profile generation,
installation, and CMake integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from toolchainkit.packages.conan import ConanIntegration
from toolchainkit.core.exceptions import (
    PackageManagerNotFoundError,
    PackageManagerInstallError,
    PackageManagerError,
)


# =============================================================================
# Mock Objects for Testing
# =============================================================================


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
# Test ConanIntegration Detection
# =============================================================================


class TestConanDetection:
    """Test Conan manifest file detection."""

    def test_detect_with_conanfile_txt(self, tmp_path):
        """Test detection when conanfile.txt exists."""
        conanfile = tmp_path / "conanfile.txt"
        conanfile.write_text("[requires]\nfmt/9.1.0")

        conan = ConanIntegration(tmp_path)
        assert conan.detect() is True

    def test_detect_with_conanfile_py(self, tmp_path):
        """Test detection when conanfile.py exists."""
        conanfile = tmp_path / "conanfile.py"
        conanfile.write_text("from conan import ConanFile")

        conan = ConanIntegration(tmp_path)
        assert conan.detect() is True

    def test_detect_with_both_files(self, tmp_path):
        """Test detection when both conanfile.txt and conanfile.py exist."""
        (tmp_path / "conanfile.txt").write_text("[requires]")
        (tmp_path / "conanfile.py").write_text("from conan import ConanFile")

        conan = ConanIntegration(tmp_path)
        assert conan.detect() is True

    def test_detect_without_conanfile(self, tmp_path):
        """Test detection when no conanfile exists."""
        conan = ConanIntegration(tmp_path)
        assert conan.detect() is False

    def test_conanfile_paths(self, tmp_path):
        """Test that conanfile paths are set correctly."""
        conan = ConanIntegration(tmp_path)
        assert conan.conanfile_txt == tmp_path / "conanfile.txt"
        assert conan.conanfile_py == tmp_path / "conanfile.py"


# =============================================================================
# Test Platform Mapping
# =============================================================================


class TestConanPlatformMapping:
    """Test platform to Conan settings mapping."""

    def test_os_mapping_linux(self, tmp_path):
        """Test Linux OS mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="linux")
        assert conan._get_conan_os(platform) == "Linux"

    def test_os_mapping_macos(self, tmp_path):
        """Test macOS mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="macos")
        assert conan._get_conan_os(platform) == "Macos"

    def test_os_mapping_darwin(self, tmp_path):
        """Test darwin (alternate macOS name) mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="darwin")
        assert conan._get_conan_os(platform) == "Macos"

    def test_os_mapping_windows(self, tmp_path):
        """Test Windows OS mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="windows")
        assert conan._get_conan_os(platform) == "Windows"

    def test_os_mapping_android(self, tmp_path):
        """Test Android OS mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="android")
        assert conan._get_conan_os(platform) == "Android"

    def test_os_mapping_ios(self, tmp_path):
        """Test iOS OS mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="ios")
        assert conan._get_conan_os(platform) == "iOS"

    def test_os_mapping_unknown(self, tmp_path):
        """Test unknown OS defaults to Linux."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(os="unknown")
        assert conan._get_conan_os(platform) == "Linux"

    def test_arch_mapping_x86_64(self, tmp_path):
        """Test x86_64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="x86_64")
        assert conan._get_conan_arch(platform) == "x86_64"

    def test_arch_mapping_x64(self, tmp_path):
        """Test x64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="x64")
        assert conan._get_conan_arch(platform) == "x86_64"

    def test_arch_mapping_amd64(self, tmp_path):
        """Test amd64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="amd64")
        assert conan._get_conan_arch(platform) == "x86_64"

    def test_arch_mapping_arm64(self, tmp_path):
        """Test arm64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="arm64")
        assert conan._get_conan_arch(platform) == "armv8"

    def test_arch_mapping_aarch64(self, tmp_path):
        """Test aarch64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="aarch64")
        assert conan._get_conan_arch(platform) == "armv8"

    def test_arch_mapping_x86(self, tmp_path):
        """Test x86 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="x86")
        assert conan._get_conan_arch(platform) == "x86"

    def test_arch_mapping_arm(self, tmp_path):
        """Test arm architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="arm")
        assert conan._get_conan_arch(platform) == "armv7"

    def test_arch_mapping_riscv64(self, tmp_path):
        """Test riscv64 architecture mapping."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="riscv64")
        assert conan._get_conan_arch(platform) == "riscv64"

    def test_arch_mapping_unknown(self, tmp_path):
        """Test unknown architecture defaults to x86_64."""
        conan = ConanIntegration(tmp_path)
        platform = MockPlatform(architecture="unknown")
        assert conan._get_conan_arch(platform) == "x86_64"

    def test_compiler_mapping_llvm(self, tmp_path):
        """Test LLVM compiler mapping."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("llvm") == "clang"

    def test_compiler_mapping_clang(self, tmp_path):
        """Test clang compiler mapping."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("clang") == "clang"

    def test_compiler_mapping_gcc(self, tmp_path):
        """Test GCC compiler mapping."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("gcc") == "gcc"

    def test_compiler_mapping_msvc(self, tmp_path):
        """Test MSVC compiler mapping."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("msvc") == "msvc"

    def test_compiler_mapping_apple_clang(self, tmp_path):
        """Test Apple Clang compiler mapping."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("apple-clang") == "apple-clang"

    def test_compiler_mapping_unknown(self, tmp_path):
        """Test unknown compiler defaults to gcc."""
        conan = ConanIntegration(tmp_path)
        assert conan._get_conan_compiler("unknown") == "gcc"


# =============================================================================
# Test Profile Generation
# =============================================================================


class TestConanProfileGeneration:
    """Test Conan profile generation."""

    def test_generate_profile_creates_directory(self, tmp_path):
        """Test that profile generation creates directory."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain()
        platform = MockPlatform()

        profile_path = conan.generate_profile(toolchain, platform)

        assert profile_path.parent.exists()
        assert profile_path.parent == tmp_path / ".toolchainkit" / "conan" / "profiles"

    def test_generate_profile_creates_file(self, tmp_path):
        """Test that profile generation creates profile file."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain()
        platform = MockPlatform()

        profile_path = conan.generate_profile(toolchain, platform)

        assert profile_path.exists()
        assert profile_path.name == "default"

    def test_generate_profile_content_linux_clang(self, tmp_path):
        """Test profile content for Linux with Clang."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="llvm", version="18.1.8")
        platform = MockPlatform(os="linux", architecture="x86_64")

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "os=Linux" in content
        assert "arch=x86_64" in content
        assert "compiler=clang" in content
        assert "compiler.version=18" in content
        assert "compiler.libcxx=libc++" in content
        assert "tools.cmake.cmaketoolchain:generator=Ninja" in content

    def test_generate_profile_content_linux_gcc(self, tmp_path):
        """Test profile content for Linux with GCC."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="gcc", version="13.2.0")
        platform = MockPlatform(os="linux", architecture="x86_64")

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "compiler=gcc" in content
        assert "compiler.version=13" in content
        assert "compiler.libcxx=libstdc++" in content

    def test_generate_profile_content_windows_msvc(self, tmp_path):
        """Test profile content for Windows with MSVC."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="msvc", version="19.38.0")
        platform = MockPlatform(os="windows", architecture="x86_64")

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "os=Windows" in content
        assert "compiler=msvc" in content
        assert "compiler.version=19" in content

    def test_generate_profile_content_macos_arm64(self, tmp_path):
        """Test profile content for macOS ARM64."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="llvm", version="17.0.0")
        platform = MockPlatform(os="macos", architecture="arm64")

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "os=Macos" in content
        assert "arch=armv8" in content
        assert "compiler=clang" in content

    def test_generate_profile_with_libcxx_stdlib(self, tmp_path):
        """Test profile generation with libc++ stdlib."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="llvm", version="18.1.8", stdlib="libc++")
        platform = MockPlatform()

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "compiler.libcxx=libc++" in content

    def test_generate_profile_with_libstdcxx_stdlib(self, tmp_path):
        """Test profile generation with libstdc++ stdlib."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="gcc", version="13.2.0", stdlib="libstdc++")
        platform = MockPlatform()

        profile_path = conan.generate_profile(toolchain, platform)
        content = profile_path.read_text()

        assert "compiler.libcxx=libstdc++" in content

    def test_generate_profile_overwrites_existing(self, tmp_path):
        """Test that profile generation overwrites existing profile."""
        conan = ConanIntegration(tmp_path)
        toolchain = MockToolchain(type="llvm", version="18.1.8")
        platform = MockPlatform()

        # Generate first profile
        profile_path = conan.generate_profile(toolchain, platform)
        first_content = profile_path.read_text()

        # Generate second profile with different toolchain
        toolchain2 = MockToolchain(type="gcc", version="13.2.0")
        profile_path2 = conan.generate_profile(toolchain2, platform)
        second_content = profile_path2.read_text()

        assert profile_path == profile_path2
        assert first_content != second_content
        assert "compiler=gcc" in second_content


# =============================================================================
# Test Installation
# =============================================================================


class TestConanInstallation:
    """Test Conan dependency installation."""

    @patch("shutil.which")
    def test_install_checks_for_conan(self, mock_which, tmp_path):
        """Test that install checks if Conan is installed."""
        mock_which.return_value = None

        conan = ConanIntegration(tmp_path)

        with pytest.raises(PackageManagerNotFoundError, match="Conan not found"):
            conan.install_dependencies()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_creates_build_directory(self, mock_run, mock_which, tmp_path):
        """Test that install creates build directory."""
        mock_which.return_value = "/usr/bin/conan"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        conan = ConanIntegration(tmp_path)
        conan.install_dependencies()

        assert (tmp_path / "build").exists()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_calls_conan_command(self, mock_run, mock_which, tmp_path):
        """Test that install calls conan install with correct arguments."""
        mock_which.return_value = "/usr/bin/conan"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        conan = ConanIntegration(tmp_path)
        profile_path = tmp_path / "profile"
        profile_path.touch()

        conan.install_dependencies(profile_path)

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        # Our enhanced implementation returns the full path from get_conan_executable()
        assert call_args[0] == "/usr/bin/conan" or call_args[0] == "\\usr\\bin\\conan"
        assert call_args[1] == "install"
        assert str(tmp_path) in call_args
        assert "--build=missing" in call_args
        assert "--output-folder" in call_args
        # Changed to --profile:all to set both host and build profiles
        assert "--profile:all" in call_args
        assert str(profile_path) in call_args

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_without_profile(self, mock_run, mock_which, tmp_path):
        """Test install without explicit profile."""
        mock_which.return_value = "/usr/bin/conan"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        conan = ConanIntegration(tmp_path)
        conan.install_dependencies()

        call_args = mock_run.call_args[0][0]
        assert "--profile:all" not in call_args

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_failure_raises_error(self, mock_run, mock_which, tmp_path):
        """Test that install failure raises PackageManagerInstallError."""
        mock_which.return_value = "/usr/bin/conan"
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="ERROR: Package not found"
        )

        conan = ConanIntegration(tmp_path)

        with pytest.raises(PackageManagerInstallError, match="exit code 1"):
            conan.install_dependencies()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_install_exception_raises_error(self, mock_run, mock_which, tmp_path):
        """Test that subprocess exception raises PackageManagerInstallError."""
        mock_which.return_value = "/usr/bin/conan"
        mock_run.side_effect = OSError("Command failed")

        conan = ConanIntegration(tmp_path)

        with pytest.raises(PackageManagerInstallError, match="Failed to execute"):
            conan.install_dependencies()


# =============================================================================
# Test CMake Integration
# =============================================================================


class TestConanCMakeIntegration:
    """Test CMake toolchain integration file generation."""

    def test_generate_integration_creates_file(self, tmp_path):
        """Test that integration file is created."""
        conan = ConanIntegration(tmp_path)
        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = conan.generate_toolchain_integration(toolchain_file)

        assert integration_file.exists()
        assert integration_file.name == "conan-integration.cmake"

    def test_generate_integration_file_location(self, tmp_path):
        """Test that integration file is in same directory as toolchain."""
        conan = ConanIntegration(tmp_path)
        toolchain_dir = tmp_path / "cmake"
        toolchain_dir.mkdir()
        toolchain_file = toolchain_dir / "toolchain.cmake"

        integration_file = conan.generate_toolchain_integration(toolchain_file)

        assert integration_file.parent == toolchain_dir

    def test_generate_integration_content(self, tmp_path):
        """Test integration file content."""
        conan = ConanIntegration(tmp_path)
        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = conan.generate_toolchain_integration(toolchain_file)
        content = integration_file.read_text()

        assert "Conan Integration" in content
        assert "CONAN_TOOLCHAIN_FILE" in content
        assert "build/conan_toolchain.cmake" in content
        assert 'include("${CONAN_TOOLCHAIN_FILE}")' in content
        assert 'message(STATUS "Conan: Using Conan-generated toolchain")' in content
        assert "message(WARNING" in content

    def test_generate_integration_returns_path(self, tmp_path):
        """Test that generate_integration returns correct path."""
        conan = ConanIntegration(tmp_path)
        toolchain_file = tmp_path / "toolchain.cmake"

        integration_file = conan.generate_toolchain_integration(toolchain_file)

        assert isinstance(integration_file, Path)
        assert integration_file == tmp_path / "conan-integration.cmake"


# =============================================================================
# Test get_name
# =============================================================================


class TestConanGetName:
    """Test get_name method."""

    def test_get_name_returns_conan(self, tmp_path):
        """Test that get_name returns 'conan'."""
        conan = ConanIntegration(tmp_path)
        assert conan.get_name() == "conan"


# =============================================================================
# Test Initialization
# =============================================================================


class TestConanInitialization:
    """Test ConanIntegration initialization."""

    def test_init_stores_project_root(self, tmp_path):
        """Test that initialization stores project_root."""
        conan = ConanIntegration(tmp_path)
        assert conan.project_root == tmp_path

    def test_init_sets_conanfile_paths(self, tmp_path):
        """Test that initialization sets conanfile paths."""
        conan = ConanIntegration(tmp_path)
        assert conan.conanfile_txt == tmp_path / "conanfile.txt"
        assert conan.conanfile_py == tmp_path / "conanfile.py"

    def test_init_validates_project_root_type(self):
        """Test that initialization validates project_root type."""
        with pytest.raises(TypeError, match="project_root must be Path"):
            ConanIntegration("not/a/path")

    def test_init_validates_project_root_exists(self, tmp_path):
        """Test that initialization validates project_root exists."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="Project root does not exist"):
            ConanIntegration(nonexistent)


class TestConanAdditionalCoverage:
    """Additional coverage tests for Conan integration."""

    def test_generate_profile_stdlib_variants(self, tmp_path):
        """Test generate_profile with different stdlib configurations."""
        conan = ConanIntegration(tmp_path)
        platform = Mock(os="linux", architecture="x86_64")

        # Test libc++
        toolchain_libcxx = Mock(type="llvm", version="18.0", stdlib="libc++")
        profile = conan.generate_profile(toolchain_libcxx, platform)
        assert "compiler.libcxx=libc++" in profile.read_text()

        # Test libstdc++
        toolchain_libstdcxx = Mock(type="gcc", version="13.0", stdlib="libstdc++")
        profile = conan.generate_profile(toolchain_libstdcxx, platform)
        assert "compiler.libcxx=libstdc++" in profile.read_text()

        # Test unknown/other stdlib with clang -> libc++
        toolchain_other_clang = Mock(type="clang", version="18.0", stdlib="custom")
        profile = conan.generate_profile(toolchain_other_clang, platform)
        assert "compiler.libcxx=libc++" in profile.read_text()

        # Test unknown/other stdlib with gcc -> libstdc++
        toolchain_other_gcc = Mock(type="gcc", version="13.0", stdlib="custom")
        profile = conan.generate_profile(toolchain_other_gcc, platform)
        assert "compiler.libcxx=libstdc++" in profile.read_text()

    def test_generate_profile_write_exception(self, tmp_path):
        """Test generate_profile write exception."""
        conan = ConanIntegration(tmp_path)
        toolchain = Mock(type="llvm", version="18.0", stdlib=None)
        platform = Mock(os="linux", architecture="x86_64")

        # Mock Path.write_text to raise exception
        with patch("pathlib.Path.write_text", side_effect=IOError("Write failed")):
            with pytest.raises(
                PackageManagerError, match="Failed to write Conan profile"
            ):
                conan.generate_profile(toolchain, platform)

    def test_generate_toolchain_integration_write_exception(self, tmp_path):
        """Test generate_toolchain_integration write exception."""
        conan = ConanIntegration(tmp_path)
        toolchain_file = tmp_path / "toolchain.cmake"

        # Mock Path.write_text to raise exception
        with patch("pathlib.Path.write_text", side_effect=IOError("Write failed")):
            with pytest.raises(
                PackageManagerError, match="Failed to write Conan integration"
            ):
                conan.generate_toolchain_integration(toolchain_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
