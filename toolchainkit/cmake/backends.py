"""
CMake build backend configuration.

This module provides classes for detecting, configuring, and using different
CMake build backends (Ninja, Make, MSBuild, Xcode) across platforms.
"""

import os
import shutil
import platform as sys_platform
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import logging

from toolchainkit.core.exceptions import (
    BuildBackendError,
    BackendNotAvailableError,
)

logger = logging.getLogger(__name__)


class BuildBackend:
    """Base class for build backend configuration."""

    def __init__(self, name: str, parallel_jobs: Optional[int] = None):
        """
        Initialize build backend.

        Args:
            name: Human-readable backend name
            parallel_jobs: Number of parallel build jobs (default: CPU count)
        """
        self.name = name
        self.parallel_jobs = parallel_jobs or os.cpu_count() or 4

    def get_cmake_generator(self) -> str:
        """
        Get CMAKE_GENERATOR value.

        Returns:
            CMake generator name
        """
        raise NotImplementedError

    def get_build_args(self) -> List[str]:
        """
        Get arguments for cmake --build.

        Returns:
            List of command-line arguments
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """
        Check if backend is available on this system.

        Returns:
            True if backend can be used
        """
        raise NotImplementedError

    def get_cmake_variables(self) -> Dict[str, str]:
        """
        Get CMake variables for this backend.

        Returns:
            Dictionary of CMake variable names to values
        """
        return {
            "CMAKE_GENERATOR": self.get_cmake_generator(),
        }

    def __str__(self) -> str:
        return f"{self.name} (parallel={self.parallel_jobs})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} parallel_jobs={self.parallel_jobs}>"


class NinjaBackend(BuildBackend):
    """Ninja build backend - fast, parallel, cross-platform."""

    def __init__(self, parallel_jobs: Optional[int] = None):
        super().__init__("Ninja", parallel_jobs)

    def get_cmake_generator(self) -> str:
        return "Ninja"

    def get_build_args(self) -> List[str]:
        """Ninja build arguments."""
        return ["-j", str(self.parallel_jobs)]

    def is_available(self) -> bool:
        """Check if ninja is on PATH."""
        return shutil.which("ninja") is not None

    def get_cmake_variables(self) -> Dict[str, str]:
        vars = super().get_cmake_variables()
        # Ninja-specific optimizations
        vars["CMAKE_EXPORT_COMPILE_COMMANDS"] = "ON"
        return vars


class MakeBackend(BuildBackend):
    """GNU Make build backend - ubiquitous on Unix."""

    def __init__(self, parallel_jobs: Optional[int] = None):
        super().__init__("Unix Makefiles", parallel_jobs)

    def get_cmake_generator(self) -> str:
        return "Unix Makefiles"

    def get_build_args(self) -> List[str]:
        """Make build arguments."""
        return ["-j", str(self.parallel_jobs)]

    def is_available(self) -> bool:
        """Check if make is on PATH."""
        return shutil.which("make") is not None


class MSBuildBackend(BuildBackend):
    """Visual Studio MSBuild backend."""

    def __init__(self, version: str = "17 2022", parallel_jobs: Optional[int] = None):
        super().__init__(f"Visual Studio {version}", parallel_jobs)
        self.version = version

    def get_cmake_generator(self) -> str:
        return f"Visual Studio {self.version}"

    def get_build_args(self) -> List[str]:
        """MSBuild arguments."""
        return [
            "--",  # Pass remaining args to MSBuild
            f"/maxcpucount:{self.parallel_jobs}",
        ]

    def is_available(self) -> bool:
        """Check if on Windows (MSBuild comes with VS)."""
        if sys_platform.system() != "Windows":
            return False

        # Check if Visual Studio is installed
        # MSBuild should be available if VS is installed
        return shutil.which("msbuild") is not None or self._check_vs_installation()

    def _check_vs_installation(self) -> bool:
        """Check if Visual Studio is installed via vswhere."""
        try:
            import subprocess

            # Try vswhere (installed with VS 2017+)
            vswhere = (
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
                / "Microsoft Visual Studio"
                / "Installer"
                / "vswhere.exe"
            )
            if vswhere.exists():
                result = subprocess.run(
                    [str(vswhere), "-latest", "-property", "installationPath"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            pass

        # Fallback: check common VS installation paths
        program_files = Path(
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        )
        vs_path = program_files / "Microsoft Visual Studio"
        return vs_path.exists()


class XcodeBackend(BuildBackend):
    """Xcode build backend for macOS."""

    def __init__(self, parallel_jobs: Optional[int] = None):
        super().__init__("Xcode", parallel_jobs)

    def get_cmake_generator(self) -> str:
        return "Xcode"

    def get_build_args(self) -> List[str]:
        """Xcode build arguments."""
        return [
            "--",  # Pass remaining args to xcodebuild
            "-jobs",
            str(self.parallel_jobs),
        ]

    def is_available(self) -> bool:
        """Check if Xcode is installed."""
        if sys_platform.system() != "Darwin":
            return False

        # Check for Xcode.app
        xcode_app = Path("/Applications/Xcode.app")
        if xcode_app.exists():
            return True

        # Check for Xcode Command Line Tools
        return shutil.which("xcodebuild") is not None


class NMakeMakefilesBackend(BuildBackend):
    """NMake Makefiles backend (Windows)."""

    def __init__(self, parallel_jobs: Optional[int] = None):
        super().__init__("NMake Makefiles", parallel_jobs)

    def get_cmake_generator(self) -> str:
        return "NMake Makefiles"

    def get_build_args(self) -> List[str]:
        """NMake doesn't support parallel builds well."""
        return []

    def is_available(self) -> bool:
        """Check if nmake is available."""
        return shutil.which("nmake") is not None


