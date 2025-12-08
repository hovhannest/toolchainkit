"""
BuildBackendPlugin interface for alternative build system support.
"""

from abc import abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from toolchainkit.plugins import Plugin
from toolchainkit.core.exceptions import BuildBackendError


class BuildBackendPlugin(Plugin):
    """
    Plugin that provides an alternative build backend (non-CMake).

    Build backend plugins add support for alternative build systems like Meson,
    Premake, xmake, etc. They handle configuration, building, and testing.

    Example:
        class MesonPlugin(BuildBackendPlugin):
            def metadata(self):
                return {
                    'name': 'meson-backend',
                    'version': '1.0.0',
                    'description': 'Meson build system support',
                    'author': 'ToolchainKit Community'
                }

            def initialize(self, context):
                context.register_backend('meson', self)

            def backend_name(self):
                return 'meson'

            def detect(self, project_root):
                return (project_root / "meson.build").exists()

            def configure(self, project_root, build_dir, config):
                import subprocess
                toolchain = config['toolchain_path']
                build_type = config.get('build_type', 'Release').lower()
                cmd = ['meson', 'setup', str(build_dir), str(project_root),
                       f'--buildtype={build_type}']
                subprocess.run(cmd, check=True)

            def build(self, build_dir, target=None, jobs=None):
                import subprocess
                cmd = ['meson', 'compile', '-C', str(build_dir)]
                if jobs:
                    cmd.extend(['-j', str(jobs)])
                subprocess.run(cmd, check=True)
    """

    @abstractmethod
    def backend_name(self) -> str:
        """
        Return unique build backend identifier.

        Returns:
            Lowercase identifier (e.g., 'meson', 'premake', 'xmake', 'build2')

        Example:
            def backend_name(self):
                return 'meson'
        """
        pass

    @abstractmethod
    def detect(self, project_root: Path) -> bool:
        """
        Detect if project uses this build system.

        Search for build system-specific files:
        - Build definition files (meson.build, premake5.lua, etc.)
        - Configuration files

        Args:
            project_root: Project directory path

        Returns:
            True if build system files detected, False otherwise

        Example (Meson):
            def detect(self, project_root):
                return (project_root / "meson.build").exists()

        Example (Premake):
            def detect(self, project_root):
                for file in ['premake5.lua', 'premake4.lua']:
                    if (project_root / file).exists():
                        return True
                return False
        """
        pass

    @abstractmethod
    def configure(
        self, project_root: Path, build_dir: Path, config: Dict[str, Any]
    ) -> None:
        """
        Configure build with toolchain settings.

        Run build system configuration step:
        - Set compiler paths
        - Set build type (Debug/Release)
        - Configure toolchain options
        - Generate build files

        Args:
            project_root: Project source directory
            build_dir: Build output directory
            config: Build configuration dict with keys:
                - toolchain_path: Path - Toolchain installation
                - build_type: str - "Debug", "Release", etc.
                - compiler: str - Compiler name
                - stdlib: str - Standard library (optional)
                - additional options

        Raises:
            BuildBackendError: If configuration fails

        Example (Meson):
            def configure(self, project_root, build_dir, config):
                import subprocess

                toolchain = config['toolchain_path']
                build_type = config.get('build_type', 'Release').lower()

                cmd = [
                    'meson', 'setup',
                    str(build_dir),
                    str(project_root),
                    f'--buildtype={build_type}',
                    f'-Dcpp={toolchain / "bin" / "clang++"}',
                ]

                subprocess.run(cmd, check=True)
        """
        pass

    @abstractmethod
    def build(
        self, build_dir: Path, target: Optional[str] = None, jobs: Optional[int] = None
    ) -> None:
        """
        Execute build.

        Run build system to compile project:
        - Compile source files
        - Link executables/libraries
        - Optionally build specific target

        Args:
            build_dir: Build directory (from configure())
            target: Optional specific target (None = all targets)
            jobs: Optional parallel job count (None = auto-detect)

        Raises:
            BuildBackendError: If build fails

        Example (Meson):
            def build(self, build_dir, target=None, jobs=None):
                import subprocess

                cmd = ['meson', 'compile', '-C', str(build_dir)]
                if jobs:
                    cmd.extend(['-j', str(jobs)])
                if target:
                    cmd.append(target)

                subprocess.run(cmd, check=True)
        """
        pass

    def test(self, build_dir: Path, test_name: Optional[str] = None) -> None:
        """
        Execute tests (optional).

        Run test suite:
        - Run all tests or specific test
        - Report results

        Args:
            build_dir: Build directory
            test_name: Optional specific test (None = all tests)

        Raises:
            NotImplementedError: If testing not supported (default)
            BuildBackendError: If tests fail

        Example (Meson):
            def test(self, build_dir, test_name=None):
                import subprocess

                cmd = ['meson', 'test', '-C', str(build_dir)]
                if test_name:
                    cmd.append(test_name)

                subprocess.run(cmd, check=True)
        """
        raise NotImplementedError(f"Testing not supported for {self.backend_name()}")

    def clean(self, build_dir: Path) -> None:
        """
        Clean build artifacts (optional).

        Remove build outputs:
        - Object files
        - Executables
        - Libraries
        - Intermediate files

        Args:
            build_dir: Build directory
        """
        pass

    def install(self, build_dir: Path, install_dir: Path) -> None:
        """
        Install built artifacts (optional).

        Copy build outputs to installation directory:
        - Executables
        - Libraries
        - Headers
        - Documentation

        Args:
            build_dir: Build directory
            install_dir: Installation destination

        Raises:
            NotImplementedError: If installation not supported
        """
        raise NotImplementedError(
            f"Installation not supported for {self.backend_name()}"
        )


__all__ = ["BuildBackendPlugin", "BuildBackendError"]
