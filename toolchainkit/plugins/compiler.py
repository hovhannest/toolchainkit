"""
CompilerPlugin interface for custom compiler toolchain support.
"""

from abc import abstractmethod
from typing import List, Optional, Any
from pathlib import Path
from toolchainkit.plugins import Plugin


class CompilerPlugin(Plugin):
    """
    Plugin that provides a custom compiler toolchain.

    Compiler plugins register new compilers that can be used in toolchainkit.yaml
    configuration files. They provide CMake integration and platform support.

    Example:
        class ZigCompilerPlugin(CompilerPlugin):
            def metadata(self):
                return {
                    'name': 'zig-compiler',
                    'version': '1.0.0',
                    'description': 'Zig compiler support',
                    'author': 'ToolchainKit Community'
                }

            def initialize(self, context):
                self.context = context
                zig_yaml = Path(__file__).parent / "zig.yaml"
                zig_config = context.load_yaml_compiler(zig_yaml)
                context.register_compiler('zig', zig_config)

            def compiler_name(self):
                return 'zig'

            def compiler_config(self):
                yaml_path = Path(__file__).parent / "zig.yaml"
                return self.context.load_yaml_compiler(yaml_path)

            def supported_platforms(self):
                return ['linux-x64', 'windows-x64', 'macos-x64']
    """

    @abstractmethod
    def compiler_name(self) -> str:
        """
        Return unique compiler identifier.

        This is the name used in toolchainkit.yaml:

        toolchains:
          - name: my-toolchain
            type: zig  # <-- compiler_name()
            version: "0.11.0"

        Returns:
            Lowercase identifier (e.g., 'zig', 'dmd', 'circle', 'rustc')

        Example:
            def compiler_name(self):
                return 'zig'
        """
        pass

    @abstractmethod
    def compiler_config(self) -> Any:
        """
        Return compiler configuration for CMake integration.

        Can return either:
        - YAMLCompilerConfig: Load from YAML file (recommended)
        - Custom CompilerConfig subclass: For complex scenarios

        The configuration provides:
        - Compiler executable paths (C, C++, linker, archiver)
        - Build flags for each build type (Debug, Release, etc.)
        - Standard library configuration
        - Warning levels
        - Language standard support

        Returns:
            CompilerConfig instance for this compiler

        Raises:
            PluginError: If configuration cannot be created

        Example (using YAML):
            def compiler_config(self):
                yaml_path = Path(__file__).parent / "compilers" / "zig.yaml"
                return self.context.load_yaml_compiler(yaml_path)

        Example (custom config):
            def compiler_config(self):
                return CustomZigConfig(
                    c_compiler="zig cc",
                    cxx_compiler="zig c++",
                    linker="zig",
                    ...
                )
        """
        pass

    @abstractmethod
    def supported_platforms(self) -> List[str]:
        """
        Return list of supported platform strings.

        Platform strings use format: {os}-{arch}[-{abi}]
        Examples: "linux-x64", "windows-x64", "macos-arm64"

        Returns:
            List of platform strings this compiler supports

        Example:
            def supported_platforms(self):
                return [
                    'linux-x64',
                    'linux-arm64',
                    'windows-x64',
                    'macos-x64',
                    'macos-arm64'
                ]
        """
        pass

    def detect_system_installation(self) -> Optional[Path]:
        """
        Detect if compiler is installed on system (optional).

        Override to search for compiler in common locations:
        - PATH environment variable
        - Standard installation directories
        - System package managers

        Returns:
            Path to compiler installation root if found, None otherwise

        Example:
            def detect_system_installation(self):
                # Check if 'zig' is in PATH
                import shutil
                zig_path = shutil.which('zig')
                if zig_path:
                    return Path(zig_path).parent
                return None
        """
        return None

    def download_compiler(self, version: str, platform: str, destination: Path) -> Path:
        """
        Download and install compiler for given version/platform (optional).

        Override to provide automatic compiler installation:
        - Download compiler archive from official source
        - Extract to destination directory
        - Verify integrity (checksums)
        - Return installation path

        Args:
            version: Requested compiler version (e.g., "0.11.0")
            platform: Target platform string (e.g., "linux-x64")
            destination: Directory to install compiler

        Returns:
            Path to installed compiler root

        Raises:
            NotImplementedError: If auto-download not supported (default)
            PluginError: If download or installation fails

        Example:
            def download_compiler(self, version, platform, destination):
                url = f"https://ziglang.org/download/{version}/zig-{platform}.tar.xz"
                archive = destination / f"zig-{version}.tar.xz"

                # Download
                from toolchainkit.core.download import download_file
                download_file(url, archive)

                # Extract
                from toolchainkit.core.filesystem import extract_archive
                extract_archive(archive, destination)

                return destination / f"zig-{version}"
        """
        raise NotImplementedError(
            f"Automatic download not supported for {self.compiler_name()} compiler. "
            f"Please install manually."
        )

    def get_version(self, compiler_path: Path) -> str:
        """
        Extract compiler version from installation (optional).

        Override to detect compiler version by running compiler:
        - Execute compiler with --version flag
        - Parse version string from output
        - Return semantic version

        Args:
            compiler_path: Path to compiler executable or installation root

        Returns:
            Semantic version string (e.g., "0.11.0")

        Raises:
            PluginError: If version cannot be determined

        Example:
            def get_version(self, compiler_path):
                import subprocess
                result = subprocess.run(
                    [str(compiler_path / "zig"), "version"],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
        """
        raise NotImplementedError("Version detection not implemented")

    def requires_ninja_on_windows(self) -> bool:
        """
        Indicate if this compiler requires Ninja build system on Windows (optional).

        Override to return True if the compiler cannot work with Visual Studio generator
        on Windows and requires Ninja or another makefile generator.

        This is typically True for:
        - Non-MSVC compilers (Clang, GCC, Zig, etc.)
        - Compilers that don't integrate with Visual Studio toolchain

        Returns:
            True if Ninja should be automatically downloaded/used on Windows,
            False otherwise (default)

        Example:
            def requires_ninja_on_windows(self):
                return True  # Zig needs Ninja on Windows
        """
        return False


__all__ = ["CompilerPlugin"]
