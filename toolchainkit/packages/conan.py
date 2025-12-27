"""
Conan 2.x package manager integration for ToolchainKit.

This module provides integration with Conan 2.x package manager,
automatically generating Conan profiles from ToolchainKit toolchains
and managing dependency installation.

Classes:
    ConanIntegration: Conan 2.x package manager implementation

Example:
    from pathlib import Path
    from toolchainkit.packages.conan import ConanIntegration
    from toolchainkit.core.platform import detect_platform

    # Create integration
    project_root = Path('/path/to/project')
    conan = ConanIntegration(project_root)

    # Check if Conan is used
    if conan.detect():
        # Generate profile for platform
        platform = detect_platform()
        profile = conan.generate_profile(toolchain, platform)

        # Install dependencies
        conan.install_dependencies(profile)

        # Generate CMake integration
        integration = conan.generate_toolchain_integration(toolchain_file)
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Dict

from toolchainkit.packages.base import PackageManager
from toolchainkit.core.exceptions import (
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerInstallError,
)
from toolchainkit.packages.tool_downloader import (
    ConanDownloader,
    get_system_conan_path,
)


class ConanIntegration(PackageManager):
    """
    Conan 2.x package manager integration.

    Provides automatic Conan profile generation from ToolchainKit toolchains,
    dependency installation, and CMake toolchain integration.

    Attributes:
        project_root: Root directory of the project
        conanfile_txt: Path to conanfile.txt (if exists)
        conanfile_py: Path to conanfile.py (if exists)
        use_system_conan: Whether to use system-installed Conan
        custom_conan_path: Optional custom path to Conan executable
        conan_home: Optional custom CONAN_HOME directory

    Example:
        conan = ConanIntegration(Path('/project'))
        if conan.detect():
            conan.install_dependencies(profile_path)
    """

    def __init__(
        self,
        project_root: Path,
        use_system_conan: bool = True,
        custom_conan_path: Optional[Path] = None,
        conan_home: Optional[Path] = None,
    ):
        """
        Initialize Conan integration.

        Args:
            project_root: Root directory of the project
            use_system_conan: If True, use system-installed Conan;
                             if False, download Conan to toolchain directory
            custom_conan_path: Optional custom path to Conan executable
            conan_home: Optional custom CONAN_HOME directory

        Raises:
            TypeError: If project_root is not a Path
            ValueError: If project_root doesn't exist
        """
        super().__init__(project_root)
        self.conanfile_txt = project_root / "conanfile.txt"
        self.conanfile_py = project_root / "conanfile.py"
        self.use_system_conan = use_system_conan
        self.custom_conan_path = Path(custom_conan_path) if custom_conan_path else None
        self.conan_home = Path(conan_home) if conan_home else None
        self._conan_exe: Optional[Path] = None

    def detect(self) -> bool:
        """
        Detect if Conan is used in the project.

        Checks for the presence of conanfile.txt or conanfile.py
        in the project root directory.

        Returns:
            True if Conan manifest file exists, False otherwise

        Example:
            if conan.detect():
                print("Project uses Conan")
        """
        return self.conanfile_txt.exists() or self.conanfile_py.exists()

    def generate_profile(self, toolchain, platform) -> Path:
        """
        Generate Conan profile from ToolchainKit toolchain.

        Creates a Conan profile in .toolchainkit/conan/profiles/default that
        matches the toolchain configuration and target platform.

        Args:
            toolchain: Toolchain specification with type and version
            platform: Platform information (OS, arch, ABI)

        Returns:
            Path to generated profile file

        Raises:
            PackageManagerError: If profile generation fails

        Example:
            profile = conan.generate_profile(toolchain, platform)
            print(f"Profile generated: {profile}")
        """
        # Create Conan profiles directory in project-local
        # Use 'profiles/default' to match Conan's expected default profile location
        profile_dir = self.project_root / ".toolchainkit" / "conan" / "profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir / "default"

        # Map ToolchainKit settings to Conan settings
        conan_os = self._get_conan_os(platform)
        conan_arch = self._get_conan_arch(platform)
        conan_compiler = self._get_conan_compiler(toolchain.type)
        compiler_version = toolchain.version.split(".")[0]  # Major version only

        # Determine standard library
        if hasattr(toolchain, "stdlib") and toolchain.stdlib:
            if "libc++" in str(toolchain.stdlib).lower():
                libcxx = "libc++"
            elif "libstdc++" in str(toolchain.stdlib).lower():
                libcxx = "libstdc++"
            else:
                libcxx = "libc++" if conan_compiler == "clang" else "libstdc++"
        else:
            # Default based on compiler
            libcxx = "libc++" if conan_compiler == "clang" else "libstdc++"

        # Generate profile content
        profile_content = f"""[settings]
