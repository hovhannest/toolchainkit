"""Unit tests for YAML compiler loader."""


import pytest

from toolchainkit.cmake.yaml_compiler import (
    YAMLCompilerError,
    YAMLCompilerInvalidError,
    YAMLCompilerLoader,
    YAMLCompilerNotFoundError,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory structure."""
    compilers_dir = tmp_path / "data" / "compilers"
    layers_dir = tmp_path / "data" / "layers" / "linker"
    compilers_dir.mkdir(parents=True)
    layers_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def basic_compiler_yaml(temp_data_dir):
    """Create a basic compiler YAML file."""
    yaml_content = """
name: test-compiler
version: "1.0"
compiler_family: gcc
language_support:
  c: {min_standard: c11, max_standard: c23}
  cpp: {min_standard: cpp11, max_standard: cpp23}

flags:
  common: ["-Wall", "-Wextra"]
  debug: ["-g", "-O0"]
  release: ["-O3", "-DNDEBUG"]
  relwithdebinfo: ["-g", "-O2"]
  minsizerel: ["-Os", "-DNDEBUG"]

language_standards:
  cpp:
    cpp11: "-std=c++11"
    cpp14: "-std=c++14"
    cpp17: "-std=c++17"
    cpp20: "-std=c++20"
  c:
    c11: "-std=c11"
    c17: "-std=c17"

warning_levels:
  "off": ["-w"]
  minimal: ["-Wall"]
  standard: ["-Wall", "-Wextra"]
  strict: ["-Wall", "-Wextra", "-Wpedantic"]
  paranoid: ["-Wall", "-Wextra", "-Wpedantic", "-Werror"]

cmake_variables:
  CMAKE_C_COMPILER: "{{toolchain_root}}/bin/gcc"
  CMAKE_CXX_COMPILER: "{{toolchain_root}}/bin/g++"
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "test-compiler.yaml"
    compiler_file.write_text(yaml_content)
    return temp_data_dir


@pytest.fixture
def compiler_with_composition(temp_data_dir):
    """Create compiler YAMLs with composition."""
    # Base compiler
    base_yaml = """
name: base-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]
  debug: ["-g"]
  release: ["-O3"]

cmake_variables:
  CMAKE_C_COMPILER: "gcc"
"""
    base_file = temp_data_dir / "data" / "compilers" / "base-compiler.yaml"
    base_file.write_text(base_yaml)

    # Derived compiler
    derived_yaml = """
name: derived-compiler
version: "2.0"
extends: base-compiler

flags:
  common: ["-Wextra"]  # Appended to base
  debug: ["-O0"]       # Appended to base
  relwithdebinfo: ["-g", "-O2"]  # New flag

cmake_variables:
  CMAKE_CXX_COMPILER: "g++"
"""
    derived_file = temp_data_dir / "data" / "compilers" / "derived-compiler.yaml"
    derived_file.write_text(derived_yaml)
    return temp_data_dir


@pytest.fixture
def compiler_with_platform_overrides(temp_data_dir):
    """Create compiler YAML with platform overrides."""
    yaml_content = """
name: cross-platform-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]
  debug: ["-g"]
  release: ["-O3"]

cmake_variables:
  CMAKE_C_COMPILER: "gcc"

platform_overrides:
  windows:
    flags:
      common: ["-Wall", "-DWIN32"]
    cmake_variables:
      CMAKE_C_COMPILER: "gcc.exe"
  linux:
    flags:
      common: ["-Wall", "-DLINUX"]
  darwin:
    flags:
      common: ["-Wall", "-DMACOS"]
"""
    compiler_file = (
        temp_data_dir / "data" / "compilers" / "cross-platform-compiler.yaml"
    )
    compiler_file.write_text(yaml_content)
    return temp_data_dir


@pytest.fixture
def compiler_with_stdlib(temp_data_dir):
    """Create compiler YAML with standard library configurations."""
    yaml_content = """
name: stdlib-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]

stdlib:
  libstdc++:
    description: "GNU Standard C++ Library"
    compile_flags: []
    defines: []
  libc++:
    description: "LLVM libc++"
    compile_flags: ["-stdlib=libc++"]
    defines: ["_LIBCPP_VERSION"]
    link_flags: ["-lc++", "-lc++abi"]
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "stdlib-compiler.yaml"
    compiler_file.write_text(yaml_content)
    return temp_data_dir


@pytest.fixture
def compiler_with_linker(temp_data_dir):
    """Create compiler YAML with linker configurations."""
    # Create linker layer
    linker_yaml = """
name: test-linker
description: "Test linker"

flag: "-fuse-ld=test"

supported_platforms: ["linux", "windows"]
"""
    linker_file = temp_data_dir / "data" / "layers" / "linker" / "test-linker.yaml"
    linker_file.write_text(linker_yaml)

    # Create compiler
    compiler_yaml = """
name: linker-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]

