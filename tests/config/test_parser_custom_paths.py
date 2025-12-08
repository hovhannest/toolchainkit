"""
Unit tests for config parser with custom paths support.

Tests the new features in config parser including:
- custom_paths in ToolchainConfig
- use_system, custom_path, conan_home, vcpkg_root in PackageManagerConfig
"""

import pytest

from toolchainkit.config.parser import (
    parse_config,
    ConfigError,
)


# =============================================================================
# Test Custom Paths in Toolchain Config
# =============================================================================


class TestToolchainCustomPaths:
    """Test custom_paths field in toolchain configuration."""

    def test_toolchain_with_custom_paths(self, tmp_path):
        """Test parsing toolchain with custom component paths."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    custom_paths:
      compiler: /custom/path/to/clang++
      linker: /custom/path/to/lld
      ar: /custom/path/to/llvm-ar
"""
        )

        config = parse_config(config_file)

        assert len(config.toolchains) == 1
        toolchain = config.toolchains[0]
        assert toolchain.custom_paths is not None
        assert toolchain.custom_paths["compiler"] == "/custom/path/to/clang++"
        assert toolchain.custom_paths["linker"] == "/custom/path/to/lld"
        assert toolchain.custom_paths["ar"] == "/custom/path/to/llvm-ar"

    def test_toolchain_without_custom_paths(self, tmp_path):
        """Test parsing toolchain without custom paths."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
"""
        )

        config = parse_config(config_file)

        assert len(config.toolchains) == 1
        toolchain = config.toolchains[0]
        assert toolchain.custom_paths is None

    def test_toolchain_with_empty_custom_paths(self, tmp_path):
        """Test parsing toolchain with empty custom_paths."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    custom_paths: {}
"""
        )

        config = parse_config(config_file)

        assert len(config.toolchains) == 1
        toolchain = config.toolchains[0]
        assert toolchain.custom_paths == {}

    def test_toolchain_custom_paths_invalid_type(self, tmp_path):
        """Test error when custom_paths is not a dictionary."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    custom_paths: "invalid"
"""
        )

        with pytest.raises(ConfigError) as exc_info:
            parse_config(config_file)

        assert "custom_paths must be a dictionary" in str(exc_info.value)

    def test_multiple_toolchains_with_custom_paths(self, tmp_path):
        """Test parsing multiple toolchains with different custom paths."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    custom_paths:
      compiler: /opt/llvm-18/bin/clang++

  - name: gcc-13
    type: gcc
    version: 13.2.0
    custom_paths:
      compiler: /usr/local/gcc-13/bin/g++
      linker: /usr/local/gcc-13/bin/ld
"""
        )

        config = parse_config(config_file)

        assert len(config.toolchains) == 2

        llvm_tc = config.toolchains[0]
        assert llvm_tc.custom_paths["compiler"] == "/opt/llvm-18/bin/clang++"

        gcc_tc = config.toolchains[1]
        assert gcc_tc.custom_paths["compiler"] == "/usr/local/gcc-13/bin/g++"
        assert gcc_tc.custom_paths["linker"] == "/usr/local/gcc-13/bin/ld"


# =============================================================================
# Test Package Manager Custom Configuration
# =============================================================================


class TestPackageManagerCustomConfig:
    """Test custom configuration fields in package manager config."""

    def test_conan_with_use_system(self, tmp_path):
        """Test parsing Conan config with use_system flag."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
  use_system: true
  conan:
    version: 2.0
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.manager == "conan"
        assert config.packages.use_system is True

    def test_conan_with_custom_path(self, tmp_path):
        """Test parsing Conan config with custom path."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
  use_system: false
  custom_path: /custom/conan/path
  conan:
    version: 2.0
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.use_system is False
        assert config.packages.custom_path == "/custom/conan/path"

    def test_conan_with_conan_home(self, tmp_path):
        """Test parsing Conan config with custom CONAN_HOME."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
  conan_home: /custom/conan/home
  conan:
    version: 2.0
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.conan_home == "/custom/conan/home"

    def test_vcpkg_with_vcpkg_root(self, tmp_path):
        """Test parsing vcpkg config with custom VCPKG_ROOT."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: vcpkg
  vcpkg_root: /custom/vcpkg/root
  vcpkg:
    registry: https://github.com/microsoft/vcpkg.git
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.manager == "vcpkg"
        assert config.packages.vcpkg_root == "/custom/vcpkg/root"

    def test_package_manager_all_custom_options(self, tmp_path):
        """Test parsing package manager with all custom options."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
  use_system: false
  custom_path: /tools/conan/venv/bin/conan
  conan_home: /data/conan_cache
  conan:
    version: 2.0
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.manager == "conan"
        assert config.packages.use_system is False
        assert config.packages.custom_path == "/tools/conan/venv/bin/conan"
        assert config.packages.conan_home == "/data/conan_cache"

    def test_package_manager_defaults(self, tmp_path):
        """Test default values for package manager custom options."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: test-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

packages:
  manager: conan
"""
        )

        config = parse_config(config_file)

        assert config.packages is not None
        assert config.packages.use_system is False  # Default
        assert config.packages.custom_path is None
        assert config.packages.conan_home is None
        assert config.packages.vcpkg_root is None


# =============================================================================
# Test Complete Configuration Examples
# =============================================================================


class TestCompleteCustomConfiguration:
    """Test complete configuration with all custom options."""

    def test_hermetic_toolchain_config(self, tmp_path):
        """Test fully hermetic configuration with everything in toolchain dir."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: hermetic-project

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    source: prebuilt

defaults:
  linux: llvm-18

packages:
  manager: conan
  use_system: false
  conan_home: .toolchainkit/conan_home

build:
  backend: ninja
  caching:
    enabled: true
    tool: sccache
"""
        )

        config = parse_config(config_file)

        assert config.project == "hermetic-project"
        assert len(config.toolchains) == 1
        assert config.packages is not None
        assert config.packages.use_system is False
        assert config.packages.conan_home == ".toolchainkit/conan_home"

    def test_mixed_system_and_custom_config(self, tmp_path):
        """Test configuration mixing system and custom components."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(
            """
version: 1
project: mixed-project

toolchains:
  - name: system-gcc
    type: gcc
    version: 13.2.0
    require_installed: true
    custom_paths:
      compiler: /usr/bin/g++-13
      linker: /usr/bin/ld

  - name: custom-llvm
    type: clang
    version: 18.1.8
    custom_paths:
      compiler: /opt/llvm-18/bin/clang++
      linker: /opt/llvm-18/bin/lld

packages:
  manager: conan
  use_system: true
  conan_home: ~/.local/share/conan2
"""
        )

        config = parse_config(config_file)

        assert len(config.toolchains) == 2

        gcc_tc = config.toolchains[0]
        assert gcc_tc.require_installed is True
        assert gcc_tc.custom_paths["compiler"] == "/usr/bin/g++-13"

        llvm_tc = config.toolchains[1]
        assert llvm_tc.custom_paths["compiler"] == "/opt/llvm-18/bin/clang++"

        assert config.packages.use_system is True
        assert config.packages.conan_home == "~/.local/share/conan2"