os={conan_os}
arch={conan_arch}
compiler={conan_compiler}
compiler.version={compiler_version}
compiler.libcxx={libcxx}
compiler.cppstd=17
build_type=Release

[conf]
tools.cmake.cmaketoolchain:generator=Ninja
"""

        # Write profile
        try:
            profile_path.write_text(profile_content)
        except Exception as e:
            raise PackageManagerError(
                f"Failed to write Conan profile to {profile_path}: {e}"
            ) from e

        return profile_path

    def get_conan_executable(self) -> Path:
        """
        Get path to Conan executable.

        Returns:
            Path to Conan executable

        Raises:
            PackageManagerNotFoundError: If Conan is not found
        """
        if self._conan_exe:
            return self._conan_exe

        # Priority 1: Custom path specified
        if self.custom_conan_path:
            if self.custom_conan_path.exists():
                self._conan_exe = self.custom_conan_path
                return self._conan_exe
            else:
                raise PackageManagerNotFoundError(
                    f"Custom Conan path not found: {self.custom_conan_path}"
                )

        # Priority 2: System Conan (if use_system_conan is True)
        if self.use_system_conan:
            system_conan = get_system_conan_path()
            if system_conan:
                self._conan_exe = system_conan
                return self._conan_exe
            else:
                raise PackageManagerNotFoundError(
                    "Conan not found in system PATH. Install with: pip install conan\n"
                    "Or set use_system_conan: false to download Conan to toolchain directory.\n"
                    "Documentation: https://docs.conan.io/2/installation.html"
                )

        # Priority 3: Downloaded Conan in global tools directory
        from toolchainkit.core.directory import get_global_cache_dir

        global_cache_dir = get_global_cache_dir()
        tools_dir = global_cache_dir / "tools"

        downloader = ConanDownloader(tools_dir)

        if not downloader.is_installed():
            # Download Conan
            try:
                downloader.download(version="2.0")
            except Exception as e:
                raise PackageManagerNotFoundError(
                    f"Failed to download Conan: {e}\n"
                    "Try installing manually: pip install conan\n"
                    "Or set use_system_conan: true to use system Conan."
                ) from e

        conan_exe = downloader.get_executable_path()
        if not conan_exe:
            raise PackageManagerNotFoundError(
                "Conan executable not found after download"
            )

        self._conan_exe = conan_exe
        return self._conan_exe

    def get_environment(self) -> Dict[str, str]:
        """
        Get environment variables for Conan execution.

        Returns:
            Dictionary of environment variables

        Note:
            CONAN_HOME behavior:
            - If explicitly configured: Use that path
            - If using system Conan: Don't set (use system default ~/.conan2)
            - If using downloaded Conan: Set to global_cache_dir/conan_home
        """
        env = os.environ.copy()

        # Set custom CONAN_HOME if explicitly specified
        if self.conan_home:
            env["CONAN_HOME"] = str(self.conan_home)
        elif not self.use_system_conan:
            # If using downloaded Conan, set CONAN_HOME next to tools directory
            from toolchainkit.core.directory import get_global_cache_dir

            global_cache_dir = get_global_cache_dir()
            default_conan_home = global_cache_dir / "conan_home"
            default_conan_home.mkdir(parents=True, exist_ok=True)
            env["CONAN_HOME"] = str(default_conan_home)

        return env

    def install_dependencies(
        self,
        profile_path: Optional[Path] = None,
        build_type: str = "Release",
        generator: Optional[str] = None,
        user_toolchain: Optional[Path] = None,
        compiler_env: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """
        Install dependencies using Conan.

        Runs 'conan install' with the generated profile to fetch and
        install all dependencies specified in the conanfile.

        Args:
            profile_path: Optional path to Conan profile
            build_type: Build type (Debug/Release)
            generator: Optional CMake generator (e.g., "Ninja")
            user_toolchain: Optional path to user toolchain file to include
            compiler_env: Optional dict of compiler environment variables (CC, CXX, etc.)
            **kwargs: Additional arguments

        Raises:
            PackageManagerNotFoundError: If Conan is not installed
            PackageManagerInstallError: If installation fails
        """
        # Get Conan executable
        conan_exe = self.get_conan_executable()
        env = self.get_environment()

        # Add compiler environment variables if provided
        if compiler_env:
            env.update(compiler_env)

        # Create build directory
        build_dir = self.project_root / "build"
        build_dir.mkdir(exist_ok=True)

        # Construct conan install command
        cmd = [
            str(conan_exe),
            "install",
            str(self.project_root),
            "--build=missing",
            "--output-folder",
            str(build_dir),
            "-s",
            f"build_type={build_type}",
        ]

        # Disable cmake_layout's subfolder creation to prevent nested generators
        # This ensures generators go directly to build/ instead of build/Release/generators/
        cmd.extend(["-c", "tools.cmake.cmake_layout:build_folder="])

        # Add profile if provided
        # Use --profile:all to set both host and build profiles to the same profile
        # This ensures Conan has a build profile when cross-compiling or using custom profiles
        if profile_path:
            cmd.extend(["--profile:all", str(profile_path)])

        # Add generator configuration if provided
        if generator:
            cmd.extend(["-c", f"tools.cmake.cmaketoolchain:generator={generator}"])

        # Add user toolchain if provided
        if user_toolchain:
            # Convert to forward slashes for Conan
            toolchain_str = str(user_toolchain).replace("\\", "/")
            cmd.extend(
                ["-c", f"tools.cmake.cmaketoolchain:user_toolchain=['{toolchain_str}']"]
            )

        # Run conan install
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root, env=env
            )
        except Exception as e:
            raise PackageManagerInstallError(
                f"Failed to execute Conan: {e}\n" f"Command: {' '.join(cmd)}"
            ) from e

        # Check for errors
        if result.returncode != 0:
            raise PackageManagerInstallError(
                f"Conan install failed with exit code {result.returncode}\n"
                f"Command: {' '.join(cmd)}\n"
                f"Error output:\n{result.stderr}\n\n"
                f"Troubleshooting:\n"
                f"  1. Verify conanfile.txt/conanfile.py syntax is correct\n"
                f"  2. Check network connection for remote downloads\n"
                f"  3. Try running: conan profile detect\n"
                f"  4. Check Conan version: conan --version (requires 2.x)"
            )

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """
        Generate CMake integration file for Conan.

        Creates a CMake file that includes the Conan-generated toolchain
        file and integrates it with ToolchainKit's toolchain.

        Args:
            toolchain_file: Path to ToolchainKit's toolchain file

        Returns:
            Path to generated integration file

        Example:
            integration = conan.generate_toolchain_integration(toolchain_file)
            # Include in main toolchain: include(${integration})
        """
        integration_file = toolchain_file.parent / "conan-integration.cmake"

        # Generate integration content
        content = """# Conan Integration
