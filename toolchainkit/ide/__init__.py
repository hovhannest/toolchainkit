"""
IDE Integration Module

This module provides integration with various IDEs including VSCode, CLion, Qt Creator, and Visual Studio.
"""

from toolchainkit.ide.vscode import VSCodeIntegrator
from toolchainkit.ide.presets import CMakePresetsGenerator

__all__ = [
    "VSCodeIntegrator",
    "CMakePresetsGenerator",
]
