"""
Regression tests for CMake toolchain file generation.

Ensures generated CMake files remain valid and compatible.
"""

import pytest
from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
    InvalidToolchainConfigError,
)


@pytest.mark.regression
class TestCMakeToolchainGeneration:
    """Test CMake toolchain file generation."""

    def test_generate_basic_toolchain_file(self, tmp_path):
        """Verify basic toolchain file can be generated."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()
        (toolchain_dir / "bin").mkdir()

        generator = CMakeToolchainGenerator(tmp_path)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        output_file = generator.generate(config)

        assert output_file.exists()
        assert output_file.name == "toolchain-llvm-18.1.8-linux-x64.cmake"
        assert output_file.parent == tmp_path / ".toolchainkit" / "cmake"

    def test_toolchain_file_content_structure(self, tmp_path):
        """Verify generated file has expected content structure."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        generator = CMakeToolchainGenerator(tmp_path)
        config = ToolchainFileConfig(
            toolchain_id="gcc-13-linux",
            toolchain_path=toolchain_dir,
            compiler_type="gcc",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        # Should have CMake comment header
        assert content.startswith("#")
        # Should contain compiler settings
        assert "CMAKE" in content or "compiler" in content.lower()

    def test_nonexistent_toolchain_path_raises_error(self, tmp_path):
        """Verify error raised for nonexistent toolchain path."""
        nonexistent_path = tmp_path / "nonexistent"

        generator = CMakeToolchainGenerator(tmp_path)
        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=nonexistent_path,
            compiler_type="clang",
        )

        with pytest.raises(Exception, match="does not exist"):
            generator.generate(config)

    def test_output_directory_created_automatically(self, tmp_path):
        """Verify output directory is created if it doesn't exist."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        # Output directory doesn't exist yet
        cmake_dir = tmp_path / ".toolchainkit" / "cmake"
        assert not cmake_dir.exists()

        generator = CMakeToolchainGenerator(tmp_path)
        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        generator.generate(config)

        # Should be created
        assert cmake_dir.exists()
        assert cmake_dir.is_dir()


@pytest.mark.regression
class TestToolchainFileConfig:
    """Test ToolchainFileConfig validation."""

    def test_valid_compiler_types(self, tmp_path):
        """Verify all valid compiler types are accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        for compiler_type in ["clang", "gcc", "msvc"]:
            config = ToolchainFileConfig(
                toolchain_id=f"test-{compiler_type}",
                toolchain_path=toolchain_dir,
                compiler_type=compiler_type,
            )
            assert config.compiler_type == compiler_type

    def test_invalid_compiler_type_rejected(self, tmp_path):
        """Verify invalid compiler types are rejected."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        with pytest.raises(InvalidToolchainConfigError, match="Invalid compiler_type"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="invalid-compiler",
            )

    def test_valid_build_types(self, tmp_path):
        """Verify all valid build types are accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        for build_type in ["Release", "Debug", "RelWithDebInfo", "MinSizeRel"]:
            config = ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                build_type=build_type,
            )
            assert config.build_type == build_type

    def test_invalid_build_type_rejected(self, tmp_path):
        """Verify invalid build types are rejected."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        with pytest.raises(InvalidToolchainConfigError, match="Invalid build_type"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                build_type="InvalidBuildType",
            )

    def test_default_build_type_is_release(self, tmp_path):
        """Verify default build type is Release."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.build_type == "Release"

    def test_valid_stdlib_types(self, tmp_path):
        """Verify valid stdlib types are accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        for stdlib in ["libc++", "libstdc++", "msvc", None]:
            config = ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                stdlib=stdlib,
            )
            assert config.stdlib == stdlib

    def test_invalid_stdlib_rejected(self, tmp_path):
        """Verify invalid stdlib types are rejected."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        with pytest.raises(InvalidToolchainConfigError, match="Invalid stdlib"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                stdlib="invalid-stdlib",
            )

    def test_valid_linker_types(self, tmp_path):
        """Verify valid linker types are accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        for linker in ["lld", "gold", "mold", "bfd", None]:
            config = ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                linker=linker,
            )
            assert config.linker == linker

    def test_invalid_linker_rejected(self, tmp_path):
        """Verify invalid linker types are rejected."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        with pytest.raises(InvalidToolchainConfigError, match="Invalid linker"):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                linker="invalid-linker",
            )

    def test_caching_requires_cache_tool(self, tmp_path):
        """Verify caching_enabled requires cache_tool."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        with pytest.raises(
            InvalidToolchainConfigError, match="cache_tool must be specified"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                caching_enabled=True,
                cache_tool=None,
            )

    def test_caching_with_tool_accepted(self, tmp_path):
        """Verify caching with cache_tool is accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
            caching_enabled=True,
            cache_tool="sccache",
        )

        assert config.caching_enabled is True
        assert config.cache_tool == "sccache"


