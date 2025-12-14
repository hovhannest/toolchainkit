"""
vcpkg package manager integration for ToolchainKit.

This module provides integration with Microsoft's vcpkg package manager,
automatically selecting appropriate triplets and managing dependency
installation with toolchain chaining.

Classes:
    VcpkgIntegration: vcpkg package manager implementation

Example:
    from pathlib import Path
    from toolchainkit.packages.vcpkg import VcpkgIntegration
    from toolchainkit.core.platform import detect_platform

    # Create integration
    project_root = Path('/path/to/project')
    vcpkg = VcpkgIntegration(project_root)

    # Check if vcpkg is used
    if vcpkg.detect():
        # Install dependencies
        platform = detect_platform()
        vcpkg.install_dependencies(platform)

        # Generate CMake integration
        integration = vcpkg.generate_toolchain_integration(toolchain_file)
"""

import subprocess
import os
from pathlib import Path
from typing import Optional

from toolchainkit.packages.base import PackageManager
from toolchainkit.core.exceptions import (
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerInstallError,
)
from toolchainkit.packages.tool_downloader import (
    VcpkgDownloader,
    get_system_vcpkg_path,
)


class VcpkgIntegration(PackageManager):
    """
    vcpkg package manager integration.

    Provides automatic triplet selection for vcpkg based on platform,
    dependency installation using manifest mode, and CMake toolchain
    chaining with ToolchainKit.

    Attributes:
        project_root: Root directory of the project
        manifest_file: Path to vcpkg.json manifest
        vcpkg_root: Path to vcpkg installation
        use_system_vcpkg: Whether to use system-installed vcpkg
        custom_vcpkg_path: Optional custom path to vcpkg installation

    Example:
        vcpkg = VcpkgIntegration(Path('/project'))
        if vcpkg.detect():
            vcpkg.install_dependencies(platform)
    """

    def __init__(
        self,
        project_root: Path,
        use_system_vcpkg: bool = True,
        custom_vcpkg_path: Optional[Path] = None,
    ):
        """
        Initialize vcpkg integration.

        Args:
            project_root: Root directory of the project
            use_system_vcpkg: If True, use system-installed vcpkg;
                             if False, download vcpkg to toolchain directory
            custom_vcpkg_path: Optional custom path to vcpkg root directory

        Raises:
            TypeError: If project_root is not a Path
            ValueError: If project_root doesn't exist
        """
        super().__init__(project_root)
        self.manifest_file = project_root / "vcpkg.json"
        self.use_system_vcpkg = use_system_vcpkg
        self.custom_vcpkg_path = Path(custom_vcpkg_path) if custom_vcpkg_path else None
        self.vcpkg_root = self._find_vcpkg_root()

    def detect(self) -> bool:
        """
        Detect if vcpkg is used in the project.

        Checks for the presence of vcpkg.json manifest file
        in the project root directory.

        Returns:
            True if vcpkg manifest file exists, False otherwise

        Example:
            if vcpkg.detect():
                print("Project uses vcpkg")
        """
        return self.manifest_file.exists()

    def _find_vcpkg_root(self) -> Optional[Path]:
        """
        Find vcpkg installation directory.

        Searches for vcpkg installation in:
        1. Custom path (if specified)
        2. System installation (if use_system_vcpkg is True)
        3. Downloaded vcpkg in toolchain directory (if use_system_vcpkg is False)

        Returns:
            Path to vcpkg root directory, or None if not found
        """
        # Priority 1: Custom path specified
        if self.custom_vcpkg_path:
            if self.custom_vcpkg_path.exists():
                return self.custom_vcpkg_path
            else:
                return None

        # Priority 2: System vcpkg (if use_system_vcpkg is True)
        if self.use_system_vcpkg:
            # Check environment variable
            vcpkg_root_env = os.getenv("VCPKG_ROOT")
            if vcpkg_root_env:
                vcpkg_path = Path(vcpkg_root_env)
                if vcpkg_path.exists():
                    return vcpkg_path

            # Check system PATH
            system_vcpkg = get_system_vcpkg_path()
            if system_vcpkg:
                # vcpkg executable found, get root directory
                return system_vcpkg.parent

            # Check common locations
            common_paths = [
                Path.home() / "vcpkg",
                Path("C:/vcpkg"),
                Path("/usr/local/vcpkg"),
                Path("/opt/vcpkg"),
            ]

            for path in common_paths:
                if (
                    path.exists()
                    and (path / "vcpkg").exists()
                    or (path / "vcpkg.exe").exists()
                ):
                    return path

            return None

        # Priority 3: Downloaded vcpkg in global tools directory
        from toolchainkit.core.directory import get_global_cache_dir

        global_cache_dir = get_global_cache_dir()
        tools_dir = global_cache_dir / "tools"

        downloader = VcpkgDownloader(tools_dir)

        if not downloader.is_installed():
            # Download vcpkg
            try:
                downloader.download()
            except Exception:
                return None

        return tools_dir / "vcpkg"

    def get_triplet(self, platform) -> str:
        """
        Get vcpkg triplet for platform.

        Maps ToolchainKit platform information to vcpkg triplet format.

        Args:
            platform: Platform information with os and architecture

        Returns:
            vcpkg triplet string (e.g., 'x64-linux', 'x64-windows')

        Example:
            triplet = vcpkg.get_triplet(platform)
            # Returns: 'x64-linux' on Linux x64
        """
        os_lower = platform.os.lower()
        arch_lower = platform.architecture.lower()

        # Map architecture
        if arch_lower in ("x86_64", "x64", "amd64"):
            arch_part = "x64"
        elif arch_lower in ("arm64", "aarch64"):
            arch_part = "arm64"
        elif arch_lower in ("x86", "i686"):
            arch_part = "x86"
        elif arch_lower in ("arm", "armv7"):
            arch_part = "arm"
        else:
            arch_part = "x64"  # Default

        # Map OS
        if os_lower == "linux":
            os_part = "linux"
        elif os_lower in ("macos", "darwin"):
            os_part = "osx"
        elif os_lower == "windows":
            os_part = "windows"
        elif os_lower == "android":
            os_part = "android"
        elif os_lower == "ios":
            os_part = "ios"
        else:
            os_part = "linux"  # Default

        return f"{arch_part}-{os_part}"

    def install_dependencies(self, platform=None, **kwargs) -> None:
        """
        Install dependencies using vcpkg.

        Runs 'vcpkg install' in manifest mode with the appropriate
        triplet for the target platform.

        Args:
            platform: Platform information for triplet selection (optional)
            **kwargs: Additional arguments (ignored)

        Raises:
            PackageManagerNotFoundError: If vcpkg is not installed
            PackageManagerInstallError: If installation fails

        Example:
            try:
                vcpkg.install_dependencies(platform)
                print("Dependencies installed")
            except PackageManagerInstallError as e:
                print(f"Installation failed: {e}")
        """
        # Check if vcpkg is installed
        if not self.vcpkg_root:
            raise PackageManagerNotFoundError(
                "vcpkg not found. Set VCPKG_ROOT environment variable or "
                "install vcpkg to a standard location.\n"
                "Installation: https://vcpkg.io/en/getting-started.html\n"
                "Common locations: ~/vcpkg, C:/vcpkg, /usr/local/vcpkg"
            )

        # Get vcpkg executable
        vcpkg_exe = self.vcpkg_root / ("vcpkg.exe" if os.name == "nt" else "vcpkg")
        if not vcpkg_exe.exists():
            raise PackageManagerNotFoundError(
                f"vcpkg executable not found at {vcpkg_exe}"
            )

        # Get triplet for platform
        triplet = self.get_triplet(platform)

        # Construct vcpkg install command
        cmd = [
            str(vcpkg_exe),
            "install",
            "--triplet",
            triplet,
            "--x-manifest-root",
            str(self.project_root),
        ]

        # Run vcpkg install
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root
            )
        except Exception as e:
            raise PackageManagerInstallError(
                f"Failed to execute vcpkg: {e}\n" f"Command: {' '.join(cmd)}"
            ) from e

        # Check for errors
        if result.returncode != 0:
            raise PackageManagerInstallError(
                f"vcpkg install failed with exit code {result.returncode}\n"
                f"Command: {' '.join(cmd)}\n"
                f"Error output:\n{result.stderr}\n\n"
                f"Troubleshooting:\n"
                f"  1. Verify vcpkg.json syntax is correct\n"
                f"  2. Check network connection for downloads\n"
                f"  3. Ensure vcpkg is up to date: git pull (in vcpkg directory)\n"
                f"  4. Try: {vcpkg_exe} integrate install"
            )

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """
        Generate CMake integration file for vcpkg.

        Creates a CMake file that chains vcpkg's toolchain with
        ToolchainKit's toolchain using VCPKG_CHAINLOAD_TOOLCHAIN_FILE.

        Args:
            toolchain_file: Path to ToolchainKit's toolchain file

        Returns:
            Path to generated integration file

        Raises:
            PackageManagerError: If vcpkg_root is not set

        Example:
            integration = vcpkg.generate_toolchain_integration(toolchain_file)
            # Include in CMake: -DCMAKE_TOOLCHAIN_FILE=${integration}
        """
        if not self.vcpkg_root:
            raise PackageManagerError(
                "Cannot generate integration: VCPKG_ROOT not set.\n"
                "Set VCPKG_ROOT environment variable or install vcpkg."
            )

        integration_file = toolchain_file.parent / "vcpkg-integration.cmake"

        # Get path to vcpkg toolchain file
        vcpkg_toolchain = self.vcpkg_root / "scripts" / "buildsystems" / "vcpkg.cmake"

        # Generate integration content with toolchain chaining
        content = f"""# vcpkg Integration
# This file is auto-generated by ToolchainKit
# Do not modify manually

# Chain ToolchainKit toolchain - vcpkg will load this via VCPKG_CHAINLOAD_TOOLCHAIN_FILE
set(VCPKG_CHAINLOAD_TOOLCHAIN_FILE "${{CMAKE_CURRENT_LIST_DIR}}/toolchainkit-base.cmake")

# Set CMAKE_TOOLCHAIN_FILE to vcpkg toolchain
set(CMAKE_TOOLCHAIN_FILE "{vcpkg_toolchain.as_posix()}")

# Include vcpkg toolchain
if(EXISTS "${{CMAKE_TOOLCHAIN_FILE}}")
    include("${{CMAKE_TOOLCHAIN_FILE}}")
    message(STATUS "vcpkg: Using vcpkg toolchain with ToolchainKit chainloading")
else()
    message(WARNING "vcpkg: Toolchain file not found at ${{CMAKE_TOOLCHAIN_FILE}}")
endif()
"""

        # Write integration file
        try:
            integration_file.write_text(content)
        except Exception as e:
            raise PackageManagerError(
                f"Failed to write vcpkg integration file to {integration_file}: {e}"
            ) from e

        return integration_file

    def get_name(self) -> str:
        """
        Get the package manager name.

        Returns:
            'vcpkg'
        """
        return "vcpkg"
