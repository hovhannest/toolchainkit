"""
CI/CD integration for ToolchainKit.

This module provides template generators for popular CI/CD platforms
(GitHub Actions, GitLab CI) to easily set up automated builds.
"""

from .templates import CITemplateGenerator

__all__ = ["CITemplateGenerator"]
