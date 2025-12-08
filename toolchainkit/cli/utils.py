"""
Shared utilities for CLI commands.

Provides common functionality used across multiple CLI commands to
eliminate duplication and ensure consistent behavior.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Management
# ============================================================================


def _normalize_legacy_config_fields(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize legacy configuration fields for backwards compatibility.

    Converts deprecated toolchain_dir/cache_dir fields to the modern
    toolchain_cache format.

    Args:
        config: Configuration dictionary

    Returns:
        Normalized configuration dictionary
    """
    # Skip if toolchain_cache is already explicitly set
    if "toolchain_cache" in config:
        return config

    # Convert legacy toolchain_dir field
    if "toolchain_dir" in config:
        toolchain_dir = config["toolchain_dir"]
        if isinstance(toolchain_dir, str):
            config["toolchain_cache"] = {
                "location": "local" if toolchain_dir.startswith(".") else "custom",
                "path": toolchain_dir,
            }
            logger.debug(
                f"Converted legacy toolchain_dir '{toolchain_dir}' to toolchain_cache"
            )
        return config

    # Convert legacy cache_dir field
    if "cache_dir" in config:
        cache_dir = config["cache_dir"]
        if isinstance(cache_dir, str):
            config["toolchain_cache"] = {
                "location": "local" if cache_dir.startswith(".") else "custom",
                "path": cache_dir,
            }
            logger.debug(f"Converted legacy cache_dir '{cache_dir}' to toolchain_cache")
        return config

    return config


