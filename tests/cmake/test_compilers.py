"""
Tests for cmake.compilers module.
"""

import pytest

from toolchainkit.cmake.compilers import ToolchainSpec, CompilerConfig


class TestToolchainSpec:
    """Test ToolchainSpec dataclass."""

    def test_toolchain_spec_creation_valid_gcc(self):
        """Test creating valid GCC toolchain spec."""
        spec = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc-13",
            cxx_compiler_path="/usr/bin/g++-13",
            install_path="/usr",
        )

        assert spec.type == "gcc"
        assert spec.version == "13.2.0"
        # Normalize path separators for comparison
        assert str(spec.c_compiler_path).replace("\\", "/") == "/usr/bin/gcc-13"
        assert str(spec.cxx_compiler_path).replace("\\", "/") == "/usr/bin/g++-13"
        assert str(spec.install_path).replace("\\", "/") == "/usr"

    def test_toolchain_spec_creation_valid_clang(self):
        """Test creating valid Clang toolchain spec."""
        spec = ToolchainSpec(
            type="clang",
            version="18.1.8",
            c_compiler_path="/usr/bin/clang-18",
            cxx_compiler_path="/usr/bin/clang++-18",
            install_path="/usr/lib/llvm-18",
        )

        assert spec.type == "clang"
        assert spec.version == "18.1.8"

    def test_toolchain_spec_creation_valid_msvc(self):
        """Test creating valid MSVC toolchain spec."""
        spec = ToolchainSpec(
            type="msvc",
            version="19.35.0",
            c_compiler_path="C:/Program Files/Microsoft Visual Studio/VC/Tools/MSVC/14.35.32215/bin/Hostx64/x64/cl.exe",
            cxx_compiler_path="C:/Program Files/Microsoft Visual Studio/VC/Tools/MSVC/14.35.32215/bin/Hostx64/x64/cl.exe",
            install_path="C:/Program Files/Microsoft Visual Studio",
        )

        assert spec.type == "msvc"
        assert spec.version == "19.35.0"

    def test_toolchain_spec_normalizes_type_to_lowercase(self):
        """Test that compiler type is normalized to lowercase."""
        spec = ToolchainSpec(
            type="GCC",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        assert spec.type == "gcc"

    def test_toolchain_spec_invalid_type(self):
        """Test that invalid compiler type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid compiler type"):
            ToolchainSpec(
                type="invalid",
                version="1.0.0",
                c_compiler_path="/usr/bin/invalid",
                cxx_compiler_path="/usr/bin/invalid++",
                install_path="/usr",
            )

    def test_toolchain_spec_invalid_version_format(self):
        """Test that invalid version format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid version format"):
            ToolchainSpec(
                type="gcc",
                version="invalid",
                c_compiler_path="/usr/bin/gcc",
                cxx_compiler_path="/usr/bin/g++",
                install_path="/usr",
            )

    def test_toolchain_spec_version_with_two_parts(self):
        """Test version with two parts (major.minor)."""
        spec = ToolchainSpec(
            type="gcc",
            version="13.2",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        assert spec.version == "13.2"

    def test_toolchain_spec_version_with_four_parts(self):
        """Test version with four parts."""
        spec = ToolchainSpec(
            type="clang",
            version="18.1.8.0",
            c_compiler_path="/usr/bin/clang",
            cxx_compiler_path="/usr/bin/clang++",
            install_path="/usr",
        )

        assert spec.version == "18.1.8.0"

    def test_toolchain_spec_version_single_number(self):
        """Test version with single number."""
        spec = ToolchainSpec(
            type="gcc",
            version="13",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        assert spec.version == "13"

    def test_toolchain_spec_paths_as_strings(self):
        """Test that paths are stored as strings."""
        spec = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        assert isinstance(spec.c_compiler_path, str)
        assert isinstance(spec.cxx_compiler_path, str)
        assert isinstance(spec.install_path, str)

    def test_toolchain_spec_with_windows_paths(self):
        """Test toolchain spec with Windows-style paths."""
        spec = ToolchainSpec(
            type="msvc",
            version="19.35.0",
            c_compiler_path="C:\\Program Files\\MSVC\\cl.exe",
            cxx_compiler_path="C:\\Program Files\\MSVC\\cl.exe",
            install_path="C:\\Program Files\\MSVC",
        )

        assert "C:" in spec.c_compiler_path
        assert "C:" in spec.cxx_compiler_path
        assert "C:" in spec.install_path

    def test_toolchain_spec_mixed_case_types(self):
        """Test that mixed case types are normalized."""
        for compiler_type in ["Clang", "CLANG", "cLaNg"]:
            spec = ToolchainSpec(
                type=compiler_type,
                version="18.1.8",
                c_compiler_path="/usr/bin/clang",
                cxx_compiler_path="/usr/bin/clang++",
                install_path="/usr",
            )
            assert spec.type == "clang"


class MockCompilerConfig(CompilerConfig):
    """Mock implementation of CompilerConfig for testing."""

    def get_cmake_variables(self):
        return {"CMAKE_CXX_STANDARD": "17", "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"}

    def get_compile_flags(self):
        return ["-Wall", "-Wextra", "-O2"]

    def get_link_flags(self):
        return ["-pthread"]


class TestCompilerConfig:
    """Test CompilerConfig abstract base class."""

    def test_compiler_config_initialization(self):
        """Test CompilerConfig initialization."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain, "Release")

        assert config.toolchain == toolchain
        assert config.build_type == "Release"

    def test_compiler_config_default_build_type(self):
        """Test CompilerConfig with default build type."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain)

        assert config.build_type == "Release"

    def test_compiler_config_debug_build_type(self):
        """Test CompilerConfig with Debug build type."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain, "Debug")

        assert config.build_type == "Debug"

    def test_compiler_config_rel_with_deb_info_build_type(self):
        """Test CompilerConfig with RelWithDebInfo build type."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain, "RelWithDebInfo")

        assert config.build_type == "RelWithDebInfo"

    def test_compiler_config_min_size_rel_build_type(self):
        """Test CompilerConfig with MinSizeRel build type."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain, "MinSizeRel")

        assert config.build_type == "MinSizeRel"

    def test_compiler_config_invalid_build_type(self):
        """Test that invalid build type raises ValueError."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        with pytest.raises(ValueError, match="Invalid build type"):
            MockCompilerConfig(toolchain, "InvalidBuildType")

    def test_compiler_config_generate_cmake_snippet(self):
        """Test generate_cmake_snippet method."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain, "Release")
        snippet = config.generate_cmake_snippet()

        assert "# Compiler Configuration" in snippet
        assert "gcc 13.2.0" in snippet
        assert "Release" in snippet

    def test_compiler_config_cmake_snippet_includes_variables(self):
        """Test that CMake snippet includes variables."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "CMAKE_CXX_STANDARD" in snippet
        assert "CMAKE_EXPORT_COMPILE_COMMANDS" in snippet

    def test_compiler_config_cmake_snippet_includes_compile_flags(self):
        """Test that CMake snippet includes compile flags."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "add_compile_options" in snippet
        assert "-Wall" in snippet
        assert "-Wextra" in snippet

    def test_compiler_config_cmake_snippet_includes_link_flags(self):
        """Test that CMake snippet includes link flags."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "add_link_options" in snippet
        assert "-pthread" in snippet

    def test_compiler_config_cmake_snippet_boolean_values(self):
        """Test that boolean CMake variables are converted to ON/OFF."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        # CMAKE_EXPORT_COMPILE_COMMANDS is set to "ON" in mock
        assert "ON" in snippet


class MockEmptyCompilerConfig(CompilerConfig):
    """Mock with empty return values for testing."""

    def get_cmake_variables(self):
        return {}

    def get_compile_flags(self):
        return []

    def get_link_flags(self):
        return []


class TestCompilerConfigEdgeCases:
    """Test edge cases in CompilerConfig."""

    def test_compiler_config_empty_cmake_variables(self):
        """Test with empty CMake variables."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockEmptyCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "# Compiler Configuration" in snippet
        # Should not have variable section
        assert "add_compile_options" not in snippet

    def test_compiler_config_empty_compile_flags(self):
        """Test with empty compile flags."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockEmptyCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "add_compile_options" not in snippet

    def test_compiler_config_empty_link_flags(self):
        """Test with empty link flags."""
        toolchain = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        config = MockEmptyCompilerConfig(toolchain)
        snippet = config.generate_cmake_snippet()

        assert "add_link_options" not in snippet

    def test_toolchain_spec_equality(self):
        """Test ToolchainSpec equality."""
        spec1 = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        spec2 = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        assert spec1 == spec2

    def test_toolchain_spec_inequality(self):
        """Test ToolchainSpec inequality."""
        spec1 = ToolchainSpec(
            type="gcc",
            version="13.2.0",
            c_compiler_path="/usr/bin/gcc",
            cxx_compiler_path="/usr/bin/g++",
            install_path="/usr",
        )

        spec2 = ToolchainSpec(
            type="clang",
            version="18.1.8",
            c_compiler_path="/usr/bin/clang",
            cxx_compiler_path="/usr/bin/clang++",
            install_path="/usr",
        )

        assert spec1 != spec2
