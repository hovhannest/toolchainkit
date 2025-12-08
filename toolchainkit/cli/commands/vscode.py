"""
VS Code configuration command.

Configures VS Code workspace for ToolchainKit.
"""

import logging
import sys
from pathlib import Path

from toolchainkit.cli.utils import (
    check_initialized,
    load_yaml_config,
    print_error,
    print_warning,
)
from toolchainkit.core.state import StateManager
from toolchainkit.ide.vscode import VSCodeIntegrator

logger = logging.getLogger(__name__)


def run(args) -> int:
    """
    Run the vscode command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Configuring VS Code workspace")
    project_root = Path(args.project_root).resolve()

    # Check if initialized
    config_file = project_root / "toolchainkit.yaml"
    if args.config:
        config_file = Path(args.config).resolve()

    if not check_initialized(project_root, config_file):
        logger.error("Project not initialized")
        print_error(
            "Project not initialized",
            "Configuration file not found. Run 'tkgen init' first.",
        )
        return 1

    # Load configuration
    try:
        load_yaml_config(config_file, required=True)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        print_error("Failed to load configuration", str(e))
        return 1

    # Load project state
    state_manager = StateManager(project_root)
    state = state_manager.load()

    # Determine paths
    toolchain_file = project_root / ".toolchainkit" / "cmake" / "toolchain.cmake"

    if not toolchain_file.exists():
        msg = f"Toolchain file not found: {toolchain_file}"
        if not args.force:
            logger.warning(msg)
            print_warning(msg)
            print(
                "  VS Code configuration may be incomplete. Run 'tkgen configure' first."
            )

    # Determine compiler path
    compiler_path = Path("clang")  # Default fallback
    toolchain_path = None  # To be determined from registry

    if state.active_toolchain:
        try:
            from toolchainkit.core.cache_registry import ToolchainCacheRegistry
            from toolchainkit.core.directory import get_global_cache_dir

            cache_dir = get_global_cache_dir()
            registry_file = cache_dir / "registry.json"
            registry = ToolchainCacheRegistry(registry_file)

            info = registry.get_toolchain_info(state.active_toolchain)
            if info and "path" in info:
                toolchain_path = Path(info["path"])
                # Heuristic to find compiler
                # TODO: Improve this based on toolchain type/metadata
                possible_compilers = [
                    "bin/clang",
                    "bin/clang++",
                    "bin/gcc",
                    "bin/g++",
                    "bin/cl.exe",
                ]

                # Check for windows extension if on windows
                is_windows = sys.platform == "win32"

                for comp in possible_compilers:
                    if is_windows and not comp.endswith(".exe"):
                        p = toolchain_path / f"{comp}.exe"
                    else:
                        p = toolchain_path / comp

                    if p.exists():
                        compiler_path = p
                        break

        except Exception as e:
            logger.warning(f"Failed to lookup toolchain info: {e}")

    # Detect Clang tools matching the compiler
    clang_tidy_path = None
    clang_format_path = None

    if toolchain_path and (
        "clang" in compiler_path.name.lower() or "llvm" in toolchain_path.name.lower()
    ):
        bin_dir = toolchain_path / "bin"
        is_windows = sys.platform == "win32"

        # Check for .clang-tidy in project root
        if (project_root / ".clang-tidy").exists():
            tidy_exe = bin_dir / ("clang-tidy.exe" if is_windows else "clang-tidy")
            if tidy_exe.exists():
                clang_tidy_path = tidy_exe
                logger.info(f"Found clang-tidy: {tidy_exe}")

        # Check for .clang-format in project root
        if (project_root / ".clang-format").exists():
            format_exe = bin_dir / (
                "clang-format.exe" if is_windows else "clang-format"
            )
            if format_exe.exists():
                clang_format_path = format_exe
                logger.info(f"Found clang-format: {format_exe}")

    # Build directory
    build_dir = args.build_dir or state.build_directory or "build"
    build_type = args.build_type or "Debug"

    # Initialize integrator
    integrator = VSCodeIntegrator(project_root)

    # Check for existing config
    if (integrator.vscode_dir / "settings.json").exists() and not args.force:
        print("VS Code configuration already exists.")
        print("  Use --force to overwrite.")
        return 0

    try:
        print("Generating VS Code configuration...")

        # Configure workspace
        integrator.configure_workspace(
            toolchain_file=toolchain_file,
            compiler_path=compiler_path,
            build_dir=build_dir,
            build_type=build_type,
            generator="Ninja",  # Default for ToolchainKit
            debugger_path=None,  # Can be improved to detect lldb
            clang_tidy_path=clang_tidy_path,
            clang_format_path=clang_format_path,
        )

        print("  ✓ .vscode/settings.json")
        print("  ✓ .vscode/extensions.json")
        print("  ✓ .vscode/tasks.json")
        if (integrator.vscode_dir / "launch.json").exists():
            print("  ✓ .vscode/launch.json")
        else:
            print("  ⚠ .vscode/launch.json (skipped - run 'cmake' to generate targets)")

        print()
        print("VS Code configured successfully!")

    except Exception as e:
        logger.error(f"Failed to configure VS Code: {e}")
        print_error("Failed to configure VS Code", str(e))
        return 1

    return 0
