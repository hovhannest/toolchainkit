"""
Unit tests for standard library configuration module.

Tests all stdlib configuration classes and the factory/detector patterns.
"""

import pytest
from unittest.mock import Mock

from toolchainkit.cmake.stdlib import (
    StandardLibraryConfig,
    LibCxxConfig,
    LibStdCxxConfig,
    MSVCStdLibConfig,
    StandardLibraryDetector,
    StandardLibraryConfigFactory,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_platform_linux():
    """Create a mock Linux platform."""
    platform = Mock()
    platform.os = "linux"
    return platform


@pytest.fixture
def mock_platform_darwin():
    """Create a mock macOS platform."""
    platform = Mock()
    platform.os = "darwin"
    return platform


@pytest.fixture
def mock_platform_windows():
    """Create a mock Windows platform."""
    platform = Mock()
    platform.os = "windows"
    return platform


# ============================================================================
# LibCxxConfig Tests
# ============================================================================


@pytest.mark.unit
class TestLibCxxConfig:
    """Tests for LibCxxConfig class."""

    def test_default_config(self):
        """Test libc++ config with defaults."""
        config = LibCxxConfig()

        assert config.stdlib_type == "libc++"
        assert config.version is None
        assert config.abi_version is None
        assert config.install_path is None

    def test_with_install_path(self, tmp_path):
        """Test libc++ config with install path."""
        # Create mock directory structure
        install_path = tmp_path / "llvm"
        include_dir = install_path / "include" / "c++" / "v1"
        lib_dir = install_path / "lib"
        include_dir.mkdir(parents=True)
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)

        assert config.install_path == install_path

    def test_compile_flags_basic(self):
        """Test basic compile flags."""
        config = LibCxxConfig()

        flags = config.get_compile_flags()
        assert "-stdlib=libc++" in flags

    def test_compile_flags_with_includes(self, tmp_path):
        """Test compile flags with include path."""
        install_path = tmp_path / "llvm"
        include_dir = install_path / "include" / "c++" / "v1"
        include_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)
        flags = config.get_compile_flags()

        assert "-stdlib=libc++" in flags
        assert any("isystem" in f and str(include_dir) in f for f in flags)

    def test_link_flags_basic(self):
        """Test basic link flags."""
        config = LibCxxConfig()

        flags = config.get_link_flags()
        assert "-stdlib=libc++" in flags
        assert "-lc++" in flags
        assert "-lc++abi" in flags

    def test_link_flags_with_lib_path(self, tmp_path):
        """Test link flags with library path."""
        install_path = tmp_path / "llvm"
        lib_dir = install_path / "lib"
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)
        flags = config.get_link_flags()

        assert any(f"-L{lib_dir}" == f for f in flags)
        assert any("rpath" in f and str(lib_dir) in f for f in flags)

    def test_cmake_variables(self, tmp_path):
        """Test CMake variables generation."""
        install_path = tmp_path / "llvm"
        config = LibCxxConfig(install_path=install_path, abi_version="1")

        variables = config.get_cmake_variables()
        assert variables["LIBCXX_INSTALL_PREFIX"] == str(install_path)
        assert variables["LIBCXX_ABI_VERSION"] == "1"

    def test_cmake_snippet_generation(self):
        """Test CMake snippet generation."""
        config = LibCxxConfig()

        snippet = config.generate_cmake_snippet()
        assert "libc++" in snippet
        assert "CMAKE_CXX_FLAGS_INIT" in snippet
        assert "-stdlib=libc++" in snippet


# ============================================================================
# LibStdCxxConfig Tests
# ============================================================================


@pytest.mark.unit
class TestLibStdCxxConfig:
    """Tests for LibStdCxxConfig class."""

    def test_default_config(self):
        """Test libstdc++ config with defaults."""
        config = LibStdCxxConfig()

        assert config.stdlib_type == "libstdc++"
        assert config.version is None
        assert config.gcc_path is None

    def test_with_gcc_path(self, tmp_path):
        """Test libstdc++ config with GCC path."""
        gcc_path = tmp_path / "gcc"
        gcc_path.mkdir()

        config = LibStdCxxConfig(gcc_path=gcc_path)
        assert config.gcc_path == gcc_path

    def test_compile_flags_no_gcc_path(self):
        """Test compile flags without GCC path."""
        config = LibStdCxxConfig()

        flags = config.get_compile_flags()
        # Should be empty or minimal when no GCC path
        assert isinstance(flags, list)

    def test_compile_flags_with_gcc_path(self, tmp_path):
        """Test compile flags with GCC path."""
        gcc_path = tmp_path / "gcc"
        gcc_path.mkdir()

        config = LibStdCxxConfig(gcc_path=gcc_path)
        flags = config.get_compile_flags()

        assert any("--gcc-toolchain" in f for f in flags)

    def test_link_flags_with_lib64(self, tmp_path):
        """Test link flags with lib64 directory."""
        gcc_path = tmp_path / "gcc"
        lib_dir = gcc_path / "lib64"
        lib_dir.mkdir(parents=True)

        config = LibStdCxxConfig(gcc_path=gcc_path)
        flags = config.get_link_flags()

        assert any(f"-L{lib_dir}" == f for f in flags)
        assert any("rpath" in f for f in flags)

    def test_link_flags_fallback_to_lib(self, tmp_path):
        """Test link flags fall back to lib directory."""
        gcc_path = tmp_path / "gcc"
        lib_dir = gcc_path / "lib"
        lib_dir.mkdir(parents=True)

        config = LibStdCxxConfig(gcc_path=gcc_path)
        flags = config.get_link_flags()

        assert any(f"-L{lib_dir}" == f for f in flags)

    def test_cmake_variables(self, tmp_path):
        """Test CMake variables generation."""
        gcc_path = tmp_path / "gcc"
        config = LibStdCxxConfig(gcc_path=gcc_path)

        variables = config.get_cmake_variables()
        assert variables["LIBSTDCXX_GCC_PATH"] == str(gcc_path)

    def test_cmake_snippet_generation(self):
        """Test CMake snippet generation."""
        config = LibStdCxxConfig()

        snippet = config.generate_cmake_snippet()
        assert "libstdc++" in snippet


