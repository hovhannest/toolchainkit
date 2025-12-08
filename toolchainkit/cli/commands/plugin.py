"""
Plugin management commands.

This module implements CLI commands for managing ToolchainKit plugins:
- list: Show all discovered and loaded plugins
- add: Add a plugin search path
- remove: Remove a plugin search path
"""

import logging
from pathlib import Path

from toolchainkit.plugins.manager import PluginManager
from toolchainkit.plugins.discovery import PluginDiscoverer
from toolchainkit.cli.utils import (
    print_error,
    safe_print,
)

logger = logging.getLogger(__name__)


def run_list(args) -> int:
    """
    List all discovered plugins.

    Args:
        args: Parsed command-line arguments with:
            - verbose: Show detailed information
            - loaded_only: Only show loaded plugins

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Create plugin manager
        project_root = Path(args.project_root) if args.project_root else None
        manager = PluginManager(project_root=project_root)

        if args.loaded_only:
            # Show only loaded plugins
            loaded_count = manager.discover_and_load_all()
            loaded_plugins = manager.get_loaded_plugins()

            if not loaded_plugins:
                safe_print("No plugins loaded.")
                return 0

            safe_print(f"\n{loaded_count} plugin(s) loaded:\n")
            for i, plugin_name in enumerate(loaded_plugins, 1):
                safe_print(f"  {i}. {plugin_name}")

        else:
            # Show all discovered plugins (loaded and unloaded)
            discoverer = PluginDiscoverer(project_root=project_root)
            all_plugins = discoverer.discover()

            if not all_plugins:
                safe_print("No plugins found in search paths.")
                safe_print("\nPlugin search paths:")
                for path in discoverer._get_plugin_directories():
                    safe_print(f"  - {path}")
                return 0

            # Try to load plugins to see which ones work
            if args.verbose:
                manager.discover_and_load_all()
                loaded_names = set(manager.get_loaded_plugins())

            safe_print(f"\n{len(all_plugins)} plugin(s) discovered:\n")

            for i, plugin_meta in enumerate(all_plugins, 1):
                status = ""
                if args.verbose:
                    status = (
                        " ✓ loaded"
                        if plugin_meta.name in loaded_names
                        else " ✗ not loaded"
                    )

                safe_print(f"  {i}. {plugin_meta.name} v{plugin_meta.version}{status}")

                if args.verbose:
                    safe_print(f"     Type: {plugin_meta.type}")
                    safe_print(f"     Path: {plugin_meta.plugin_dir}")
                    if plugin_meta.description:
                        safe_print(f"     Description: {plugin_meta.description}")
                    if plugin_meta.author:
                        safe_print(f"     Author: {plugin_meta.author}")
                    safe_print("")

            if not args.verbose:
                safe_print("\nUse --verbose for more details")

        return 0

    except Exception as e:
        logger.error(f"Failed to list plugins: {e}", exc_info=True)
        print_error("Failed to list plugins", str(e))
        return 1


def run_add(args) -> int:
    """
    Add a plugin search path.

    This stores the path in a user configuration file so plugins in this
    location will be discovered in future runs.

    Args:
        args: Parsed command-line arguments with:
            - path: Path to plugin directory

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        plugin_path = Path(args.path).resolve()

        # Validate path exists
        if not plugin_path.exists():
            print_error(
                "Path does not exist",
                f"The specified path does not exist: {plugin_path}",
            )
            return 1

        if not plugin_path.is_dir():
            print_error(
                "Not a directory",
                f"The specified path is not a directory: {plugin_path}",
            )
            return 1

        # Check if it looks like a plugin directory
        # It should either:
        # 1. Contain plugin.yaml (single plugin)
        # 2. Contain subdirectories with plugin.yaml (multiple plugins)
        has_plugin_yaml = (plugin_path / "plugin.yaml").exists()
        has_plugin_subdirs = any(
            (item / "plugin.yaml").exists()
            for item in plugin_path.iterdir()
            if item.is_dir()
        )

        if not has_plugin_yaml and not has_plugin_subdirs:
            safe_print(
                f"⚠️  Warning: {plugin_path} does not appear to contain any plugins.\n"
                f"   Expected 'plugin.yaml' files."
            )
            if not args.force:
                safe_print("   Use --force to add anyway.")
                return 1

        # Load existing config
        config_file = _get_plugin_config_file()
        config = _load_plugin_config(config_file)

        # Add path if not already present
        path_str = str(plugin_path)
        if path_str in config.get("search_paths", []):
            safe_print(f"Plugin path already registered: {plugin_path}")
            return 0

        if "search_paths" not in config:
            config["search_paths"] = []

        config["search_paths"].append(path_str)

        # Save config
        _save_plugin_config(config_file, config)

        safe_print(f"✓ Added plugin search path: {plugin_path}")
        safe_print("\nPlugins in this location will now be discovered automatically.")
        safe_print("Run 'toolchainkit plugin list' to see available plugins.")

        return 0

    except Exception as e:
        logger.error(f"Failed to add plugin path: {e}", exc_info=True)
        print_error("Failed to add plugin path", str(e))
        return 1


