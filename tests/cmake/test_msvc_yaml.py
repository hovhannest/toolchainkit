"""
Tests for MSVC YAML compiler configuration.

Validates that the MSVC compiler YAML definition works correctly.
"""

import pytest
from pathlib import Path

from toolchainkit.cmake.yaml_compiler import (
    YAMLCompilerLoader,
)


@pytest.fixture
def yaml_loader():
    """Create a YAML compiler loader pointing to production compilers directory."""
    data_dir = Path(__file__).parent.parent.parent / "toolchainkit" / "data"
    return YAMLCompilerLoader(data_dir)


@pytest.fixture
def msvc_windows(yaml_loader):
    """Load MSVC configuration for Windows platform."""
    return yaml_loader.load("msvc", platform="windows")


class TestMSVCYAMLLoader:
    """Test loading MSVC YAML configuration."""

    def test_msvc_loads_successfully(self, yaml_loader):
        """Test that msvc.yaml can be loaded."""
        config = yaml_loader.load("msvc")
        assert config is not None
        assert config.name == "msvc"

    def test_msvc_available_in_list(self, yaml_loader):
        """Test that msvc appears in available compilers list."""
        available = yaml_loader.list_available()
        assert "msvc" in available

    def test_msvc_windows_platform(self, yaml_loader):
        """Test MSVC loads correctly with Windows platform."""
        config = yaml_loader.load("msvc", platform="windows")
        assert config is not None
        cmake_vars = config.get_cmake_variables()
        assert "cl.exe" in cmake_vars.get("CMAKE_CXX_COMPILER", "")


class TestMSVCBuildTypes:
    """Test MSVC build type flags."""

    def test_debug_flags(self, msvc_windows):
        """Test Debug build type flags."""
        flags = msvc_windows.get_flags_for_build_type("debug")
        assert flags is not None
        assert "/MDd" in flags  # Multithreaded debug DLL
        assert "/Zi" in flags  # Debug info
        assert "/Od" in flags  # Disable optimization
        assert "/RTC1" in flags  # Runtime checks

    def test_release_flags(self, msvc_windows):
        """Test Release build type flags."""
        flags = msvc_windows.get_flags_for_build_type("release")
        assert flags is not None
        assert "/MD" in flags  # Multithreaded release DLL
        assert "/O2" in flags  # Maximize speed
        assert "/DNDEBUG" in flags
        assert "/GL" in flags  # Whole program optimization

    def test_relwithdebinfo_flags(self, msvc_windows):
        """Test RelWithDebInfo build type flags."""
        flags = msvc_windows.get_flags_for_build_type("relwithdebinfo")
        assert flags is not None
        assert "/MD" in flags
        assert "/Zi" in flags
        assert "/O2" in flags
        assert "/DNDEBUG" in flags

    def test_minsizerel_flags(self, msvc_windows):
        """Test MinSizeRel build type flags."""
        flags = msvc_windows.get_flags_for_build_type("minsizerel")
        assert flags is not None
        assert "/MD" in flags
        assert "/O1" in flags  # Minimize size
        assert "/DNDEBUG" in flags


class TestMSVCWarnings:
    """Test MSVC warning level flags."""

    def test_off_warnings(self, msvc_windows):
        """Test 'off' warning level."""
        flags = msvc_windows.get_warning_flags("off")
        assert flags is not None
        assert "/w" in flags

    def test_basic_warnings(self, msvc_windows):
        """Test 'basic' warning level."""
        flags = msvc_windows.get_warning_flags("basic")
        assert flags is not None
        assert "/W3" in flags

    def test_extra_warnings(self, msvc_windows):
        """Test 'extra' warning level."""
        flags = msvc_windows.get_warning_flags("extra")
        assert flags is not None
        assert "/W4" in flags

    def test_strict_warnings(self, msvc_windows):
        """Test 'strict' warning level."""
        flags = msvc_windows.get_warning_flags("strict")
        assert flags is not None
        assert "/W4" in flags
        assert "/permissive-" in flags

    def test_pedantic_warnings(self, msvc_windows):
        """Test 'pedantic' warning level."""
        flags = msvc_windows.get_warning_flags("pedantic")
        assert flags is not None
        assert "/Wall" in flags
        assert "/permissive-" in flags

    def test_error_warnings(self, msvc_windows):
        """Test 'error' warning level."""
        flags = msvc_windows.get_warning_flags("error")
        assert flags is not None
        assert "/WX" in flags


class TestMSVCStandardLibrary:
    """Test MSVC standard library configuration."""

    def test_msvc_stdlib(self, msvc_windows):
        """Test MSVC standard library (built-in)."""
        flags = msvc_windows.get_stdlib_flags("msvc")
        assert flags is not None
        # MSVC stdlib is built-in, no special flags
        compile_flags = flags.get("compile_flags", [])
        assert isinstance(compile_flags, list)


class TestMSVCLinker:
    """Test MSVC linker configuration."""

    def test_link_linker(self, msvc_windows):
        """Test link.exe linker flag."""
        flag = msvc_windows.get_linker_flag("link")
        assert flag is not None
        assert flag == "/link"


class TestMSVCSanitizers:
    """Test MSVC sanitizer configuration."""

    def test_address_sanitizer(self, msvc_windows):
        """Test AddressSanitizer flags (VS 2019 16.9+)."""
        flags = msvc_windows.get_sanitizer_flags("address")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "/fsanitize=address" in compile_flags


class TestMSVCLTO:
    """Test MSVC link-time code generation (LTCG)."""

    def test_full_lto(self, msvc_windows):
        """Test LTCG flags."""
        flags = msvc_windows.get_lto_flags("full")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        link_flags = flags.get("link_flags", [])
        assert "/GL" in compile_flags  # Whole program optimization
        assert "/LTCG" in link_flags  # Link-time code generation


class TestMSVCCoverage:
    """Test MSVC code coverage configuration."""

    def test_coverage_flags(self, msvc_windows):
        """Test code coverage flags (MSVC requires external tools)."""
        flags = msvc_windows.get_coverage_flags()
        assert flags is not None
        # MSVC doesn't have built-in coverage, returns empty
        assert isinstance(flags, list)


class TestMSVCCMakeVariables:
    """Test MSVC CMake variable generation."""

    def test_cmake_variables(self, msvc_windows):
        """Test CMake variables for MSVC."""
        vars = msvc_windows.get_cmake_variables()
        assert vars is not None
        assert "CMAKE_C_COMPILER" in vars
        assert "CMAKE_CXX_COMPILER" in vars
        assert "cl.exe" in vars["CMAKE_C_COMPILER"]
        assert "cl.exe" in vars["CMAKE_CXX_COMPILER"]
        assert "lib.exe" in vars["CMAKE_AR"]
        assert "link.exe" in vars["CMAKE_LINKER"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