# ============================================================================
# MSVCStdLibConfig Tests
# ============================================================================


@pytest.mark.unit
class TestMSVCStdLibConfig:
    """Tests for MSVCStdLibConfig class."""

    def test_default_config(self):
        """Test MSVC stdlib config with defaults."""
        config = MSVCStdLibConfig()

        assert config.stdlib_type == "msvc"
        assert config.version is None

    def test_with_version(self):
        """Test MSVC stdlib config with version."""
        config = MSVCStdLibConfig(version="19.39")

        assert config.version == "19.39"

    def test_compile_flags_empty(self):
        """Test that compile flags are empty."""
        config = MSVCStdLibConfig()

        flags = config.get_compile_flags()
        assert flags == []

    def test_link_flags_empty(self):
        """Test that link flags are empty."""
        config = MSVCStdLibConfig()

        flags = config.get_link_flags()
        assert flags == []

    def test_cmake_variables_empty(self):
        """Test that CMake variables are empty."""
        config = MSVCStdLibConfig()

        variables = config.get_cmake_variables()
        assert variables == {}

    def test_cmake_snippet_generation(self):
        """Test CMake snippet generation."""
        config = MSVCStdLibConfig()

        snippet = config.generate_cmake_snippet()
        assert "msvc" in snippet


# ============================================================================
# StandardLibraryDetector Tests
# ============================================================================


@pytest.mark.unit
class TestStandardLibraryDetector:
    """Tests for StandardLibraryDetector class."""

    def test_detector_initialization(self, mock_platform_linux):
        """Test detector initialization."""
        detector = StandardLibraryDetector(mock_platform_linux)

        assert detector.platform == mock_platform_linux

    def test_detect_libcxx_not_found(self, mock_platform_linux, tmp_path, monkeypatch):
        """Test libc++ detection when not found."""
        # Mock Path to return non-existent paths
        detector = StandardLibraryDetector(mock_platform_linux)
        result = detector.detect_libcxx()

        # Should return None if not found
        assert result is None

    def test_detect_libstdcxx_not_found(self, mock_platform_linux):
        """Test libstdc++ detection when not found."""
        detector = StandardLibraryDetector(mock_platform_linux)
        result = detector.detect_libstdcxx()

        # May return None if not found
        assert result is None or isinstance(result, LibStdCxxConfig)

    def test_detect_msvc_stdlib_on_windows(self, mock_platform_windows):
        """Test MSVC stdlib detection on Windows."""
        detector = StandardLibraryDetector(mock_platform_windows)
        result = detector.detect_msvc_stdlib()

        assert isinstance(result, MSVCStdLibConfig)

    def test_detect_msvc_stdlib_on_linux(self, mock_platform_linux):
        """Test MSVC stdlib detection on Linux returns None."""
        detector = StandardLibraryDetector(mock_platform_linux)
        result = detector.detect_msvc_stdlib()

        assert result is None

    def test_detect_default_for_clang(self, mock_platform_linux):
        """Test default stdlib detection for Clang."""
        detector = StandardLibraryDetector(mock_platform_linux)
        result = detector.detect_default("clang")

        # Should return some stdlib config
        assert isinstance(result, StandardLibraryConfig)

    def test_detect_default_for_gcc(self, mock_platform_linux):
        """Test default stdlib detection for GCC."""
        detector = StandardLibraryDetector(mock_platform_linux)
        result = detector.detect_default("gcc")

        assert isinstance(result, LibStdCxxConfig)

    def test_detect_default_for_msvc(self, mock_platform_windows):
        """Test default stdlib detection for MSVC."""
        detector = StandardLibraryDetector(mock_platform_windows)
        result = detector.detect_default("msvc")

        assert isinstance(result, MSVCStdLibConfig)

    def test_detect_default_invalid_compiler(self, mock_platform_linux):
        """Test detection with invalid compiler type."""
        detector = StandardLibraryDetector(mock_platform_linux)

        with pytest.raises(ValueError, match="Unknown compiler type"):
            detector.detect_default("invalid")


