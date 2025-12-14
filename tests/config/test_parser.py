"""Unit tests for configuration parser."""

import pytest
from pathlib import Path
from toolchainkit.config.parser import (
    parse_config,
    ConfigError,
)


@pytest.mark.unit
def test_parse_basic_config(tmp_path):
    """Test parsing basic configuration."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
project: test

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.version == 1
    assert config.project == "test"
    assert len(config.toolchains) == 1
    assert config.toolchains[0].name == "llvm-18"
    assert config.toolchains[0].type == "clang"
    assert config.toolchains[0].version == "18.1.8"


@pytest.mark.unit
def test_parse_complete_config(tmp_path):
    """Test parsing complete configuration with all fields."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
project: complete

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    stdlib: libc++
    source: prebuilt
  - name: gcc-13
    type: gcc
    version: 13.2.0

defaults:
  linux: gcc-13
  macos: llvm-18

toolchain_cache:
  location: shared
  path: ~/.toolchainkit

packages:
  manager: conan
  conan:
    version: 2.0

build:
  backend: ninja
  parallel: auto
  caching:
    enabled: true
    tool: sccache

targets:
  - os: android
    arch: arm64
    api_level: 29

modules:
  - core
  - cmake
  - caching
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.version == 1
    assert config.project == "complete"
    assert len(config.toolchains) == 2
    assert config.defaults["linux"] == "gcc-13"
    assert config.defaults["macos"] == "llvm-18"
    assert config.toolchain_cache["location"] == "shared"
    assert config.packages.manager == "conan"
    assert config.build.backend == "ninja"
    assert config.build.caching.enabled is True
    assert config.build.caching.tool == "sccache"
    assert len(config.targets) == 1
    assert config.targets[0].os == "android"
    assert config.targets[0].api_level == 29
    assert "caching" in config.modules


