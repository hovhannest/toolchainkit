"""
Directory structure management for ToolchainKit.

This module handles creation and management of the global cache directory
and project-local directories. It provides cross-platform path resolution
and ensures consistent directory structure across all ToolchainKit operations.

Directory Structure:
    Global Cache (~/.toolchainkit/ or %USERPROFILE%\\.toolchainkit\\):
        - toolchains/     : Downloaded/extracted toolchain installations
        - lock/           : Concurrent access control files
        - registry.json   : Toolchain reference counting database

    Project-Local (<project-root>/.toolchainkit/):
        - toolchains      : Symlink/junction to global cache toolchains
        - packages/       : Package manager cache (Conan/vcpkg)
        - state.json      : Current configuration state
        - cmake/          : Generated CMake toolchain files
          - toolchainkit/ : CMake modules and toolchain files
"""

import os
from pathlib import Path, PurePath
from typing import Dict, Optional


class DirectoryError(Exception):
    """Base exception for directory-related errors."""

    pass


class PermissionError(DirectoryError):
    """Raised when directory operations fail due to insufficient permissions."""

    pass


class DirectoryCreationError(DirectoryError):
    """Raised when directory creation fails."""

    pass


def get_global_cache_dir() -> Path:
    """
    Get the platform-specific global cache directory path.

    Returns:
        Path: The global cache directory path.
            - Windows: %USERPROFILE%\\.toolchainkit
            - Linux/macOS: ~/.toolchainkit/

    Example:
        >>> cache_dir = get_global_cache_dir()
        >>> print(cache_dir)
        /home/user/.toolchainkit  # on Linux
    """
    if os.name == "nt":  # Windows
        user_profile = os.environ.get("USERPROFILE")
        if not user_profile:
            raise DirectoryError(
                "USERPROFILE environment variable is not set. "
                "Cannot determine global cache directory."
            )
        return Path(user_profile) / ".toolchainkit"
    else:  # Linux/macOS
        return Path.home() / ".toolchainkit"


def get_project_local_dir(project_root: Path) -> Path:
    """
    Get the project-local .toolchainkit directory path.

    Args:
        project_root: Root directory of the project.

    Returns:
        Path: The project-local .toolchainkit directory path.

    Example:
        >>> project_dir = get_project_local_dir(Path('/path/to/project'))
        >>> print(project_dir)
        /path/to/project/.toolchainkit
    """
    if not isinstance(project_root, (Path, PurePath)):
        project_root = Path(project_root)
    return project_root / ".toolchainkit"


def verify_directory_writable(path: Path) -> bool:
    """
    Verify that a directory exists and is writable.

    Args:
        path: Directory path to verify.

    Returns:
        bool: True if directory exists and is writable, False otherwise.

    Example:
        >>> if verify_directory_writable(Path('/tmp/test')):
        ...     print("Directory is writable")
    """
    if not path.exists():
        return False

    if not path.is_dir():
        return False

    # Try to create a temporary file to test write permissions
    try:
        test_file = path / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, IOError):
        return False


def ensure_global_cache_structure() -> Path:
    """
    Create the global cache directory structure if it doesn't exist.

    Creates:
        - Global cache root directory
        - toolchains/ subdirectory
        - lock/ subdirectory
        - registry.json file (empty JSON object if doesn't exist)

    Returns:
        Path: The global cache directory path.

    Raises:
        DirectoryCreationError: If directory creation fails.
        PermissionError: If insufficient permissions to create directories.

    Example:
        >>> cache_dir = ensure_global_cache_structure()
        >>> print(f"Global cache at: {cache_dir}")
    """
    global_cache = get_global_cache_dir()

    # Create main cache directory
    try:
        global_cache.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DirectoryCreationError(
            f"Failed to create global cache directory at {global_cache}: {e}"
        )

    # Verify it's writable
    if not verify_directory_writable(global_cache):
        raise PermissionError(
            f"Global cache directory at {global_cache} is not writable. "
            "Please check directory permissions."
        )

    # Create subdirectories
    subdirs = ["toolchains", "lock"]
    for subdir in subdirs:
        subdir_path = global_cache / subdir
        try:
            subdir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise DirectoryCreationError(
                f"Failed to create subdirectory {subdir_path}: {e}"
            )

    # Create registry.json if it doesn't exist
    registry_file = global_cache / "registry.json"
    if not registry_file.exists():
        try:
            registry_file.write_text("{}")
        except OSError as e:
            raise DirectoryCreationError(
                f"Failed to create registry file at {registry_file}: {e}"
            )

    return global_cache