linker:
  default: test-linker
  available: [test-linker]
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "linker-compiler.yaml"
    compiler_file.write_text(compiler_yaml)
    return temp_data_dir


@pytest.fixture
def compiler_with_sanitizers(temp_data_dir):
    """Create compiler YAML with sanitizer support."""
    yaml_content = """
name: sanitizer-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]

features:
  sanitizers:
    address:
      compile_flags: ["-fsanitize=address"]
      defines: ["__SANITIZE_ADDRESS__"]
      link_flags: ["-fsanitize=address"]
    thread:
      compile_flags: ["-fsanitize=thread"]
      link_flags: ["-fsanitize=thread"]
    undefined:
      compile_flags: ["-fsanitize=undefined"]
      link_flags: ["-fsanitize=undefined"]
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "sanitizer-compiler.yaml"
    compiler_file.write_text(yaml_content)
    return temp_data_dir


@pytest.fixture
def compiler_with_lto(temp_data_dir):
    """Create compiler YAML with LTO support."""
    yaml_content = """
name: lto-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]

features:
  lto:
    full:
      compile_flags: ["-flto"]
      link_flags: ["-flto"]
    thin:
      compile_flags: ["-flto=thin"]
      link_flags: ["-flto=thin"]
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "lto-compiler.yaml"
    compiler_file.write_text(yaml_content)
    return temp_data_dir


@pytest.fixture
def compiler_with_coverage(temp_data_dir):
    """Create compiler YAML with coverage support."""
    yaml_content = """
name: coverage-compiler
version: "1.0"
compiler_family: gcc

flags:
  common: ["-Wall"]

features:
  coverage:
    flags: ["--coverage"]
    link_flags: ["--coverage"]
"""
    compiler_file = temp_data_dir / "data" / "compilers" / "coverage-compiler.yaml"
    compiler_file.write_text(yaml_content)
    return temp_data_dir


class TestYAMLCompilerLoader:
    """Test YAMLCompilerLoader class."""

    def test_load_basic_compiler(self, basic_compiler_yaml):
        """Test loading a basic compiler configuration."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        assert config is not None
        assert config._config["name"] == "test-compiler"
        assert config._config["version"] == "1.0"
        assert config._config["compiler_family"] == "gcc"

    def test_load_nonexistent_compiler(self, temp_data_dir):
        """Test loading a non-existent compiler raises error."""
        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        with pytest.raises(YAMLCompilerNotFoundError):
            loader.load("nonexistent-compiler")

    def test_load_with_composition(self, compiler_with_composition):
        """Test loading compiler with composition."""
        loader = YAMLCompilerLoader(str(compiler_with_composition / "data"))
        config = loader.load("derived-compiler")

        # Should have merged flags from base
        common_flags = config.get_flags_for_build_type("common")
        assert "-Wall" in common_flags
        assert "-Wextra" in common_flags

        debug_flags = config.get_flags_for_build_type("debug")
        assert "-g" in debug_flags
        assert "-O0" in debug_flags

        # New flag from derived
        relwithdebinfo_flags = config.get_flags_for_build_type("relwithdebinfo")
        assert "-g" in relwithdebinfo_flags
        assert "-O2" in relwithdebinfo_flags

    def test_load_with_platform_override_linux(self, compiler_with_platform_overrides):
        """Test loading compiler with Linux platform override."""
        loader = YAMLCompilerLoader(str(compiler_with_platform_overrides / "data"))
        config = loader.load("cross-platform-compiler", platform="linux")

        common_flags = config.get_flags_for_build_type("common")
        assert "-Wall" in common_flags
        assert "-DLINUX" in common_flags
        assert "-DWIN32" not in common_flags

    def test_load_with_platform_override_windows(
        self, compiler_with_platform_overrides
    ):
        """Test loading compiler with Windows platform override."""
        loader = YAMLCompilerLoader(str(compiler_with_platform_overrides / "data"))
        config = loader.load("cross-platform-compiler", platform="windows")

        common_flags = config.get_flags_for_build_type("common")
        assert "-Wall" in common_flags
        assert "-DWIN32" in common_flags
        assert "-DLINUX" not in common_flags

        cmake_vars = config.get_cmake_variables("/toolchain")
        assert cmake_vars["CMAKE_C_COMPILER"] == "gcc.exe"

    def test_caching(self, basic_compiler_yaml):
        """Test that loader caches configurations."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config1 = loader.load("test-compiler")
        config2 = loader.load("test-compiler")

        assert config1 is config2  # Same object due to caching

    def test_list_available(self, basic_compiler_yaml):
        """Test listing available compilers."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        available = loader.list_available()

        assert "test-compiler" in available
        assert len(available) == 1

    def test_invalid_yaml(self, temp_data_dir):
        """Test loading invalid YAML raises error."""
        invalid_yaml = temp_data_dir / "data" / "compilers" / "invalid.yaml"
        invalid_yaml.write_text("{ invalid yaml content")

        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        with pytest.raises(YAMLCompilerInvalidError):
            loader.load("invalid")

    def test_missing_required_fields(self, temp_data_dir):
        """Test loading YAML with missing required fields raises error."""
        incomplete_yaml = temp_data_dir / "data" / "compilers" / "incomplete.yaml"
        incomplete_yaml.write_text(
            """
