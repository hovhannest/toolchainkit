"""
Hunter Package Manager Plugin for ToolchainKit

This plugin provides integration for the Hunter C++ package manager.
Hunter is a CMake-driven cross-platform package manager for C/C++ projects.

Hunter website: https://hunter.readthedocs.io/
"""

from pathlib import Path
from typing import Dict, List, Any

from toolchainkit.plugins import PackageManagerPlugin, PackageManagerError


class HunterPlugin(PackageManagerPlugin):
    """
    Plugin that provides Hunter package manager support.

    Hunter is a CMake-driven package manager that integrates seamlessly
    with CMake-based projects. It downloads and builds dependencies during
    the CMake configure step.

    Features:
    - Automatic dependency download and build
    - Version pinning via Hunter configuration
    - Cross-platform support (Linux, Windows, macOS)
    - Integration with CMake's find_package()
    - Support for custom package archives

    Example usage in toolchainkit.yaml:
        packages:
          manager: hunter
          config:
            url: "https://github.com/cpp-pm/hunter/archive/v0.24.18.tar.gz"
            sha1: "2e9ae973d028660b735ac4c6142725ca36a0048b"
    """

    def __init__(self):
        """Initialize the Hunter package manager plugin."""
        super().__init__()
        self.context = None

    def metadata(self) -> dict:
        """
        Return plugin metadata.

        Returns:
            Dictionary with plugin information
        """
        return {
            "name": "hunter-package-manager",
            "version": "1.0.0",
            "type": "package_manager",
            "description": "Hunter C++ package manager integration for ToolchainKit",
            "author": "ToolchainKit Community",
            "homepage": "https://github.com/toolchainkit/tk-hunter",
            "license": "MIT",
        }

    def initialize(self, context) -> None:
        """
        Initialize the plugin and register Hunter package manager.

        Args:
            context: PluginContext providing access to registry and utilities

        Raises:
            PluginError: If plugin initialization fails
        """
        self.context = context

        # Register this plugin as the Hunter package manager handler
        context.register_package_manager("hunter", self)

        # Log successful registration
        if hasattr(context, "logger"):
            context.logger.info("Hunter package manager registered successfully")

    def cleanup(self) -> None:
        """
        Cleanup plugin resources.

        Called when the plugin manager is shutting down.
        """
        self.context = None

    def package_manager_name(self) -> str:
        """
        Return the unique package manager identifier.

        Returns:
            'hunter' - the name used in toolchainkit.yaml configurations
        """
        return "hunter"

    def detect(self, project_root: Path) -> bool:
        """
        Detect if Hunter is used in this project.

        Checks for Hunter-specific files:
        - cmake/HunterGate.cmake (Hunter bootstrap file)
        - HunterGate.cmake in project root
        - cmake/Hunter/config.cmake (Hunter configuration)

        Args:
            project_root: Project root directory

        Returns:
            True if Hunter files found, False otherwise
        """
        # Check common Hunter file locations
        hunter_files = [
            project_root / "cmake" / "HunterGate.cmake",
            project_root / "HunterGate.cmake",
            project_root / "cmake" / "Hunter" / "config.cmake",
        ]

        return any(f.exists() for f in hunter_files)

    def install_dependencies(self, project_root: Path) -> None:
        """
        Install dependencies using Hunter.

        Note: Hunter automatically downloads and builds dependencies
        during the CMake configure step. This method is a no-op since
        the actual installation happens when CMake runs.

        Args:
            project_root: Project root directory

        Raises:
            PackageManagerError: If Hunter is not detected in project
        """
        if not self.detect(project_root):
            raise PackageManagerError(
                f"Hunter not detected in project: {project_root}. "
                "Ensure HunterGate.cmake exists in cmake/ directory."
            )

        # Hunter installs dependencies during CMake configure
        # No explicit installation step required
        if self.context and hasattr(self.context, "logger"):
            self.context.logger.info(
                "Hunter dependencies will be installed during CMake configure"
            )

    def generate_toolchain_integration(
        self, toolchain_file: Path, config: Dict[str, Any]
    ) -> None:
        """
        Generate CMake integration code for Hunter.

        Appends Hunter initialization code to the toolchain file.
        This code sets up HunterGate with the specified URL and SHA1.

        Args:
            toolchain_file: Path to CMake toolchain file
            config: Hunter configuration with keys:
                - url: Hunter archive URL (default: latest stable release)
                - sha1: SHA1 hash of Hunter archive (required for security)
                - local: Path to local Hunter installation (optional)

        Example config:
            {
                "url": "https://github.com/cpp-pm/hunter/archive/v0.24.18.tar.gz",
                "sha1": "2e9ae973d028660b735ac4c6142725ca36a0048b"
            }

        Raises:
            PackageManagerError: If SHA1 not provided
        """
        # Default Hunter URL (latest stable)
        default_url = "https://github.com/cpp-pm/hunter/archive/v0.24.18.tar.gz"
        default_sha1 = "2e9ae973d028660b735ac4c6142725ca36a0048b"

        hunter_url = config.get("url", default_url)
        hunter_sha1 = config.get("sha1", default_sha1)
        hunter_local = config.get("local")

        if not hunter_sha1:
            raise PackageManagerError(
                "Hunter SHA1 hash must be specified for security. "
                "Get SHA1 from https://github.com/cpp-pm/hunter/releases"
            )

        # Generate CMake code
        cmake_code = "\n\n# Hunter package manager integration\n"

        if hunter_local:
            # Use local Hunter installation
            cmake_code += f'set(HUNTER_ROOT "{hunter_local}")\n'

        cmake_code += f"""
# Include HunterGate module
include(cmake/HunterGate.cmake)

# Initialize Hunter
HunterGate(
    URL "{hunter_url}"
    SHA1 "{hunter_sha1}"
)
"""

        # Append to toolchain file
        with open(toolchain_file, "a", encoding="utf-8") as f:
            f.write(cmake_code)

        if self.context and hasattr(self.context, "logger"):
            self.context.logger.debug(
                f"Generated Hunter integration in {toolchain_file}"
            )

    def get_installed_packages(self, project_root: Path) -> List[Dict[str, Any]]:
        """
        Get list of packages configured in Hunter.

        Parses cmake/Hunter/config.cmake to extract configured packages.

        Args:
            project_root: Project root directory

        Returns:
            List of dictionaries with package information:
                - name: Package name
                - version: Package version (if specified)
                - sha1: Package SHA1 (if specified)

        Example return:
            [
                {'name': 'Boost', 'version': '1.83.0', 'sha1': '...'},
                {'name': 'fmt', 'version': '10.1.1', 'sha1': '...'}
            ]
        """
        config_file = project_root / "cmake" / "Hunter" / "config.cmake"

        if not config_file.exists():
            return []

        packages = []

        try:
            content = config_file.read_text(encoding="utf-8")

            # Simple parsing of hunter_config() calls
            # Format: hunter_config(PackageName VERSION "x.y.z" SHA1 "...")
            import re

            pattern = (
                r'hunter_config\s*\(\s*(\w+)\s+VERSION\s+"([^"]+)"\s+SHA1\s+"([^"]+)"'
            )
            matches = re.finditer(pattern, content)

            for match in matches:
                packages.append(
                    {
                        "name": match.group(1),
                        "version": match.group(2),
                        "sha1": match.group(3),
                    }
                )

        except Exception as e:
            if self.context and hasattr(self.context, "logger"):
                self.context.logger.warning(f"Failed to parse Hunter config: {e}")

        return packages

    def clean_cache(self, project_root: Path) -> None:
        """
        Clean Hunter cache directory.

        Removes downloaded package archives and build artifacts from
        Hunter's cache directory (~/.hunter by default).

        Args:
            project_root: Project root directory
        """
        import shutil

        # Hunter cache is typically at ~/.hunter
        hunter_cache = Path.home() / ".hunter"

        if hunter_cache.exists():
            try:
                shutil.rmtree(hunter_cache)
                if self.context and hasattr(self.context, "logger"):
                    self.context.logger.info(f"Cleaned Hunter cache: {hunter_cache}")
            except Exception as e:
                if self.context and hasattr(self.context, "logger"):
                    self.context.logger.warning(f"Failed to clean Hunter cache: {e}")


__all__ = ["HunterPlugin"]
