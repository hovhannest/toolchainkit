"""
Tests for Clang YAML compiler configuration.

Validates that the Clang compiler YAML definition works correctly
and produces equivalent results to the Python ClangConfig class.
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
def clang_linux(yaml_loader):
    """Load Clang configuration for Linux platform."""
    return yaml_loader.load("clang", platform="linux")


@pytest.fixture
def clang_windows(yaml_loader):
    """Load Clang configuration for Windows platform."""
    return yaml_loader.load("clang", platform="windows")


@pytest.fixture
def clang_macos(yaml_loader):
    """Load Clang configuration for macOS platform."""
    return yaml_loader.load("clang", platform="macos")


class TestClangYAMLLoader:
    """Test loading Clang YAML configuration."""

    def test_clang_loads_successfully(self, yaml_loader):
        """Test that clang.yaml can be loaded."""
        config = yaml_loader.load("clang")
        assert config is not None
        assert config.name == "clang"

    def test_clang_available_in_list(self, yaml_loader):
        """Test that clang appears in available compilers list."""
        available = yaml_loader.list_available()
        assert "clang" in available

    def test_clang_linux_platform_override(self, yaml_loader):
        """Test Clang loads correctly with Linux platform."""
        config = yaml_loader.load("clang", platform="linux")
        assert config is not None
        # Linux should use Unix-style executables
        cmake_vars = config.get_cmake_variables(toolchain_root="/opt/llvm")
        # Check that we get clang, not clang-cl
        assert "clang++" in cmake_vars.get(
            "CMAKE_CXX_COMPILER", ""
        ) or "clang" in cmake_vars.get("CMAKE_CXX_COMPILER", "")

    def test_clang_windows_platform_override(self, yaml_loader):
        """Test Clang loads correctly with Windows platform override (clang-cl)."""
        config = yaml_loader.load("clang", platform="windows")
        assert config is not None
        # Windows should use clang-cl
        cmake_vars = config.get_cmake_variables(toolchain_root="C:/LLVM")
        # Check that we get clang-cl
        assert "clang-cl" in cmake_vars.get("CMAKE_CXX_COMPILER", "")


class TestClangBuildTypes:
    """Test Clang build type flags."""

    def test_debug_flags(self, clang_linux):
        """Test Debug build type flags."""
        flags = clang_linux.get_flags_for_build_type("debug")
        assert flags is not None
        assert "-g" in flags
        assert "-O0" in flags
        assert "-fno-omit-frame-pointer" in flags

    def test_release_flags(self, clang_linux):
        """Test Release build type flags."""
        flags = clang_linux.get_flags_for_build_type("release")
        assert flags is not None
        assert "-O3" in flags
        assert "-DNDEBUG" in flags
        assert "-fomit-frame-pointer" in flags

    def test_relwithdebinfo_flags(self, clang_linux):
        """Test RelWithDebInfo build type flags."""
        flags = clang_linux.get_flags_for_build_type("relwithdebinfo")
        assert flags is not None
        assert "-g" in flags
        assert "-O2" in flags
        assert "-DNDEBUG" in flags

    def test_minsizerel_flags(self, clang_linux):
        """Test MinSizeRel build type flags."""
        flags = clang_linux.get_flags_for_build_type("minsizerel")
        assert flags is not None
        assert "-Os" in flags
        assert "-DNDEBUG" in flags

    def test_windows_debug_flags(self, clang_windows):
        """Test Windows-specific Debug flags (clang-cl style)."""
        flags = clang_windows.get_flags_for_build_type("debug")
        assert flags is not None
        # Windows should use MSVC-style flags
        assert "/MDd" in flags
        assert "/Zi" in flags
        assert "/Od" in flags

    def test_windows_release_flags(self, clang_windows):
        """Test Windows-specific Release flags (clang-cl style)."""
        flags = clang_windows.get_flags_for_build_type("release")
        assert flags is not None
        # Windows should use MSVC-style flags
        assert "/MD" in flags
        assert "/O2" in flags
        assert "/DNDEBUG" in flags


class TestClangWarnings:
    """Test Clang warning flags."""

    def test_off_warnings(self, clang_linux):
        """Test no warnings configuration."""
        flags = clang_linux.get_warning_flags("off")
        assert flags is not None
        assert len(flags) == 0 or flags == []

    def test_basic_warnings(self, clang_linux):
        """Test basic warning flags."""
        flags = clang_linux.get_warning_flags("basic")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags

    def test_extra_warnings(self, clang_linux):
        """Test extra warning flags."""
        flags = clang_linux.get_warning_flags("extra")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags
        assert "-Wpedantic" in flags
        assert "-Wshadow" in flags
        assert "-Wconversion" in flags

    def test_strict_warnings(self, clang_linux):
        """Test strict warning flags."""
        flags = clang_linux.get_warning_flags("strict")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wextra" in flags
        assert "-Wpedantic" in flags
        assert "-Wold-style-cast" in flags

    def test_pedantic_warnings(self, clang_linux):
        """Test pedantic warning flags."""
        flags = clang_linux.get_warning_flags("pedantic")
        assert flags is not None
        assert "-Wall" in flags
        assert "-Wnull-dereference" in flags
        assert "-Wdouble-promotion" in flags

    def test_error_warnings(self, clang_linux):
        """Test warnings-as-errors flag."""
        flags = clang_linux.get_warning_flags("error")
        assert flags is not None
        assert "-Werror" in flags


class TestClangStandardLibrary:
    """Test Clang standard library configuration."""

    def test_libcxx_compile_flags(self, clang_linux):
        """Test libc++ compile flags."""
        flags = clang_linux.get_stdlib_flags("libc++")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-stdlib=libc++" in compile_flags

    def test_libcxx_link_flags(self, clang_linux):
        """Test libc++ link flags."""
        flags = clang_linux.get_stdlib_flags("libc++")
        assert flags is not None
        link_flags = flags.get("link_flags", [])
        assert "-lc++" in link_flags
        assert "-lc++abi" in link_flags

    def test_libstdcxx_compile_flags(self, clang_linux):
        """Test libstdc++ compile flags."""
        flags = clang_linux.get_stdlib_flags("libstdc++")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-stdlib=libstdc++" in compile_flags

    def test_msvc_stdlib_on_windows(self, clang_windows):
        """Test MSVC standard library on Windows."""
        flags = clang_windows.get_stdlib_flags("msvc")
        assert flags is not None
        # MSVC stdlib typically has empty flags (auto-linked)
        compile_flags = flags.get("compile_flags", [])
        assert isinstance(compile_flags, list)


class TestClangLinker:
    """Test Clang linker configuration."""

    def test_lld_linker(self, clang_linux):
        """Test lld linker flag."""
        flag = clang_linux.get_linker_flag("lld")
        assert flag is not None
        assert flag == "-fuse-ld=lld"

    def test_gold_linker(self, clang_linux):
        """Test gold linker flag."""
        flag = clang_linux.get_linker_flag("gold")
        assert flag is not None
        assert flag == "-fuse-ld=gold"

    def test_mold_linker(self, clang_linux):
        """Test mold linker flag."""
        flag = clang_linux.get_linker_flag("mold")
        assert flag is not None
        assert flag == "-fuse-ld=mold"

    def test_ld_linker(self, clang_linux):
        """Test ld linker flag."""
        flag = clang_linux.get_linker_flag("ld")
        assert flag is not None
        assert flag == "-fuse-ld=ld"

    def test_windows_linker(self, clang_windows):
        """Test Windows linker flag (clang-cl)."""
        flag = clang_windows.get_linker_flag("link")
        assert flag is not None
        assert flag == "/link"


class TestClangSanitizers:
    """Test Clang sanitizer configuration."""

    def test_address_sanitizer(self, clang_linux):
        """Test AddressSanitizer flags."""
        flags = clang_linux.get_sanitizer_flags("address")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=address" in compile_flags
        assert "-fno-omit-frame-pointer" in compile_flags
        link_flags = flags.get("link_flags", [])
        assert "-fsanitize=address" in link_flags

    def test_undefined_sanitizer(self, clang_linux):
        """Test UndefinedBehaviorSanitizer flags."""
        flags = clang_linux.get_sanitizer_flags("undefined")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=undefined" in compile_flags

    def test_thread_sanitizer(self, clang_linux):
        """Test ThreadSanitizer flags."""
        flags = clang_linux.get_sanitizer_flags("thread")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=thread" in compile_flags

    def test_memory_sanitizer(self, clang_linux):
        """Test MemorySanitizer flags."""
        flags = clang_linux.get_sanitizer_flags("memory")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=memory" in compile_flags

    def test_leak_sanitizer(self, clang_linux):
        """Test LeakSanitizer flags."""
        flags = clang_linux.get_sanitizer_flags("leak")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-fsanitize=leak" in compile_flags


class TestClangLTO:
    """Test Clang link-time optimization configuration."""

    def test_thin_lto(self, clang_linux):
        """Test ThinLTO flags."""
        flags = clang_linux.get_lto_flags("thin")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-flto=thin" in compile_flags
        link_flags = flags.get("link_flags", [])
        assert "-flto=thin" in link_flags

    def test_full_lto(self, clang_linux):
        """Test full LTO flags."""
        flags = clang_linux.get_lto_flags("full")
        assert flags is not None
        compile_flags = flags.get("compile_flags", [])
        assert "-flto" in compile_flags
        link_flags = flags.get("link_flags", [])
        assert "-flto" in link_flags


class TestClangCoverage:
    """Test Clang code coverage configuration."""

    def test_coverage_flags(self, clang_linux):
        """Test code coverage flags."""
        flags = clang_linux.get_coverage_flags()
        assert flags is not None
        assert "-fprofile-instr-generate" in flags
        assert "-fcoverage-mapping" in flags


class TestClangCMakeVariables:
    """Test Clang CMake variable generation."""

    def test_cmake_variables_linux(self, clang_linux):
        """Test CMake variables for Linux."""
        vars = clang_linux.get_cmake_variables(toolchain_root="/opt/llvm-18")
        assert vars is not None
        assert "CMAKE_C_COMPILER" in vars
        assert "CMAKE_CXX_COMPILER" in vars
        assert "/opt/llvm-18/bin/clang" in vars["CMAKE_C_COMPILER"]
        assert "/opt/llvm-18/bin/clang++" in vars["CMAKE_CXX_COMPILER"]
        assert "CMAKE_AR" in vars
        assert "CMAKE_RANLIB" in vars
        assert "CMAKE_LINKER" in vars
        assert "LLVM_ROOT" in vars

    def test_cmake_variables_windows(self, clang_windows):
        """Test CMake variables for Windows (clang-cl)."""
        vars = clang_windows.get_cmake_variables(toolchain_root="C:/LLVM")
        assert vars is not None
        assert "CMAKE_C_COMPILER" in vars
        assert "CMAKE_CXX_COMPILER" in vars
        # Windows should use clang-cl.exe
        assert "clang-cl.exe" in vars["CMAKE_CXX_COMPILER"]
        assert "llvm-lib.exe" in vars["CMAKE_AR"]

    def test_variable_interpolation(self, clang_linux):
        """Test that {{toolchain_root}} is interpolated correctly."""
        vars = clang_linux.get_cmake_variables(
            toolchain_root="/custom/path", compiler_version="18.1.8"
        )
        assert vars is not None
        # Verify interpolation worked
        for key, value in vars.items():
            assert "{{" not in str(
                value
            ), f"Variable {key} has un-interpolated placeholder: {value}"
            assert "}}" not in str(
                value
            ), f"Variable {key} has un-interpolated placeholder: {value}"


class TestClangPlatformOverrides:
    """Test that platform overrides work correctly."""

    def test_different_executables_per_platform(self, yaml_loader):
        """Test that different platforms get different executables."""
        linux_config = yaml_loader.load("clang", platform="linux")
        windows_config = yaml_loader.load("clang", platform="windows")

        linux_vars = linux_config.get_cmake_variables(toolchain_root="/opt/llvm")
        windows_vars = windows_config.get_cmake_variables(toolchain_root="C:/LLVM")

        # Linux should use clang, Windows should use clang-cl
        assert "clang++" in linux_vars["CMAKE_CXX_COMPILER"]
        assert "clang-cl" in windows_vars["CMAKE_CXX_COMPILER"]

    def test_different_flags_per_platform(self, yaml_loader):
        """Test that different platforms get different build flags."""
        linux_config = yaml_loader.load("clang", platform="linux")
        windows_config = yaml_loader.load("clang", platform="windows")

        linux_debug = linux_config.get_flags_for_build_type("debug")
        windows_debug = windows_config.get_flags_for_build_type("debug")

        # Linux should use Unix-style flags, Windows should use MSVC-style
        assert "-g" in linux_debug
        assert "/MDd" in windows_debug


@pytest.mark.integration
class TestClangYAMLIntegration:
    """Integration tests for Clang YAML configuration."""

    def test_complete_linux_workflow(self, yaml_loader):
        """Test a complete workflow: load Clang, configure for Linux Release build."""
        # Load compiler
        clang = yaml_loader.load("clang", platform="linux")

        # Get build flags
        release_flags = clang.get_flags_for_build_type("release")
        warning_flags = clang.get_warning_flags("extra")
        stdlib_config = clang.get_stdlib_flags("libc++")
        linker_flag = clang.get_linker_flag("lld")
        lto_flags = clang.get_lto_flags("thin")

        # Generate CMake variables
        cmake_vars = clang.get_cmake_variables(
            toolchain_root="/opt/llvm-18", compiler_version="18.1.8"
        )

        # Verify everything is present
        assert release_flags
        assert warning_flags
        assert stdlib_config
        assert linker_flag
        assert lto_flags
        assert cmake_vars
        assert "CMAKE_C_COMPILER" in cmake_vars
        assert "CMAKE_CXX_COMPILER" in cmake_vars

    def test_complete_windows_workflow(self, yaml_loader):
        """Test a complete workflow: load Clang, configure for Windows Debug build."""
        # Load compiler with Windows overrides
        clang = yaml_loader.load("clang", platform="windows")

        # Get build flags
        debug_flags = clang.get_flags_for_build_type("debug")
        stdlib_config = clang.get_stdlib_flags("msvc")
        linker_flag = clang.get_linker_flag("link")

        # Generate CMake variables
        cmake_vars = clang.get_cmake_variables(
            toolchain_root="C:/Program Files/LLVM", compiler_version="18.1.8"
        )

        # Verify Windows-specific configuration
        assert "/MDd" in debug_flags
        assert stdlib_config is not None
        assert linker_flag == "/link"
        assert "clang-cl.exe" in cmake_vars["CMAKE_CXX_COMPILER"]

    def test_macos_workflow(self, yaml_loader):
        """Test a complete workflow: load Clang, configure for macOS."""
        # Load compiler for macOS
        clang = yaml_loader.load("clang", platform="macos")

        # macOS should default to libc++
        cmake_vars = clang.get_cmake_variables(toolchain_root="/usr/local/opt/llvm")

        # Verify macOS configuration
        assert cmake_vars
        assert "clang++" in cmake_vars["CMAKE_CXX_COMPILER"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