name: incomplete
# Missing compiler_family
flags:
  common: ["-Wall"]
"""
        )

        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        with pytest.raises(YAMLCompilerInvalidError):
            loader.load("incomplete")

    def test_circular_extends(self, temp_data_dir):
        """Test that circular extends relationships are detected."""
        yaml1 = temp_data_dir / "data" / "compilers" / "circular1.yaml"
        yaml1.write_text(
            """
name: circular1
extends: circular2
compiler_family: gcc
flags:
  common: ["-Wall"]
"""
        )

        yaml2 = temp_data_dir / "data" / "compilers" / "circular2.yaml"
        yaml2.write_text(
            """
name: circular2
extends: circular1
compiler_family: gcc
flags:
  common: ["-Wall"]
"""
        )

        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        with pytest.raises(YAMLCompilerError, match="Circular.*extends"):
            loader.load("circular1")


class TestYAMLCompilerConfig:
    """Test YAMLCompilerConfig class."""

    def test_get_flags_for_build_type(self, basic_compiler_yaml):
        """Test getting flags for different build types."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        debug_flags = config.get_flags_for_build_type("debug")
        assert "-g" in debug_flags
        assert "-O0" in debug_flags

        release_flags = config.get_flags_for_build_type("release")
        assert "-O3" in release_flags
        assert "-DNDEBUG" in release_flags

        # Unknown build type should return empty list
        unknown_flags = config.get_flags_for_build_type("unknown")
        assert unknown_flags == []

    def test_get_warning_flags(self, basic_compiler_yaml):
        """Test getting warning flags for different levels."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        off_flags = config.get_warning_flags("off")
        assert "-w" in off_flags

        standard_flags = config.get_warning_flags("standard")
        assert "-Wall" in standard_flags
        assert "-Wextra" in standard_flags

        paranoid_flags = config.get_warning_flags("paranoid")
        assert "-Wall" in paranoid_flags
        assert "-Wextra" in paranoid_flags
        assert "-Wpedantic" in paranoid_flags
        assert "-Werror" in paranoid_flags

        # Unknown level should return empty list
        unknown_flags = config.get_warning_flags("unknown")
        assert unknown_flags == []

    def test_get_standard_flag(self, basic_compiler_yaml):
        """Test getting language standard flags."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        cpp17_flag = config.get_standard_flag("cpp", "cpp17")
        assert cpp17_flag == "-std=c++17"

        c11_flag = config.get_standard_flag("c", "c11")
        assert c11_flag == "-std=c11"

        # Unknown standard should return None
        unknown_flag = config.get_standard_flag("cpp", "cpp99")
        assert unknown_flag is None

        # Unknown language should return None
        unknown_lang = config.get_standard_flag("fortran", "f90")
        assert unknown_lang is None

    def test_get_stdlib_flags(self, compiler_with_stdlib):
        """Test getting standard library flags."""
        loader = YAMLCompilerLoader(str(compiler_with_stdlib / "data"))
        config = loader.load("stdlib-compiler")

        # libstdc++ should have no flags
        libstdcpp_flags = config.get_stdlib_flags("libstdc++")
        assert libstdcpp_flags == {"compile_flags": [], "defines": [], "link_flags": []}

        # libc++ should have specific flags
        libcpp_flags = config.get_stdlib_flags("libc++")
        assert "-stdlib=libc++" in libcpp_flags["compile_flags"]
        assert "_LIBCPP_VERSION" in libcpp_flags["defines"]
        assert "-lc++" in libcpp_flags["link_flags"]
        assert "-lc++abi" in libcpp_flags["link_flags"]

        # Unknown stdlib should return None
        unknown_stdlib = config.get_stdlib_flags("unknown")
        assert unknown_stdlib is None

    def test_get_linker_flag(self, compiler_with_linker):
        """Test getting linker flags."""
        loader = YAMLCompilerLoader(str(compiler_with_linker / "data"))
        config = loader.load("linker-compiler")

        linker_flag = config.get_linker_flag("test-linker")
        assert linker_flag == "-fuse-ld=test"

        # Unknown linker should return None
        unknown_linker = config.get_linker_flag("unknown-linker")
        assert unknown_linker is None

    def test_get_sanitizer_flags(self, compiler_with_sanitizers):
        """Test getting sanitizer flags."""
        loader = YAMLCompilerLoader(str(compiler_with_sanitizers / "data"))
        config = loader.load("sanitizer-compiler")

        asan_flags = config.get_sanitizer_flags("address")
        assert "-fsanitize=address" in asan_flags["compile_flags"]
        assert "__SANITIZE_ADDRESS__" in asan_flags["defines"]
        assert "-fsanitize=address" in asan_flags["link_flags"]

        tsan_flags = config.get_sanitizer_flags("thread")
        assert "-fsanitize=thread" in tsan_flags["compile_flags"]
        assert "-fsanitize=thread" in tsan_flags["link_flags"]

        # Unknown sanitizer should return None
        unknown_san = config.get_sanitizer_flags("memory")
        assert unknown_san is None

    def test_get_lto_flags(self, compiler_with_lto):
        """Test getting LTO flags."""
        loader = YAMLCompilerLoader(str(compiler_with_lto / "data"))
        config = loader.load("lto-compiler")

        full_lto = config.get_lto_flags("full")
        assert "-flto" in full_lto["compile_flags"]
        assert "-flto" in full_lto["link_flags"]

        thin_lto = config.get_lto_flags("thin")
        assert "-flto=thin" in thin_lto["compile_flags"]
        assert "-flto=thin" in thin_lto["link_flags"]

        # Unknown LTO type should return None
        unknown_lto = config.get_lto_flags("unknown")
        assert unknown_lto is None

    def test_get_coverage_flags(self, compiler_with_coverage):
        """Test getting coverage flags."""
        loader = YAMLCompilerLoader(str(compiler_with_coverage / "data"))
        config = loader.load("coverage-compiler")

        coverage_flags = config.get_coverage_flags()
        assert "--coverage" in coverage_flags

    def test_get_cmake_variables(self, basic_compiler_yaml):
        """Test getting CMake variables."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        cmake_vars = config.get_cmake_variables("/opt/toolchain")
        assert "CMAKE_C_COMPILER" in cmake_vars
        assert cmake_vars["CMAKE_C_COMPILER"] == "/opt/toolchain/bin/gcc"
        assert "CMAKE_CXX_COMPILER" in cmake_vars
        assert cmake_vars["CMAKE_CXX_COMPILER"] == "/opt/toolchain/bin/g++"

    def test_interpolate_variables_simple(self, basic_compiler_yaml):
        """Test simple variable interpolation."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        result = config.interpolate_variables(
            "{{toolchain_root}}/bin", toolchain_root="/opt/gcc"
        )
        assert result == "/opt/gcc/bin"

    def test_interpolate_variables_multiple(self, basic_compiler_yaml):
        """Test multiple variable interpolation."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        result = config.interpolate_variables(
            "{{toolchain_root}}/{{version}}/bin",
            toolchain_root="/opt/gcc",
            version="13.2.0",
        )
        assert result == "/opt/gcc/13.2.0/bin"

    def test_interpolate_variables_list(self, basic_compiler_yaml):
        """Test variable interpolation in lists."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        result = config.interpolate_variables(
            ["{{toolchain_root}}/bin/gcc", "{{toolchain_root}}/bin/g++"],
            toolchain_root="/opt/gcc",
        )
        assert result == ["/opt/gcc/bin/gcc", "/opt/gcc/bin/g++"]

    def test_interpolate_variables_dict(self, basic_compiler_yaml):
        """Test variable interpolation in dictionaries."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        result = config.interpolate_variables(
            {
                "compiler": "{{toolchain_root}}/bin/gcc",
                "flags": ["-I{{toolchain_root}}/include"],
            },
            toolchain_root="/opt/gcc",
        )
        assert result["compiler"] == "/opt/gcc/bin/gcc"
        assert result["flags"] == ["-I/opt/gcc/include"]

    def test_interpolate_variables_missing(self, basic_compiler_yaml):
        """Test interpolation with missing variables."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))
        config = loader.load("test-compiler")

        # Missing variable should be left as-is
        result = config.interpolate_variables("{{toolchain_root}}/bin")
        assert result == "{{toolchain_root}}/bin"


