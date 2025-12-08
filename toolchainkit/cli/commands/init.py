"""
Init command implementation.

Initializes ToolchainKit in an existing CMake project.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import yaml

from toolchainkit.cli.utils import (
    check_initialized,
    format_success_message,
    print_error,
    print_warning,
)

logger = logging.getLogger(__name__)


def run(args) -> int:
    """
    Run the init command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Initializing ToolchainKit")
    logger.debug(f"Arguments: {args}")

    # 1. Validation
    project_root = Path(args.project_root).resolve()

    if not (project_root / "CMakeLists.txt").exists():
        logger.error("No CMakeLists.txt found in project root")
        print_error(
            "No CMakeLists.txt found in project root",
            f"Project root: {project_root}\n  ToolchainKit requires an existing CMake project",
        )
        return 1

    config_file = (
        args.config.resolve() if args.config else (project_root / "toolchainkit.yaml")
    )

    if check_initialized(project_root, config_file) and not args.force:
        logger.error("Project already initialized")
        print_error(
            "Project already initialized",
            f"Configuration file exists: {config_file}\n  Use --force to reinitialize",
        )
        return 1

    # 2. Platform detection
    logger.debug("Detecting platform")
    from toolchainkit.core.platform import detect_platform

    platform_info = detect_platform()
    logger.info(f"Platform: {platform_info.os} {platform_info.arch}")

    # 3. Package manager detection (if --auto-detect)
    package_manager = None
    if args.auto_detect:
        logger.debug("Auto-detecting package manager")
        package_manager = _detect_package_manager(project_root)
        if package_manager:
            logger.info(f"Detected package manager: {package_manager}")
        else:
            logger.info("No package manager detected")

    # 4. Generate configuration
    logger.debug("Generating configuration")
    config = _generate_config(
        project_root=project_root,
        toolchain=args.toolchain,
        minimal=args.minimal,
        package_manager=package_manager,
        platform_info=platform_info,
    )

    # Add config file name for success message (internal use only)
    config["config_file_name"] = config_file.name

    # 5. Write toolchainkit.yaml
    logger.debug(f"Writing configuration to {config_file}")
    try:
        _write_config_file(config_file, config)
    except Exception as e:
        logger.error(f"Failed to write configuration file: {e}")
        print_error("Failed to write configuration file", str(e))
        return 1

    # 6. Generate bootstrap scripts
    logger.debug("Generating bootstrap scripts")
    try:
        from toolchainkit.bootstrap.generator import BootstrapGenerator

        generator = BootstrapGenerator(project_root, config)
        scripts = generator.generate_all()
    except Exception as e:
        logger.error(f"Failed to generate bootstrap scripts: {e}")
        print_warning(f"Failed to generate bootstrap scripts: {e}")
        scripts = {}

    # 7. Update .gitignore
    logger.debug("Updating .gitignore")
    try:
        _update_gitignore(project_root)
    except Exception as e:
        logger.warning(f"Failed to update .gitignore: {e}")
        print_warning(f"Failed to update .gitignore: {e}")

    # 8. Display success message
    _print_success_message(project_root, config, scripts)

    logger.info("Initialization complete")
    return 0


def _detect_package_manager(project_root: Path) -> Optional[str]:
    """
    Auto-detect package manager from project files.

    Args:
        project_root: Project root directory

    Returns:
        Package manager name or None if not detected
    """
    # Check for Conan
    if (project_root / "conanfile.txt").exists() or (
        project_root / "conanfile.py"
    ).exists():
        return "conan"

    # Check for vcpkg
    if (project_root / "vcpkg.json").exists():
        return "vcpkg"

    # Check for CPM
    if (project_root / "CPM.cmake").exists() or (
        project_root / "cmake" / "CPM.cmake"
    ).exists():
        return "cpm"

    return None