class BuildBackendDetector:
    """Detect and select optimal build backend."""

    def __init__(
        self,
        platform_info=None,
        tools_dir: Optional[Path] = None,
        custom_paths: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize backend detector.

        Args:
            platform_info: Optional PlatformInfo object (for testing).
                          If None, will detect current platform.
            tools_dir: Optional tools directory for downloaded tools.
                      Defaults to ~/.toolchainkit/tools
            custom_paths: Optional dict of custom tool paths.
                         Keys: 'cmake', 'ninja', 'make', etc.
        """
        if platform_info is None:
            # Avoid circular import
            from ..core.platform import detect_platform

            platform_info = detect_platform()

        self.platform = platform_info
        if tools_dir is None:
            from ..core.directory import get_global_cache_dir

            tools_dir = get_global_cache_dir() / "tools"
        self.tools_dir = tools_dir
        self.custom_paths = custom_paths or {}
        self._backends = self._discover_backends()

    def _check_tool_available(self, tool_name: str) -> bool:
        """
        Check if a build tool is available.

        Priority order:
        1. Custom path (from config)
        2. Downloaded tool (in tools_dir)
        3. System PATH

        Args:
            tool_name: Tool name ('cmake', 'ninja', 'make', etc.)

        Returns:
            True if tool is available, False otherwise
        """
        # 1. Check custom path
        if tool_name in self.custom_paths:
            custom_path = Path(self.custom_paths[tool_name])
            if custom_path.exists():
                logger.debug(f"Found {tool_name} via custom path: {custom_path}")
                return True

        # 2. Check downloaded tools
        if tool_name in ("cmake", "ninja", "sccache", "make"):
            try:
                from ..packages.tool_downloader import (
                    CMakeDownloader,
                    NinjaDownloader,
                    SccacheDownloader,
                    MakeDownloader,
                )

                downloader: Optional[
                    Union[
                        CMakeDownloader,
                        NinjaDownloader,
                        SccacheDownloader,
                        MakeDownloader,
                    ]
                ] = None

                if tool_name == "cmake":
                    downloader = CMakeDownloader(self.tools_dir, platform=self.platform)
                elif tool_name == "ninja":
                    downloader = NinjaDownloader(self.tools_dir, platform=self.platform)
                elif tool_name == "sccache":
                    downloader = SccacheDownloader(
                        self.tools_dir, platform=self.platform
                    )
                elif tool_name == "make":
                    # MakeDownloader only works on Windows
                    if self.platform.os == "windows":
                        downloader = MakeDownloader(
                            self.tools_dir, platform=self.platform
                        )

                if downloader and downloader.is_installed():
                    logger.debug(f"Found {tool_name} in downloaded tools")
                    return True
            except Exception as e:
                logger.debug(f"Error checking downloaded {tool_name}: {e}")

        # 3. Check system PATH
        if shutil.which(tool_name):
            logger.debug(f"Found {tool_name} on system PATH")
            return True

        return False

    def _discover_backends(self) -> List[BuildBackend]:
        """Discover all available backends."""
        candidates: List[BuildBackend] = []

        # Try Ninja first (preferred)
        # Check with priority: custom > downloaded > system
        if self._check_tool_available("ninja"):
            ninja = NinjaBackend()
            candidates.append(ninja)
            logger.info("Ninja build backend available")

        # Platform-specific backends
        if self.platform.os == "windows":
            # Try Visual Studio
            for vs_version in ["17 2022", "16 2019", "15 2017"]:
                msbuild = MSBuildBackend(vs_version)
                if msbuild.is_available():
                    candidates.append(msbuild)
                    logger.info(f"MSBuild {vs_version} available")
                    break

            # NMake as fallback
            nmake = NMakeMakefilesBackend()
            if nmake.is_available():
                candidates.append(nmake)
                logger.info("NMake build backend available")

        elif self.platform.os == "macos":
            # Try Xcode
            xcode = XcodeBackend()
            if xcode.is_available():
                candidates.append(xcode)
                logger.info("Xcode build backend available")

            # Make as fallback
            # Check with priority: custom > downloaded > system
            if self._check_tool_available("make"):
                make = MakeBackend()
                candidates.append(make)
                logger.info("Make build backend available")

        else:  # Linux/Unix
            # Make is standard
            # Check with priority: custom > downloaded > system
            if self._check_tool_available("make"):
                make = MakeBackend()
                candidates.append(make)
                logger.info("Make build backend available")

        return candidates

    def detect_best(self) -> BuildBackend:
        """
        Detect best available backend.

        Preference order:
        1. Ninja (fastest, most portable)
        2. Platform native (MSBuild, Xcode)
        3. Make (universal fallback)

        Returns:
            Best available BuildBackend

        Raises:
            BuildBackendError: If no backend is available
        """
        if not self._backends:
            raise BuildBackendError(
                "No build backend available. Please install Ninja, Make, "
                "MSBuild (Visual Studio), or Xcode."
            )

        # Prefer Ninja if available
        for backend in self._backends:
            if isinstance(backend, NinjaBackend):
                logger.info(f"Selected build backend: {backend}")
                return backend

        # Otherwise use first available
        backend = self._backends[0]
        logger.info(f"Selected build backend: {backend}")
        return backend

    def get_all(self) -> List[BuildBackend]:
        """
        Get all available backends.

        Returns:
            List of available BuildBackend instances
        """
        return self._backends.copy()

    def get_by_name(self, name: str) -> Optional[BuildBackend]:
        """
        Get backend by name (case-insensitive).

        Args:
            name: Backend name (e.g., 'ninja', 'make', 'visual studio')

        Returns:
            BuildBackend if found, None otherwise
        """
        name_lower = name.lower()

        for backend in self._backends:
            if backend.name.lower() == name_lower:
                return backend

            # Check for partial matches
            if name_lower in backend.name.lower():
                return backend

        return None


class BuildBackendConfig:
    """Configuration for build backend."""

    def __init__(self, backend: BuildBackend):
        """
        Initialize build backend configuration.

        Args:
            backend: BuildBackend instance to configure
        """
        self.backend = backend

    def generate_cmake_args(self) -> List[str]:
        """
        Generate cmake configuration arguments.

        Returns:
            List of CMake command-line arguments
        """
        args = [
            "-G",
            self.backend.get_cmake_generator(),
        ]

        # Add any extra variables
        for key, value in self.backend.get_cmake_variables().items():
            if key != "CMAKE_GENERATOR":
                args.extend(["-D", f"{key}={value}"])

        return args

    def generate_build_args(self, config: str = "Release") -> List[str]:
        """
        Generate cmake build arguments.

        Args:
            config: Build configuration (Debug, Release, etc.)

        Returns:
            List of cmake --build arguments
        """
        args = ["--build", ".", "--config", config]
        args.extend(self.backend.get_build_args())
        return args

    def generate_cmake_snippet(self) -> str:
        """
        Generate CMake configuration snippet.

        Returns:
            CMake code snippet as string
        """
        lines = [
            f"# Build Backend: {self.backend.name}",
            f"# Parallel Jobs: {self.backend.parallel_jobs}",
            "",
        ]

        for key, value in self.backend.get_cmake_variables().items():
            lines.append(f'set({key} "{value}")')

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.backend.name,
            "generator": self.backend.get_cmake_generator(),
            "parallel_jobs": self.backend.parallel_jobs,
            "cmake_variables": self.backend.get_cmake_variables(),
        }


def detect_build_backend(
    platform_info=None, prefer: Optional[str] = None
) -> BuildBackend:
    """
    Detect and return the best build backend.

    Args:
        platform_info: Optional PlatformInfo object
        prefer: Optional preferred backend name

    Returns:
        BuildBackend instance

    Raises:
        BuildBackendError: If no backend available
        BackendNotAvailableError: If preferred backend not available
    """
    detector = BuildBackendDetector(platform_info)

    if prefer:
        backend = detector.get_by_name(prefer)
        if backend is None:
            available = [b.name for b in detector.get_all()]
            raise BackendNotAvailableError(
                f"Preferred backend '{prefer}' not available. "
                f"Available backends: {', '.join(available)}"
            )
        return backend

    return detector.detect_best()


def example_usage():
    """Example: Detect and configure build backend."""
    from ..core.platform import detect_platform

    print("=== Build Backend Detection ===\n")

    platform = detect_platform()
    print(f"Platform: {platform.os} {platform.architecture}")

    detector = BuildBackendDetector(platform)

    # Detect best backend
    backend = detector.detect_best()
    print(f"\nBest backend: {backend}")

    # Show all available
    print("\nAll available backends:")
    for b in detector.get_all():
        print(f"  - {b}")

    # Create configuration
    config = BuildBackendConfig(backend)

    # Generate cmake args
    cmake_args = config.generate_cmake_args()
    print("\nCMake configuration args:")
    print(f"  cmake {' '.join(cmake_args)} <source-dir>")

    # Generate build args
    build_args = config.generate_build_args("Debug")
    print("\nCMake build args:")
    print(f"  cmake {' '.join(build_args)}")

    # Generate CMake snippet
    print("\nCMake configuration snippet:")
    print(config.generate_cmake_snippet())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
