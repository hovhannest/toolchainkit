"""
Python environment management for ToolchainKit.

This module provides hermetic Python environment management, enabling ToolchainKit
to run with an embedded Python interpreter without requiring users to manually
install Python. It handles downloading, extracting, and verifying platform-specific
Python distributions.

The embedded Python is isolated from system Python installations to ensure
reproducible behavior across different machines.

Python distributions:
    - Windows: Python embeddable zip from python.org (~10MB)
    - Linux: Standalone builds from python-build-standalone (~20MB)
    - macOS: Standalone builds from python-build-standalone (~25MB)

All distributions are extracted to the global cache directory under 'python/'.
"""

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

# Import from Task 01
from toolchainkit.core.directory import get_global_cache_dir
from toolchainkit.core.download import download_file, DownloadProgress
from toolchainkit.core.filesystem import extract_archive, ArchiveExtractionError


class PythonEnvironmentError(Exception):
    """Base exception for Python environment-related errors."""

    pass


class PlatformNotSupportedError(PythonEnvironmentError):
    """Raised when the current platform is not supported."""

    pass


class PythonDownloadError(PythonEnvironmentError):
    """Raised when downloading Python distribution fails."""

    pass


class PythonExtractionError(PythonEnvironmentError):
    """Raised when extracting Python distribution fails."""

    pass


class PythonVerificationError(PythonEnvironmentError):
    """Raised when Python verification fails."""

    pass


# Python 3.11.7 distribution URLs for all supported platforms
PYTHON_URLS = {
    "windows-x64": "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip",
    "windows-arm64": "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-arm64.zip",
    "linux-x64": "https://github.com/astral-sh/python-build-standalone/releases/download/20251031/cpython-3.11.14+20251031-x86_64-unknown-linux-gnu-install_only.tar.gz",
    "linux-arm64": "https://github.com/astral-sh/python-build-standalone/releases/download/20251031/cpython-3.11.14+20251031-aarch64-unknown-linux-gnu-install_only.tar.gz",
    "macos-x64": "https://github.com/astral-sh/python-build-standalone/releases/download/20251031/cpython-3.11.14+20251031-x86_64-apple-darwin-install_only.tar.gz",
    "macos-arm64": "https://github.com/astral-sh/python-build-standalone/releases/download/20251031/cpython-3.11.14+20251031-aarch64-apple-darwin-install_only.tar.gz",
}