@pytest.mark.unit
def test_parse_missing_file():
    """Test parsing non-existent file raises error."""
    # Arrange
    config_file = Path("/nonexistent/toolchainkit.yaml")

    # Act & Assert
    with pytest.raises(ConfigError, match="Configuration file not found"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_invalid_yaml(tmp_path):
    """Test parsing invalid YAML syntax raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: test
    type: clang
  bad indentation
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Invalid YAML syntax"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_empty_file(tmp_path):
    """Test parsing empty file raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text("")

    # Act & Assert
    with pytest.raises(ConfigError, match="Configuration file is empty"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_missing_version(tmp_path):
    """Test missing version field raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Missing required field: version"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_unsupported_version(tmp_path):
    """Test unsupported version raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 999
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Unsupported version: 999"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_missing_toolchains(tmp_path):
    """Test missing toolchains raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
project: test
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="At least one toolchain must be defined"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_empty_toolchains(tmp_path):
    """Test empty toolchains list raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains: []
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="At least one toolchain must be defined"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_toolchain_missing_name(tmp_path):
    """Test toolchain missing name raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - type: clang
    version: 18.1.8
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Toolchain missing required field: name"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_toolchain_missing_type(tmp_path):
    """Test toolchain missing type raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    version: 18.1.8
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Toolchain missing required field: type"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_toolchain_missing_version(tmp_path):
    """Test toolchain missing version raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Toolchain missing required field: version"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_toolchain_invalid_type(tmp_path):
    """Test invalid toolchain type raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: test
    type: invalid
    version: 1.0.0
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Invalid toolchain type: invalid"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_duplicate_toolchain_names(tmp_path):
    """Test duplicate toolchain names raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  - name: llvm-18
    type: clang
    version: 18.1.7
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Duplicate toolchain name: llvm-18"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_defaults_invalid_reference(tmp_path):
    """Test defaults referencing undefined toolchain raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

defaults:
  linux: gcc-13
"""
    )

    # Act & Assert
    with pytest.raises(
        ConfigError, match="defaults.linux references undefined toolchain: gcc-13"
    ):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_invalid_build_backend(tmp_path):
    """Test invalid build backend raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: invalid
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Invalid build backend: invalid"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_invalid_package_manager(tmp_path):
    """Test invalid package manager raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: invalid
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError, match="Invalid package manager: invalid"):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_target_missing_os(tmp_path):
    """Test cross-compilation target missing os raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - arch: arm64
"""
    )

    # Act & Assert
    with pytest.raises(
        ConfigError, match="Cross-compilation target must specify 'os' and 'arch'"
    ):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_target_missing_arch(tmp_path):
    """Test cross-compilation target missing arch raises error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: android
"""
    )

    # Act & Assert
    with pytest.raises(
        ConfigError, match="Cross-compilation target must specify 'os' and 'arch'"
    ):
        parse_config(config_file)


@pytest.mark.unit
def test_parse_default_values(tmp_path):
    """Test default values are applied correctly."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert - Check defaults
    assert config.toolchain_cache["location"] == "shared"
    assert config.build.backend == "ninja"
    assert config.build.parallel == "auto"
    assert config.modules == ["core", "cmake"]
    assert config.build.caching.enabled is False
    assert config.toolchains[0].source == "prebuilt"
    assert config.toolchains[0].require_installed is False


@pytest.mark.unit
def test_parse_toolchain_with_stdlib(tmp_path):
    """Test parsing toolchain with stdlib specification."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    stdlib: libc++
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.toolchains[0].stdlib == "libc++"


@pytest.mark.unit
def test_parse_toolchain_require_installed(tmp_path):
    """Test parsing toolchain with require_installed flag."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: system-gcc
    type: gcc
    version: 13.2.0
    require_installed: true
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.toolchains[0].require_installed is True


@pytest.mark.unit
def test_parse_build_with_caching(tmp_path):
    """Test parsing build configuration with caching."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: ninja
  caching:
    enabled: true
    tool: sccache
    directory: /tmp/cache
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.build.caching.enabled is True
    assert config.build.caching.tool == "sccache"
    assert config.build.caching.directory == "/tmp/cache"


@pytest.mark.unit
def test_parse_cross_compilation_targets(tmp_path):
    """Test parsing cross-compilation targets."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: android
    arch: arm64
    api_level: 29
    toolchain: llvm-18
  - os: ios
    arch: arm64
    sdk: iphoneos
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert len(config.targets) == 2
    assert config.targets[0].os == "android"
    assert config.targets[0].arch == "arm64"
    assert config.targets[0].api_level == 29
    assert config.targets[0].toolchain == "llvm-18"
    assert config.targets[1].os == "ios"
    assert config.targets[1].sdk == "iphoneos"


@pytest.mark.unit
def test_parse_packages_conan_config(tmp_path):
    """Test parsing Conan package manager configuration."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
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
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.packages.manager == "conan"
    assert config.packages.conan["version"] == 2.0
    assert config.packages.conan["profile"] == "default"


@pytest.mark.unit
def test_parse_packages_vcpkg_config(tmp_path):
    """Test parsing vcpkg package manager configuration."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: vcpkg
  vcpkg:
    manifest_mode: true
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.packages.manager == "vcpkg"
    assert config.packages.vcpkg["manifest_mode"] is True


@pytest.mark.unit
def test_parse_custom_modules(tmp_path):
    """Test parsing custom modules list."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

modules:
  - core
  - cmake
  - caching
  - packages
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.modules == ["core", "cmake", "caching", "packages"]


@pytest.mark.unit
def test_parse_legacy_toolchain_dir_relative(tmp_path):
    """Test parsing legacy toolchain_dir field with relative path."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

toolchain_dir: .toolchainkit
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.toolchain_cache["location"] == "local"
    assert config.toolchain_cache["path"] == ".toolchainkit"


@pytest.mark.unit
def test_parse_legacy_toolchain_dir_absolute(tmp_path):
    """Test parsing legacy toolchain_dir field with absolute path."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

toolchain_dir: /custom/toolchains
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.toolchain_cache["location"] == "custom"
    assert config.toolchain_cache["path"] == "/custom/toolchains"


@pytest.mark.unit
def test_parse_legacy_cache_dir(tmp_path):
    """Test parsing legacy cache_dir field."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

cache_dir: .toolchainkit
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.toolchain_cache["location"] == "local"
    assert config.toolchain_cache["path"] == ".toolchainkit"


@pytest.mark.unit
def test_parse_toolchain_cache_takes_precedence(tmp_path):
    """Test that toolchain_cache takes precedence over legacy fields."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

toolchain_dir: .toolchainkit
cache_dir: .cache
toolchain_cache:
  location: shared
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert - toolchain_cache should take precedence
    assert config.toolchain_cache["location"] == "shared"


@pytest.mark.unit
def test_parse_build_with_custom_flags(tmp_path):
    """Test parsing build configuration with custom compiler and linker flags."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  backend: ninja
  flags:
    cxx: -fsanitize=address -fno-omit-frame-pointer -g
    linker: -fsanitize=address
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.build.flags is not None
    assert config.build.flags["cxx"] == "-fsanitize=address -fno-omit-frame-pointer -g"
    assert config.build.flags["linker"] == "-fsanitize=address"


@pytest.mark.unit
def test_parse_build_with_all_flag_types(tmp_path):
    """Test parsing build configuration with all types of custom flags."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

build:
  backend: ninja
  flags:
    cxx: -Wall -Wextra
    c: -Wall -Wpedantic
    linker: -flto
    exe_linker: -pie
    shared_linker: -shared
"""
    )

    # Act
    config = parse_config(config_file)

    # Assert
    assert config.build.flags is not None
    assert config.build.flags["cxx"] == "-Wall -Wextra"
    assert config.build.flags["c"] == "-Wall -Wpedantic"
    assert config.build.flags["linker"] == "-flto"
    assert config.build.flags["exe_linker"] == "-pie"
    assert config.build.flags["shared_linker"] == "-shared"


@pytest.mark.unit
def test_parse_build_with_invalid_flag_key(tmp_path):
    """Test that invalid flag keys raise a ConfigError."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  flags:
    invalid_key: -Wall
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "Invalid flag keys" in str(exc_info.value)
    assert "invalid_key" in str(exc_info.value)


@pytest.mark.unit
def test_parse_build_with_non_dict_flags(tmp_path):
    """Test that non-dict flags raise a ConfigError."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

build:
  flags: "-Wall -Wextra"
"""
    )

    # Act & Assert
    with pytest.raises(ConfigError) as exc_info:
        parse_config(config_file)

    assert "build.flags must be a dictionary" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
