"""
PackageManagerPlugin interface for custom package manager integrations.
"""

from abc import abstractmethod
from typing import Dict, List, Any
from pathlib import Path
from toolchainkit.plugins import Plugin
from toolchainkit.core.exceptions import PackageManagerError


class PackageManagerPlugin(Plugin):
    """
    Plugin that provides a package manager integration.

    Package manager plugins add support for dependency management systems.
    They handle dependency installation and CMake integration.

    Example:
        class HunterPlugin(PackageManagerPlugin):
            def metadata(self):
                return {
                    'name': 'hunter-package-manager',
                    'version': '1.0.0',
                    'description': 'Hunter C++ package manager',
                    'author': 'ToolchainKit Community'
                }

            def initialize(self, context):
                context.register_package_manager('hunter', self)

            def package_manager_name(self):
                return 'hunter'

            def detect(self, project_root):
                return (project_root / "cmake" / "HunterGate.cmake").exists()

            def install_dependencies(self, project_root):
                # Hunter auto-installs during CMake configure
                pass

            def generate_toolchain_integration(self, toolchain_file, config):
                url = config.get('url', 'https://...')
                sha1 = config.get('sha1', '...')
                with open(toolchain_file, 'a') as f:
                    f.write(f'HunterGate(URL "{url}" SHA1 "{sha1}")')
    """

    @abstractmethod
    def package_manager_name(self) -> str:
        """
        Return unique package manager identifier.

        This is the name used in toolchainkit.yaml:

        packages:
          manager: hunter  # <-- package_manager_name()
          manifest: cmake/HunterGate.cmake

        Returns:
            Lowercase identifier (e.g., 'hunter', 'bazel', 'xmake', 'build2')

        Example:
            def package_manager_name(self):
                return 'hunter'
        """
        pass

    @abstractmethod
    def detect(self, project_root: Path) -> bool:
        """
        Detect if this package manager is used in the project.

        Search for package manager-specific files:
        - Manifest files (requirements.txt, BUILD, etc.)
        - Configuration files
        - Lock files

        Args:
            project_root: Project directory path

        Returns:
            True if package manager files detected, False otherwise

        Example (Hunter):
            def detect(self, project_root):
                hunter_gate = project_root / "cmake" / "HunterGate.cmake"
                return hunter_gate.exists()

        Example (Bazel):
            def detect(self, project_root):
                return (project_root / "WORKSPACE").exists() or \
                       (project_root / "WORKSPACE.bazel").exists()
        """
        pass

    @abstractmethod
    def install_dependencies(self, project_root: Path) -> None:
        """
        Install project dependencies.

        Execute package manager-specific installation:
        - Read manifest/configuration
        - Download dependencies
        - Build/prepare dependencies
        - Update lock files if applicable

        Args:
            project_root: Project directory path

        Raises:
            PackageManagerError: If installation fails

        Example (explicit install):
            def install_dependencies(self, project_root):
                import subprocess
                result = subprocess.run(
                    ['xmake', 'install', '-y'],
                    cwd=project_root,
                    check=True
                )

        Example (CMake-integrated):
            def install_dependencies(self, project_root):
                # Hunter installs dependencies during CMake configure
                pass  # No explicit install step
        """
        pass

    @abstractmethod
    def generate_toolchain_integration(
        self, toolchain_file: Path, config: Dict[str, Any]
    ) -> None:
        """
                Generate CMake integration code for this package manager.

                Append CMake code to toolchain file that:
                - Initializes package manager
                - Configures package manager settings
                - Sets up find_package() integration
                - Configures package paths

                Args:
                    toolchain_file: Path to CMake toolchain file
                    config: Package manager configuration from toolchainkit.yaml

                Example (Hunter):
                    def generate_toolchain_integration(self, toolchain_file, config):
                        hunter_url = config.get('url', 'https://github.com/cpp-pm/hunter/...')
                        hunter_sha1 = config.get('sha1', '...')

                        cmake_code = f'''
        # Hunter package manager integration
        include(cmake/HunterGate.cmake)
        HunterGate(
            URL "{hunter_url}"
            SHA1 "{hunter_sha1}"
        )
        '''
                        with open(toolchain_file, 'a') as f:
                            f.write(cmake_code)
        """
        pass

    def get_installed_packages(self, project_root: Path) -> List[Dict[str, Any]]:
        """
        Get list of installed packages (optional).

        Override to provide package introspection:
        - List installed package names
        - Include version information
        - Show installation paths

        Args:
            project_root: Project directory path

        Returns:
            List of dicts with keys: name, version, path

        Example:
            def get_installed_packages(self, project_root):
                # Parse lock file or query package manager
                return [
                    {'name': 'boost', 'version': '1.83.0', 'path': '...'},
                    {'name': 'fmt', 'version': '10.1.1', 'path': '...'}
                ]
        """
        return []

    def update_dependencies(self, project_root: Path) -> None:
        """
        Update dependencies to latest versions (optional).

        Override to provide dependency updates:
        - Check for newer versions
        - Update manifest/lock files
        - Re-install dependencies

        Args:
            project_root: Project directory path

        Raises:
            PackageManagerError: If update fails
        """
        raise NotImplementedError(
            f"Dependency updates not supported for {self.package_manager_name()}"
        )

    def clean_cache(self, project_root: Path) -> None:
        """
        Clean package manager cache (optional).

        Override to provide cache cleanup:
        - Remove downloaded archives
        - Clean build artifacts
        - Reset to clean state

        Args:
            project_root: Project directory path
        """
        pass


__all__ = ["PackageManagerPlugin", "PackageManagerError"]
