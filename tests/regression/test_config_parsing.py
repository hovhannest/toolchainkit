"""
Regression tests for configuration parsing.

Ensures config file format remains backward compatible.
"""

import pytest
from toolchainkit.config.parser import (
    parse_config,
    ConfigError,
    ToolchainKitConfig,
)


@pytest.mark.regression
class TestLegacyConfigCompatibility:
    """Test backward compatibility with config formats."""

    def test_parse_minimal_valid_config(self, tmp_path):
        """Verify minimal valid config parses correctly."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert config.version == 1
        assert len(config.toolchains) == 1
        assert config.toolchains[0].name == "llvm-18"
        assert config.toolchains[0].type == "clang"
        assert config.toolchains[0].version == "18.1.8"

    def test_parse_config_with_all_optional_fields(self, tmp_path):
        """Verify config with all optional fields works."""
        config_content = """version: 1
project: my-project
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    stdlib: libc++
    source: prebuilt
    require_installed: false

defaults:
  linux: llvm-18
  windows: llvm-18

toolchain_cache:
  location: shared

build:
  backend: ninja
  parallel: auto
  caching:
    enabled: true
    tool: ccache
    directory: ~/.cache/ccache

modules:
  - core
  - cmake
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert config.version == 1
        assert config.project == "my-project"
        assert len(config.toolchains) == 1
        assert config.toolchains[0].stdlib == "libc++"
        assert config.defaults["linux"] == "llvm-18"
        assert config.build.backend == "ninja"
        assert config.build.caching.enabled is True
        assert config.modules == ["core", "cmake"]

    def test_parse_config_with_multiple_toolchains(self, tmp_path):
        """Verify multiple toolchains can be specified."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  - name: gcc-13
    type: gcc
    version: 13.2.0
  - name: msvc-19
    type: msvc
    version: 19.38.0
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert len(config.toolchains) == 3
        assert config.toolchains[0].name == "llvm-18"
        assert config.toolchains[0].type == "clang"
        assert config.toolchains[1].name == "gcc-13"
        assert config.toolchains[1].type == "gcc"
        assert config.toolchains[2].name == "msvc-19"
        assert config.toolchains[2].type == "msvc"

    def test_parse_config_with_cross_compilation_targets(self, tmp_path):
        """Verify cross-compilation target specification."""
        config_content = """version: 1
toolchains:
  - name: android-ndk
    type: clang
    version: 18.1.8

targets:
  - os: android
    arch: arm64
    api_level: 28
  - os: ios
    arch: arm64
    sdk: iphoneos
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert len(config.targets) == 2
        assert config.targets[0].os == "android"
        assert config.targets[0].arch == "arm64"
        assert config.targets[0].api_level == 28
        assert config.targets[1].os == "ios"
        assert config.targets[1].sdk == "iphoneos"


@pytest.mark.regression
class TestConfigDefaultValues:
    """Test that default values remain consistent."""

    def test_default_build_backend(self, tmp_path):
        """Verify default build backend is 'ninja'."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: default should remain 'ninja'
        assert config.build.backend == "ninja"

    def test_default_parallel_setting(self, tmp_path):
        """Verify default parallel setting is 'auto'."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: default should remain 'auto'
        assert config.build.parallel == "auto"

    def test_default_caching_disabled(self, tmp_path):
        """Verify caching is disabled by default."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: caching should be disabled by default
        assert config.build.caching.enabled is False

    def test_default_toolchain_source(self, tmp_path):
        """Verify default toolchain source is 'prebuilt'."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: default source should be 'prebuilt'
        assert config.toolchains[0].source == "prebuilt"

    def test_default_modules(self, tmp_path):
        """Verify default modules are ['core', 'cmake']."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: default modules should be ['core', 'cmake']
        assert config.modules == ["core", "cmake"]

    def test_default_toolchain_cache_location(self, tmp_path):
        """Verify default toolchain cache location is 'shared'."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        # Regression: default cache location should be 'shared'
        assert config.toolchain_cache["location"] == "shared"


@pytest.mark.regression
class TestConfigSchemaValidation:
    """Test schema validation remains consistent."""

    def test_invalid_version_rejected(self, tmp_path):
        """Verify unsupported version numbers are rejected."""
        config_content = """version: 999
toolchains:
  - name: test
    type: clang
    version: 1.0
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Unsupported version"):
            parse_config(config_file)

    def test_missing_version_rejected(self, tmp_path):
        """Verify missing version field is rejected."""
        config_content = """toolchains:
  - name: test
    type: clang
    version: 1.0
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Missing required field: version"):
            parse_config(config_file)

    def test_missing_toolchains_rejected(self, tmp_path):
        """Verify missing toolchains field is rejected."""
        config_content = """version: 1
project: test
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="At least one toolchain must be defined"):
            parse_config(config_file)

    def test_empty_toolchains_rejected(self, tmp_path):
        """Verify empty toolchains list is rejected."""
        config_content = """version: 1
