"""
ToolchainKit CLI argument parser.

This module implements the command-line interface for ToolchainKit using argparse.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Get version from package
try:
    from importlib.metadata import version

    __version__ = version("toolchainkit")
except Exception:
    __version__ = "0.1.0"

# Ensure package managers and plugins are registered
try:
    import toolchainkit.packages  # noqa: F401 - Import registers plugins in registry
except ImportError:
    pass

logger = logging.getLogger(__name__)


class CLI:
    """ToolchainKit command-line interface."""

    def __init__(self):
        """Initialize CLI with argument parser."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser with all subcommands.

        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            prog="tkgen",
            description="ToolchainKit - Hermetic C++ build system",
            epilog='Use "tkgen COMMAND --help" for command-specific help',
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Global options
        parser.add_argument(
            "--version", action="version", version=f"ToolchainKit {__version__}"
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose output"
        )
        parser.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="Enable minimal output (errors only)",
        )
        parser.add_argument(
            "--config",
            type=Path,
            metavar="PATH",
            help="Path to configuration file (default: ./toolchainkit.yaml)",
        )
        parser.add_argument(
            "--project-root",
            type=Path,
            metavar="PATH",
            default=Path.cwd(),
            help="Project root directory (default: current directory)",
        )

        # Subcommands
        subparsers = parser.add_subparsers(
            dest="command", help="Available commands", metavar="COMMAND"
        )

        self._add_init_command(subparsers)
        self._add_bootstrap_command(subparsers)
        self._add_configure_command(subparsers)
        self._add_cleanup_command(subparsers)
        self._add_upgrade_command(subparsers)
        self._add_verify_command(subparsers)
        self._add_doctor_command(subparsers)
        self._add_plugin_command(subparsers)
        self._add_vscode_command(subparsers)

        return parser

    def _add_init_command(self, subparsers):
        """Add 'init' subcommand."""
        parser = subparsers.add_parser(
            "init",
            help="Initialize ToolchainKit in existing project",
            description="Initialize ToolchainKit in an existing CMake project",
        )
        parser.add_argument(
            "--auto-detect",
            action="store_true",
            help="Auto-detect package manager and configuration",
        )
        parser.add_argument(
            "--toolchain",
            metavar="NAME",
            help="Initial toolchain (e.g., llvm-18, gcc-13, msvc-latest)",
        )
        parser.add_argument(
            "--minimal", action="store_true", help="Create minimal configuration"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reinitialization if already initialized",
        )

    def _add_bootstrap_command(self, subparsers):
        """Add 'bootstrap' subcommand."""
        parser = subparsers.add_parser(
            "bootstrap",
            help="Generate bootstrap scripts",
            description="Generate or regenerate platform-specific bootstrap scripts",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing bootstrap scripts",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview scripts without creating files",
        )
        parser.add_argument(
            "--platform",
            choices=["unix", "windows", "powershell", "all"],
            default="all",
            metavar="PLATFORM",
            help="Platform to generate scripts for (unix|windows|powershell|all) [default: all]",
        )
        parser.add_argument(
            "--toolchain",
            metavar="NAME",
            help="Override toolchain from config",
        )
        parser.add_argument(
            "--build-type",
            choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
            metavar="TYPE",
            help="Override build type from config",
        )
        # Phase 2: Advanced configuration options
        parser.add_argument(
            "--cmake-args",
            action="append",
            metavar="ARG",
            help="Additional CMake arguments (can be used multiple times)",
        )
        parser.add_argument(
            "--env",
            action="append",
            type=lambda kv: kv.split("=", 1),
            metavar="KEY=VALUE",
            help="Environment variables to set (can be used multiple times)",
        )
        parser.add_argument(
            "--pre-configure-hook",
            metavar="SCRIPT",
            help="Script to run before CMake configure",
        )
        parser.add_argument(
            "--post-configure-hook",
            metavar="SCRIPT",
            help="Script to run after CMake configure",
        )
        # Phase 3: Script validation
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate generated scripts using shellcheck/bash (requires shellcheck installed)",
        )

    def _add_configure_command(self, subparsers):
        """Add 'configure' subcommand."""
        parser = subparsers.add_parser(
            "configure",
            help="Configure toolchain and run CMake",
            description="Configure toolchain and run CMake configuration",
        )
        parser.add_argument(
            "--toolchain",
            required=True,
            metavar="NAME",
            help="Toolchain to use (e.g., llvm-18, gcc-13, msvc-latest)",
        )
        parser.add_argument(
            "--stdlib",
            choices=["libc++", "libstdc++", "msvc"],
            metavar="STD",
            help="C++ standard library",
        )
        parser.add_argument(
            "--build-type",
            default="Release",
            choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
            metavar="TYPE",
            help="CMake build type (default: Release)",
        )
        parser.add_argument(
            "--build-dir",
            default="build",
            metavar="DIR",
            help="CMake build directory (default: build)",
        )
        parser.add_argument(
            "--cache",
            choices=["sccache", "ccache", "none"],
            metavar="TOOL",
            help="Enable build caching",
        )
        parser.add_argument(
            "--target",
            metavar="TARGET",
            help="Cross-compilation target (e.g., android-arm64, ios-arm64)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean build directory before configuring",
        )
        parser.add_argument(
            "--bootstrap",
            action="store_true",
            help="Run bootstrap mode (install tools, dependencies, and run CMake)",
        )
        parser.add_argument(
            "--cmake-args",
            action="append",
            metavar="ARG",
            help="Additional CMake arguments (can be used multiple times)",
        )
        parser.add_argument(
            "--env",
            action="append",
            type=lambda kv: kv.split("=", 1),
            metavar="KEY=VALUE",
            help="Environment variables to set (can be used multiple times)",
        )

    def _add_cleanup_command(self, subparsers):
        """Add 'cleanup' subcommand."""
        parser = subparsers.add_parser(
            "cleanup",
            help="Clean up unused toolchains",
            description="Clean up unused toolchains from shared cache",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be removed without removing",
        )
        parser.add_argument(
            "--unused",
            action="store_true",
            help="Remove toolchains with no project references",
        )
        parser.add_argument(
            "--older-than",
            type=int,
            metavar="DAYS",
            help="Remove toolchains unused for N days",
        )
        parser.add_argument(
            "--toolchain", metavar="NAME", help="Remove specific toolchain"
        )

    def _add_upgrade_command(self, subparsers):
        """Add 'upgrade' subcommand."""
        parser = subparsers.add_parser(
            "upgrade",
            help="Upgrade toolchains",
            description="Upgrade toolchains to latest versions",
        )
        parser.add_argument(
            "--toolchain", metavar="NAME", help="Upgrade specific toolchain"
        )
        parser.add_argument("--all", action="store_true", help="Upgrade all toolchains")

    def _add_verify_command(self, subparsers):
        """Add 'verify' subcommand."""
        parser = subparsers.add_parser(
            "verify",
            help="Verify toolchain integrity",
            description="Verify toolchain integrity and functionality",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Full verification including checksums and compile tests",
        )

    def _add_doctor_command(self, subparsers):
        """Add 'doctor' subcommand."""
        parser = subparsers.add_parser(
            "doctor",
            help="Diagnose environment and configuration",
            description="Diagnose development environment and suggest fixes",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to automatically fix detected issues",
        )

    def _add_plugin_command(self, subparsers):
        """Add 'plugin' subcommand with sub-subcommands."""
        parser = subparsers.add_parser(
            "plugin",
            help="Manage plugins",
            description="Manage ToolchainKit plugins (list, add, remove)",
        )

        plugin_subparsers = parser.add_subparsers(
            dest="plugin_command", help="Plugin management commands", metavar="COMMAND"
        )

        # plugin list
        list_parser = plugin_subparsers.add_parser(
            "list",
            help="List discovered plugins",
            description="Show all discovered plugins and their status",
        )
        list_parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Show detailed plugin information",
        )
        list_parser.add_argument(
            "--loaded-only", action="store_true", help="Only show loaded plugins"
        )

        # plugin add
        add_parser = plugin_subparsers.add_parser(
            "add",
            help="Add plugin search path",
            description="Add a directory to plugin search paths",
        )
        add_parser.add_argument("path", type=str, help="Path to plugin directory")
        add_parser.add_argument(
            "--force", action="store_true", help="Add path even if no plugins found"
        )

        # plugin remove
        remove_parser = plugin_subparsers.add_parser(
            "remove",
            help="Remove plugin search path",
            description="Remove a plugin or search path from configuration",
        )
        remove_parser.add_argument(
            "name_or_path", type=str, help="Plugin name or path to remove"
        )

        # plugin list-paths
        plugin_subparsers.add_parser(
            "list-paths",
            help="List plugin search paths",
            description="Show all configured plugin search paths",
        )

    def _add_vscode_command(self, subparsers):
        """Add 'vscode' subcommand."""
        parser = subparsers.add_parser(
            "vscode",
            help="Configure VS Code workspace",
            description="Generate VS Code configuration (settings, launch, tasks)",
        )
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite existing configuration",
        )
        parser.add_argument(
            "--build-dir",
            metavar="DIR",
            help="Build directory to use/query",
        )
        parser.add_argument(
            "--build-type",
            default="Debug",
            choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
            metavar="TYPE",
            help="Build type for launch config (default: Debug)",
        )

    def parse_args(self, args: Optional[List[str]] = None):
        """
        Parse command-line arguments.

        Args:
            args: Arguments to parse (uses sys.argv if None)

        Returns:
            Parsed arguments namespace
        """
        return self.parser.parse_args(args)

    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run CLI with given arguments.

        Args:
            args: Arguments to parse (uses sys.argv if None)

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parsed_args = self.parse_args(args)

        # Configure logging
        self._configure_logging(parsed_args)

        # Check if command specified
        if not parsed_args.command:
            self.parser.print_help()
            return 1

        # Load plugins if config file is provided
        self._load_plugins_from_config(parsed_args)

        # Dispatch to command handler
        try:
            return self._dispatch_command(parsed_args)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            logger.error(f"Error: {e}")
            if parsed_args.verbose:
                import traceback

                traceback.print_exc()
            return 1

    def _load_plugins_from_config(self, args):
        """
        Load plugins from configuration file if available.

        Args:
            args: Parsed arguments with config and project_root
        """
        try:
            # Determine config file path
            project_root = (
                Path(args.project_root).resolve()
                if hasattr(args, "project_root")
                else Path.cwd()
            )
            config_file = None

            if hasattr(args, "config") and args.config:
                config_file = Path(args.config)
            else:
                # Look for default config file
                default_config = project_root / "toolchainkit.yaml"
                if default_config.exists():
                    config_file = default_config

            if not config_file or not config_file.exists():
                logger.debug("No config file found, skipping plugin loading")
                return

            # Load configuration
            from toolchainkit.cli.utils import load_yaml_config

            config = load_yaml_config(config_file, required=False)

            if not config:
                return

            # Check for plugin paths in config
            if not ("plugins" in config and "paths" in config["plugins"]):
                logger.debug("No plugin paths configured")
                return

            # Initialize plugin manager with project root and config
            from toolchainkit.plugins.manager import PluginManager

            # Create manager with project root and config
            # The PluginDiscoverer will automatically use the plugin paths from config
            manager = PluginManager(project_root=project_root)
            manager.discoverer.project_config = config

            # Discover and load all plugins
            loaded_count = manager.discover_and_load_all()
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} plugin(s)")

        except Exception as e:
            # Don't fail the entire CLI if plugin loading fails
            logger.warning(f"Failed to load plugins: {e}")
            if hasattr(args, "verbose") and args.verbose:
                import traceback

                traceback.print_exc()

    def _configure_logging(self, args):
        """
        Configure logging based on verbose/quiet flags.

        Args:
            args: Parsed arguments with verbose/quiet flags
        """
        if args.verbose:
            level = logging.DEBUG
            format_str = "%(levelname)s [%(name)s] %(message)s"
        elif args.quiet:
            level = logging.ERROR
            format_str = "%(levelname)s: %(message)s"
        else:
            level = logging.INFO
            format_str = "%(message)s"

        logging.basicConfig(
            level=level,
            format=format_str,
            force=True,  # Reconfigure if already configured
        )

    def _dispatch_command(self, args) -> int:
        """
        Dispatch to appropriate command handler.

        Args:
            args: Parsed arguments with command field

        Returns:
            Exit code from command handler
        """
        # Special handling for plugin command (has sub-commands)
        if args.command == "plugin":
            return self._dispatch_plugin_command(args)

        # Command module mapping
        command_map = {
            "init": "toolchainkit.cli.commands.init",
            "bootstrap": "toolchainkit.cli.commands.bootstrap",
            "configure": "toolchainkit.cli.commands.configure",
            "cleanup": "toolchainkit.cli.commands.cleanup",
            "upgrade": "toolchainkit.cli.commands.upgrade",
            "verify": "toolchainkit.cli.commands.verify",
            "doctor": "toolchainkit.cli.commands.doctor",
            "vscode": "toolchainkit.cli.commands.vscode",
        }

        module_name = command_map.get(args.command)
        if not module_name:
            logger.error(f"Unknown command: {args.command}")
            return 1

        try:
            # Dynamic import of command module
            import importlib

            module = importlib.import_module(module_name)

            # Call run() function in module
            if not hasattr(module, "run"):
                logger.error(f"Command module {module_name} has no run() function")
                return 1

            return module.run(args)

        except ImportError as e:
            logger.error(f"Failed to load command module: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1

    def _dispatch_plugin_command(self, args) -> int:
        """
        Dispatch plugin sub-commands.

        Args:
            args: Parsed arguments with plugin_command field

        Returns:
            Exit code from command handler
        """
        if not hasattr(args, "plugin_command") or not args.plugin_command:
            logger.error("No plugin sub-command specified")
            self.parser.parse_args(["plugin", "--help"])
            return 1

        try:
            from toolchainkit.cli.commands import plugin

            # Map sub-commands to functions
            plugin_command_map = {
                "list": plugin.run_list,
                "add": plugin.run_add,
                "remove": plugin.run_remove,
                "list-paths": plugin.run_list_paths,
            }

            handler = plugin_command_map.get(args.plugin_command)
            if not handler:
                logger.error(f"Unknown plugin command: {args.plugin_command}")
                return 1

            return handler(args)

        except Exception as e:
            logger.error(f"Failed to execute plugin command: {e}")
            if hasattr(args, "verbose") and args.verbose:
                import traceback

                traceback.print_exc()
            return 1


def main():
    """Main entry point for CLI."""
    # Initialize core framework (register standard strategies, package managers)
    from toolchainkit.core.initialization import initialize_core

    initialize_core()

    cli = CLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
