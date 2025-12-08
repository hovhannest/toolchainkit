"""
ToolchainKit Plugin System.

This module provides the base classes and interfaces for the ToolchainKit plugin system,
enabling third-party extensions for compilers, package managers, and build backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path


# Exception Hierarchy
class PluginError(Exception):
    """Base exception for all plugin-related errors."""

    pass


class PluginNotFoundError(PluginError):
    """Plugin not found in search paths."""

    def __init__(self, plugin_name: str, search_paths: List[Path]):
        self.plugin_name = plugin_name
        self.search_paths = search_paths
        super().__init__(
            f"Plugin '{plugin_name}' not found in search paths: "
            f"{', '.join(str(p) for p in search_paths)}"
        )


class PluginLoadError(PluginError):
    """Failed to load plugin module or class."""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Failed to load plugin '{plugin_name}': {reason}")


class PluginValidationError(PluginError):
    """Plugin metadata or environment validation failed."""

    def __init__(self, plugin_name: str, issues: List[str]):
        self.plugin_name = plugin_name
        self.issues = issues
        issues_str = "\n  - ".join(issues)
        super().__init__(f"Plugin '{plugin_name}' validation failed:\n  - {issues_str}")


class PluginDependencyError(PluginError):
    """Plugin dependency not satisfied."""

    def __init__(self, plugin_name: str, dependency: str, reason: str):
        self.plugin_name = plugin_name
        self.dependency = dependency
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}' requires '{dependency}': {reason}")


class PluginInitializationError(PluginError):
    """Plugin initialization failed."""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}' initialization failed: {reason}")


# Base Plugin Interface
class Plugin(ABC):
    """
    Base class for all ToolchainKit plugins.

    All plugin types (CompilerPlugin, PackageManagerPlugin, BuildBackendPlugin)
    must extend this class and implement its abstract methods.

    Lifecycle:
        1. Plugin discovered (from plugin.yaml)
        2. Plugin loaded (Python module imported)
        3. Plugin initialized (initialize() called with context)
        4. Plugin used (provides functionality)
        5. Plugin cleaned up (cleanup() called on shutdown)
    """

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return plugin metadata.

        Returns:
            Dict with required keys:
            - name: str - Unique plugin identifier (e.g., "zig-compiler")
            - version: str - Semantic version (e.g., "1.0.0")
            - description: str - Short description of plugin functionality
            - author: str - Author name or organization

            Optional keys:
            - homepage: str - Project URL
            - license: str - License identifier (e.g., "MIT", "Apache-2.0")
            - requires: List[str] - Plugin dependencies with version constraints
            - tags: List[str] - Searchable tags

        Example:
            {
                'name': 'zig-compiler',
                'version': '1.0.0',
                'description': 'Zig compiler support for ToolchainKit',
                'author': 'ToolchainKit Community',
                'homepage': 'https://github.com/example/tk-zig',
                'license': 'MIT',
                'requires': ['base-utils >= 1.0'],
                'tags': ['compiler', 'zig', 'cross-platform']
            }
        """
        pass

    @abstractmethod
    def initialize(self, context: Any) -> None:
        """
        Initialize plugin with provided context.

        Called once when plugin is loaded. Use this to:
        - Validate environment and dependencies
        - Register provided functionality (compilers, package managers, etc.)
        - Set up internal state
        - Perform one-time setup operations

        Args:
            context: PluginContext object providing:
                - Access to plugin registry for registration
                - Cache directory for plugin data
                - Global configuration
                - Helper methods (load YAML compilers, etc.)

        Raises:
            PluginInitializationError: If initialization fails (missing dependencies,
                                       invalid environment, etc.)

        Example:
            def initialize(self, context):
                # Validate compiler exists
                if not self._find_zig_compiler():
                    raise PluginInitializationError(
                        self.metadata()['name'],
                        "Zig compiler not found in PATH"
                    )

                # Load and register compiler configuration
                zig_config = context.load_yaml_compiler(
                    Path(__file__).parent / "zig.yaml"
                )
                context.register_compiler('zig', zig_config)
        """
        pass

    def cleanup(self) -> None:
        """
        Called when plugin is unloaded (optional).

        Override this method to perform cleanup:
        - Close open file handles
        - Terminate background processes
        - Release system resources
        - Save state if needed

        Default implementation does nothing.

        Note: This is called on system shutdown or explicit plugin unload.
              It's not guaranteed to be called in abnormal termination.
        """
        pass

    def validate(self) -> bool:
        """
        Validate plugin can function in current environment (optional).

        Override to perform environment checks:
        - Check if required executables exist
        - Verify required dependencies are available
        - Test system compatibility

        Returns:
            True if plugin can function, False otherwise

        Default implementation returns True (assume valid).
        """
        return True


# Export public API
# Import plugin types
from toolchainkit.plugins.compiler import CompilerPlugin  # noqa: E402
from toolchainkit.plugins.package_manager import (  # noqa: E402
    PackageManagerPlugin,
    PackageManagerError,
)
from toolchainkit.plugins.build_backend import (  # noqa: E402
    BuildBackendPlugin,
    BuildBackendError,
)
from toolchainkit.plugins.metadata import (  # noqa: E402
    PluginMetadata,
    PluginMetadataParser,
)
from toolchainkit.plugins.discovery import PluginDiscoverer  # noqa: E402
from toolchainkit.plugins.loader import PluginLoader  # noqa: E402
from toolchainkit.plugins.registry import (  # noqa: E402
    PluginRegistry,
    get_global_registry,
    reset_global_registry,
)
from toolchainkit.plugins.context import PluginContext  # noqa: E402
from toolchainkit.plugins.manager import PluginManager  # noqa: E402

__all__ = [
    # Base class
    "Plugin",
    # Plugin types
    "CompilerPlugin",
    "PackageManagerPlugin",
    "BuildBackendPlugin",
    # Metadata
    "PluginMetadata",
    "PluginMetadataParser",
    # Discovery
    "PluginDiscoverer",
    # Loading
    "PluginLoader",
    # Registry
    "PluginRegistry",
    "get_global_registry",
    "reset_global_registry",
    # Context
    "PluginContext",
    # Manager
    "PluginManager",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginLoadError",
    "PluginValidationError",
    "PluginDependencyError",
    "PluginInitializationError",
    "PackageManagerError",
    "BuildBackendError",
]