def ensure_project_structure(project_root: Path) -> Path:
    """
    Create the project-local directory structure if it doesn't exist.

    Args:
        project_root: Root directory of the project.

    Creates:
        - .toolchainkit/ directory
        - packages/ subdirectory
        - cmake/toolchainkit/ subdirectory structure
        - state.json file (empty JSON object if doesn't exist)

    Returns:
        Path: The project-local .toolchainkit directory path.

    Raises:
        DirectoryCreationError: If directory creation fails.
        PermissionError: If insufficient permissions to create directories.

    Example:
        >>> project_dir = ensure_project_structure(Path('/path/to/project'))
        >>> print(f"Project structure at: {project_dir}")
    """
    if not isinstance(project_root, (Path, PurePath)):
        project_root = Path(project_root)

    if not project_root.exists():
        raise DirectoryError(f"Project root directory does not exist: {project_root}")

    if not project_root.is_dir():
        raise DirectoryError(f"Project root is not a directory: {project_root}")

    project_local = get_project_local_dir(project_root)

    # Create main project-local directory
    try:
        project_local.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DirectoryCreationError(
            f"Failed to create project-local directory at {project_local}: {e}"
        )

    # Verify it's writable
    if not verify_directory_writable(project_local):
        raise PermissionError(
            f"Project-local directory at {project_local} is not writable. "
            "Please check directory permissions."
        )

    # Create subdirectories
    subdirs = [
        "packages",
        "cmake/toolchainkit",
    ]
    for subdir in subdirs:
        subdir_path = project_local / subdir
        try:
            subdir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise DirectoryCreationError(
                f"Failed to create subdirectory {subdir_path}: {e}"
            )

    # Create state.json if it doesn't exist
    state_file = project_local / "state.json"
    if not state_file.exists():
        try:
            state_file.write_text("{}")
        except OSError as e:
            raise DirectoryCreationError(
                f"Failed to create state file at {state_file}: {e}"
            )

    return project_local


def update_gitignore(project_root: Path) -> None:
    """
    Add .toolchainkit/ to project's .gitignore if not already present.

    This ensures that the project-local ToolchainKit directory is not
    committed to version control, as it contains local state and caches.

    Args:
        project_root: Root directory of the project.

    Raises:
        DirectoryError: If project root doesn't exist or isn't a directory.
        PermissionError: If insufficient permissions to write .gitignore.

    Example:
        >>> update_gitignore(Path('/path/to/project'))
        # .gitignore now contains .toolchainkit/
    """
    if not isinstance(project_root, (Path, PurePath)):
        project_root = Path(project_root)

    if not project_root.exists():
        raise DirectoryError(f"Project root directory does not exist: {project_root}")

    if not project_root.is_dir():
        raise DirectoryError(f"Project root is not a directory: {project_root}")

    gitignore_path = project_root / ".gitignore"
    pattern = ".toolchainkit/"

    # Read existing content
    existing_content = ""
    if gitignore_path.exists():
        try:
            existing_content = gitignore_path.read_text(encoding="utf-8")
        except OSError as e:
            raise PermissionError(f"Failed to read .gitignore at {gitignore_path}: {e}")

    # Check if pattern already exists
    lines = existing_content.splitlines()
    if pattern in lines:
        # Pattern already exists, nothing to do
        return

    # Add pattern to gitignore
    try:
        # Ensure file ends with newline if it exists
        if existing_content and not existing_content.endswith("\n"):
            existing_content += "\n"

        # Add pattern with comment
        new_content = existing_content
        if not existing_content:
            new_content = f"# ToolchainKit local state and cache\n{pattern}\n"
        else:
            new_content += f"\n# ToolchainKit local state and cache\n{pattern}\n"

        gitignore_path.write_text(new_content, encoding="utf-8")
    except OSError as e:
        raise PermissionError(f"Failed to update .gitignore at {gitignore_path}: {e}")


def create_directory_structure(project_root: Optional[Path] = None) -> Dict[str, Path]:
    """
    Create the complete ToolchainKit directory structure.

    This is the main entry point for setting up directories. It creates
    both the global cache structure and, if a project root is provided,
    the project-local structure.

    Args:
        project_root: Optional root directory of the project. If provided,
                     creates project-local structure and updates .gitignore.

    Returns:
        Dict[str, Path]: Dictionary containing paths to created directories:
            - 'global_cache': Global cache directory path
            - 'project_local': Project-local directory path (if project_root provided)

    Raises:
        DirectoryCreationError: If directory creation fails.
        PermissionError: If insufficient permissions.

    Example:
        >>> # Create only global cache
        >>> paths = create_directory_structure()
        >>> print(paths['global_cache'])

        >>> # Create both global and project-local
        >>> paths = create_directory_structure(Path('/path/to/project'))
        >>> print(paths['global_cache'])
        >>> print(paths['project_local'])
    """
    result = {}

    # Always create global cache structure
    global_cache = ensure_global_cache_structure()
    result["global_cache"] = global_cache

    # Create project-local structure if project root provided
    if project_root is not None:
        if not isinstance(project_root, (Path, PurePath)):
            project_root = Path(project_root)

        project_local = ensure_project_structure(project_root)
        result["project_local"] = project_local

        # Update .gitignore
        update_gitignore(project_root)

    return result
