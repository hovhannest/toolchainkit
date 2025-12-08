"""
Compiler Strategy Interface.

This module defines the interface for compiler strategies, which encapsulate
compiler-specific logic for toolchain generation.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional


class CompilerStrategy(ABC):
    """
    Abstract base class for compiler strategies.

    A compiler strategy defines how to configure a specific compiler type
    (e.g., Clang, GCC, MSVC) for CMake toolchain generation.
    """

    @abstractmethod
    def get_compiler_paths(self, toolchain_root: Path, platform: Any) -> Dict[str, str]:
        """
        Get paths to C and C++ compilers.

        Args:
            toolchain_root: Root directory of the toolchain installation
            platform: Platform information object

        Returns:
            Dictionary with keys 'CMAKE_C_COMPILER' and 'CMAKE_CXX_COMPILER'
            mapping to absolute paths.
        """
        pass

    @abstractmethod
    def get_flags(self, config: Any) -> List[str]:
        """
        Get compiler and linker flags.

        Args:
            config: ToolchainFileConfig object containing settings

        Returns:
            List of CMake set() commands to configure flags.
        """
        pass

    def get_preferred_generator(self, platform: Any) -> Optional[str]:
        """
        Get the preferred CMake generator for this compiler on the given platform.

        Args:
            platform: Platform information object

        Returns:
            Generator name (e.g., "Ninja", "Unix Makefiles") or None for default.
        """
        return None