def run_remove(args) -> int:
    """
    Remove a plugin search path.

    Args:
        args: Parsed command-line arguments with:
            - name_or_path: Plugin name or path to remove

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load existing config
        config_file = _get_plugin_config_file()
        config = _load_plugin_config(config_file)

        if "search_paths" not in config or not config["search_paths"]:
            safe_print("No plugin search paths configured.")
            return 0

        # Try to match by path first
        name_or_path = args.name_or_path

        # Try exact path match
        path_to_remove = None
        try:
            resolved_path = str(Path(name_or_path).resolve())
            if resolved_path in config["search_paths"]:
                path_to_remove = resolved_path
        except Exception:
            pass

        # If not found by path, try by plugin name
        if not path_to_remove:
            # Discover plugins and find one with matching name
            discoverer = PluginDiscoverer()
            plugins = discoverer.discover()

            for plugin_meta in plugins:
                if plugin_meta.name == name_or_path:
                    # Found plugin, get its parent directory
                    plugin_dir = plugin_meta.plugin_dir.parent
                    plugin_dir_str = str(plugin_dir)

                    # Check if this directory is in search paths
                    if plugin_dir_str in config["search_paths"]:
                        path_to_remove = plugin_dir_str
                        break

        if not path_to_remove:
            print_error(
                "Not found",
                f"Plugin or path '{name_or_path}' not found in configured search paths.\n"
                f"Use 'toolchainkit plugin list-paths' to see configured paths.",
            )
            return 1

        # Remove from config
        config["search_paths"].remove(path_to_remove)
        _save_plugin_config(config_file, config)

        safe_print(f"✓ Removed plugin search path: {path_to_remove}")

        return 0

    except Exception as e:
        logger.error(f"Failed to remove plugin: {e}", exc_info=True)
        print_error("Failed to remove plugin", str(e))
        return 1


def run_list_paths(args) -> int:
    """
    List all configured plugin search paths.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load config
        config_file = _get_plugin_config_file()
        config = _load_plugin_config(config_file)

        # Get all search paths (config + default)
        project_root = Path(args.project_root) if args.project_root else None
        discoverer = PluginDiscoverer(project_root=project_root)
        all_paths = discoverer._get_plugin_directories()

        configured_paths = set(config.get("search_paths", []))

        safe_print("\nPlugin search paths:\n")

        for path in all_paths:
            path_str = str(path)
            source = ""

            if path_str in configured_paths:
                source = " (configured)"
            elif "TOOLCHAINKIT_PLUGIN_PATH" in str(path):
                source = " (environment)"
            elif ".toolchainkit/plugins" in path_str:
                if project_root and str(project_root) in path_str:
                    source = " (project)"
                else:
                    source = " (global)"

            # Use ASCII characters for better cross-platform compatibility
            exists = " [OK]" if path.exists() else " [--]"
            safe_print(f"  {exists} {path}{source}")

        safe_print(f"\nConfiguration file: {config_file}")

        return 0

    except Exception as e:
        logger.error(f"Failed to list plugin paths: {e}", exc_info=True)
        print_error("Failed to list plugin paths", str(e))
        return 1


def _get_plugin_config_file() -> Path:
    """Get path to plugin configuration file."""
    config_dir = Path.home() / ".toolchainkit"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "plugins.yaml"


def _load_plugin_config(config_file: Path) -> dict:
    """Load plugin configuration from YAML file."""
    if not config_file.exists():
        return {}

    import yaml

    with open(config_file, "r") as f:
        return yaml.safe_load(f) or {}


def _save_plugin_config(config_file: Path, config: dict) -> None:
    """Save plugin configuration to YAML file."""
    import yaml

    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