# This file is auto-generated by ToolchainKit
# Do not modify manually

set(CONAN_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/../../build/conan_toolchain.cmake")

if(EXISTS "${CONAN_TOOLCHAIN_FILE}")
    include("${CONAN_TOOLCHAIN_FILE}")
    message(STATUS "Conan: Using Conan-generated toolchain")
else()
    message(WARNING "Conan: toolchain file not found at ${CONAN_TOOLCHAIN_FILE}")
    message(WARNING "Conan: Run 'conan install' to generate toolchain file")
endif()
"""

        # Write integration file
        try:
            integration_file.write_text(content)
        except Exception as e:
            raise PackageManagerError(
                f"Failed to write Conan integration file to {integration_file}: {e}"
            ) from e

        return integration_file

    def get_name(self) -> str:
        """
        Get the package manager name.

        Returns:
            'conan'
        """
        return "conan"

    # Private helper methods for platform mapping

    def _get_conan_os(self, platform) -> str:
        """
        Map ToolchainKit platform OS to Conan OS.

        Args:
            platform: Platform information

        Returns:
            Conan OS name (Linux, Macos, Windows, Android, iOS)
        """
        os_map = {
            "linux": "Linux",
            "macos": "Macos",
            "darwin": "Macos",
            "windows": "Windows",
            "android": "Android",
            "ios": "iOS",
        }

        os_lower = platform.os.lower()
        return os_map.get(os_lower, "Linux")

    def _get_conan_arch(self, platform) -> str:
        """
        Map ToolchainKit platform architecture to Conan architecture.

        Args:
            platform: Platform information

        Returns:
            Conan architecture (x86_64, armv8, x86, armv7, etc.)
        """
        arch_map = {
            "x86_64": "x86_64",
            "x64": "x86_64",
            "amd64": "x86_64",
            "arm64": "armv8",
            "aarch64": "armv8",
            "x86": "x86",
            "i686": "x86",
            "arm": "armv7",
            "armv7": "armv7",
            "riscv64": "riscv64",
        }

        arch_lower = platform.architecture.lower()
        return arch_map.get(arch_lower, "x86_64")

    def _get_conan_compiler(self, compiler_type: str) -> str:
        """
        Map ToolchainKit compiler type to Conan compiler.

        Args:
            compiler_type: Compiler type (llvm, gcc, msvc)

        Returns:
            Conan compiler name (clang, gcc, msvc, apple-clang)
        """
        compiler_map = {
            "llvm": "clang",
            "clang": "clang",
            "gcc": "gcc",
            "msvc": "msvc",
            "apple-clang": "apple-clang",
        }

        compiler_lower = compiler_type.lower()
        return compiler_map.get(compiler_lower, "gcc")
