"""
Cross-compilation support for ToolchainKit.

This module provides cross-compilation target configuration for various platforms
including Android, iOS, and embedded systems, as well as sysroot management.
"""

from toolchainkit.cross.targets import CrossCompileTarget, CrossCompilationConfigurator
from toolchainkit.cross.sysroot import SysrootSpec, SysrootManager

__all__ = [
    "CrossCompileTarget",
    "CrossCompilationConfigurator",
    "SysrootSpec",
    "SysrootManager",
]
