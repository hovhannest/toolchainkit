"""
Core interfaces for ToolchainKit.

This module defines the abstract interfaces that the core framework depends on.
Plugins and other components implement these interfaces to provide functionality
without the core having direct knowledge of them.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class ToolchainProvider(ABC):
    """
    Abstract interface for components that can provide toolchains.

    This interface allows the core framework to request toolchains without
    knowing whether they come from downloads, plugins, system installations,
    or other sources.
    """

    @abstractmethod
    def can_provide(self, toolchain_type: str, version: str) -> bool:
        """
        Check if this provider can supply the requested toolchain.

        Args:
            toolchain_type: Type of toolchain (e.g., "llvm", "gcc", "zig")
            version: Version string (e.g., "18.1.0", "latest")

        Returns:
            True if this provider can supply the toolchain, False otherwise
        """
        pass

    @abstractmethod
    def provide_toolchain(
        self, toolchain_type: str, version: str, platform: str, **kwargs
    ) -> Optional[Path]:
        """
        Provide the requested toolchain.

        Args:
            toolchain_type: Type of toolchain
            version: Version string
            platform: Platform identifier (e.g., "linux-x64")
            **kwargs: Additional provider-specific options

        Returns:
            Path to toolchain root directory, or None if unavailable
        """
        pass

    @abstractmethod
    def get_toolchain_id(self, toolchain_type: str, version: str, platform: str) -> str:
        """
        Get unique identifier for the toolchain.

        Args:
            toolchain_type: Type of toolchain
            version: Version string
            platform: Platform identifier

        Returns:
            Unique toolchain identifier (e.g., "llvm-18.1.0-linux-x64")
        """
        pass


class StrategyResolver(ABC):
    """
    Abstract interface for resolving compiler strategies.

    This interface decouples the core from the plugin registry, allowing
    the CMake generator to work with strategies without knowing their source.
    """

    @abstractmethod
    def resolve_strategy(self, compiler_type: str) -> Any:
        """
        Resolve a compiler strategy for the given compiler type.

        Args:
            compiler_type: Compiler type (e.g., "clang", "gcc", "zig")

        Returns:
            CompilerStrategy instance for the given type

        Raises:
            KeyError: If no strategy found for the compiler type
        """
        pass

    @abstractmethod
    def has_strategy(self, compiler_type: str) -> bool:
        """
        Check if a strategy is available for the given compiler type.

        Args:
            compiler_type: Compiler type

        Returns:
            True if strategy available, False otherwise
        """
        pass


class PackageManagerResolver(ABC):
    """
    Abstract interface for resolving package managers.

    This interface allows the core to work with package managers without
    knowing their implementation details.
    """

    @abstractmethod
    def resolve_manager(self, manager_name: str) -> Any:
        """
        Resolve a package manager by name.

        Args:
            manager_name: Package manager name (e.g., "conan", "vcpkg")

        Returns:
            Package manager instance

        Raises:
            KeyError: If manager not found
        """
        pass

    @abstractmethod
    def has_manager(self, manager_name: str) -> bool:
        """
        Check if a package manager is available.

        Args:
            manager_name: Package manager name

        Returns:
            True if available, False otherwise
        """
        pass


__all__ = [
    "ToolchainProvider",
    "StrategyResolver",
    "PackageManagerResolver",
]