class TestYAMLCompilerIntegration:
    """Integration tests for YAML compiler system."""

    def test_full_compiler_lifecycle(self, basic_compiler_yaml):
        """Test complete lifecycle: load, configure, get flags."""
        loader = YAMLCompilerLoader(str(basic_compiler_yaml / "data"))

        # List available compilers
        available = loader.list_available()
        assert "test-compiler" in available

        # Load compiler
        config = loader.load("test-compiler")
        assert config is not None

        # Get various flags
        debug_flags = config.get_flags_for_build_type("debug")
        assert len(debug_flags) > 0

        warning_flags = config.get_warning_flags("standard")
        assert len(warning_flags) > 0

        standard_flag = config.get_standard_flag("cpp", "cpp17")
        assert standard_flag is not None

        # Get CMake variables
        cmake_vars = config.get_cmake_variables("/toolchain")
        assert len(cmake_vars) > 0

    def test_composition_chain(self, temp_data_dir):
        """Test multi-level composition chain."""
        # Create base compiler
        base_yaml = """
name: base
compiler_family: gcc
flags:
  common: ["-Wall"]
cmake_variables:
  CMAKE_C_COMPILER: "gcc"
"""
        (temp_data_dir / "data" / "compilers" / "base.yaml").write_text(base_yaml)

        # Create middle compiler
        middle_yaml = """
name: middle
extends: base
flags:
  common: ["-Wextra"]
  debug: ["-g"]
"""
        (temp_data_dir / "data" / "compilers" / "middle.yaml").write_text(middle_yaml)

        # Create derived compiler
        derived_yaml = """
name: derived
extends: middle
flags:
  common: ["-Wpedantic"]
  debug: ["-O0"]
  release: ["-O3"]
"""
        (temp_data_dir / "data" / "compilers" / "derived.yaml").write_text(derived_yaml)

        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        config = loader.load("derived")

        # Should have all flags from base -> middle -> derived
        common_flags = config.get_flags_for_build_type("common")
        assert "-Wall" in common_flags
        assert "-Wextra" in common_flags
        assert "-Wpedantic" in common_flags

        debug_flags = config.get_flags_for_build_type("debug")
        assert "-g" in debug_flags
        assert "-O0" in debug_flags

        release_flags = config.get_flags_for_build_type("release")
        assert "-O3" in release_flags

    def test_platform_override_precedence(self, temp_data_dir):
        """Test that platform overrides have correct precedence."""
        yaml_content = """
name: override-test
extends: base
compiler_family: gcc

flags:
  common: ["-Wall"]
  debug: ["-g"]

platform_overrides:
  linux:
    flags:
      debug: ["-O0"]  # Override debug flags on Linux
"""
        (temp_data_dir / "data" / "compilers" / "override-test.yaml").write_text(
            yaml_content
        )

        base_yaml = """
name: base
compiler_family: gcc
flags:
  common: ["-W"]
  debug: ["-ggdb"]
"""
        (temp_data_dir / "data" / "compilers" / "base.yaml").write_text(base_yaml)

        loader = YAMLCompilerLoader(str(temp_data_dir / "data"))
        config = loader.load("override-test", platform="linux")

        # Debug flags should be overridden on Linux
        debug_flags = config.get_flags_for_build_type("debug")
        assert "-O0" in debug_flags
        assert "-g" not in debug_flags  # Replaced by platform override

        # Common flags should still include base flags
        common_flags = config.get_flags_for_build_type("common")
        assert "-W" in common_flags
        assert "-Wall" in common_flags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
