"""
Zig Compiler Plugin for ToolchainKit

This plugin provides integration for the Zig compiler toolchain.
Zig is a general-purpose programming language and toolchain for maintaining
robust, optimal, and reusable software.

Zig can also be used as a drop-in C/C++ compiler with excellent cross-compilation
support.

This plugin automatically downloads and manages Zig toolchains, storing them
in the ToolchainKit cache directory alongside other compilers.
"""

import shutil
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict

from toolchainkit.plugins import CompilerPlugin
from toolchainkit.toolchain.downloader import ToolchainDownloader
from toolchainkit.core.platform import detect_platform
from toolchainkit.toolchain.strategy import CompilerStrategy
from toolchainkit.core.interfaces import ToolchainProvider

logger = logging.getLogger(__name__)


class ZigToolchainProvider(ToolchainProvider):
    """Provides Zig toolchains from the plugin's registry."""

    def __init__(self, downloader, metadata_registry):
        """
        Initialize Zig toolchain provider.

        Args:
            downloader: ToolchainDownloader configured with Zig registry
            metadata_registry: ToolchainMetadataRegistry for Zig
        """
        self._downloader = downloader
        self._metadata_registry = metadata_registry

    def can_provide(self, toolchain_type: str, version: str) -> bool:
        """Check if we can provide this toolchain."""
        return toolchain_type.lower() == "zig"

    def provide_toolchain(
        self, toolchain_type: str, version: str, platform: str, **kwargs
    ) -> Optional[Path]:
        """Download and provide the Zig toolchain."""
        if not self.can_provide(toolchain_type, version):
            return None

        try:
            # Use the plugin's downloader with plugin-specific registry
            result = self._downloader.download_toolchain(
                toolchain_name=toolchain_type,
                version=version,
                platform=platform,
                force=kwargs.get("force", False),
                progress_callback=kwargs.get("progress_callback"),
            )
            return result.toolchain_path
        except Exception as e:
            logger.error(f"Failed to provide Zig toolchain: {e}")
            return None

    def get_toolchain_id(self, toolchain_type: str, version: str, platform: str) -> str:
        """Get unique identifier for the toolchain."""
        return f"{toolchain_type}-{version}-{platform}"


class ZigStrategy(CompilerStrategy):
    """Strategy for Zig compiler."""

    def get_compiler_paths(self, toolchain_root: Path, platform: Any) -> Dict[str, str]:
        """Get Zig compiler paths (single executable for both C and C++)."""
        if platform.os == "windows":
            zig_exe = toolchain_root / "zig.exe"
            compiler_path = str(zig_exe)
        else:
            zig_exe = toolchain_root / "zig"
            compiler_path = str(zig_exe)

        # Return the compiler path for both C and C++
        # CMake will invoke it with the appropriate arguments via our strategy's get_flags()
        return {
            "CMAKE_C_COMPILER": compiler_path,
            "CMAKE_CXX_COMPILER": compiler_path,
        }

    def get_flags(self, config: Any) -> List[str]:
        """Get compiler flags for Zig."""
        from toolchainkit.core.platform import detect_platform

        lines = ["# Zig compiler flags"]

        # Set compiler arguments to use zig as a C/C++ compiler
        # This tells CMake to invoke: zig cc <source> and zig c++ <source>
        lines.append(
            'set(CMAKE_C_COMPILER_ARG1 "cc" CACHE STRING "Zig C compiler argument")'
        )
        lines.append(
            'set(CMAKE_CXX_COMPILER_ARG1 "c++" CACHE STRING "Zig C++ compiler argument")'
        )

        # On Windows, target MinGW (GNU ABI) for C++ compatibility
        # Zig's libc++ uses Itanium ABI which is compatible with MinGW but not MSVC
        # This allows C++ code to work correctly with Zig's bundled standard library
        platform = detect_platform()
        if platform.os == "windows":
            if (
                platform.arch == "x86_64"
                or platform.arch == "x64"
                or platform.arch == "amd64"
            ):
                target = "x86_64-windows-gnu"
            elif platform.arch == "aarch64" or platform.arch == "arm64":
                target = "aarch64-windows-gnu"
            else:
                target = "x86_64-windows-gnu"  # default

            lines.append(
                f'set(CMAKE_C_COMPILER_TARGET "{target}" CACHE STRING "Zig target triple")'
            )
            lines.append(
                f'set(CMAKE_CXX_COMPILER_TARGET "{target}" CACHE STRING "Zig target triple")'
            )

            # Tell CMake that Zig uses GNU-style command line
            lines.append(
                'set(CMAKE_C_COMPILER_FRONTEND_VARIANT "GNU" CACHE STRING "Zig uses GNU-style flags")'
            )
            lines.append(
                'set(CMAKE_CXX_COMPILER_FRONTEND_VARIANT "GNU" CACHE STRING "Zig uses GNU-style flags")'
            )

            # Tell CMake the system details
            lines.append(
                'set(CMAKE_SYSTEM_NAME "Windows" CACHE STRING "Target system")'
            )
            lines.append(
                'set(CMAKE_SYSTEM_PROCESSOR "AMD64" CACHE STRING "Target processor")'
            )

        return lines

    def get_preferred_generator(self, platform) -> str | None:
        """
        Get the preferred CMake generator for Zig.

        Zig produces GNU-style object files, which are incompatible with
        MSVC's linker on Windows. Therefore, we require Ninja on Windows.

        Args:
            platform: Platform information object

        Returns:
            "Ninja" on Windows, None on other platforms
        """
        if platform.os == "windows":
            return "Ninja"
        return None


