"""
CMake integration module for ToolchainKit.

This module provides functionality for generating CMake toolchain files
and configurations from ToolchainKit managed toolchains.
"""

from .toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
)
from .compilers import (
    CompilerConfig,
    ToolchainSpec,
)
from .stdlib import (
    StandardLibraryConfig,
    LibCxxConfig,
    LibStdCxxConfig,
    MSVCStdLibConfig,
    StandardLibraryDetector,
    StandardLibraryConfigFactory,
)
from .yaml_compiler import (
    YAMLCompilerLoader,
    YAMLCompilerConfig,
    YAMLCompilerError,
    YAMLCompilerNotFoundError,
    YAMLCompilerInvalidError,
)

__all__ = [
    "CMakeToolchainGenerator",
    "ToolchainFileConfig",
    "CompilerConfig",
    "ToolchainSpec",
    "StandardLibraryConfig",
    "LibCxxConfig",
    "LibStdCxxConfig",
    "MSVCStdLibConfig",
    "StandardLibraryDetector",
    "StandardLibraryConfigFactory",
    "YAMLCompilerLoader",
    "YAMLCompilerConfig",
    "YAMLCompilerError",
    "YAMLCompilerNotFoundError",
    "YAMLCompilerInvalidError",
]
