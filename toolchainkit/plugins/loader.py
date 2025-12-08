"""
Plugin loader for dynamically importing and instantiating plugins.

This module provides functionality to load plugin Python modules and
instantiate plugin classes from entry point specifications.
"""

import sys
import importlib
from toolchainkit.plugins import (
    Plugin,
    CompilerPlugin,
    PackageManagerPlugin,
    BuildBackendPlugin,
    PluginLoadError,
    PluginValidationError,
)
from toolchainkit.plugins.metadata import PluginMetadata


class PluginLoader:
    """
    Load plugins by dynamically importing modules and instantiating classes.

    The loader handles:
    - Dynamic module import using importlib
    - Plugin class instantiation
    - Type validation (plugin extends correct base class)
    - Error handling for import and instantiation failures
    """

    # Map plugin types to expected base classes
    PLUGIN_TYPE_MAP = {
        "compiler": CompilerPlugin,
        "package_manager": PackageManagerPlugin,
        "backend": BuildBackendPlugin,
    }

    def load(self, metadata: PluginMetadata) -> Plugin:
        """
        Load plugin from metadata.

        Process:
        1. Add plugin directory to sys.path
        2. Import module dynamically
        3. Get plugin class
        4. Instantiate plugin
        5. Validate plugin type
        6. Return plugin instance

        Args:
            metadata: PluginMetadata with entry_point and plugin_dir

        Returns:
            Plugin instance (CompilerPlugin, PackageManagerPlugin, or BuildBackendPlugin)

        Raises:
            PluginLoadError: If module import or class instantiation fails
            PluginValidationError: If plugin doesn't extend correct base class

        Example:
            loader = PluginLoader()
            plugin = loader.load(metadata)
            plugin.initialize(context)
        """
        # Add plugin directory to sys.path
        if metadata.plugin_dir:
            plugin_dir_str = str(metadata.plugin_dir)
            if plugin_dir_str not in sys.path:
                sys.path.insert(0, plugin_dir_str)

        try:
            # Import module
            module = self._import_module(metadata)

            # Instantiate plugin
            plugin = self._instantiate_plugin(module, metadata)

            # Validate plugin type
            self._validate_plugin(plugin, metadata)

            return plugin

        except PluginLoadError:
            # Re-raise PluginLoadError as-is
            raise
        except PluginValidationError:
            # Re-raise PluginValidationError as-is
            raise
        except Exception as e:
            # Wrap other exceptions
            raise PluginLoadError(metadata.name, f"Unexpected error: {e}")

    def _import_module(self, metadata: PluginMetadata):
        """
        Import plugin module dynamically.

        Args:
            metadata: PluginMetadata with module name

        Returns:
            Imported module object

        Raises:
            PluginLoadError: If module cannot be imported
        """
        module_name = metadata.get_module_name()

        try:
            module = importlib.import_module(module_name)
            return module
        except ModuleNotFoundError as e:
            raise PluginLoadError(
                metadata.name, f"Module '{module_name}' not found: {e}"
            )
        except ImportError as e:
            raise PluginLoadError(metadata.name, f"Failed to import module: {e}")
        except Exception as e:
            raise PluginLoadError(
                metadata.name, f"Error importing module '{module_name}': {e}"
            )

    def _instantiate_plugin(self, module, metadata: PluginMetadata) -> Plugin:
        """
        Instantiate plugin class from module.

        Args:
            module: Imported module object
            metadata: PluginMetadata with class name

        Returns:
            Plugin instance

        Raises:
            PluginLoadError: If class not found or instantiation fails
        """
        class_name = metadata.get_class_name()

        # Get class from module
        if not hasattr(module, class_name):
            raise PluginLoadError(
                metadata.name,
                f"Class '{class_name}' not found in module '{metadata.get_module_name()}'",
            )

        plugin_class = getattr(module, class_name)

        # Verify it's a class
        if not isinstance(plugin_class, type):
            raise PluginLoadError(
                metadata.name,
                f"'{class_name}' is not a class (it's {type(plugin_class)})",
            )

        # Instantiate plugin
        try:
            plugin = plugin_class()
            return plugin
        except TypeError as e:
            raise PluginLoadError(
                metadata.name,
                f"Failed to instantiate '{class_name}' (does it require arguments?): {e}",
            )
        except Exception as e:
            raise PluginLoadError(
                metadata.name, f"Error instantiating '{class_name}': {e}"
            )

    def _validate_plugin(self, plugin: Plugin, metadata: PluginMetadata) -> None:
        """
        Validate plugin extends correct base class.

        Args:
            plugin: Plugin instance
            metadata: PluginMetadata with expected type

        Raises:
            PluginValidationError: If plugin doesn't extend expected base class
        """
        # Check plugin extends Plugin
        if not isinstance(plugin, Plugin):
            raise PluginValidationError(
                metadata.name,
                [
                    f"Plugin class '{metadata.get_class_name()}' must extend Plugin base class"
                ],
            )

        # Check plugin extends correct type-specific base class
        expected_base = self.PLUGIN_TYPE_MAP.get(metadata.type)
        if expected_base and not isinstance(plugin, expected_base):
            raise PluginValidationError(
                metadata.name,
                [
                    f"Plugin type '{metadata.type}' must extend {expected_base.__name__}, "
                    f"but '{metadata.get_class_name()}' does not"
                ],
            )


__all__ = ["PluginLoader"]