class ZigCompilerPlugin(CompilerPlugin):
    """
    Zig compiler plugin for ToolchainKit.

    Provides Zig compiler integration with support for C/C++ compilation
    and cross-compilation capabilities.
    """

    def __init__(self):
        """Initialize the Zig compiler plugin."""
        super().__init__()
        self.context = None
        self._config = None
        self._downloader = None
        self._toolchain_path = None
        self._plugin_registry = None

    def metadata(self) -> dict:
        """Return plugin metadata."""
        return {
            "name": "zig-compiler",
            "version": "1.0.0",
            "type": "compiler",
            "description": "Zig compiler support for ToolchainKit with cross-compilation",
            "author": "ToolchainKit Community",
            "homepage": "https://github.com/toolchainkit/tk-zig",
            "license": "MIT",
        }

    def initialize(self, context) -> None:
        """
        Initialize the plugin and register the Zig compiler.

        Args:
            context: PluginContext providing access to registry and utilities

        Raises:
            PluginError: If compiler configuration cannot be loaded
        """
        self.context = context

        # Initialize plugin-specific toolchain registry
        from toolchainkit.toolchain.metadata_registry import ToolchainMetadataRegistry

        registry_path = Path(__file__).parent / "toolchains.json"

        if not registry_path.exists():
            raise RuntimeError(
                f"Zig toolchain registry not found at {registry_path}. "
                "Plugin installation may be incomplete."
            )

        self._plugin_registry = ToolchainMetadataRegistry(registry_path)
        logger.info(f"Loaded plugin-specific registry: {registry_path}")

        # Initialize toolchain downloader with plugin registry
        self._downloader = ToolchainDownloader()
        # Override the downloader's registry with our plugin-specific one
        self._downloader.metadata_registry = self._plugin_registry

        # Load Zig compiler configuration from YAML
        yaml_path = Path(__file__).parent / "compilers" / "zig.yaml"

        if not yaml_path.exists():
            raise RuntimeError(
                f"Zig compiler configuration not found at {yaml_path}. "
                "Ensure the plugin is installed correctly."
            )

        # Load compiler configuration directly from the plugin's directory
        from toolchainkit.cmake.yaml_compiler import YAMLCompilerLoader

        plugin_dir = Path(__file__).parent
        loader = YAMLCompilerLoader(plugin_dir)
        self._config = loader.load("zig")

        # Register the compiler with the registry
        context.register_compiler("zig", self._config)

        # Register the Zig compiler strategy
        context.register_compiler_strategy("zig", ZigStrategy())

        # Register the Zig toolchain provider
        toolchain_provider = ZigToolchainProvider(
            self._downloader, self._plugin_registry
        )
        context.register_toolchain_provider(toolchain_provider)

        # Log successful registration
        logger.info("Zig compiler plugin initialized successfully")

    def cleanup(self) -> None:
        """
        Cleanup plugin resources.

        Called when the plugin manager is shutting down.
        """
        self.context = None
        self._config = None

    def compiler_name(self) -> str:
        """Return the unique compiler identifier."""
        return "zig"

    def compiler_config(self) -> Any:
        """Return the compiler configuration."""
        if self._config is None:
            raise RuntimeError("Plugin not initialized. Call initialize() first.")
        return self._config

    def supported_platforms(self) -> List[str]:
        """Return list of supported platforms."""
        return [
            "linux-x64",
            "linux-arm64",
            "windows-x64",
            "macos-x64",
            "macos-arm64",
        ]

    def detect_system_installation(self) -> Optional[Path]:
        """Detect if Zig is installed on the system."""
        # Check if 'zig' is in PATH
        zig_exe = shutil.which("zig")
        if zig_exe:
            # Return parent directory (installation root)
            zig_path = Path(zig_exe).resolve()
            return zig_path.parent

        # Check common installation directories
        common_paths = [
            Path("/usr/local/zig"),
            Path("/opt/zig"),
            Path.home() / ".local" / "zig",
        ]

        # On Windows, also check Program Files
        if Path("C:/").exists():
            common_paths.extend(
                [
                    Path("C:/Program Files/zig"),
                    Path("C:/zig"),
                ]
            )

        for path in common_paths:
            zig_exe_name = "zig.exe" if Path("C:/").exists() else "zig"
            if (path / zig_exe_name).exists():
                return path

        return None

    def get_version(self, compiler_path: Path) -> str:
        """
        Extract Zig compiler version from installation.

        Args:
            compiler_path: Path to Zig installation directory

        Returns:
            Version string (e.g., "0.11.0")

        Raises:
            RuntimeError: If version cannot be determined

        Example:
            >>> plugin = ZigCompilerPlugin()
            >>> version = plugin.get_version(Path("/usr/local/zig"))
            >>> print(version)
            '0.11.0'
        """
        import subprocess

        # Determine executable name based on platform
        zig_exe = compiler_path / "zig"
        if not zig_exe.exists():
            zig_exe = compiler_path / "zig.exe"

        if not zig_exe.exists():
            raise RuntimeError(
                f"Zig executable not found at {compiler_path}. "
                "Expected 'zig' or 'zig.exe'."
            )

        try:
            # Run 'zig version' command
            result = subprocess.run(
                [str(zig_exe), "version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            version = result.stdout.strip()

            if not version:
                raise RuntimeError("Empty version output from Zig compiler")

            return version

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get Zig version: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Timeout while getting Zig version") from e
        except Exception as e:
            raise RuntimeError(f"Error getting Zig version: {e}") from e

    def ensure_toolchain(self, version: str, platform: Optional[str] = None) -> Path:
        """
        Ensure Zig toolchain is available, downloading if necessary.

        This method checks if the requested Zig version is already cached.
        If not, it downloads and extracts it to the ToolchainKit cache directory.

        Args:
            version: Zig version (e.g., "0.13.0")
            platform: Target platform (e.g., "linux-x64"). If None, auto-detects.

        Returns:
            Path to Zig installation directory

        Raises:
            RuntimeError: If download or extraction fails

        Example:
            >>> plugin = ZigCompilerPlugin()
            >>> zig_path = plugin.ensure_toolchain("0.13.0")
            >>> print(f"Zig installed at: {zig_path}")
        """
        if platform is None:
            platform = detect_platform()

        # Convert platform to string format if it's a PlatformInfo object
        if hasattr(platform, "os") and hasattr(platform, "arch"):
            platform_str = f"{platform.os}-{platform.arch}"
        else:
            platform_str = str(platform)

        logger.info(f"Ensuring Zig {version} for {platform_str}")

        try:
            # Use ToolchainDownloader to get or download Zig
            result = self._downloader.download_toolchain(
                toolchain_name="zig",
                version=version,
                platform=platform_str,
                progress_callback=self._download_progress,
            )

            self._toolchain_path = result.toolchain_path

            if result.was_cached:
                logger.info(f"Using cached Zig {version} from {self._toolchain_path}")
            else:
                logger.info(f"Downloaded Zig {version} to {self._toolchain_path}")

            return self._toolchain_path

        except Exception as e:
            raise RuntimeError(f"Failed to ensure Zig toolchain: {e}") from e

    def _download_progress(self, progress):
        """
        Progress callback for toolchain download.

        Args:
            progress: ProgressInfo object with download status
        """
        if progress.phase == "downloading":
            percent = progress.percentage
            speed_mb = progress.speed_bps / (1024 * 1024)
            logger.info(f"Downloading Zig: {percent:.1f}% " f"({speed_mb:.2f} MB/s)")
        elif progress.phase == "extracting":
            logger.info(f"Extracting Zig: {progress.percentage:.1f}%")
        elif progress.phase == "complete":
            logger.info("Zig toolchain ready")

    def get_toolchain_path(self, version: str, root: Optional[Path] = None) -> Path:
        """
        Get path to Zig toolchain, ensuring it's downloaded if needed.

        This is the main method for obtaining a Zig toolchain. It follows this logic:
        1. If 'root' is explicitly provided, use that path
        2. If Zig is found in system PATH, use that
        3. Otherwise, download the specified version

        Args:
            version: Zig version string (e.g., "0.13.0")
            root: Optional explicit path to Zig installation

        Returns:
            Path to Zig installation directory

        Raises:
            RuntimeError: If toolchain cannot be obtained

        Example:
            >>> plugin = ZigCompilerPlugin()
            >>> # Will download if not found
            >>> zig_path = plugin.get_toolchain_path("0.13.0")
            >>> print(f"Using Zig at: {zig_path}")
        """
        # Option 1: Explicit root path provided
        if root:
            if not root.exists():
                raise RuntimeError(f"Specified Zig root does not exist: {root}")
            logger.info(f"Using explicitly specified Zig at: {root}")
            return root

        # Option 2: Check system installation
        system_zig = self.detect_system_installation()
        if system_zig:
            try:
                detected_version = self.get_version(system_zig)
                if detected_version == version:
                    logger.info(f"Using system Zig {version} at: {system_zig}")
                    return system_zig
                else:
                    logger.info(
                        f"System Zig version mismatch: "
                        f"found {detected_version}, need {version}. "
                        f"Will download correct version."
                    )
            except Exception as e:
                logger.warning(
                    f"Could not verify system Zig version: {e}. "
                    f"Will download version {version}."
                )

        # Option 3: Download the toolchain
        logger.info(f"Downloading Zig {version}...")
        return self.ensure_toolchain(version)

    def requires_ninja_on_windows(self) -> bool:
        """
        Zig compiler requires Ninja on Windows.

        Visual Studio generator doesn't work well with non-MSVC compilers.
        Ninja is required for proper Zig compilation on Windows.
        We use /MANIFEST:NO linker flag to prevent CMake from adding /MANIFEST:EMBED.

        Returns:
            True - Ninja is required on Windows for Zig
        """
        return True

    def get_conan_settings(self, platform: Any) -> Dict[str, str]:
        """
        Get Conan profile settings for Zig compiler.

        On Windows, Zig targets MinGW (GNU ABI) for C++ compatibility since
        Zig's libc++ uses Itanium ABI which is compatible with MinGW but not MSVC.

        This method tells Conan to use GCC settings which are compatible with
        MinGW and Zig's standard library.

        Args:
            platform: Platform information

        Returns:
            Dictionary of Conan settings (os, arch, compiler, etc.)
            Includes special keys:
            - conan.buildenv.CC: C compiler path and flags
            - conan.buildenv.CXX: C++ compiler path and flags
            - conan.conf.tools.cmake.cmaketoolchain:generator: CMake generator

        Note:
            When building dependencies from source, use --build=missing with Conan.
            Pre-built MSVC packages from Conan Center are NOT compatible.
        """
        settings = {}

        if platform.os == "windows":
            # Use GCC settings for MinGW compatibility
            settings["compiler"] = "gcc"
            settings["compiler.version"] = "13"  # Zig uses Clang 18, similar to GCC 13
            settings["compiler.libcxx"] = "libstdc++11"
            settings["compiler.cppstd"] = "20"

            # Set architecture
            if platform.arch in ["x86_64", "x64", "amd64"]:
                settings["arch"] = "x86_64"
            elif platform.arch in ["aarch64", "arm64"]:
                settings["arch"] = "aarch64"
            else:
                settings["arch"] = "x86_64"

            settings["os"] = "Windows"

            # Add Conan [buildenv] and [conf] settings
            # Get Zig path from system installation or use the one we found
            if self._toolchain_path:
                zig_exe = self._toolchain_path / "zig.exe"
            else:
                # Try to detect system Zig
                system_zig = self.detect_system_installation()
                if system_zig:
                    zig_exe = system_zig / "zig.exe"
                else:
                    # Fallback to common location
                    zig_exe = Path("C:/workspace/zig/zig-windows-x86_64-0.13.0/zig.exe")

            zig_exe_str = str(zig_exe).replace("\\", "/")

            # Set environment variables for Conan to use Zig as compiler
            settings[
                "conan.buildenv.CC"
            ] = f"{zig_exe_str} cc --target=x86_64-windows-gnu"
            settings[
                "conan.buildenv.CXX"
            ] = f"{zig_exe_str} c++ --target=x86_64-windows-gnu -std=c++20"

            # Tell Conan to use Ninja generator (required for non-MSVC on Windows)
            settings["conan.conf.tools.cmake.cmaketoolchain:generator"] = "Ninja"
        else:
            # On other platforms, Zig works like Clang
            settings["compiler"] = "clang"
            settings["compiler.version"] = "18"  # Zig 0.13 uses Clang 18
            settings["compiler.libcxx"] = "libc++"
            settings["compiler.cppstd"] = "20"

            settings["arch"] = (
                "x86_64"
                if platform.arch in ["x86_64", "x64", "amd64"]
                else platform.arch
            )
            settings["os"] = (
                "Linux" if platform.os == "linux" else platform.os.capitalize()
            )

        return settings


__all__ = ["ZigCompilerPlugin"]
