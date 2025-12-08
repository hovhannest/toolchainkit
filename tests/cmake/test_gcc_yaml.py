"""
Tests for GCC YAML compiler configuration.

Validates that the GCC compiler YAML definition works correctly.
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
def gcc_linux(yaml_loader):
    """Load GCC configuration for Linux platform."""
    return yaml_loader.load("gcc", platform="linux")


@pytest.fixture
def gcc_windows(yaml_loader):
    """Load GCC configuration for Windows platform (MinGW)."""
    return yaml_loader.load("gcc", platform="windows")


@pytest.fixture
def gcc_macos(yaml_loader):
    """Load GCC configuration for macOS platform."""
    return yaml_loader.load("gcc", platform="macos")


class TestGCCYAMLLoader:
    """Test loading GCC YAML configuration."""

    def test_gcc_loads_successfully(self, yaml_loader):
        """Test that gcc.yaml can be loaded."""
        config = yaml_loader.load("gcc")
        assert config is not None
        assert config.name == "gcc"

    def test_gcc_available_in_list(self, yaml_loader):
        """Test that gcc appears in available compilers list."""
        available = yaml_loader.list_available()
        assert "gcc" in available

    def test_gcc_linux_platform(self, yaml_loader):
        """Test GCC loads correctly with Linux platform."""
        config = yaml_loader.load("gcc", platform="linux")
        assert config is not None
        cmake_vars = config.get_cmake_variables(toolchain_root="/usr")
        assert "gcc" in cmake_vars.get("CMAKE_C_COMPILER", "")
        assert "g++" in cmake_vars.get("CMAKE_CXX_COMPILER", "")

    def test_gcc_windows_platform(self, yaml_loader):
        """Test GCC loads correctly with Windows platform (MinGW)."""
        config = yaml_loader.load("gcc", platform="windows")
        assert config is not None
        cmake_vars = config.get_cmake_variables(toolchain_root="C:/mingw64")
        assert "gcc.exe" in cmake_vars.get("CMAKE_C_COMPILER", "")
        assert "g++.exe" in cmake_vars.get("CMAKE_CXX_COMPILER", "")


class TestGCCBuildTypes:
    """Test GCC build type flags."""

    def test_debug_flags(self, gcc_linux):
        """Test Debug build type flags."""
        flags = gcc_linux.get_flags_for_build_type("debug")
        assert flags is not None
        assert "-g" in flags
        assert "-O0" in flags
        assert "-fno-omit-frame-pointer" in flags

    def test_release_flags(self, gcc_linux):
        """Test Release build type flags."""
        flags = gcc_linux.get_flags_for_build_type("release")
        assert flags is not None
        assert "-O3" in flags
        assert "-DNDEBUG" in flags

    def test_relwithdebinfo_flags(self, gcc_linux):
        """Test RelWithDebInfo build type flags."""
        flags = gcc_linux.get_flags_for_build_type("relwithdebinfo")
        assert flags is not None
        assert "-g" in flags
        assert "-O2" in flags
        assert "-DNDEBUG" in flags

    def test_minsizerel_flags(self, gcc_linux):
        """Test MinSizeRel build type flags."""
        flags = gcc_linux.get_flags_for_build_type("minsizerel")
        assert flags is not None
        assert "-Os" in flags
        assert "-DNDEBUG" in flags


class TestGCCWarnings:
    """Test GCC warning level flags."""

    def test_off_warnings(self, gcc_linux):
        """Test 'off' warning level."""
        flags = gcc_linux.get_warning_flags("off")
        assert flags is not None
        assert flags == []

    def test_basic_warnings(self, gcc_linux):
        """Test 'basic' warning level."""
        flags = gcc_linux.get_warning_flags("basic")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags

    def test_extra_warnings(self, gcc_linux):
        """Test 'extra' warning level."""
        flags = gcc_linux.get_warning_flags("extra")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags
        assert "-Wpedantic" in flags
        assert "-Wshadow" in flags

    def test_strict_warnings(self, gcc_linux):
        """Test 'strict' warning level."""
        flags = gcc_linux.get_warning_flags("strict")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags
        assert "-Wold-style-cast" in flags

    def test_pedantic_warnings(self, gcc_linux):
        """Test 'pedantic' warning level."""
        flags = gcc_linux.get_warning_flags("pedantic")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags
        assert "-Wnull-dereference" in flags
        assert "-Wformat=2" in flags

    def test_error_warnings(self, gcc_linux):
        """Test 'error' warning level."""
        flags = gcc_linux.get_warning_flags("error")
        assert flags is not None
        assert "-Werror" in flags


class TestGCCStandardLibrary:
    """Test GCC standard library configuration."""

    def test_libstdcxx_flags(self, gcc_linux):
        """Test libstdc++ (default GCC stdlib)."""
        flags = gcc_linux.get_stdlib_flags("libstdc++")
        assert flags is not None
        # libstdc++ is default, no special flags needed
        compile_flags = flags.get("compile_flags", [])
        assert isinstance(compile_flags, list)

    def test_libcxx_flags(self, gcc_linux):
        """Test libc++ (if available)."""
        flags = gcc_linux.get_stdlib_flags("libc++")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-stdlib=libc++" in compile_flags


class TestGCCLinker:
    """Test GCC linker configuration."""

    def test_ld_linker(self, gcc_linux):
        """Test ld (default) linker flag."""
        flag = gcc_linux.get_linker_flag("ld")
        assert flag is not None
        assert flag == "-fuse-ld=ld"

    def test_gold_linker(self, gcc_linux):
        """Test gold linker flag."""
        flag = gcc_linux.get_linker_flag("gold")
        assert flag is not None
        assert flag == "-fuse-ld=gold"

    def test_bfd_linker(self, gcc_linux):
        """Test bfd linker flag."""
        flag = gcc_linux.get_linker_flag("bfd")
        assert flag is not None
        assert flag == "-fuse-ld=bfd"

    def test_mold_linker(self, gcc_linux):
        """Test mold linker flag."""
        flag = gcc_linux.get_linker_flag("mold")
        assert flag is not None
        assert flag == "-fuse-ld=mold"


class TestGCCSanitizers:
    """Test GCC sanitizer configuration."""

    def test_address_sanitizer(self, gcc_linux):
        """Test AddressSanitizer flags."""
        flags = gcc_linux.get_sanitizer_flags("address")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=address" in compile_flags
        assert "-fno-omit-frame-pointer" in compile_flags

    def test_undefined_sanitizer(self, gcc_linux):
        """Test UndefinedBehaviorSanitizer flags."""
        flags = gcc_linux.get_sanitizer_flags("undefined")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=undefined" in compile_flags

    def test_thread_sanitizer(self, gcc_linux):
        """Test ThreadSanitizer flags."""
        flags = gcc_linux.get_sanitizer_flags("thread")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=thread" in compile_flags

    def test_leak_sanitizer(self, gcc_linux):
        """Test LeakSanitizer flags."""
        flags = gcc_linux.get_sanitizer_flags("leak")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=leak" in compile_flags


class TestGCCLTO:
    """Test GCC link-time optimization configuration."""

    def test_full_lto(self, gcc_linux):
        """Test full LTO flags."""
        flags = gcc_linux.get_lto_flags("full")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-flto" in compile_flags

    def test_thin_lto(self, gcc_linux):
        """Test thin LTO flags."""
        flags = gcc_linux.get_lto_flags("thin")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-flto=thin" in compile_flags


class TestGCCCoverage:
    """Test GCC code coverage configuration."""

    def test_coverage_flags(self, gcc_linux):
        """Test code coverage flags (--coverage)."""
        flags = gcc_linux.get_coverage_flags()
        assert flags is not None
        assert "--coverage" in flags


class TestGCCCMakeVariables:
    """Test GCC CMake variable generation."""

    def test_cmake_variables_linux(self, gcc_linux):
        """Test CMake variables for Linux."""
        vars = gcc_linux.get_cmake_variables(toolchain_root="/usr/local")
        assert vars is not None
        assert "CMAKE_C_COMPILER" in vars
        assert "CMAKE_CXX_COMPILER" in vars
        assert "/usr/local/bin/gcc" in vars["CMAKE_C_COMPILER"]
        assert "/usr/local/bin/g++" in vars["CMAKE_CXX_COMPILER"]
        assert "CMAKE_AR" in vars
        assert "gcc-ar" in vars["CMAKE_AR"]

    def test_cmake_variables_windows(self, gcc_windows):
        """Test CMake variables for Windows (MinGW)."""
        vars = gcc_windows.get_cmake_variables(toolchain_root="C:/mingw64")
        assert vars is not None
        assert "CMAKE_C_COMPILER" in vars
        assert "CMAKE_CXX_COMPILER" in vars
        assert "gcc.exe" in vars["CMAKE_C_COMPILER"]
        assert "g++.exe" in vars["CMAKE_CXX_COMPILER"]


class TestGCCPlatformOverrides:
    """Test GCC platform-specific behavior."""

    def test_different_executables_per_platform(self, yaml_loader):
        """Test that Linux and Windows use different executable names."""
        linux_config = yaml_loader.load("gcc", platform="linux")
        windows_config = yaml_loader.load("gcc", platform="windows")

        linux_vars = linux_config.get_cmake_variables(toolchain_root="/usr")
        windows_vars = windows_config.get_cmake_variables(toolchain_root="C:/mingw")

        # Linux uses Unix-style names
        assert "gcc" in linux_vars["CMAKE_C_COMPILER"]
        assert "g++" in linux_vars["CMAKE_CXX_COMPILER"]

        # Windows uses .exe extension
        assert "gcc.exe" in windows_vars["CMAKE_C_COMPILER"]
        assert "g++.exe" in windows_vars["CMAKE_CXX_COMPILER"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
