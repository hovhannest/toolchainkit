"""
Unit tests for CMake Toolchain File Generator.

Tests cover:
- Toolchain file generation
- Configuration validation
- Compiler-specific settings
- Build caching configuration
- Package manager integration
- Cross-compilation settings
- Error handling
"""

import pytest
from pathlib import Path

from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
    CMakeToolchainGeneratorError,
    InvalidToolchainConfigError,
)


@pytest.mark.unit
class TestToolchainFileConfig:
    """Test ToolchainFileConfig dataclass."""

    def test_valid_config(self, temp_dir):
        """Test creating a valid configuration."""
        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)

        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            build_type="Release",
            linker="lld",
        )

        assert config.toolchain_id == "llvm-18.1.8-linux-x64"
        assert config.toolchain_path == toolchain_path
        assert config.compiler_type == "clang"
        assert config.stdlib == "libc++"
        assert config.build_type == "Release"
        assert config.linker == "lld"
        assert config.caching_enabled is False
        assert config.cache_tool is None

    def test_invalid_compiler_type(self, temp_dir):
        """Test invalid compiler type raises error."""
        with pytest.raises(InvalidToolchainConfigError, match="Invalid compiler_type"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="invalid",
            )

    def test_invalid_build_type(self, temp_dir):
        """Test invalid build type raises error."""
        with pytest.raises(InvalidToolchainConfigError, match="Invalid build_type"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                build_type="Invalid",
            )

    def test_invalid_stdlib(self, temp_dir):
        """Test invalid stdlib raises error."""
        with pytest.raises(InvalidToolchainConfigError, match="Invalid stdlib"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                stdlib="invalid",
            )

    def test_invalid_linker(self, temp_dir):
        """Test invalid linker raises error."""
        with pytest.raises(InvalidToolchainConfigError, match="Invalid linker"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                linker="invalid",
            )

    def test_invalid_cache_tool(self, temp_dir):
        """Test invalid cache tool raises error."""
        with pytest.raises(InvalidToolchainConfigError, match="Invalid cache_tool"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                caching_enabled=True,
                cache_tool="invalid",
            )

    def test_caching_enabled_without_tool(self, temp_dir):
        """Test caching enabled without specifying tool raises error."""
        with pytest.raises(
            InvalidToolchainConfigError, match="cache_tool must be specified"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                caching_enabled=True,
            )

    def test_invalid_package_manager(self, temp_dir):
        """Test invalid package manager raises error."""
        with pytest.raises(
            InvalidToolchainConfigError, match="Invalid package_manager"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                package_manager="invalid",
            )

    def test_invalid_cross_compile_missing_keys(self, temp_dir):
        """Test cross_compile without required keys raises error."""
        with pytest.raises(
            InvalidToolchainConfigError, match="must contain 'os' and 'arch'"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=temp_dir,
                compiler_type="clang",
                cross_compile={"os": "Android"},  # Missing 'arch'
            )


@pytest.mark.unit
class TestCMakeToolchainGenerator:
    """Test CMakeToolchainGenerator class."""

    def test_init(self, temp_dir):
        """Test generator initialization."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        generator = CMakeToolchainGenerator(project_root)

        assert generator.project_root == project_root
        assert generator.output_dir == project_root / ".toolchainkit" / "cmake"

    def test_generate_creates_output_dir(self, temp_dir):
        """Test that generate() creates output directory."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)

        assert generator.output_dir.exists()
        assert output_file.parent == generator.output_dir

    def test_generate_returns_correct_filename(self, temp_dir):
        """Test that generated file has correct name."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)

        assert output_file.name == "toolchain-llvm-18.1.8-linux-x64.cmake"

    def test_generate_nonexistent_toolchain_path(self, temp_dir):
        """Test that nonexistent toolchain path raises error."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=temp_dir / "nonexistent",
            compiler_type="clang",
        )

        with pytest.raises(CMakeToolchainGeneratorError, match="does not exist"):
            generator.generate(config)

    def test_generate_idempotent(self, temp_dir):
        """Test that generating twice produces same result."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            linker="lld",
        )

        # Generate twice
        output_file1 = generator.generate(config)
        content1 = output_file1.read_text()

        output_file2 = generator.generate(config)
        content2 = output_file2.read_text()

        # Should be the same file
        assert output_file1 == output_file2

        # Content should be identical except for timestamp
        lines1 = content1.split("\n")
        lines2 = content2.split("\n")

        # Remove timestamp lines for comparison
        lines1 = [line for line in lines1 if not line.startswith("# Generated:")]
        lines2 = [line for line in lines2 if not line.startswith("# Generated:")]

        assert lines1 == lines2


@pytest.mark.unit
class TestHeaderGeneration:
    """Test header generation."""

    def test_header_contains_metadata(self, temp_dir):
        """Test that header contains required metadata."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "# Generated by ToolchainKit" in content
        assert "# Toolchain: llvm-18.1.8-linux-x64" in content
        assert "# Platform:" in content
        assert "# Generated:" in content
        assert "# DO NOT EDIT" in content
        assert "set(TOOLCHAINKIT_ROOT" in content
        assert 'set(TOOLCHAINKIT_VERSION "0.1.0")' in content


