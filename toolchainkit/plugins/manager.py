"""
Plugin manager for orchestrating plugin discovery, loading, and initialization.

This module provides the PluginManager class which coordinates the entire plugin
lifecycle from discovery through initialization.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Dict, List, Tuple

from toolchainkit.plugins.context import PluginContext
from toolchainkit.plugins.discovery import PluginDiscoverer
from toolchainkit.plugins.loader import PluginLoader
from toolchainkit.plugins.registry import get_global_registry

if TYPE_CHECKING:
    from toolchainkit.plugins.registry import PluginRegistry

import logging

logger = logging.getLogger(__name__)


class PluginManager:
    """
    High-level manager for plugin system.

    Orchestrates plugin discovery, loading, and initialization. Provides a simple
    API for working with the plugin system without needing to understand the
    individual components.

    Example:
        ```python
        from toolchainkit.plugins import PluginManager

        # Create manager
        manager = PluginManager()

        # Discover and load all plugins
        loaded = manager.discover_and_load_all()
        print(f"Loaded {loaded} plugins")

        # Access registered compilers
        registry = manager.registry
        if registry.has_compiler('zig'):
            zig = registry.get_compiler('zig')
        ```
    """

    def __init__(
        self,
        registry: Optional["PluginRegistry"] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        """
        Initialize plugin manager.

        Args:
            registry: Optional plugin registry (uses global registry if None)
            project_root: Optional project root directory for project-local plugins
                         (uses default paths if None)
        """
        self.registry = registry or get_global_registry()
        self.discoverer = PluginDiscoverer(project_root=project_root)
        self.loader = PluginLoader()
        self._loaded_plugins: List[Tuple[str, Any]] = []

    def discover_and_load_all(
        self,
        cache_base_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Discover and load all available plugins.

        This method:
        1. Discovers all plugin.yaml files in search paths
        2. Loads each plugin's Python module
        3. Creates PluginContext for each plugin
        4. Calls plugin.initialize(context)
        5. Handles errors gracefully (continues loading other plugins)

        Args:
            cache_base_dir: Base directory for plugin caches
                           (defaults to ~/.toolchainkit/plugins/cache)
            config: Global configuration dict to pass to plugins
                   (defaults to empty dict)

        Returns:
            Number of plugins successfully loaded and initialized

        Example:
            ```python
            manager = PluginManager()
            loaded_count = manager.discover_and_load_all()
            print(f"Successfully loaded {loaded_count} plugins")
            ```
        """
        if cache_base_dir is None:
            cache_base_dir = Path.home() / ".toolchainkit" / "plugins" / "cache"

        if config is None:
            config = {}

        # Discover all plugins
        metadata_list = self.discoverer.discover()
        logger.info(f"Discovered {len(metadata_list)} plugins")

        loaded_count = 0
        for metadata in metadata_list:
            try:
                # Load plugin module and instantiate plugin class
                plugin = self.loader.load(metadata)
                logger.debug(f"Loaded plugin: {metadata.name}")

                # Create plugin-specific cache directory
                plugin_cache_dir = cache_base_dir / metadata.name
                plugin_cache_dir.mkdir(parents=True, exist_ok=True)

                # Create context for plugin
                context = PluginContext(
                    registry=self.registry,
                    cache_dir=plugin_cache_dir,
                    config=config,
                )

                # Initialize plugin
                plugin.initialize(context)
                logger.info(f"Initialized plugin: {metadata.name} v{metadata.version}")

                # Store reference to loaded plugin
                self._loaded_plugins.append((metadata.name, plugin))
                loaded_count += 1

            except Exception as e:
                # Log error but continue with other plugins
                logger.error(
                    f"Failed to load plugin '{metadata.name}': {e}",
                    exc_info=True,
                )
                continue

        logger.info(f"Successfully loaded {loaded_count}/{len(metadata_list)} plugins")
        return loaded_count

    def discover_and_load_one(
        self,
        plugin_name: str,
        cache_base_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Discover and load a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to load
            cache_base_dir: Base directory for plugin caches
            config: Global configuration dict to pass to plugin

        Returns:
            True if plugin was loaded successfully, False otherwise

        Example:
            ```python
            manager = PluginManager()
            if manager.discover_and_load_one('zig-compiler'):
                print("Zig compiler plugin loaded")
            ```
        """
        if cache_base_dir is None:
            cache_base_dir = Path.home() / ".toolchainkit" / "plugins" / "cache"

        if config is None:
            config = {}

        # Discover all plugins and find the one we want
        metadata_list = self.discoverer.discover()

        for metadata in metadata_list:
            if metadata.name == plugin_name:
                try:
                    plugin = self.loader.load(metadata)

                    plugin_cache_dir = cache_base_dir / metadata.name
                    plugin_cache_dir.mkdir(parents=True, exist_ok=True)

                    context = PluginContext(
                        registry=self.registry,
                        cache_dir=plugin_cache_dir,
                        config=config,
                    )

                    plugin.initialize(context)
                    logger.info(
                        f"Initialized plugin: {metadata.name} v{metadata.version}"
                    )

                    self._loaded_plugins.append((metadata.name, plugin))
                    return True

                except Exception as e:
                    logger.error(
                        f"Failed to load plugin '{metadata.name}': {e}",
                        exc_info=True,
                    )
                    return False

        logger.warning(f"Plugin '{plugin_name}' not found")
        return False

    def cleanup_all(self) -> None:
        """
        Call cleanup() on all loaded plugins.

        Should be called on application shutdown to give plugins a chance
        to clean up resources.

        Example:
            ```python
            manager = PluginManager()
            manager.discover_and_load_all()

            # ... use plugins ...

            # On shutdown
            manager.cleanup_all()
            ```
        """
        for plugin_name, plugin in self._loaded_plugins:
            try:
                plugin.cleanup()
                logger.debug(f"Cleaned up plugin: {plugin_name}")
            except Exception as e:
                logger.error(
                    f"Error cleaning up plugin '{plugin_name}': {e}",
                    exc_info=True,
                )

        self._loaded_plugins.clear()

    def get_loaded_plugins(self) -> List[str]:
        """
        Get list of loaded plugin names.

        Returns:
            List of plugin names that have been successfully loaded

        Example:
            ```python
            manager = PluginManager()
            manager.discover_and_load_all()
            plugins = manager.get_loaded_plugins()
            print(f"Loaded plugins: {', '.join(plugins)}")
            ```
        """
        return [name for name, _ in self._loaded_plugins]