def load_yaml_config(config_file: Path, required: bool = False) -> Dict[str, Any]:
    """
    Load and parse a YAML configuration file.

    Args:
        config_file: Path to YAML configuration file
        required: If True, raise error if file doesn't exist

    Returns:
        Configuration dictionary (empty dict if file doesn't exist and not required)

    Raises:
        FileNotFoundError: If required=True and file doesn't exist
        ValueError: If YAML parsing fails

    Example:
        >>> config = load_yaml_config(Path("toolchainkit.yaml"))
        >>> config.get("toolchain", "llvm-18")
    """
    if not config_file.exists():
        if required:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        logger.debug(f"Config file not found (optional): {config_file}")
        return {}

    logger.debug(f"Loading configuration from {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config = config or {}

        # Normalize legacy fields for backwards compatibility
        config = _normalize_legacy_config_fields(config)

        return config
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML: {e}")
        raise ValueError(f"Invalid YAML in {config_file}: {e}")


def validate_config(config: Dict[str, Any], required_keys: list) -> bool:
    """
    Validate that configuration contains required keys.

    Args:
        config: Configuration dictionary
        required_keys: List of required key paths (e.g., ["build.type", "toolchain"])

    Returns:
        True if all required keys present

    Raises:
        ValueError: If any required keys are missing
    """
    missing = []
    for key_path in required_keys:
        keys = key_path.split(".")
        value = config
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                missing.append(key_path)
                break
            value = value[key]

    if missing:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")

    return True


# ============================================================================
# Package Manager Integration
# ============================================================================


def get_package_manager_instance(
    manager_name: str, project_root: Path, packages_config: Optional[dict] = None
):
    """
    Get an instance of a package manager by name.

    Args:
        manager_name: Name of package manager ('conan', 'vcpkg', etc.)
        project_root: Project root directory
        packages_config: Optional package configuration dict (e.g., conan_home)

    Returns:
        Package manager instance

    Raises:
        KeyError: If package manager not found in registry

    Example:
        >>> manager = get_package_manager_instance("conan", Path.cwd())
        >>> manager.install_dependencies()
    """
    from toolchainkit.plugins.registry import get_global_registry

    logger.debug(f"Loading package manager: {manager_name}")

    registry = get_global_registry()

    try:
        manager_cls = registry.get_package_manager(manager_name)

        # Pass additional config to manager constructor if provided
        if packages_config and manager_name == "conan":
            # Extract Conan-specific config
            conan_home = packages_config.get("conan_home")
            use_system_conan = packages_config.get("use_system_conan", False)

            # Resolve conan_home relative path
            if conan_home:
                conan_home_path = Path(conan_home)
                if not conan_home_path.is_absolute():
                    conan_home_path = project_root / conan_home_path
                logger.debug(f"Setting CONAN_HOME to: {conan_home_path}")
                manager = manager_cls(
                    project_root,
                    use_system_conan=use_system_conan,
                    conan_home=conan_home_path,
                )
            else:
                manager = manager_cls(project_root, use_system_conan=use_system_conan)
        else:
            manager = manager_cls(project_root)

        return manager
    except KeyError:
        logger.error(f"Unknown package manager: {manager_name}")
        raise KeyError(
            f"Package manager '{manager_name}' not found. Available: conan, vcpkg"
        )


# ============================================================================
# User Interface / Output Formatting
# ============================================================================


def print_box(text: str, width: int = 70, char: str = "="):
    """Print text in a box for emphasis."""
    print(char * width)
    print(text)
    print(char * width)


def format_success_message(
    title: str,
    details: Dict[str, Any],
    next_steps: Optional[list] = None,
    width: int = 70,
) -> str:
    """
    Format a standardized success message.

    Args:
        title: Success message title
        details: Key-value pairs to display
        next_steps: Optional list of next step instructions
        width: Width of message box

    Returns:
        Formatted message string
    """
    lines = []
    lines.append("=" * width)
    lines.append(title)
    lines.append("=" * width)
    lines.append("")

    # Add details
    for key, value in details.items():
        lines.append(f"{key}: {value}")

    # Add next steps
    if next_steps:
        lines.append("")
        lines.append("Next steps:")
        for step in next_steps:
            lines.append(f"  {step}")

    lines.append("")
    return "\n".join(lines)


def print_error(message: str, details: Optional[str] = None):
    """
    Print error message to stderr in consistent format.

    Args:
        message: Main error message
        details: Optional additional details
    """
    print(f"ERROR: {message}", file=sys.stderr)
    if details:
        print(f"  {details}", file=sys.stderr)


def print_warning(message: str):
    """Print warning message to stderr."""
    print(f"WARNING: {message}", file=sys.stderr)


def safe_print(message: str, file=None):
    """
    Print message with safe encoding handling for Windows console.

    Falls back to ASCII-safe characters if Unicode emojis can't be encoded.

    Args:
        message: Message to print
        file: Output file (default: stdout)
    """
    try:
        print(message, file=file)
    except UnicodeEncodeError:
        # Replace common Unicode characters with ASCII equivalents
        safe_message = (
            message.replace("⚠️", "WARNING:")
            .replace("✓", "[OK]")
            .replace("✅", "[OK]")
            .replace("❌", "[ERROR]")
            .replace("🔧", "[CONFIG]")
        )
        print(safe_message, file=file)


# ============================================================================
# Project Structure Validation
# ============================================================================


def check_initialized(project_root: Path, config_file: Optional[Path] = None) -> bool:
    """
    Check if project is initialized (has toolchainkit.yaml or specified config).

    Args:
        project_root: Project root directory
        config_file: Optional path to specific configuration file

    Returns:
        True if initialized, False otherwise
    """
    if config_file:
        return config_file.exists()

    default_config = project_root / "toolchainkit.yaml"
    return default_config.exists()


def require_initialized(project_root: Path, command_name: str):
    """
    Raise error if project is not initialized.

    Args:
        project_root: Project root directory
        command_name: Name of command being run

    Raises:
        RuntimeError: If project not initialized
    """
    if not check_initialized(project_root):
        raise RuntimeError(
            f"Project not initialized. Run 'tkgen init' before '{command_name}'."
        )


# ============================================================================
# Path Utilities
# ============================================================================


def resolve_project_root(path: Optional[Path] = None) -> Path:
    """
    Resolve project root directory.

    Args:
        path: Optional path (defaults to current directory)

    Returns:
        Resolved absolute path
    """
    if path is None:
        path = Path.cwd()
    return path.resolve()


def ensure_directory(path: Path, description: str = "directory"):
    """
    Ensure directory exists, create if needed.

    Args:
        path: Directory path
        description: Description for error messages

    Raises:
        OSError: If directory cannot be created
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured {description} exists: {path}")
    except OSError as e:
        logger.error(f"Failed to create {description}: {e}")
        raise OSError(f"Could not create {description} at {path}: {e}")