@pytest.mark.unit
class TestCompilerConfiguration:
    """Test compiler configuration generation."""

    def test_clang_compiler_config(self, temp_dir):
        """Test Clang compiler configuration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "set(CMAKE_C_COMPILER" in content
        assert "set(CMAKE_CXX_COMPILER" in content
        assert 'clang")' in content or 'clang.exe")' in content
        assert 'clang++")' in content or 'clang++.exe")' in content

    def test_gcc_compiler_config(self, temp_dir):
        """Test GCC compiler configuration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "gcc-13"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "gcc").touch()
        (toolchain_path / "bin" / "g++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="gcc-13.2.0",
            toolchain_path=toolchain_path,
            compiler_type="gcc",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "set(CMAKE_C_COMPILER" in content
        assert "set(CMAKE_CXX_COMPILER" in content
        assert 'gcc")' in content or 'gcc.exe")' in content
        assert 'g++")' in content or 'g++.exe")' in content

    def test_msvc_compiler_config(self, temp_dir):
        """Test MSVC compiler configuration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "msvc"
        toolchain_path.mkdir(parents=True)

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="msvc-19.39",
            toolchain_path=toolchain_path,
            compiler_type="msvc",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "MSVC" in content


@pytest.mark.unit
class TestCompilerFlags:
    """Test compiler and linker flags generation."""

    def test_clang_with_libcxx(self, temp_dir):
        """Test Clang with libc++ generates correct flags."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert 'CMAKE_CXX_FLAGS_INIT "-stdlib=libc++"' in content

    def test_clang_with_lld_linker(self, temp_dir):
        """Test Clang with lld linker generates correct flags."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            linker="lld",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert 'CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld"' in content
        assert 'CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld"' in content

    def test_clang_with_libcxx_and_lld(self, temp_dir):
        """Test Clang with libc++ and lld generates both flags."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            linker="lld",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "-stdlib=libc++" in content
        assert "-fuse-ld=lld" in content
        assert "-lc++" in content
        assert "-lc++abi" in content

    def test_gcc_with_gold_linker(self, temp_dir):
        """Test GCC with gold linker generates correct flags."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "gcc-13"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "gcc").touch()
        (toolchain_path / "bin" / "g++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="gcc-13.2.0",
            toolchain_path=toolchain_path,
            compiler_type="gcc",
            linker="gold",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "-fuse-ld=gold" in content


@pytest.mark.unit
class TestStaticAnalysis:
    """Test static analysis configuration."""

    def test_clang_tidy_config(self, temp_dir):
        """Test Clang-Tidy configuration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            clang_tidy_path=Path("/usr/bin/clang-tidy"),
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        # Check for CMake variable setting
        assert "# Clang-Tidy configuration" in content
        assert (
            'set(CMAKE_CXX_CLANG_TIDY "/usr/bin/clang-tidy" CACHE STRING "Clang-Tidy setup" FORCE)'
            in content
        )
        assert (
            'set(CMAKE_C_CLANG_TIDY "/usr/bin/clang-tidy" CACHE STRING "Clang-Tidy setup" FORCE)'
            in content
        )


@pytest.mark.unit
class TestBuildCaching:
    """Test build caching configuration."""

    def test_caching_with_sccache(self, temp_dir):
        """Test build caching with sccache."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            caching_enabled=True,
            cache_tool="sccache",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "# Build caching" in content
        assert "set(CMAKE_C_COMPILER_LAUNCHER sccache)" in content
        assert "set(CMAKE_CXX_COMPILER_LAUNCHER sccache)" in content

    def test_caching_with_ccache(self, temp_dir):
        """Test build caching with ccache."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            caching_enabled=True,
            cache_tool="ccache",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "set(CMAKE_C_COMPILER_LAUNCHER ccache)" in content
        assert "set(CMAKE_CXX_COMPILER_LAUNCHER ccache)" in content

    def test_no_caching_config_when_disabled(self, temp_dir):
        """Test that caching config is not included when disabled."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            caching_enabled=False,
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "CMAKE_C_COMPILER_LAUNCHER" not in content
        assert "CMAKE_CXX_COMPILER_LAUNCHER" not in content


@pytest.mark.unit
class TestPackageManagerIntegration:
    """Test package manager integration."""

    def test_conan_integration(self, temp_dir):
        """Test Conan package manager integration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            package_manager="conan",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "# Package manager integration" in content
        assert (
            "include(${CMAKE_CURRENT_LIST_DIR}/conan-integration.cmake OPTIONAL)"
            in content
        )

    def test_vcpkg_integration(self, temp_dir):
        """Test vcpkg package manager integration."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            package_manager="vcpkg",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert (
            "include(${CMAKE_CURRENT_LIST_DIR}/vcpkg-integration.cmake OPTIONAL)"
            in content
        )

    def test_no_package_manager(self, temp_dir):
        """Test that no package manager config is included when not specified."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "Package manager integration" not in content
        assert "conan-integration.cmake" not in content
        assert "vcpkg-integration.cmake" not in content


@pytest.mark.unit
class TestCrossCompilation:
    """Test cross-compilation configuration."""

    def test_android_cross_compile(self, temp_dir):
        """Test Android cross-compilation settings."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            cross_compile={
                "os": "Android",
                "arch": "aarch64",
                "api_level": "24",
            },
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "# Cross-compilation settings" in content
        assert "set(CMAKE_SYSTEM_NAME Android)" in content
        assert "set(CMAKE_SYSTEM_PROCESSOR aarch64)" in content
        assert "set(CMAKE_SYSTEM_VERSION 24)" in content

    def test_ios_cross_compile(self, temp_dir):
        """Test iOS cross-compilation settings."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            cross_compile={
                "os": "iOS",
                "arch": "arm64",
                "deployment_target": "15.0",
            },
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "set(CMAKE_SYSTEM_NAME iOS)" in content
        assert "set(CMAKE_SYSTEM_PROCESSOR arm64)" in content
        assert "set(CMAKE_OSX_DEPLOYMENT_TARGET 15.0)" in content

    def test_cross_compile_with_sysroot(self, temp_dir):
        """Test cross-compilation with sysroot."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        sysroot = temp_dir / "sysroots" / "android-arm64"

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            cross_compile={
                "os": "Android",
                "arch": "aarch64",
                "sysroot": str(sysroot),
            },
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert f'set(CMAKE_SYSROOT "{sysroot}")' in content


@pytest.mark.unit
class TestDebugInfo:
    """Test debug information messages."""

    def test_debug_info_present(self, temp_dir):
        """Test that debug info messages are present."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            linker="lld",
            caching_enabled=True,
            cache_tool="sccache",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        assert "# Toolchain info (for debugging)" in content
        assert (
            'message(STATUS "ToolchainKit: Using toolchain llvm-18.1.8-linux-x64")'
            in content
        )
        assert (
            'message(STATUS "ToolchainKit: C compiler: ${CMAKE_C_COMPILER}")' in content
        )
        assert (
            'message(STATUS "ToolchainKit: CXX compiler: ${CMAKE_CXX_COMPILER}")'
            in content
        )
        assert 'message(STATUS "ToolchainKit: C++ stdlib: libc++")' in content
        assert 'message(STATUS "ToolchainKit: Linker: lld")' in content
        assert 'message(STATUS "ToolchainKit: Build caching: sccache")' in content


@pytest.mark.unit
class TestCompleteConfiguration:
    """Test complete configurations with multiple features."""

    def test_full_featured_configuration(self, temp_dir):
        """Test configuration with all features enabled."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            build_type="Release",
            linker="lld",
            caching_enabled=True,
            cache_tool="sccache",
            package_manager="conan",
            cross_compile={
                "os": "Android",
                "arch": "aarch64",
                "api_level": "24",
            },
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        # Check all sections are present
        assert "# Generated by ToolchainKit" in content
        assert "set(TOOLCHAINKIT_ROOT" in content
        assert "set(CMAKE_C_COMPILER" in content
        assert "set(CMAKE_CXX_COMPILER" in content
        assert "-stdlib=libc++" in content
        assert "-fuse-ld=lld" in content
        assert "CMAKE_C_COMPILER_LAUNCHER sccache" in content
        assert "conan-integration.cmake" in content
        assert "CMAKE_SYSTEM_NAME Android" in content
        assert 'message(STATUS "ToolchainKit:' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
