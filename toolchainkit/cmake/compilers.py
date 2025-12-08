"""
Compiler-specific configuration module for CMake toolchain generation.

This module provides the base abstractions for compiler configurations.
For actual compiler configurations, use the YAML-based system via
toolchainkit.cmake.yaml_compiler.YAMLCompilerLoader.

Example:
    ```python
    from toolchainkit.cmake.yaml_compiler import YAMLCompilerLoader

    # Load compiler configuration from YAML
    loader = YAMLCompilerLoader()
    config = loader.load_compiler('clang')

    # Use configuration for toolchain generation
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ToolchainSpec:
    """
    Specification for a compiler toolchain.

    This dataclass holds information about a specific compiler toolchain including
    its type, version, and installation paths.

    Attributes:
        type: Compiler type ('clang', 'gcc', 'msvc')
        version: Compiler version string (e.g., '18.1.8', '13.2.0')
        c_compiler_path: Path to C compiler executable
        cxx_compiler_path: Path to C++ compiler executable
        install_path: Root installation directory of the toolchain

    Example:
        ```python
        spec = ToolchainSpec(
            type='gcc',
            version='13.2.0',
            c_compiler_path='/usr/bin/gcc-13',
            cxx_compiler_path='/usr/bin/g++-13',
            install_path='/usr'
        )
        ```
    """

    type: str
    version: str
    c_compiler_path: str
    cxx_compiler_path: str
    install_path: str

    def __post_init__(self):
        """Validate toolchain spec after initialization."""
        # Validate compiler type
        valid_types = ["clang", "gcc", "msvc"]
        if self.type.lower() not in valid_types:
            raise ValueError(
                f"Invalid compiler type: {self.type}. " f"Must be one of {valid_types}"
            )

        # Normalize type to lowercase
        self.type = self.type.lower()

        # Validate version format (basic check)
        if not re.match(r"^\d+(\.\d+)*", self.version):
            raise ValueError(
                f"Invalid version format: {self.version}. "
                "Expected format like '18.1.8' or '13.2.0'"
            )

        # Convert paths to Path objects for validation
        c_path = Path(self.c_compiler_path)
        cxx_path = Path(self.cxx_compiler_path)
        install_path = Path(self.install_path)

        # Store as strings for CMake compatibility
        self.c_compiler_path = str(c_path)
        self.cxx_compiler_path = str(cxx_path)
        self.install_path = str(install_path)


class CompilerConfig(ABC):
    """
    Abstract base class for compiler-specific configuration.

    This class defines the interface that all compiler configuration classes
    must implement. Each concrete compiler config generates CMake variables
    and flags specific to that compiler.
    """

    def __init__(self, toolchain: ToolchainSpec, build_type: str = "Release"):
        """
        Initialize compiler configuration.

        Args:
            toolchain: Toolchain specification
            build_type: Build type ('Debug', 'Release', 'RelWithDebInfo', 'MinSizeRel')
        """
        self.toolchain = toolchain
        self.build_type = build_type
        self._validate_build_type()

    def _validate_build_type(self):
        """Validate build type."""
        valid_types = ["Debug", "Release", "RelWithDebInfo", "MinSizeRel"]
        if self.build_type not in valid_types:
            raise ValueError(
                f"Invalid build type: {self.build_type}. "
                f"Must be one of {valid_types}"
            )

    @abstractmethod
    def get_cmake_variables(self) -> Dict[str, str]:
        """
        Get compiler-specific CMake variables.

        Returns:
            Dictionary of CMake variable names to values
        """
        pass

    @abstractmethod
    def get_compile_flags(self) -> List[str]:
        """
        Get compiler-specific compile flags.

        Returns:
            List of compiler flags for compilation
        """
        pass

    @abstractmethod
    def get_link_flags(self) -> List[str]:
        """
        Get compiler-specific link flags.

        Returns:
            List of linker flags
        """
        pass

    def generate_cmake_snippet(self) -> str:
        """
        Generate CMake code snippet for this compiler configuration.

        Returns:
            CMake code as string
        """
        lines = []
        lines.append("# Compiler Configuration")
        lines.append(f"# Compiler: {self.toolchain.type} {self.toolchain.version}")
        lines.append(f"# Build Type: {self.build_type}")
        lines.append("")

        # Set CMake variables
        variables = self.get_cmake_variables()
        if variables:
            lines.append("# Compiler-specific CMake variables")
            for name, value in variables.items():
                if isinstance(value, bool):
                    cmake_value = "ON" if value else "OFF"
                else:
                    cmake_value = value
                lines.append(f'set({name} "{cmake_value}")')
            lines.append("")

        # Set compile flags
        compile_flags = self.get_compile_flags()
        if compile_flags:
            lines.append("# Compile flags")
            flags_str = " ".join(compile_flags)
            lines.append(f"add_compile_options({flags_str})")
            lines.append("")

        # Set link flags
        link_flags = self.get_link_flags()
        if link_flags:
            lines.append("# Link flags")
            flags_str = " ".join(link_flags)
            lines.append(f"add_link_options({flags_str})")
            lines.append("")

        return "\n".join(lines)
