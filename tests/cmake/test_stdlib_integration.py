"""
Integration tests for standard library configuration module.

Tests integration between stdlib configurations and real-world usage scenarios.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from toolchainkit.cmake.stdlib import (
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
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def mock_platform():
    """Create a mock platform object."""
    platform = Mock()
    platform.os = "linux"
    return platform


# ============================================================================
# Real-World Scenario Tests
# ============================================================================


@pytest.mark.integration
class TestRealWorldScenarios:
    """Tests for real-world usage scenarios."""

    def test_libcxx_with_custom_path(self, temp_dir):
        """Test libc++ configuration with custom installation path."""
        # Create mock LLVM directory structure
        install_path = temp_dir / "llvm-18.1.8"
        include_dir = install_path / "include" / "c++" / "v1"
        lib_dir = install_path / "lib"
        include_dir.mkdir(parents=True)
        lib_dir.mkdir(parents=True)

        # Create configuration
        config = LibCxxConfig(version="18.1.8", install_path=install_path)

        # Verify flags
        compile_flags = config.get_compile_flags()
        link_flags = config.get_link_flags()

        assert "-stdlib=libc++" in compile_flags
        assert any(str(include_dir) in f for f in compile_flags)
        assert any(str(lib_dir) in f for f in link_flags)
        assert any("rpath" in f for f in link_flags)

    def test_libstdcxx_with_gcc_toolchain(self, temp_dir):
        """Test libstdc++ configuration with GCC toolchain."""
        # Create mock GCC directory structure
        gcc_path = temp_dir / "gcc-13.2.0"
        lib_dir = gcc_path / "lib64"
        lib_dir.mkdir(parents=True)

        # Create configuration
        config = LibStdCxxConfig(version="13.2.0", gcc_path=gcc_path)

        # Verify flags
        compile_flags = config.get_compile_flags()
        link_flags = config.get_link_flags()

        assert any("--gcc-toolchain" in f for f in compile_flags)
        assert any(str(lib_dir) in f for f in link_flags)

    def test_msvc_stdlib_configuration(self):
        """Test MSVC standard library configuration."""
        config = MSVCStdLibConfig(version="19.39")

        # MSVC should have no explicit flags
        assert config.get_compile_flags() == []
        assert config.get_link_flags() == []

        # But should generate valid CMake snippet
        snippet = config.generate_cmake_snippet()
        assert "msvc" in snippet

    def test_cmake_snippet_integration(self, temp_dir):
        """Test CMake snippet generation and file writing."""
        install_path = temp_dir / "llvm"
        include_dir = install_path / "include" / "c++" / "v1"
        lib_dir = install_path / "lib"
        include_dir.mkdir(parents=True)
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)

        # Generate and write snippet
        snippet = config.generate_cmake_snippet()
        cmake_file = temp_dir / "stdlib.cmake"
        cmake_file.write_text(snippet)

        # Verify file was created and is readable
        assert cmake_file.exists()
        content = cmake_file.read_text()
        assert "libc++" in content
        assert "CMAKE_CXX_FLAGS_INIT" in content

    def test_factory_pattern_usage(self, temp_dir):
        """Test using factory pattern to create configs."""
        install_path = temp_dir / "llvm"

        # Create configs via factory
        libcxx_config = StandardLibraryConfigFactory.create(
            "libc++", install_path=install_path
        )

        libstdcxx_config = StandardLibraryConfigFactory.create(
            "libstdc++", version="13.2.0"
        )

        msvc_config = StandardLibraryConfigFactory.create("msvc")

        # Verify correct types
        assert isinstance(libcxx_config, LibCxxConfig)
        assert isinstance(libstdcxx_config, LibStdCxxConfig)
        assert isinstance(msvc_config, MSVCStdLibConfig)

        # Verify all can generate CMake snippets
        assert libcxx_config.generate_cmake_snippet()
        assert libstdcxx_config.generate_cmake_snippet()
        assert msvc_config.generate_cmake_snippet()

    def test_multiple_stdlib_configs(self, temp_dir):
        """Test creating multiple stdlib configurations."""
        # Create different configurations
        configs = {
            "libc++": LibCxxConfig(),
            "libstdc++": LibStdCxxConfig(),
            "msvc": MSVCStdLibConfig(),
        }

        # Generate snippets for each
        snippets = {}
        for name, config in configs.items():
            snippet = config.generate_cmake_snippet()
            snippets[name] = snippet

            # Write to file
            file_path = temp_dir / f"stdlib_{name}.cmake"
            file_path.write_text(snippet)

        # Verify all files created
        assert len(list(temp_dir.glob("stdlib_*.cmake"))) == 3

    def test_clang_with_libstdcxx_crosscompile(self, temp_dir):
        """Test Clang using libstdc++ (common on Linux)."""
        # Create GCC installation
        gcc_path = temp_dir / "gcc"
        lib_dir = gcc_path / "lib64"
        lib_dir.mkdir(parents=True)

        # Configure for Clang + libstdc++
        config = LibStdCxxConfig(gcc_path=gcc_path)

        compile_flags = config.get_compile_flags()
        link_flags = config.get_link_flags()

        # Should have GCC toolchain flag for Clang
        assert any("--gcc-toolchain" in f for f in compile_flags)

        # Should have library path
        assert any(str(lib_dir) in f for f in link_flags)


# ============================================================================
# Detection Tests
# ============================================================================


@pytest.mark.integration
class TestStdlibDetection:
    """Tests for stdlib detection on real systems."""

    def test_detector_with_mock_platform(self, mock_platform):
        """Test detector with mock platform."""
        detector = StandardLibraryDetector(mock_platform)

        # Should not crash
        result = detector.detect_libcxx()
        assert result is None or isinstance(result, LibCxxConfig)

    def test_detect_default_stdlib_clang(self, mock_platform):
        """Test detecting default stdlib for Clang."""
        detector = StandardLibraryDetector(mock_platform)

        config = detector.detect_default("clang")
        assert config is not None
        assert isinstance(config, (LibCxxConfig, LibStdCxxConfig))

    def test_detect_default_stdlib_gcc(self, mock_platform):
        """Test detecting default stdlib for GCC."""
        detector = StandardLibraryDetector(mock_platform)

        config = detector.detect_default("gcc")
        assert config is not None
        assert isinstance(config, LibStdCxxConfig)

    def test_factory_create_default(self, mock_platform):
        """Test factory create_default method."""
        config = StandardLibraryConfigFactory.create_default("clang", mock_platform)

        assert config is not None
        assert isinstance(config, (LibCxxConfig, LibStdCxxConfig))


# ============================================================================
# CMake Integration Tests
# ============================================================================


@pytest.mark.integration
class TestCMakeIntegration:
    """Tests for CMake integration."""

    def test_cmake_snippet_valid_syntax(self, temp_dir):
        """Test that generated CMake snippets have valid syntax."""
        configs = [
            LibCxxConfig(),
            LibStdCxxConfig(),
            MSVCStdLibConfig(),
        ]

        for config in configs:
            snippet = config.generate_cmake_snippet()

            # Write to file
            cmake_file = temp_dir / f"test_{config.stdlib_type}.cmake"
            cmake_file.write_text(snippet)

            # Verify file is readable
            assert cmake_file.exists()
            content = cmake_file.read_text()

            # Check for basic CMake syntax elements
            if config.get_compile_flags():
                assert "CMAKE_CXX_FLAGS_INIT" in content
            if config.get_link_flags():
                assert (
                    "CMAKE_EXE_LINKER_FLAGS_INIT" in content
                    or "CMAKE_SHARED_LINKER_FLAGS_INIT" in content
                )

    def test_cmake_variables_in_snippet(self, temp_dir):
        """Test that CMake variables are included in snippet."""
        install_path = temp_dir / "llvm"
        config = LibCxxConfig(install_path=install_path, abi_version="1")

        snippet = config.generate_cmake_snippet()

        # Check for CMake set() commands
        assert "set(LIBCXX_INSTALL_PREFIX" in snippet
        assert "set(LIBCXX_ABI_VERSION" in snippet

    def test_flag_quoting_in_cmake(self, temp_dir):
        """Test that flags are properly formatted for CMake."""
        install_path = temp_dir / "llvm"
        include_dir = install_path / "include" / "c++" / "v1"
        lib_dir = install_path / "lib"
        include_dir.mkdir(parents=True)
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)
        snippet = config.generate_cmake_snippet()

        # Flags should be in string(APPEND ...) commands
        assert "string(APPEND CMAKE_CXX_FLAGS_INIT" in snippet


# ============================================================================
# Cross-Platform Tests
# ============================================================================


@pytest.mark.integration
class TestCrossPlatform:
    """Tests for cross-platform compatibility."""

    def test_path_handling_unix_style(self, temp_dir):
        """Test path handling with Unix-style paths."""
        install_path = temp_dir / "opt" / "llvm"
        lib_dir = install_path / "lib"
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)
        link_flags = config.get_link_flags()

        # Paths should be preserved
        assert any(str(lib_dir) in f for f in link_flags)

    def test_path_handling_windows_style(self, temp_dir):
        """Test path handling with Windows-style paths."""
        # Use Windows-style path
        install_path = temp_dir / "Program Files" / "LLVM"
        lib_dir = install_path / "lib"
        lib_dir.mkdir(parents=True)

        config = LibCxxConfig(install_path=install_path)
        link_flags = config.get_link_flags()

        # Paths should work with spaces
        assert any("lib" in f for f in link_flags)

    def test_platform_specific_detection(self):
        """Test platform-specific detection logic."""
        platforms = [
            Mock(os="linux"),
            Mock(os="darwin"),
            Mock(os="windows"),
        ]

        for platform in platforms:
            detector = StandardLibraryDetector(platform)

            # Should not crash on any platform
            result = detector.detect_libcxx()
            assert result is None or isinstance(result, LibCxxConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
