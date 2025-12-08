"""
Plugin discovery system for finding available plugins.

This module provides functionality to scan plugin directories and discover
available plugins without loading their code.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from toolchainkit.plugins.metadata import PluginMetadata, PluginMetadataParser
from toolchainkit.plugins import PluginValidationError


class PluginDiscoverer:
    """
    Discover plugins by scanning plugin directories.

    The discoverer scans multiple locations for plugins (in priority order):
    1. Project-local: <project>/.toolchainkit/plugins/
    2. User-global: ~/.toolchainkit/plugins/
    3. Environment: TOOLCHAINKIT_PLUGIN_PATH

    Higher priority plugins override lower priority ones with the same name.
    """

    def __init__(
        self, project_root: Optional[Path] = None, project_config: Optional[dict] = None
    ):
        """
        Initialize plugin discoverer.

        Args:
            project_root: Optional project root for project-local plugins.
                         If None, only global and env plugins discovered.
            project_config: Optional project configuration dict (from toolchainkit.yaml)
        """
        self.project_root = project_root
        self.project_config = project_config or {}
        self.parser = PluginMetadataParser()

    def discover(self) -> List[PluginMetadata]:
        """
        Discover all plugins from all search locations.

        Scans plugin directories and returns discovered plugins.
        Higher priority plugins override lower priority ones.

        Returns:
            List of PluginMetadata for discovered plugins.
            Deduplication by plugin name (project > global > env).

        Example:
            discoverer = PluginDiscoverer()
            plugins = discoverer.discover()
            for plugin in plugins:
                print(f"Found {plugin.name} v{plugin.version}")
        """
        plugins_by_name: Dict[str, PluginMetadata] = {}

        # Scan in reverse priority order (so higher priority overwrites)
        for directory in reversed(self._get_plugin_directories()):
            discovered = self.discover_in_directory(directory)
            for plugin in discovered:
                plugins_by_name[plugin.name] = plugin

        return list(plugins_by_name.values())

    def discover_in_directory(self, directory: Path) -> List[PluginMetadata]:
        """
        Discover plugins in a specific directory.

        Scans directory for plugin subdirectories containing plugin.yaml files.
        Each plugin should be in its own subdirectory:
        <directory>/<plugin_name>/plugin.yaml

        Args:
            directory: Path to search for plugins

        Returns:
            List of PluginMetadata for plugins found in this directory

        Example:
            discoverer = PluginDiscoverer()
            plugins = discoverer.discover_in_directory(Path("~/.toolchainkit/plugins"))
        """
        if not directory.exists():
            return []

        if not directory.is_dir():
            return []

        plugins = []

        try:
            # Each plugin is in its own subdirectory
            for item in directory.iterdir():
                if not item.is_dir():
                    continue

                plugin_yaml = item / "plugin.yaml"
                if not plugin_yaml.exists():
                    continue

                try:
                    metadata = self.parser.parse_file(plugin_yaml)
                    plugins.append(metadata)
                except PluginValidationError as e:
                    # Log warning but continue discovery
                    import warnings

                    warnings.warn(
                        f"Skipping invalid plugin at {plugin_yaml}: {e}",
                        RuntimeWarning,
                    )
                except Exception as e:
                    # Log warning for any other errors
                    import warnings

                    warnings.warn(
                        f"Error loading plugin at {plugin_yaml}: {e}", RuntimeWarning
                    )

        except PermissionError:
            # Can't read directory - skip silently
            pass
        except Exception:
            # Other errors - skip silently
            pass

        return plugins

    def _get_plugin_directories(self) -> List[Path]:
        """
        Get list of plugin directories to search (in priority order).

        Priority (high to low):
        1. Project-local: <project>/.toolchainkit/plugins/
        2. Project config paths: from plugins.paths in toolchainkit.yaml
        3. User-global: ~/.toolchainkit/plugins/
        4. User config paths: from ~/.toolchainkit/plugins.yaml
        5. Environment: TOOLCHAINKIT_PLUGIN_PATH

        Returns:
            List of Path objects for plugin directories
        """
        directories = []

        # 1. Project-local plugins (highest priority)
        if self.project_root:
            project_plugins = self.project_root / ".toolchainkit" / "plugins"
            directories.append(project_plugins)

        # 2. Project-configured plugin paths (from toolchainkit.yaml)
        if self.project_config and self.project_root:
            project_plugin_paths = self.project_config.get("plugins", {}).get(
                "paths", []
            )
            for plugin_path in project_plugin_paths:
                abs_path = Path(plugin_path)
                if not abs_path.is_absolute():
                    abs_path = self.project_root / plugin_path
                abs_path = abs_path.resolve()
                directories.append(abs_path)

        # 3. User-global plugins
        home = Path.home()
        global_plugins = home / ".toolchainkit" / "plugins"
        directories.append(global_plugins)

        # 4. User-configured search paths (from ~/.toolchainkit/plugins.yaml)
        configured_paths = self._load_configured_paths()
        directories.extend(configured_paths)

        # 5. Environment variable paths (lowest priority)
        env_paths = os.environ.get("TOOLCHAINKIT_PLUGIN_PATH", "")
        if env_paths:
            # Handle both Windows (;) and Unix (:) path separators
            separator = ";" if os.name == "nt" else ":"
            for path_str in env_paths.split(separator):
                if path_str.strip():
                    directories.append(Path(path_str.strip()))

        return directories

    def _load_configured_paths(self) -> List[Path]:
        """
        Load configured plugin search paths from user config file.

        Returns:
            List of configured plugin directory paths
        """
        try:
            config_file = Path.home() / ".toolchainkit" / "plugins.yaml"
            if not config_file.exists():
                return []

            import yaml

            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}

            search_paths = config.get("search_paths", [])
            return [Path(p) for p in search_paths if p]

        except Exception:
            # Silently ignore config loading errors
            return []


__all__ = ["PluginDiscoverer"]
