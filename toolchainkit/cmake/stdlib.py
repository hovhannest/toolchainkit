"""
C++ standard library configuration module for CMake toolchain generation.

This module provides classes for configuring different C++ standard libraries
(libc++, libstdc++, MSVC) with library-specific flags, paths, and settings.
Each standard library has its own configuration class that generates appropriate
CMake variables and compile/link flags.

Example:
    ```python
    from toolchainkit.cmake.stdlib import LibCxxConfig
    from pathlib import Path

    # Create libc++ configuration
    config = LibCxxConfig(
        install_path=Path('/opt/llvm-18.1.8')
    )

    # Generate CMake snippet
    cmake_content = config.generate_cmake_snippet()
    ```
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StandardLibraryConfig:
    """
    Abstract base class for C++ standard library configuration.

    This class defines the interface that all standard library configuration
    classes must implement. Each concrete stdlib config generates CMake variables
    and flags specific to that standard library.

    Attributes:
        stdlib_type: Type of standard library ('libc++', 'libstdc++', 'msvc')
        version: Optional version string
        include_paths: List of include directories
        library_paths: List of library directories
    """

    def __init__(
        self,
        stdlib_type: str,
        version: Optional[str] = None,
        include_paths: Optional[List[Path]] = None,
        library_paths: Optional[List[Path]] = None,
    ):
        """
        Initialize standard library configuration.

        Args:
            stdlib_type: Type of standard library
            version: Optional version string
            include_paths: Optional list of include directories
            library_paths: Optional list of library directories
        """
        self.stdlib_type = stdlib_type
        self.version = version
        self.include_paths = include_paths or []
        self.library_paths = library_paths or []

    def get_compile_flags(self) -> List[str]:
        """
        Get standard library compile flags.

        Returns:
            List of compiler flags for compilation
        """
        raise NotImplementedError

    def get_link_flags(self) -> List[str]:
        """
        Get standard library link flags.

        Returns:
            List of linker flags
        """
        raise NotImplementedError

    def get_cmake_variables(self) -> Dict[str, str]:
        """
        Get CMake variables for this standard library.

        Returns:
            Dictionary of CMake variable names to values
        """
        return {}

    def generate_cmake_snippet(self) -> str:
        """
        Generate CMake code snippet for this stdlib configuration.

        Returns:
            CMake code as string
        """
        lines = []
        lines.append(f"# Standard Library: {self.stdlib_type}")
        if self.version:
            lines.append(f"# Version: {self.version}")
        lines.append("")

        # Set CMake variables
        variables = self.get_cmake_variables()
        if variables:
            lines.append("# Standard library CMake variables")
            for name, value in variables.items():
                lines.append(f'set({name} "{value}")')
            lines.append("")

        # Set compile flags
        compile_flags = self.get_compile_flags()
        if compile_flags:
            lines.append("# Standard library compile flags")
            flags_str = " ".join(compile_flags)
            lines.append(f'string(APPEND CMAKE_CXX_FLAGS_INIT " {flags_str}")')
            lines.append("")

        # Set link flags
        link_flags = self.get_link_flags()
        if link_flags:
            lines.append("# Standard library link flags")
            flags_str = " ".join(link_flags)
            lines.append(f'string(APPEND CMAKE_EXE_LINKER_FLAGS_INIT " {flags_str}")')
            lines.append(
                f'string(APPEND CMAKE_SHARED_LINKER_FLAGS_INIT " {flags_str}")'
            )
            lines.append("")

        return "\n".join(lines)


class LibCxxConfig(StandardLibraryConfig):
    """
    Configuration for libc++ (LLVM C++ standard library).

    libc++ is LLVM's implementation of the C++ standard library. It provides
    modern C++ features and is the default on macOS. Can be used with Clang
    on Linux and Windows.

    Attributes:
        abi_version: Optional ABI version string
        install_path: Path to libc++ installation directory

    Example:
        ```python
        config = LibCxxConfig(
            install_path=Path('/opt/llvm-18.1.8'),
            abi_version='1'
        )
        ```
    """

    def __init__(
        self,
        version: Optional[str] = None,
        abi_version: Optional[str] = None,
        install_path: Optional[Path] = None,
    ):
        """
        Initialize libc++ configuration.

        Args:
            version: Optional version string
            abi_version: Optional ABI version
            install_path: Path to libc++ installation
        """
        super().__init__("libc++", version)
        self.abi_version = abi_version
        self.install_path = install_path

    def get_compile_flags(self) -> List[str]:
        """Get libc++ compile flags."""
        flags = ["-stdlib=libc++"]

        if self.install_path:
            # Add include directory with -isystem to avoid warnings
            include_dir = self.install_path / "include" / "c++" / "v1"
            if include_dir.exists():
                flags.append(f"-isystem{include_dir}")

        return flags

    def get_link_flags(self) -> List[str]:
        """Get libc++ link flags."""
        flags = ["-stdlib=libc++", "-lc++", "-lc++abi"]

        if self.install_path:
            lib_dir = self.install_path / "lib"
            if lib_dir.exists():
                flags.append(f"-L{lib_dir}")
                # Set rpath for runtime library loading
                flags.append(f"-Wl,-rpath,{lib_dir}")

        return flags

    def get_cmake_variables(self) -> Dict[str, str]:
        """Get CMake variables."""
        variables = {}

        if self.install_path:
            variables["LIBCXX_INSTALL_PREFIX"] = str(self.install_path)

        if self.abi_version:
            variables["LIBCXX_ABI_VERSION"] = self.abi_version

        return variables


class LibStdCxxConfig(StandardLibraryConfig):
    """
    Configuration for libstdc++ (GNU C++ standard library).

    libstdc++ is the GNU implementation of the C++ standard library. It is
    the default standard library for GCC and can also be used with Clang
    on Linux systems.

    Attributes:
        gcc_path: Path to GCC installation (for Clang with libstdc++)

    Example:
        ```python
        config = LibStdCxxConfig(
            gcc_path=Path('/usr'),
            version='13.2.0'
        )
        ```
    """

    def __init__(self, version: Optional[str] = None, gcc_path: Optional[Path] = None):
        """
        Initialize libstdc++ configuration.

        Args:
            version: Optional version string
            gcc_path: Path to GCC installation
        """
        super().__init__("libstdc++", version)
        self.gcc_path = gcc_path

    def get_compile_flags(self) -> List[str]:
        """Get libstdc++ compile flags."""
        flags = []

        # If using Clang with specific GCC version, point to GCC toolchain
        if self.gcc_path:
            flags.append(f"--gcc-toolchain={self.gcc_path}")

        return flags

    def get_link_flags(self) -> List[str]:
        """Get libstdc++ link flags."""
        flags = []

        if self.gcc_path:
            # Try lib64 first (common on 64-bit Linux), fall back to lib
            lib_dir = self.gcc_path / "lib64"
            if not lib_dir.exists():
                lib_dir = self.gcc_path / "lib"

            if lib_dir.exists():
                flags.append(f"-L{lib_dir}")
                # Set rpath for runtime library loading
                flags.append(f"-Wl,-rpath,{lib_dir}")

        return flags

    def get_cmake_variables(self) -> Dict[str, str]:
        """Get CMake variables."""
        variables = {}

        if self.gcc_path:
            variables["LIBSTDCXX_GCC_PATH"] = str(self.gcc_path)

        return variables


class MSVCStdLibConfig(StandardLibraryConfig):
    """
    Configuration for MSVC C++ standard library.

    The MSVC standard library is Microsoft's implementation of the C++ standard
    library. It is automatically linked with MSVC compiler and doesn't require
    explicit configuration flags.

    Example:
        ```python
        config = MSVCStdLibConfig(version='19.39')
        ```
    """

    def __init__(self, version: Optional[str] = None):
        """
        Initialize MSVC standard library configuration.

        Args:
            version: Optional version string
        """
        super().__init__("msvc", version)

    def get_compile_flags(self) -> List[str]:
        """
        Get MSVC stdlib compile flags.

        MSVC standard library doesn't require explicit compile flags.
        It is automatically included via default include paths.

        Returns:
            Empty list (no flags needed)
        """
        return []

    def get_link_flags(self) -> List[str]:
        """
        Get MSVC stdlib link flags.

        MSVC standard library is automatically linked via
        #pragma comment(lib, ...) directives in headers.

        Returns:
            Empty list (no flags needed)
        """
        return []


class StandardLibraryDetector:
    """
    Detector for available standard libraries on the system.

    Searches common installation locations for libc++, libstdc++, and MSVC
    standard libraries on Windows, Linux, and macOS.

    Example:
        ```python
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = StandardLibraryDetector(platform)

        libcxx = detector.detect_libcxx()
        if libcxx:
            print(f"Found libc++ at {libcxx.install_path}")
        ```
    """

    def __init__(self, platform):
        """
        Initialize stdlib detector.

        Args:
            platform: Platform information object
        """
        self.platform = platform

    def detect_libcxx(self) -> Optional[LibCxxConfig]:
        """
        Detect libc++ installation on the system.

        Searches platform-specific locations for libc++ headers and libraries.

        Returns:
            LibCxxConfig if found, None otherwise
        """
        # Platform-specific search locations
        if hasattr(self.platform, "os") and self.platform.os == "windows":
            # libc++ less common on Windows
            locations = [
                Path("C:/Program Files/LLVM/include/c++/v1"),
                Path("C:/LLVM/include/c++/v1"),
            ]
        elif hasattr(self.platform, "os") and self.platform.os == "darwin":
            # System libc++ on macOS
            locations = [
                Path(
                    "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1"
                ),
                Path(
                    "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/c++/v1"
                ),
                Path("/usr/include/c++/v1"),
            ]
        else:  # Linux and others
            locations = [
                Path("/usr/include/c++/v1"),
                Path("/usr/lib/llvm-18/include/c++/v1"),
                Path("/usr/lib/llvm-17/include/c++/v1"),
                Path("/usr/lib/llvm-16/include/c++/v1"),
                Path("/usr/local/include/c++/v1"),
                Path("/opt/llvm/include/c++/v1"),
            ]

        for loc in locations:
            if loc.exists():
                # Try to find install root
                install_path = loc.parent.parent.parent
                # Verify lib directory exists
                lib_dir = install_path / "lib"
                if lib_dir.exists():
                    logger.info(f"Detected libc++ at {install_path}")
                    return LibCxxConfig(install_path=install_path)

        logger.debug("libc++ not detected")
        return None

    def detect_libstdcxx(self) -> Optional[LibStdCxxConfig]:
        """
        Detect libstdc++ installation on the system.

        Searches for GCC installations that include libstdc++.

        Returns:
            LibStdCxxConfig if found, None otherwise
        """
        # Platform-specific search locations
        if hasattr(self.platform, "os") and self.platform.os == "windows":
            # Check MinGW locations
            gcc_paths = [
                Path("C:/mingw64"),
                Path("C:/msys64/mingw64"),
                Path("C:/MinGW"),
            ]
        elif hasattr(self.platform, "os") and self.platform.os == "darwin":
            # Less common on macOS (uses libc++)
            return None
        else:  # Linux
            gcc_paths = [
                Path("/usr"),
                Path("/usr/lib/gcc"),
            ]

        for gcc_path in gcc_paths:
            # Check for libstdc++.so in various lib directories
            for lib_dir_name in [
                "lib64",
                "lib",
                "lib/x86_64-linux-gnu",
                "lib/aarch64-linux-gnu",
            ]:
                lib_dir = gcc_path / lib_dir_name
                if lib_dir.exists():
                    # Look for libstdc++.so (Linux) or libstdc++.a (static)
                    if list(lib_dir.glob("libstdc++.so*")) or list(
                        lib_dir.glob("libstdc++.a")
                    ):
                        logger.info(f"Detected libstdc++ at {gcc_path}")
                        return LibStdCxxConfig(gcc_path=gcc_path)

        logger.debug("libstdc++ not detected")
        return None

    def detect_msvc_stdlib(self) -> Optional[MSVCStdLibConfig]:
        """
        Detect MSVC standard library.

        MSVC stdlib is part of the MSVC toolchain and is available
        when MSVC is installed.

        Returns:
            MSVCStdLibConfig on Windows, None otherwise
        """
        if not (hasattr(self.platform, "os") and self.platform.os == "windows"):
            return None

        # MSVC stdlib is part of MSVC toolchain
        # If MSVC is installed, stdlib is available
        logger.info("MSVC standard library available")
        return MSVCStdLibConfig()

    def detect_default(self, compiler_type: str) -> StandardLibraryConfig:
        """
        Detect default standard library for a compiler type.

        Args:
            compiler_type: Compiler type ('clang', 'gcc', 'msvc')

        Returns:
            Appropriate StandardLibraryConfig

        Raises:
            ValueError: Unknown compiler type
        """
        compiler_type_lower = compiler_type.lower()

        if compiler_type_lower in ["llvm", "clang"]:
            # Try libc++ first, fall back to libstdc++
            libcxx = self.detect_libcxx()
            if libcxx:
                return libcxx

            libstdcxx = self.detect_libstdcxx()
            if libstdcxx:
                return libstdcxx

            # Default to libc++ even if not detected (will use system default)
            return LibCxxConfig()

        elif compiler_type_lower == "gcc":
            # GCC uses libstdc++
            libstdcxx = self.detect_libstdcxx()
            if libstdcxx:
                return libstdcxx
            return LibStdCxxConfig()

        elif compiler_type_lower == "msvc":
            # MSVC uses MSVC stdlib
            return MSVCStdLibConfig()

        else:
            raise ValueError(f"Unknown compiler type: {compiler_type}")


class StandardLibraryConfigFactory:
    """
    Factory for creating standard library configuration objects.

    Provides static methods to create appropriate stdlib configuration
    instances based on stdlib type or by detecting the default for a compiler.

    Example:
        ```python
        # Create specific stdlib config
        config = StandardLibraryConfigFactory.create(
            'libc++',
            install_path=Path('/opt/llvm')
        )

        # Create default config for compiler
        from toolchainkit.core.platform import detect_platform
        platform = detect_platform()
        config = StandardLibraryConfigFactory.create_default('clang', platform)
        ```
    """

    @staticmethod
    def create(stdlib_type: str, **kwargs) -> StandardLibraryConfig:
        """
        Create standard library configuration.

        Args:
            stdlib_type: Type of stdlib ('libc++', 'libstdc++', 'msvc')
            **kwargs: Stdlib-specific keyword arguments

        Returns:
            Appropriate StandardLibraryConfig instance

        Raises:
            ValueError: Unknown stdlib type

        Example:
            ```python
            config = StandardLibraryConfigFactory.create(
                'libc++',
                install_path=Path('/opt/llvm-18.1.8')
            )
            ```
        """
        stdlib_type_lower = stdlib_type.lower()

        if stdlib_type_lower == "libc++":
            return LibCxxConfig(**kwargs)
        elif stdlib_type_lower == "libstdc++":
            return LibStdCxxConfig(**kwargs)
        elif stdlib_type_lower == "msvc":
            return MSVCStdLibConfig(**kwargs)
        else:
            raise ValueError(
                f"Unknown stdlib type: {stdlib_type}. "
                "Supported types: libc++, libstdc++, msvc"
            )

    @staticmethod
    def create_default(compiler_type: str, platform) -> StandardLibraryConfig:
        """
        Create default stdlib configuration for compiler type.

        Automatically detects available standard libraries and selects
        the most appropriate one for the compiler.

        Args:
            compiler_type: Compiler type ('clang', 'gcc', 'msvc')
            platform: Platform information object

        Returns:
            Default StandardLibraryConfig for the compiler

        Example:
            ```python
            from toolchainkit.core.platform import detect_platform

            platform = detect_platform()
            config = StandardLibraryConfigFactory.create_default('clang', platform)
            ```
        """
        detector = StandardLibraryDetector(platform)
        return detector.detect_default(compiler_type)