def _generate_config(
    project_root: Path,
    toolchain: Optional[str],
    minimal: bool,
    package_manager: Optional[str],
    platform_info,
) -> dict:
    """
    Generate configuration dictionary.

    Args:
        project_root: Project root directory
        toolchain: Toolchain name (optional)
        minimal: Generate minimal configuration
        package_manager: Package manager name (optional)
        platform_info: Platform information

    Returns:
        Configuration dictionary
    """
    # Get project name from directory
    project_name = project_root.name

    # Base configuration
    config = {
        "project": {"name": project_name},
        "build": {"build_dir": "build", "build_type": "Release"},
    }

    # Add toolchain if specified
    if toolchain:
        config["toolchain"] = {"name": toolchain}
    elif not minimal:
        # Add empty toolchain section with comment
        config["toolchain"] = {
            "_comment": "Configure your toolchain here. Example: name: llvm-18"
        }

    # Add package manager if detected
    if package_manager and not minimal:
        config["packages"] = {"manager": package_manager}

    return config


def _write_config_file(config_file: Path, config: dict):
    """
    Write configuration to YAML file.

    Args:
        config_file: Path to configuration file
        config: Configuration dictionary
    """
    # Create header comment
    header = """\
# ToolchainKit Configuration
# Generated automatically - edit as needed
#
# For more information, see: https://github.com/yourusername/toolchainkit

"""

    # Convert config to YAML
    yaml_content = yaml.safe_dump(
        config, default_flow_style=False, sort_keys=False, indent=2
    )

    # Remove comment entries (used as placeholders)
    lines = yaml_content.split("\n")
    filtered_lines = [
        line for line in lines if not line.strip().startswith("_comment:")
    ]
    yaml_content = "\n".join(filtered_lines)

    # Write file
    config_file.write_text(header + yaml_content, encoding="utf-8")


def _update_gitignore(project_root: Path):
    """
    Update .gitignore with ToolchainKit entries.

    Args:
        project_root: Project root directory
    """
    gitignore_file = project_root / ".gitignore"

    # ToolchainKit entries to add
    entries = [
        "",
        "# ToolchainKit",
        ".toolchainkit/",
        "!.toolchainkit/config/",
        "bootstrap.sh",
        "bootstrap.bat",
    ]

    # Read existing .gitignore or create empty
    if gitignore_file.exists():
        content = gitignore_file.read_text(encoding="utf-8")
        lines = content.splitlines()
    else:
        lines = []

    # Check if ToolchainKit entries already exist
    if any("# ToolchainKit" in line for line in lines):
        logger.debug(".gitignore already contains ToolchainKit entries")
        return

    # Add entries
    lines.extend(entries)

    # Write back
    gitignore_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_success_message(project_root: Path, config: dict, scripts: dict):
    """
    Print success message with next steps.

    Args:
        project_root: Project root directory
        config: Configuration dictionary
        scripts: Dictionary of generated scripts
    """
    details = {
        "Configuration file": config.get("config_file_name", "toolchainkit.yaml")
    }

    if scripts:
        script_list = []
        if "shell" in scripts:
            script_list.append("bootstrap.sh")
        if "batch" in scripts:
            script_list.append("bootstrap.bat")
        details["Bootstrap scripts"] = ", ".join(script_list)

    next_steps = [
        "1. Review and edit toolchainkit.yaml if needed",
        "",
    ]

    # Platform-specific instructions
    if sys.platform == "win32":
        if "batch" in scripts:
            next_steps.append("2. Run: bootstrap.bat")
        else:
            next_steps.append("2. Run: tkgen configure --toolchain <name>")
    else:
        if "shell" in scripts:
            next_steps.append("2. Run: ./bootstrap.sh")
        else:
            next_steps.append("2. Run: tkgen configure --toolchain <name>")

    next_steps.append("")
    next_steps.append("3. Build your project with CMake")
    next_steps.append("")
    next_steps.append("For help: tkgen --help")

    message = format_success_message(
        "ToolchainKit initialized successfully!", details, next_steps=next_steps
    )
    print()
    print(message)