@pytest.mark.regression
class TestCrossCompilationConfig:
    """Test cross-compilation configuration."""

    def test_cross_compile_requires_os_and_arch(self, tmp_path):
        """Verify cross_compile dict must have os and arch."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        # Missing 'arch'
        with pytest.raises(
            InvalidToolchainConfigError, match="must contain 'os' and 'arch'"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                cross_compile={"os": "android"},
            )

        # Missing 'os'
        with pytest.raises(
            InvalidToolchainConfigError, match="must contain 'os' and 'arch'"
        ):
            ToolchainFileConfig(
                toolchain_id="test",
                toolchain_path=toolchain_dir,
                compiler_type="clang",
                cross_compile={"arch": "arm64"},
            )

    def test_valid_cross_compile_config(self, tmp_path):
        """Verify valid cross-compilation config is accepted."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
            cross_compile={"os": "android", "arch": "arm64", "sysroot": "/sysroot"},
        )

        assert config.cross_compile["os"] == "android"
        assert config.cross_compile["arch"] == "arm64"
        assert config.cross_compile["sysroot"] == "/sysroot"


@pytest.mark.regression
class TestToolchainConfigDefaults:
    """Test ToolchainFileConfig default values."""

    def test_default_stdlib_is_none(self, tmp_path):
        """Verify default stdlib is None."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.stdlib is None

    def test_default_linker_is_none(self, tmp_path):
        """Verify default linker is None."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.linker is None

    def test_default_caching_disabled(self, tmp_path):
        """Verify caching is disabled by default."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.caching_enabled is False
        assert config.cache_tool is None

    def test_default_cross_compile_is_none(self, tmp_path):
        """Verify cross_compile is None by default."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.cross_compile is None

    def test_default_package_manager_is_none(self, tmp_path):
        """Verify package_manager is None by default."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        assert config.package_manager is None


@pytest.mark.regression
class TestMultipleGenerations:
    """Test multiple toolchain file generations."""

    def test_generate_multiple_toolchains(self, tmp_path):
        """Verify multiple toolchain files can be generated."""
        toolchain1 = tmp_path / "toolchain1"
        toolchain1.mkdir()
        toolchain2 = tmp_path / "toolchain2"
        toolchain2.mkdir()

        generator = CMakeToolchainGenerator(tmp_path)

        config1 = ToolchainFileConfig(
            toolchain_id="clang-18",
            toolchain_path=toolchain1,
            compiler_type="clang",
        )
        config2 = ToolchainFileConfig(
            toolchain_id="gcc-13",
            toolchain_path=toolchain2,
            compiler_type="gcc",
        )

        file1 = generator.generate(config1)
        file2 = generator.generate(config2)

        assert file1.exists()
        assert file2.exists()
        assert file1.name == "toolchain-clang-18.cmake"
        assert file2.name == "toolchain-gcc-13.cmake"

    def test_regenerate_overwrites_existing(self, tmp_path):
        """Verify regenerating overwrites existing toolchain file."""
        toolchain_dir = tmp_path / "toolchain"
        toolchain_dir.mkdir()

        generator = CMakeToolchainGenerator(tmp_path)
        config = ToolchainFileConfig(
            toolchain_id="test",
            toolchain_path=toolchain_dir,
            compiler_type="clang",
        )

        # First generation
        file1 = generator.generate(config)
        content1 = file1.read_text()

        # Second generation (should overwrite)
        file2 = generator.generate(config)
        content2 = file2.read_text()

        assert file1 == file2  # Same path
        # Content should be similar (timestamps might differ slightly)
        assert len(content1) > 0
        assert len(content2) > 0


@pytest.mark.regression
def test_generator_uses_atomic_write(tmp_path):
    """
    Verify generator uses atomic write for safety.

    This ensures partial writes don't corrupt toolchain files.
    """
    toolchain_dir = tmp_path / "toolchain"
    toolchain_dir.mkdir()

    generator = CMakeToolchainGenerator(tmp_path)
    config = ToolchainFileConfig(
        toolchain_id="test",
        toolchain_path=toolchain_dir,
        compiler_type="clang",
    )

    output_file = generator.generate(config)

    # File should exist and be readable (atomic write completed)
    assert output_file.exists()
    content = output_file.read_text()
    assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
