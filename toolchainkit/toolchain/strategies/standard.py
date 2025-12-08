"""
Standard Compiler Strategies.

Implementations for standard compilers: Clang, GCC, MSVC.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from ..strategy import CompilerStrategy


class ClangStrategy(CompilerStrategy):
    """Strategy for Clang compiler."""

    def get_compiler_paths(self, toolchain_root: Path, platform: Any) -> Dict[str, str]:
        c_path = toolchain_root / "bin" / "clang"
        cxx_path = toolchain_root / "bin" / "clang++"

        if platform.os == "windows":
            c_path = c_path.with_suffix(".exe")
            cxx_path = cxx_path.with_suffix(".exe")
            rc_path = toolchain_root / "bin" / "llvm-rc.exe"
            return {
                "CMAKE_C_COMPILER": str(c_path),
                "CMAKE_CXX_COMPILER": str(cxx_path),
                "CMAKE_RC_COMPILER": str(rc_path),
            }

        return {"CMAKE_C_COMPILER": str(c_path), "CMAKE_CXX_COMPILER": str(cxx_path)}

    def get_flags(self, config: Any) -> List[str]:
        lines = ["# Clang compiler flags"]

        # Standard library
        if config.stdlib:
            lines.append(f'set(CMAKE_CXX_FLAGS_INIT "-stdlib={config.stdlib}")')

        # Linker
        if config.linker:
            lines.append(f'set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld={config.linker}")')
            lines.append(
                f'set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld={config.linker}")'
            )

            # If using libc++, link against libc++ libraries
            if config.stdlib == "libc++":
                lines.append(
                    'string(APPEND CMAKE_EXE_LINKER_FLAGS_INIT " -lc++ -lc++abi")'
                )
                lines.append(
                    'string(APPEND CMAKE_SHARED_LINKER_FLAGS_INIT " -lc++ -lc++abi")'
                )

        return lines

    def get_preferred_generator(self, platform: Any) -> Optional[str]:
        """
        Get the preferred CMake generator for Clang.

        On Windows, Clang can have issues with the default Visual Studio generator
        when using GNU-style command lines, so we prefer Ninja.

        Args:
            platform: Platform information object

        Returns:
            "Ninja" on Windows, None on other platforms
        """
        if platform.os == "windows":
            return "Ninja"
        return None


class GccStrategy(CompilerStrategy):
    """Strategy for GCC compiler."""

    def get_compiler_paths(self, toolchain_root: Path, platform: Any) -> Dict[str, str]:
        c_path = toolchain_root / "bin" / "gcc"
        cxx_path = toolchain_root / "bin" / "g++"

        if platform.os == "windows":
            c_path = c_path.with_suffix(".exe")
            cxx_path = cxx_path.with_suffix(".exe")

        return {"CMAKE_C_COMPILER": str(c_path), "CMAKE_CXX_COMPILER": str(cxx_path)}

    def get_flags(self, config: Any) -> List[str]:
        lines = ["# GCC compiler flags"]

        # Linker
        if config.linker:
            lines.append(f'set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld={config.linker}")')
            lines.append(
                f'set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld={config.linker}")'
            )

        return lines


class MsvcStrategy(CompilerStrategy):
    """Strategy for MSVC compiler."""

    def get_compiler_paths(self, toolchain_root: Path, platform: Any) -> Dict[str, str]:
        # MSVC paths are typically detected by CMake or set via environment
        # But if we have a specific toolchain root, we can try to point to it
        cl_path = toolchain_root / "bin" / "Hostx64" / "x64" / "cl.exe"
        if cl_path.exists():
            return {
                "CMAKE_C_COMPILER": str(cl_path),
                "CMAKE_CXX_COMPILER": str(cl_path),
            }
        return {}

    def get_flags(self, config: Any) -> List[str]:
        return ["# MSVC compiler flags"]