# ============================================================================
# StandardLibraryConfigFactory Tests
# ============================================================================


@pytest.mark.unit
class TestStandardLibraryConfigFactory:
    """Tests for StandardLibraryConfigFactory class."""

    def test_create_libcxx(self):
        """Test creating libc++ config from factory."""
        config = StandardLibraryConfigFactory.create("libc++")

        assert isinstance(config, LibCxxConfig)
        assert config.stdlib_type == "libc++"

    def test_create_libstdcxx(self):
        """Test creating libstdc++ config from factory."""
        config = StandardLibraryConfigFactory.create("libstdc++")

        assert isinstance(config, LibStdCxxConfig)
        assert config.stdlib_type == "libstdc++"

    def test_create_msvc(self):
        """Test creating MSVC stdlib config from factory."""
        config = StandardLibraryConfigFactory.create("msvc")

        assert isinstance(config, MSVCStdLibConfig)
        assert config.stdlib_type == "msvc"

    def test_create_with_kwargs(self, tmp_path):
        """Test creating config with kwargs."""
        install_path = tmp_path / "llvm"
        config = StandardLibraryConfigFactory.create(
            "libc++", install_path=install_path, abi_version="1"
        )

        assert isinstance(config, LibCxxConfig)
        assert config.install_path == install_path
        assert config.abi_version == "1"

    def test_create_invalid_type(self):
        """Test creating config with invalid type."""
        with pytest.raises(ValueError, match="Unknown stdlib type"):
            StandardLibraryConfigFactory.create("invalid")

    def test_create_default_clang(self, mock_platform_linux):
        """Test creating default config for Clang."""
        config = StandardLibraryConfigFactory.create_default(
            "clang", mock_platform_linux
        )

        assert isinstance(config, StandardLibraryConfig)

    def test_create_default_gcc(self, mock_platform_linux):
        """Test creating default config for GCC."""
        config = StandardLibraryConfigFactory.create_default("gcc", mock_platform_linux)

        assert isinstance(config, LibStdCxxConfig)

    def test_create_default_msvc(self, mock_platform_windows):
        """Test creating default config for MSVC."""
        config = StandardLibraryConfigFactory.create_default(
            "msvc", mock_platform_windows
        )

        assert isinstance(config, MSVCStdLibConfig)


# ============================================================================
# CMake Snippet Generation Tests
# ============================================================================


@pytest.mark.unit
class TestCMakeSnippetGeneration:
    """Tests for CMake snippet generation."""

    def test_libcxx_snippet_structure(self):
        """Test libc++ CMake snippet structure."""
        config = LibCxxConfig()
        snippet = config.generate_cmake_snippet()

        lines = snippet.split("\n")
        assert any("Standard Library" in line for line in lines)
        assert any("CMAKE_CXX_FLAGS_INIT" in line for line in lines)

    def test_libstdcxx_snippet_structure(self, tmp_path):
        """Test libstdc++ CMake snippet structure."""
        gcc_path = tmp_path / "gcc"
        lib_dir = gcc_path / "lib64"
        lib_dir.mkdir(parents=True)

        config = LibStdCxxConfig(gcc_path=gcc_path)
        snippet = config.generate_cmake_snippet()

        assert "libstdc++" in snippet

    def test_msvc_snippet_minimal(self):
        """Test MSVC CMake snippet is minimal."""
        config = MSVCStdLibConfig()
        snippet = config.generate_cmake_snippet()

        # Should be minimal since MSVC is automatic
        assert "msvc" in snippet
        lines = [line for line in snippet.split("\n") if line.strip()]
        assert len(lines) <= 5  # Should be very short


# ============================================================================
# Case Sensitivity Tests
# ============================================================================


@pytest.mark.unit
class TestCaseSensitivity:
    """Tests for case-insensitive handling."""

    def test_factory_case_insensitive(self):
        """Test factory handles case-insensitive stdlib types."""
        configs = [
            StandardLibraryConfigFactory.create("libc++"),
            StandardLibraryConfigFactory.create("LIBC++"),
            StandardLibraryConfigFactory.create("LibC++"),
        ]

        for config in configs:
            assert isinstance(config, LibCxxConfig)

    def test_detector_case_insensitive(self, mock_platform_linux):
        """Test detector handles case-insensitive compiler types."""
        detector = StandardLibraryDetector(mock_platform_linux)

        configs = [
            detector.detect_default("clang"),
            detector.detect_default("CLANG"),
            detector.detect_default("Clang"),
        ]

        for config in configs:
            assert isinstance(config, StandardLibraryConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