toolchains: []
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="At least one toolchain must be defined"):
            parse_config(config_file)

    def test_invalid_toolchain_type_rejected(self, tmp_path):
        """Verify invalid toolchain types are rejected."""
        config_content = """version: 1
toolchains:
  - name: invalid
    type: unknown-type
    version: 1.0.0
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid toolchain type"):
            parse_config(config_file)

    def test_missing_toolchain_name_rejected(self, tmp_path):
        """Verify toolchain without name is rejected."""
        config_content = """version: 1
toolchains:
  - type: clang
    version: 18.1.8
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="missing required field: name"):
            parse_config(config_file)

    def test_duplicate_toolchain_names_rejected(self, tmp_path):
        """Verify duplicate toolchain names are rejected."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  - name: llvm-18
    type: clang
    version: 18.1.9
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Duplicate toolchain name"):
            parse_config(config_file)

    def test_invalid_build_backend_rejected(self, tmp_path):
        """Verify invalid build backend is rejected."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: invalid-backend
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid build backend"):
            parse_config(config_file)

    def test_invalid_package_manager_rejected(self, tmp_path):
        """Verify invalid package manager is rejected."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: invalid-manager
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid package manager"):
            parse_config(config_file)

    def test_defaults_referencing_undefined_toolchain_rejected(self, tmp_path):
        """Verify defaults referencing undefined toolchains are rejected."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

defaults:
  linux: nonexistent-toolchain
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="references undefined toolchain"):
            parse_config(config_file)


@pytest.mark.regression
class TestConfigErrorHandling:
    """Test error handling remains consistent."""

    def test_nonexistent_file_error(self, tmp_path):
        """Verify appropriate error for nonexistent config file."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError, match="Configuration file not found"):
            parse_config(config_file)

    def test_empty_file_error(self, tmp_path):
        """Verify appropriate error for empty config file."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigError, match="Configuration file is empty"):
            parse_config(config_file)

    def test_invalid_yaml_syntax_error(self, tmp_path):
        """Verify appropriate error for invalid YAML syntax."""
        config_content = """version: 1
toolchains:
  - name: test
    type: clang
    version: 18.1.8
    invalid_indent
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid YAML syntax"):
            parse_config(config_file)

    def test_missing_target_os_rejected(self, tmp_path):
        """Verify targets without os field are rejected."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - arch: arm64
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError, match="must specify 'os' and 'arch'"):
            parse_config(config_file)


@pytest.mark.regression
class TestComplexConfigParsing:
    """Test complex configuration scenarios."""

    def test_config_with_all_toolchain_types(self, tmp_path):
        """Verify all valid toolchain types parse correctly."""
        config_content = """version: 1
toolchains:
  - name: clang-18
    type: clang
    version: 18.1.8
  - name: gcc-13
    type: gcc
    version: 13.2.0
  - name: msvc-19
    type: msvc
    version: 19.38.0
  - name: zig-0.12
    type: zig
    version: 0.12.0
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert len(config.toolchains) == 4
        types = [tc.type for tc in config.toolchains]
        assert "clang" in types
        assert "gcc" in types
        assert "msvc" in types
        assert "zig" in types

    def test_config_with_all_build_backends(self, tmp_path):
        """Verify all valid build backends parse correctly."""
        for backend in ["ninja", "make", "msbuild", "xcode"]:
            config_content = f"""version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: {backend}
"""
            config_file = tmp_path / f"config_{backend}.yaml"
            config_file.write_text(config_content)

            config = parse_config(config_file)
            assert config.build.backend == backend

    def test_config_with_package_managers(self, tmp_path):
        """Verify package manager configurations."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
  conan:
    version: 2.0
    profile: default
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.manager == "conan"
        assert config.packages.conan["version"] == 2.0

    def test_config_with_build_caching(self, tmp_path):
        """Verify build caching configuration."""
        config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: ninja
  parallel: 8
  caching:
    enabled: true
    tool: sccache
    directory: /cache/sccache
    remote:
      endpoint: cache.example.com
      bucket: my-builds
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert config.build.parallel == 8
        assert config.build.caching.enabled is True
        assert config.build.caching.tool == "sccache"
        assert config.build.caching.directory == "/cache/sccache"
        assert config.build.caching.remote["endpoint"] == "cache.example.com"

    def test_config_with_stdlib_specifications(self, tmp_path):
        """Verify stdlib can be specified per toolchain."""
        config_content = """version: 1
toolchains:
  - name: clang-libcxx
    type: clang
    version: 18.1.8
    stdlib: libc++
  - name: clang-libstdcxx
    type: clang
    version: 18.1.8
    stdlib: libstdc++
  - name: msvc-stdlib
    type: msvc
    version: 19.38.0
    stdlib: msvc
"""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert len(config.toolchains) == 3
        assert config.toolchains[0].stdlib == "libc++"
        assert config.toolchains[1].stdlib == "libstdc++"
        assert config.toolchains[2].stdlib == "msvc"


@pytest.mark.regression
def test_config_return_type_consistency(tmp_path):
    """
    Verify parse_config always returns ToolchainKitConfig.

    This ensures the API contract is maintained.
    """
    config_content = """version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(config_content)

    config = parse_config(config_file)

    assert isinstance(config, ToolchainKitConfig)
    assert hasattr(config, "version")
    assert hasattr(config, "toolchains")
    assert hasattr(config, "build")
    assert hasattr(config, "modules")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