def detect_platform() -> str:
    """
    Detect the current platform and architecture.

    Returns:
        str: Platform key in format 'os-arch' (e.g., 'windows-x64', 'linux-arm64').
             Valid values: windows-x64, windows-arm64, linux-x64, linux-arm64,
                          macos-x64, macos-arm64

    Raises:
        PlatformNotSupportedError: If platform or architecture is not supported.

    Example:
        >>> platform_key = detect_platform()
        >>> print(platform_key)
        linux-x64
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize OS name
    if system == "windows":
        os_name = "windows"
    elif system == "linux":
        os_name = "linux"
    elif system == "darwin":
        os_name = "macos"
    else:
        raise PlatformNotSupportedError(
            f"Unsupported operating system: {system}. "
            f"Supported platforms: Windows, Linux, macOS"
        )

    # Normalize architecture
    if machine in ("x86_64", "amd64", "x64"):
        arch = "x64"
    elif machine in ("aarch64", "arm64", "armv8l", "armv8b"):
        arch = "arm64"
    else:
        raise PlatformNotSupportedError(
            f"Unsupported architecture: {machine}. "
            f"Supported architectures: x64, arm64"
        )

    platform_key = f"{os_name}-{arch}"

    # Verify we have a URL for this platform
    if platform_key not in PYTHON_URLS:
        raise PlatformNotSupportedError(
            f"Platform {platform_key} is not supported. "
            f"Available platforms: {', '.join(PYTHON_URLS.keys())}"
        )

    return platform_key


def get_python_url(platform_key: Optional[str] = None) -> str:
    """
    Get the download URL for Python distribution for a specific platform.

    Args:
        platform_key: Platform identifier (e.g., 'windows-x64'). If None,
                     detects current platform automatically.

    Returns:
        str: Download URL for the Python distribution.

    Raises:
        PlatformNotSupportedError: If platform is not supported.

    Example:
        >>> url = get_python_url('linux-x64')
        >>> print(url)
        https://github.com/indygreg/python-build-standalone/releases/...
    """
    if platform_key is None:
        platform_key = detect_platform()

    if platform_key not in PYTHON_URLS:
        raise PlatformNotSupportedError(
            f"No Python distribution available for platform: {platform_key}"
        )

    return PYTHON_URLS[platform_key]


def get_python_dir() -> Path:
    """
    Get the directory where Python should be installed.

    Returns:
        Path: Python installation directory (global_cache/python).

    Example:
        >>> python_dir = get_python_dir()
        >>> print(python_dir)
        /home/user/.toolchainkit/python
    """
    return get_global_cache_dir() / "python"


def find_python_executable(python_dir: Path) -> Path:
    """
    Find the Python executable in the installation directory.

    Args:
        python_dir: Python installation directory.

    Returns:
        Path: Path to Python executable.

    Raises:
        PythonVerificationError: If Python executable is not found.

    Example:
        >>> python_exe = find_python_executable(Path('/path/to/python'))
        >>> print(python_exe)
        /path/to/python/bin/python3
    """
    if not python_dir.exists():
        raise PythonVerificationError(f"Python directory does not exist: {python_dir}")

    # Platform-specific executable paths
    if os.name == "nt":  # Windows
        candidates = [
            python_dir / "python.exe",
            python_dir / "Scripts" / "python.exe",
        ]
    else:  # Linux/macOS
        candidates = [
            python_dir / "bin" / "python3",
            python_dir / "bin" / "python",
            python_dir
            / "python"
            / "bin"
            / "python3",  # python-build-standalone structure
            python_dir / "python" / "bin" / "python",
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise PythonVerificationError(
        f"Python executable not found in {python_dir}. "
        f"Searched: {', '.join(str(c) for c in candidates)}"
    )


def verify_python(python_exe: Path) -> bool:
    """
    Verify that Python executable works and meets version requirements.

    Args:
        python_exe: Path to Python executable.

    Returns:
        bool: True if Python is valid and meets requirements, False otherwise.

    Example:
        >>> if verify_python(Path('/path/to/python')):
        ...     print("Python is valid")
    """
    if not python_exe.exists():
        return False

    try:
        # Check if executable
        if not os.access(python_exe, os.X_OK):
            # Try to make it executable on Unix-like systems
            if os.name != "nt":
                python_exe.chmod(0o755)

        # Run python --version
        result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONNOUSERSITE": "1"},
        )

        if result.returncode != 0:
            return False

        # Parse version (e.g., "Python 3.11.7")
        version_output = result.stdout.strip() or result.stderr.strip()
        if not version_output.startswith("Python "):
            return False

        version_str = version_output.split()[1]
        version_parts = version_str.split(".")

        if len(version_parts) < 2:
            return False

        major = int(version_parts[0])
        minor = int(version_parts[1])

        # Require Python 3.8+
        if major != 3 or minor < 8:
            return False

        # Verify critical stdlib modules are available
        test_code = (
            "import pathlib, hashlib, json, zipfile, tarfile, subprocess, sys; "
            "print('OK')"
        )

        result = subprocess.run(
            [str(python_exe), "-c", test_code],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONNOUSERSITE": "1"},
        )

        return result.returncode == 0 and "OK" in result.stdout

    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError):
        return False


def download_python(url: str, dest_path: Path, timeout: int = 300) -> None:
    """
    Download Python distribution from URL using robust download implementation.

    This now uses the core download_file function which provides:
    - Progress tracking with visual feedback
    - Automatic retry with exponential backoff
    - Resume capability for interrupted downloads
    - Better error handling and timeouts

    Args:
        url: Download URL for Python distribution.
        dest_path: Destination file path for downloaded archive.
        timeout: Download timeout in seconds (default: 300 = 5 minutes).

    Raises:
        PythonDownloadError: If download fails.

    Example:
        >>> download_python(
        ...     'https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip',
        ...     Path('/tmp/python.zip')
        ... )
    """
    try:
        # Use robust download implementation with progress tracking
        def progress_callback(progress: DownloadProgress) -> None:
            """Show download progress."""
            if progress.total_bytes > 0:
                print(
                    f"Downloading Python: {progress.percentage:.1f}%",
                    end="\r",
                    flush=True,
                )

        download_file(
            url=url,
            destination=dest_path,
            progress_callback=progress_callback,
            resume=True,
            timeout=timeout,
            max_retries=3,
        )

        # Clear progress line
        print("Downloading Python: 100.0%")

    except Exception as e:
        # Clean up partial download on error
        if dest_path.exists():
            dest_path.unlink()
        raise PythonDownloadError(f"Failed to download Python from {url}: {e}")


def extract_python(archive_path: Path, dest_dir: Path) -> None:
    """
    Extract Python distribution archive to destination directory.

    Delegates to core.filesystem.extract_archive for consistent behavior.

    Args:
        archive_path: Path to downloaded archive (.zip or .tar.gz).
        dest_dir: Destination directory for extraction.

    Raises:
        PythonExtractionError: If extraction fails.

    Example:
        >>> extract_python(
        ...     Path('/tmp/python.zip'),
        ...     Path('/home/user/.toolchainkit/python')
        ... )
    """
    try:
        # Remove existing installation if present
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        # Create destination directory (extract_archive will also do this, but being explicit)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Use centralized extraction function for consistent behavior
        extract_archive(archive_path, dest_dir, progress_callback=None)

        # Verify extraction created files
        if not any(dest_dir.iterdir()):
            raise PythonExtractionError(
                f"Extraction completed but directory is empty: {dest_dir}"
            )

    except ArchiveExtractionError as e:
        # Clean up on failure
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise PythonExtractionError(
            f"Failed to extract Python archive {archive_path}: {e}"
        )
    except Exception as e:
        # Clean up on failure
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise PythonExtractionError(
            f"Failed to extract Python archive {archive_path}: {e}"
        )


def get_python_environment(python_exe: Path) -> Dict[str, str]:
    """
    Get environment variables for isolated Python execution.

    Args:
        python_exe: Path to Python executable.

    Returns:
        Dict[str, str]: Environment variables to set for Python isolation.

    Example:
        >>> env = get_python_environment(Path('/path/to/python/bin/python3'))
        >>> subprocess.run([python_exe, 'script.py'], env=env)
    """
    python_dir = (
        python_exe.parent.parent
        if python_exe.parent.name == "bin"
        else python_exe.parent
    )

    env = os.environ.copy()

    # Set Python home
    env["PYTHONHOME"] = str(python_dir)

    # Set Python path
    if os.name == "nt":  # Windows
        lib_path = python_dir
    else:  # Linux/macOS
        lib_path = python_dir / "lib"
        if not lib_path.exists():
            lib_path = python_dir / "python" / "lib"

    env["PYTHONPATH"] = str(lib_path)

    # Ensure isolation from user site-packages
    env["PYTHONNOUSERSITE"] = "1"

    # Disable writing .pyc files
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    return env


def setup_python_environment(force_reinstall: bool = False, timeout: int = 600) -> Path:
    """
    Ensure Python environment is available and return path to executable.

    This is the main entry point for setting up the embedded Python environment.
    It will check if Python is already installed, verify it works, and download/
    install it if necessary.

    Args:
        force_reinstall: If True, re-download and reinstall even if Python exists.
        timeout: Maximum time in seconds for download operation (default: 600 = 10 minutes).

    Returns:
        Path: Path to Python executable.

    Raises:
        PlatformNotSupportedError: If current platform is not supported.
        PythonDownloadError: If download fails or times out.
        PythonExtractionError: If extraction fails.
        PythonVerificationError: If Python verification fails after installation.

    Example:
        >>> python_exe = setup_python_environment()
        >>> print(f"Python installed at: {python_exe}")
        >>> # Now you can use python_exe to run Python scripts
    """
    python_dir = get_python_dir()

    # Check if Python already exists and works
    if not force_reinstall and python_dir.exists():
        try:
            python_exe = find_python_executable(python_dir)
            if verify_python(python_exe):
                return python_exe
        except PythonVerificationError:
            # Existing installation is broken, will reinstall
            pass

    # Need to download and install Python
    platform_key = detect_platform()
    url = get_python_url(platform_key)

    # Create temporary directory for download
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Determine archive filename from URL
        archive_name = url.split("/")[-1]
        archive_path = tmpdir_path / archive_name

        # Download Python with timeout
        print(f"Downloading Python for {platform_key}...")
        download_python(url, archive_path, timeout=timeout)

        # Extract Python
        print("Extracting Python...")
        extract_python(archive_path, python_dir)

    # Find and verify Python executable
    python_exe = find_python_executable(python_dir)

    if not verify_python(python_exe):
        raise PythonVerificationError(
            f"Python installation at {python_dir} failed verification. "
            f"The Python executable may be corrupted or incomplete."
        )

    print(f"Python successfully installed at: {python_exe}")
    return python_exe


def get_python_version(python_exe: Path) -> Tuple[int, int, int]:
    """
    Get the version of a Python executable.

    Args:
        python_exe: Path to Python executable.

    Returns:
        Tuple[int, int, int]: Python version as (major, minor, patch).

    Raises:
        PythonVerificationError: If version cannot be determined.

    Example:
        >>> version = get_python_version(Path('/usr/bin/python3'))
        >>> print(f"Python {version[0]}.{version[1]}.{version[2]}")
        Python 3.11.7
    """
    try:
        result = subprocess.run(
            [str(python_exe), "--version"], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            raise PythonVerificationError(
                f"Failed to get Python version: {result.stderr}"
            )

        # Parse version (e.g., "Python 3.11.7")
        version_output = result.stdout.strip() or result.stderr.strip()
        if not version_output.startswith("Python "):
            raise PythonVerificationError(
                f"Unexpected version output: {version_output}"
            )

        version_str = version_output.split()[1]
        parts = version_str.split(".")

        if len(parts) < 3:
            parts += ["0"] * (3 - len(parts))

        return (int(parts[0]), int(parts[1]), int(parts[2]))

    except (
        subprocess.TimeoutExpired,
        ValueError,
        IndexError,
        FileNotFoundError,
        OSError,
    ) as e:
        raise PythonVerificationError(f"Failed to parse Python version: {e}")
