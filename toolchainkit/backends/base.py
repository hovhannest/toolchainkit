"""
Build backend interface for ToolchainKit.

This module defines the abstract base class for build backends (e.g., CMake, Meson).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class BuildBackend(ABC):
    """
    Abstract base class for build backends.

    A build backend is responsible for configuring and building the project.
    """

    @abstractmethod
    def configure(
        self,
        project_root: Path,
        build_dir: Path,
        toolchain_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        """
        Configure the build.

        Args:
            project_root: Root directory of the project
            build_dir: Directory where build artifacts should be placed
            toolchain_data: Information about the toolchain (paths, etc.)
            config: Configuration dictionary
        """
        pass
