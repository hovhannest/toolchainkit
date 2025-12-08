"""
Test helper utilities for ToolchainKit testing.

This module provides utility functions for common test operations such as
checking command availability, creating file trees, and running commands safely.
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Union, Tuple
import shutil


def has_command(command: str, timeout: int = 5) -> bool:
    """
    Check if a command is available in PATH.

    Attempts to run the command with --version flag and returns True
    if it executes successfully.

    Args:
        command: Command name to check (e.g., 'cmake', 'gcc')
        timeout: Timeout in seconds for command execution

    Returns:
        True if command is available and responds, False otherwise

    Example:
        >>> if has_command('cmake'):
        ...     print("CMake is available")
    """
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def has_cmake() -> bool:
    """
    Check if CMake is available.

    Returns:
        True if CMake is installed and accessible, False otherwise

    Example:
        >>> if not has_cmake():
        ...     pytest.skip("CMake not available")
    """
    return has_command("cmake")


def has_ninja() -> bool:
    """
    Check if Ninja build system is available.

    Returns:
        True if Ninja is installed and accessible, False otherwise

    Example:
        >>> if has_ninja():
        ...     generator = "Ninja"
        ... else:
        ...     generator = "Unix Makefiles"
    """
    return has_command("ninja")


def has_gcc() -> bool:
    """
    Check if GCC compiler is available.

    Returns:
        True if GCC is installed and accessible, False otherwise

    Example:
        >>> if has_gcc():
        ...     run_gcc_specific_test()
    """
    return has_command("gcc")


def has_clang() -> bool:
    """
    Check if Clang compiler is available.

    Returns:
        True if Clang is installed and accessible, False otherwise

    Example:
        >>> if has_clang():
        ...     run_clang_specific_test()
    """
    return has_command("clang")


def has_msvc() -> bool:
    """
    Check if MSVC compiler is available.

    Returns:
        True if MSVC cl.exe is accessible, False otherwise

    Example:
        >>> if has_msvc():
        ...     run_msvc_specific_test()
    """
    return has_command("cl")


def create_file_tree(
    root: Path, structure: Dict[str, Optional[Union[str, bytes]]]
) -> None:
    """
    Create a file tree from a dictionary structure.

    Creates files and directories based on a dictionary mapping paths to content.
    If content is None, creates a directory. If content is a string or bytes,
    creates a file with that content.

    Args:
        root: Root directory for the file tree
        structure: Dictionary mapping paths to content
            - Keys are file/directory paths relative to root
            - Values are:
                - None: Create directory
                - str: Create file with text content
                - bytes: Create file with binary content

    Example:
        >>> create_file_tree(tmp_path, {
        ...     'src/main.cpp': '#include <iostream>\\nint main() { return 0; }',
        ...     'include/': None,  # Directory
        ...     'include/header.h': '#pragma once',
        ...     'CMakeLists.txt': 'cmake_minimum_required(VERSION 3.20)',
        ...     'data/binary.dat': b'\\x00\\x01\\x02\\x03',
        ... })
    """
    for path_str, content in structure.items():
        file_path = root / path_str

        if content is None:
            # Create directory
            file_path.mkdir(parents=True, exist_ok=True)
        else:
            # Create file with content
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content, encoding="utf-8")


def run_command_safe(
    command: list[str],
    cwd: Optional[Path] = None,
    timeout: int = 30,
    check: bool = True,
) -> Tuple[int, str, str]:
    """
    Run a command safely with timeout and error handling.

    Executes a command in a subprocess with proper timeout handling,
    output capture, and error checking.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command execution
        timeout: Timeout in seconds
        check: If True, raise exception on non-zero exit code

    Returns:
        Tuple of (return_code, stdout, stderr)

    Raises:
        subprocess.TimeoutExpired: If command exceeds timeout
        subprocess.CalledProcessError: If check=True and command fails

    Example:
        >>> returncode, stdout, stderr = run_command_safe(
        ...     ['cmake', '--version'],
        ...     timeout=5
        ... )
        >>> assert returncode == 0
        >>> assert 'cmake version' in stdout.lower()
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        # Re-raise with captured output
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, output=e.stdout, stderr=e.stderr
        )
    except subprocess.TimeoutExpired as e:
        # Re-raise with any captured output
        raise subprocess.TimeoutExpired(
            e.cmd, e.timeout, output=e.stdout, stderr=e.stderr
        )


def compare_files(file1: Path, file2: Path, ignore_whitespace: bool = False) -> bool:
    """
    Compare two files for equality.

    Args:
        file1: First file path
        file2: Second file path
        ignore_whitespace: If True, ignore whitespace differences in text files

    Returns:
        True if files are identical, False otherwise

    Example:
        >>> assert compare_files(generated_file, expected_file)
    """
    if not file1.exists() or not file2.exists():
        return False

    if ignore_whitespace:
        try:
            # Try text comparison with whitespace normalization
            content1 = file1.read_text().split()
            content2 = file2.read_text().split()
            return content1 == content2
        except (UnicodeDecodeError, AttributeError):
            # Fall through to binary comparison
            pass

    # Binary comparison
    return file1.read_bytes() == file2.read_bytes()


def get_command_version(command: str) -> Optional[str]:
    """
    Get version string from a command.

    Runs command with --version flag and returns the version string.

    Args:
        command: Command name

    Returns:
        Version string if available, None otherwise

    Example:
        >>> version = get_command_version('cmake')
        >>> if version:
        ...     print(f"CMake version: {version}")
    """
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            # Return first line of output (typically contains version)
            return result.stdout.strip().split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def find_executable(name: str) -> Optional[Path]:
    """
    Find executable in PATH.

    Args:
        name: Executable name to find

    Returns:
        Path to executable if found, None otherwise

    Example:
        >>> cmake_path = find_executable('cmake')
        >>> if cmake_path:
        ...     print(f"CMake found at: {cmake_path}")
    """
    path = shutil.which(name)
    return Path(path) if path else None


def create_empty_file(path: Path, size: int = 0) -> None:
    """
    Create an empty file or file with specific size.

    Args:
        path: File path to create
        size: Size in bytes (0 for empty file)

    Example:
        >>> create_empty_file(tmp_path / "test.txt")
        >>> create_empty_file(tmp_path / "large.dat", size=1024 * 1024)  # 1MB
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if size == 0:
        path.touch()
    else:
        with path.open("wb") as f:
            f.write(b"\x00" * size)


def copy_tree(
    src: Path, dst: Path, ignore_patterns: Optional[list[str]] = None
) -> None:
    """
    Copy directory tree with optional ignore patterns.

    Args:
        src: Source directory
        dst: Destination directory
        ignore_patterns: List of glob patterns to ignore

    Example:
        >>> copy_tree(
        ...     source_dir,
        ...     dest_dir,
        ...     ignore_patterns=['*.pyc', '__pycache__', '.git']
        ... )
    """
    if ignore_patterns:

        def ignore_func(directory, names):
            import fnmatch

            ignored = set()
            for pattern in ignore_patterns:
                ignored.update(fnmatch.filter(names, pattern))
            return ignored

        shutil.copytree(src, dst, ignore=ignore_func, dirs_exist_ok=True)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)
