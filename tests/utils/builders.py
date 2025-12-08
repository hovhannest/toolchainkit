"""
Test data builders for ToolchainKit testing.

This module provides builder classes for constructing test objects
with fluent API, making tests more readable and maintainable.
"""

from pathlib import Path
from typing import Optional, Dict, Any


class ToolchainBuilder:
    """Builder for test toolchain objects."""

    def __init__(self):
        """Initialize builder with default values."""
        self._name = "test-toolchain"
        self._type = "llvm"
        self._version = "18.1.8"
        self._path = Path("/opt/toolchains/llvm-18.1.8")
        self._compilers = None

    def with_name(self, name: str) -> "ToolchainBuilder":
        """
        Set toolchain name.

        Args:
            name: Toolchain name

        Returns:
            Self for method chaining
        """
        self._name = name
        return self

    def with_type(self, toolchain_type: str) -> "ToolchainBuilder":
        """
        Set toolchain type.

        Args:
            toolchain_type: Type (e.g., 'llvm', 'gcc', 'msvc')

        Returns:
            Self for method chaining
        """
        self._type = toolchain_type
        return self

    def with_version(self, version: str) -> "ToolchainBuilder":
        """
        Set toolchain version.

        Args:
            version: Version string

        Returns:
            Self for method chaining
        """
        self._version = version
        return self

    def with_path(self, path: Path) -> "ToolchainBuilder":
        """
        Set toolchain installation path.

        Args:
            path: Installation path

        Returns:
            Self for method chaining
        """
        self._path = path
        return self

    def with_compilers(self, c_compiler: str, cxx_compiler: str) -> "ToolchainBuilder":
        """
        Set custom compiler paths.

        Args:
            c_compiler: C compiler path
            cxx_compiler: C++ compiler path

        Returns:
            Self for method chaining
        """
        self._compilers = {"c": c_compiler, "cxx": cxx_compiler}
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build toolchain dictionary.

        Returns:
            Toolchain configuration dictionary
        """
        compilers = self._compilers
        if compilers is None:
            # Auto-generate compiler paths based on type
            if self._type == "llvm":
                compilers = {
                    "c": str(self._path / "bin" / "clang"),
                    "cxx": str(self._path / "bin" / "clang++"),
                }
            elif self._type == "gcc":
                compilers = {
                    "c": str(self._path / "bin" / "gcc"),
                    "cxx": str(self._path / "bin" / "g++"),
                }
            elif self._type == "msvc":
                compilers = {
                    "c": str(self._path / "bin" / "cl.exe"),
                    "cxx": str(self._path / "bin" / "cl.exe"),
                }
            else:
                compilers = {
                    "c": str(self._path / "bin" / "cc"),
                    "cxx": str(self._path / "bin" / "c++"),
                }

        return {
            "name": self._name,
            "type": self._type,
            "version": self._version,
            "path": str(self._path),
            "compilers": compilers,
        }


class ConfigBuilder:
    """Builder for test configuration objects."""

    def __init__(self):
        """Initialize builder with default configuration."""
        self._config = {
            "version": 1,
            "project": {"name": "test-project", "language": "cpp"},
            "toolchains": [],
            "build": {"generator": "Ninja", "configurations": ["Debug", "Release"]},
        }

    def with_project_name(self, name: str) -> "ConfigBuilder":
        """
        Set project name.

        Args:
            name: Project name

        Returns:
            Self for method chaining
        """
        self._config["project"]["name"] = name
        return self

    def with_language(self, language: str) -> "ConfigBuilder":
        """
        Set project language.

        Args:
            language: Language (e.g., 'cpp', 'c', 'mixed')

        Returns:
            Self for method chaining
        """
        self._config["project"]["language"] = language
        return self

    def with_toolchain(
        self, name: str, toolchain_type: str, version: str
    ) -> "ConfigBuilder":
        """
        Add toolchain to configuration.

        Args:
            name: Toolchain name
            toolchain_type: Toolchain type
            version: Toolchain version

        Returns:
            Self for method chaining
        """
        self._config["toolchains"].append(
            {"name": name, "type": toolchain_type, "version": version}
        )
        return self

    def with_generator(self, generator: str) -> "ConfigBuilder":
        """
        Set CMake generator.

        Args:
            generator: Generator name (e.g., 'Ninja', 'Unix Makefiles')

        Returns:
            Self for method chaining
        """
        self._config["build"]["generator"] = generator
        return self

    def with_configurations(self, *configs: str) -> "ConfigBuilder":
        """
        Set build configurations.

        Args:
            *configs: Configuration names (e.g., 'Debug', 'Release')

        Returns:
            Self for method chaining
        """
        self._config["build"]["configurations"] = list(configs)
        return self

    def with_package_manager(
        self, name: str, config: Optional[Dict[str, Any]] = None
    ) -> "ConfigBuilder":
        """
        Add package manager configuration.

        Args:
            name: Package manager name (e.g., 'conan', 'vcpkg')
            config: Optional package manager configuration

        Returns:
            Self for method chaining
        """
        if "package_managers" not in self._config:
            self._config["package_managers"] = {}

        self._config["package_managers"][name] = config or {}
        return self

    def with_cache(self, cache_type: str, enabled: bool = True) -> "ConfigBuilder":
        """
        Add cache configuration.

        Args:
            cache_type: Cache type (e.g., 'sccache', 'ccache')
            enabled: Whether cache is enabled

        Returns:
            Self for method chaining
        """
        if "cache" not in self._config:
            self._config["cache"] = {}

        self._config["cache"][cache_type] = {"enabled": enabled}
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build configuration dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()


class PlatformInfoBuilder:
    """Builder for PlatformInfo test objects."""

    def __init__(self):
        """Initialize builder with default platform info."""
        self._os = "linux"
        self._architecture = "x64"
        self._abi = "glibc-2.31"
        self._os_version = None
        self._distribution = None

    def with_os(self, os: str) -> "PlatformInfoBuilder":
        """Set operating system."""
        self._os = os
        return self

    def with_architecture(self, arch: str) -> "PlatformInfoBuilder":
        """Set architecture."""
        self._architecture = arch
        return self

    def with_abi(self, abi: str) -> "PlatformInfoBuilder":
        """Set ABI."""
        self._abi = abi
        return self

    def with_os_version(self, version: str) -> "PlatformInfoBuilder":
        """Set OS version."""
        self._os_version = version
        return self

    def with_distribution(self, distro: str) -> "PlatformInfoBuilder":
        """Set Linux distribution."""
        self._distribution = distro
        return self

    def build(self):
        """Build PlatformInfo object."""
        from toolchainkit.core.platform import PlatformInfo

        return PlatformInfo(
            os=self._os,
            architecture=self._architecture,
            abi=self._abi,
            os_version=self._os_version,
            distribution=self._distribution,
        )
