"""
Cross-platform file system utilities for ToolchainKit.

This module provides robust, platform-aware file operations including:
- Symlink/junction creation (with Windows junction support)
- Archive extraction (tar.gz, tar.xz, tar.bz2, zip, 7z)
- Safe file operations (atomic writes, safe deletion)
- Path utilities (normalization, long path support)

All operations handle platform differences transparently and provide
appropriate fallbacks when privileged operations are unavailable.
"""

import os
import sys
import shutil
import tarfile
import zipfile
import tempfile
import hashlib
import json
from pathlib import Path
from typing import Optional, Callable, Union, Literal
from contextlib import contextmanager

# Platform detection
IS_WINDOWS = os.name == "nt"
IS_UNIX = not IS_WINDOWS

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes


# ============================================================================
# Link Type and Error Handling
# ============================================================================

LinkType = Literal["auto", "symlink", "junction", "hardlink", "reference"]


class FilesystemError(Exception):
    """Base exception for filesystem operations."""

    pass


class LinkCreationError(FilesystemError):
    """Failed to create a symbolic link or junction."""

    pass


class ArchiveExtractionError(FilesystemError):
    """Failed to extract an archive."""

    pass


class UnsupportedArchiveFormat(ArchiveExtractionError):
    """Archive format is not supported."""

    pass


class InsecureArchiveError(ArchiveExtractionError):
    """Archive contains insecure paths (directory traversal attempt)."""

    pass


# ============================================================================
# Path Utilities
# ============================================================================


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a path for consistent comparison across platforms.

    Resolves symlinks, makes path absolute, and normalizes separators.

    Args:
        path: Path to normalize

    Returns:
        Normalized absolute path

    Example:
        >>> normalize_path("./foo/../bar")
        PosixPath('/absolute/path/to/bar')
    """
    return Path(path).resolve().absolute()


def make_long_path_safe(path: Union[str, Path]) -> str:
    """
    Add Windows long path prefix if needed.

    Windows has a 260 character path limit (MAX_PATH) unless the \\\\?\\
    prefix is used. This function automatically adds the prefix when needed.

    Args:
        path: Path that might be too long

    Returns:
        Path string, with \\\\?\\ prefix added on Windows if needed

    Example:
        >>> make_long_path_safe("C:\\very\\long\\path\\...")
        '\\\\?\\C:\\very\\long\\path\\...'
    """
    path_str = str(Path(path).absolute())

    if IS_WINDOWS and len(path_str) > 260 and not path_str.startswith("\\\\?\\"):
        # Convert forward slashes to backslashes for \\?\ prefix
        path_str = path_str.replace("/", "\\")
        return f"\\\\?\\{path_str}"

    return path_str


def is_relative_to(path: Path, parent: Path) -> bool:
    """
    Check if path is relative to (under) parent directory.

    Backport of Path.is_relative_to() for Python < 3.9.

    Args:
        path: Path to check
        parent: Parent directory

    Returns:
        True if path is under parent directory

    Example:
        >>> is_relative_to(Path("/home/user/project/file.txt"), Path("/home/user"))
        True
    """
    # Use built-in method if available (Python 3.9+)
    if hasattr(Path, "is_relative_to"):
        return path.is_relative_to(parent)

    # Fallback for older Python versions
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_link(link_path: Union[str, Path]) -> Path:
    """
    Resolve a symbolic link to its target.

    Args:
        link_path: Path to the link

    Returns:
        Resolved target path

    Raises:
        ValueError: If path is not a link
    """
    link_path = Path(link_path)

    if not link_path.is_symlink():
        raise ValueError(f"Path is not a symbolic link: {link_path}")

    return link_path.resolve()


def find_executable(
    name: str, search_paths: Optional[list[Path]] = None
) -> Optional[Path]:
    """
    Find an executable in the system PATH or provided search paths.

    Args:
        name: Executable name (e.g., 'python', 'gcc')
        search_paths: Optional list of directories to search

    Returns:
        Path to executable if found, None otherwise

    Example:
        >>> find_executable('python')
        PosixPath('/usr/bin/python')
    """
    # Add Windows executable extensions
    extensions = [""] if not IS_WINDOWS else ["", ".exe", ".bat", ".cmd"]

    # Use provided paths or system PATH
    if search_paths is None:
        path_env = os.environ.get("PATH", "")
        search_paths = [Path(p) for p in path_env.split(os.pathsep) if p]

    for directory in search_paths:
        for ext in extensions:
            exe_path = directory / f"{name}{ext}"
            if exe_path.is_file() and os.access(exe_path, os.X_OK):
                return exe_path

    return None


# ============================================================================
# Windows-Specific Link Functions
# ============================================================================

if sys.platform == "win32":
    # Windows API constants
    SYMBOLIC_LINK_FLAG_DIRECTORY = 0x1
    SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE = 0x2

    # Load Windows API functions
    CreateSymbolicLinkW = ctypes.windll.kernel32.CreateSymbolicLinkW  # type: ignore
    CreateSymbolicLinkW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    CreateSymbolicLinkW.restype = wintypes.BOOLEAN

    def _has_symlink_privilege() -> bool:
        """Check if current process has privilege to create symlinks."""
        # Try to create a test symlink
        temp_dir = Path(tempfile.gettempdir())
        test_target = temp_dir / f"test_symlink_target_{os.getpid()}"
        test_link = temp_dir / f"test_symlink_{os.getpid()}"

        try:
            test_target.mkdir(exist_ok=True)
            os.symlink(test_target, test_link, target_is_directory=True)
            test_link.unlink()
            test_target.rmdir()
            return True
        except (OSError, PermissionError):
            return False
        finally:
            # Cleanup
            try:
                if test_link.exists():
                    test_link.unlink()
                if test_target.exists():
                    test_target.rmdir()
            except (OSError, PermissionError):
                pass

    def _create_junction_windows(source: Path, target: Path) -> None:
        """
        Create a Windows junction point.

        Junction points are directory symbolic links that don't require
        administrator privileges on Windows.

        Args:
            source: Directory that will be linked to
            target: Location of the junction point

        Raises:
            LinkCreationError: If junction creation fails
        """
        if not source.is_dir():
            raise LinkCreationError(f"Junction source must be a directory: {source}")

        if target.exists():
            raise LinkCreationError(f"Junction target already exists: {target}")

        # Ensure source is absolute
        source = source.resolve()
        target = target.resolve()

        # Try using mklink command as it's more reliable for junctions
        import subprocess

        try:
            # Use mklink /J for junction (doesn't require admin)
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Fall back to Windows API
                flags = (
                    SYMBOLIC_LINK_FLAG_DIRECTORY
                    | SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE
                )

                api_result = CreateSymbolicLinkW(str(target), str(source), flags)

                if not api_result:
                    error_code = ctypes.get_last_error()  # type: ignore
                    raise LinkCreationError(
                        f"Failed to create junction from {target} to {source}. "
                        f"Windows error code: {error_code}. "
                        f"mklink output: {result.stderr}"
                    )

        except Exception as e:
            if isinstance(e, LinkCreationError):
                raise
            raise LinkCreationError(f"Failed to create junction: {e}")

    def _create_symlink_windows(source: Path, target: Path) -> None:
        """
        Create a Windows symbolic link (requires admin privileges).

        Args:
            source: File or directory to link to
            target: Location of the symbolic link

        Raises:
            LinkCreationError: If symlink creation fails
            PermissionError: If admin privileges are required but not available
        """
        if target.exists():
            raise LinkCreationError(f"Symlink target already exists: {target}")

        try:
            is_directory = source.is_dir()
            os.symlink(source, target, target_is_directory=is_directory)
        except OSError as e:
            if (
                hasattr(e, "winerror") and e.winerror == 1314
            ):  # ERROR_PRIVILEGE_NOT_HELD
                raise PermissionError(
                    "Creating symlinks requires administrator privileges on Windows. "
                    "Consider using junction points instead (LinkType='junction')."
                )
            raise LinkCreationError(f"Failed to create symlink: {e}")


def _detect_best_link_type() -> LinkType:
    """
    Detect the best link type for the current platform.

    Returns:
        'junction' on Windows (no admin needed)
        'symlink' on Unix-like systems
    """
    if IS_WINDOWS:
        # Prefer junctions as they don't require admin rights
        return "junction"
    else:
        return "symlink"


# ============================================================================
# Link Creation (Cross-Platform)
# ============================================================================


def create_link(
    source: Union[str, Path],
    target: Union[str, Path],
    link_type: LinkType = "auto",
    allow_fallback: bool = True,
) -> None:
    """
    Create a symbolic link or junction point.

    This function abstracts over platform differences in link creation:
    - On Windows: Creates junction points (preferred) or symlinks
    - On Unix: Creates standard symbolic links
    - Fallback: Stores link reference in registry file

    Args:
        source: Path to the actual directory/file (link target)
        target: Path where the link should be created
        link_type: Type of link to create ('auto', 'symlink', 'junction', 'reference')
        allow_fallback: If True, fall back to reference tracking on failure

    Raises:
        LinkCreationError: If link creation fails and no fallback allowed
        ValueError: If unsupported link_type is specified

    Example:
        >>> create_link('/path/to/toolchain', '.toolchainkit/toolchains/llvm-15')
        # Creates appropriate link type for platform
    """
    source = Path(source).resolve()
    target = Path(target)

    # Auto-detect best link type
    if link_type == "auto":
        link_type = _detect_best_link_type()

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing link/file at target
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            target.unlink()
        elif target.is_file():
            target.unlink()
        elif target.is_dir():
            # Don't automatically delete directories
            raise LinkCreationError(
                f"Target path exists as a directory: {target}. "
                "Please remove it manually if you want to create a link."
            )

    try:
        if sys.platform == "win32":
            if link_type == "junction":
                _create_junction_windows(source, target)
            elif link_type == "symlink":
                _create_symlink_windows(source, target)
            elif link_type == "reference":
                _create_reference_tracking(source, target)
            else:
                raise ValueError(f"Unsupported link type for Windows: {link_type}")
        else:
            # Unix-like systems
            if link_type in ("symlink", "junction"):  # junction maps to symlink on Unix
                os.symlink(source, target)
            elif link_type == "reference":
                _create_reference_tracking(source, target)
            else:
                raise ValueError(f"Unsupported link type for Unix: {link_type}")

    except (LinkCreationError, PermissionError):
        if allow_fallback and link_type != "reference":
            # Fall back to reference tracking
            _create_reference_tracking(source, target)
        else:
            raise


def _create_reference_tracking(source: Path, target: Path) -> None:
    """
    Create a reference tracking entry when native links aren't available.

    Stores a JSON file mapping the target path to the source path.
    This is a fallback mechanism when symlinks/junctions cannot be created.

    Args:
        source: Actual path
        target: Link path
    """
    # Create a marker file indicating this is a reference
    registry_file = target.with_suffix(".link_reference")

    reference_data = {
        "source": str(source.resolve()),
        "target": str(target.resolve()),
        "type": "reference",
        "created": str(Path(__file__).stat().st_mtime),
    }

    # Ensure parent exists
    registry_file.parent.mkdir(parents=True, exist_ok=True)

    with open(registry_file, "w") as f:
        json.dump(reference_data, f, indent=2)


# ============================================================================
# Archive Extraction
# ============================================================================


def _validate_archive_path(path: str, destination: Path) -> None:
    """
    Validate that an archive member path is safe to extract.

    Prevents directory traversal attacks (e.g., paths containing '../').

    Args:
        path: Member path from archive
        destination: Extraction destination

    Raises:
        InsecureArchiveError: If path attempts directory traversal
    """
    # Normalize the path
    member_path = destination / path
    member_path = member_path.resolve()

    # Ensure it's under destination
    if not is_relative_to(member_path, destination.resolve()):
        raise InsecureArchiveError(
            f"Archive member '{path}' attempts directory traversal. "
            "This is a security risk and extraction has been blocked."
        )


def extract_archive(
    archive_path: Union[str, Path],
    destination: Union[str, Path],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Extract an archive to a destination directory.

    Automatically detects archive format and extracts safely.
    Validates all paths to prevent directory traversal attacks.

    Supported formats:
    - .zip
    - .tar.gz, .tgz
    - .tar.xz
    - .tar.bz2
    - .7z (if py7zr is installed)

    Args:
        archive_path: Path to the archive file
        destination: Directory to extract to
        progress_callback: Optional callback(current, total) for progress

    Raises:
        UnsupportedArchiveFormat: If archive format is not recognized
        ArchiveExtractionError: If extraction fails
        InsecureArchiveError: If archive contains malicious paths

    Example:
        >>> extract_archive('toolchain.tar.gz', '/tmp/toolchain')
        >>> extract_archive('package.zip', '.', lambda c, t: print(f"{c}/{t}"))
    """
    archive_path = Path(archive_path)
    destination = Path(destination)

    if not archive_path.exists():
        raise ArchiveExtractionError(f"Archive not found: {archive_path}")

    # Create destination directory
    destination.mkdir(parents=True, exist_ok=True)

    # Detect format and extract
    archive_name = archive_path.name.lower()

    try:
        if archive_name.endswith(".zip"):
            _extract_zip(archive_path, destination, progress_callback)
        elif archive_name.endswith((".tar.gz", ".tgz")):
            _extract_tar_gz(archive_path, destination, progress_callback)
        elif archive_name.endswith(".tar.xz"):
            _extract_tar_xz(archive_path, destination, progress_callback)
        elif archive_name.endswith((".tar.bz2", ".tbz2")):
            _extract_tar_bz2(archive_path, destination, progress_callback)
        elif archive_name.endswith(".7z"):
            _extract_7z(archive_path, destination, progress_callback)
        elif archive_name.endswith(".exe"):
            _extract_exe_installer(archive_path, destination, progress_callback)
        else:
            raise UnsupportedArchiveFormat(
                f"Unsupported archive format: {archive_path.suffix}. "
                "Supported: .zip, .tar.gz, .tar.xz, .tar.bz2, .7z, .exe"
            )
    except (InsecureArchiveError, UnsupportedArchiveFormat):
        raise
    except Exception as e:
        raise ArchiveExtractionError(f"Failed to extract {archive_path}: {e}")


def _extract_zip(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a ZIP archive."""
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = zf.namelist()
        total = len(members)

        # Validate all paths first
        for member in members:
            _validate_archive_path(member, destination)

        # Extract
        for i, member in enumerate(members):
            zf.extract(member, destination)
            if progress_callback:
                progress_callback(i + 1, total)


def _extract_tar_gz(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a .tar.gz archive."""
    _extract_tar(archive_path, destination, "r:gz", progress_callback)


def _extract_tar_xz(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a .tar.xz archive."""
    _extract_tar(archive_path, destination, "r:xz", progress_callback)


def _extract_tar_bz2(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a .tar.bz2 archive."""
    _extract_tar(archive_path, destination, "r:bz2", progress_callback)


def _extract_tar(
    archive_path: Path,
    destination: Path,
    mode: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a tar archive with specified compression."""
    with tarfile.open(archive_path, mode) as tar:
        members = tar.getmembers()
        total = len(members)

        # Validate all paths first
        for member in members:
            _validate_archive_path(member.name, destination)

        # Extract with filter for security (Python 3.12+)
        # For older Python, we've already validated paths above
        if sys.version_info >= (3, 12):
            tar.extractall(destination, filter="data")
        else:
            tar.extractall(destination)

        if progress_callback:
            progress_callback(total, total)


def _extract_exe_installer(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a Windows .exe installer using 7zip."""
    import subprocess
    import shutil

    # Try to find 7zip
    seven_zip = shutil.which("7z") or shutil.which("7za")

    if not seven_zip:
        # Try common installation paths
        common_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                seven_zip = path
                break

    if not seven_zip:
        raise UnsupportedArchiveFormat(
            "Extracting .exe installers requires 7-Zip. "
            "Install from: https://www.7-zip.org/ or use: winget install 7zip.7zip"
        )

    try:
        # Extract using 7zip
        cmd = [seven_zip, "x", str(archive_path), f"-o{destination}", "-y"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        if progress_callback:
            # Report completion
            progress_callback(1, 1)

    except subprocess.CalledProcessError as e:
        raise ArchiveExtractionError(f"7-Zip extraction failed: {e.stderr}")
    except Exception as e:
        raise ArchiveExtractionError(f"Failed to extract .exe installer: {e}")


def _extract_7z(
    archive_path: Path,
    destination: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Extract a .7z archive (requires py7zr)."""
    try:
        import py7zr
    except ImportError:
        raise UnsupportedArchiveFormat(
            "7z extraction requires 'py7zr' package. "
            "Install it with: pip install py7zr"
        )

    with py7zr.SevenZipFile(archive_path, "r") as archive:
        members = archive.getnames()
        total = len(members)

        # Validate all paths first
        for member in members:
            _validate_archive_path(member, destination)

        # Extract
        archive.extractall(destination)

        if progress_callback:
            progress_callback(total, total)


# ============================================================================
# Safe File Operations
# ============================================================================


def atomic_write(
    file_path: Union[str, Path], content: Union[str, bytes], encoding: str = "utf-8"
) -> None:
    """
    Write file atomically using temp file + rename.

    This ensures the file is never in a partially-written state.
    If the write fails, the original file (if any) remains unchanged.

    Args:
        file_path: Path to write to
        content: Content to write (string or bytes)
        encoding: Text encoding (used only for string content)

    Example:
        >>> atomic_write('config.json', '{"key": "value"}')
        >>> atomic_write('binary.dat', b'\\x00\\x01\\x02')
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (ensures same filesystem)
    temp_fd, temp_path_str = tempfile.mkstemp(
        dir=file_path.parent, prefix=f".{file_path.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_path_str)

    try:
        # Write content to temp file
        if isinstance(content, str):
            with open(temp_fd, "w", encoding=encoding) as f:
                f.write(content)
        else:
            with open(temp_fd, "wb") as f:
                f.write(content)

        # Atomic rename (replaces destination if it exists)
        temp_path.replace(file_path)

    except Exception:
        # Cleanup temp file on failure
        try:
            temp_path.unlink(missing_ok=True)
        except (OSError, PermissionError):
            pass
        raise


def safe_rmtree(
    path: Union[str, Path], require_prefix: Optional[Union[str, Path]] = None
) -> None:
    """
    Safely remove a directory tree with safeguards.

    Args:
        path: Directory to remove
        require_prefix: If specified, path must be under this directory

    Raises:
        ValueError: If path is not under require_prefix
        FilesystemError: If deletion fails

    Example:
        >>> safe_rmtree('/tmp/build', require_prefix='/tmp')
        >>> safe_rmtree('~/.cache/myapp')  # OK
        >>> safe_rmtree('/usr/bin', require_prefix='/home')  # ValueError
    """
    path = Path(path).resolve()

    # Safety check: require path to be under specified prefix
    if require_prefix is not None:
        require_prefix = Path(require_prefix).resolve()
        if not is_relative_to(path, require_prefix):
            raise ValueError(
                f"Refusing to delete '{path}': not under required prefix '{require_prefix}'"
            )

    if not path.exists():
        return  # Already gone, nothing to do

    if not path.is_dir():
        raise FilesystemError(f"Path is not a directory: {path}")

    try:
        # Handle read-only files on Windows
        if IS_WINDOWS:

            def handle_remove_readonly(func, path, exc):
                """Error handler for Windows read-only files."""
                if not os.access(path, os.W_OK):
                    os.chmod(path, 0o777)
                    func(path)
                else:
                    raise

            shutil.rmtree(path, onerror=handle_remove_readonly)
        else:
            shutil.rmtree(path)

    except Exception as e:
        raise FilesystemError(f"Failed to remove directory '{path}': {e}")


def recursive_copy(
    source: Union[str, Path],
    destination: Union[str, Path],
    progress_callback: Optional[Callable[[Path], None]] = None,
    symlinks: bool = False,
) -> None:
    """
    Recursively copy a directory tree.

    Args:
        source: Source directory
        destination: Destination directory
        progress_callback: Optional callback called for each file
        symlinks: If True, copy symlinks as symlinks (default: follow symlinks)

    Example:
        >>> recursive_copy('/source', '/dest', lambda p: print(f"Copied {p}"))
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        raise FilesystemError(f"Source does not exist: {source}")

    if not source.is_dir():
        raise FilesystemError(f"Source is not a directory: {source}")

    destination.mkdir(parents=True, exist_ok=True)

    for item in source.rglob("*"):
        # Calculate relative path
        rel_path = item.relative_to(source)
        dest_item = destination / rel_path

        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
        elif item.is_symlink() and symlinks:
            # Copy symlink as symlink
            link_target = item.readlink()
            if dest_item.exists() or dest_item.is_symlink():
                dest_item.unlink()
            os.symlink(link_target, dest_item)
        else:
            # Copy file
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_item)  # copy2 preserves metadata

        if progress_callback:
            progress_callback(item)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists (idempotent).

    Args:
        path: Directory path

    Returns:
        Path object (resolved)

    Example:
        >>> ensure_directory('/tmp/my_app/cache')
        PosixPath('/tmp/my_app/cache')
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def is_empty_directory(path: Union[str, Path]) -> bool:
    """
    Check if a directory is empty.

    Args:
        path: Directory path

    Returns:
        True if directory exists and is empty

    Example:
        >>> is_empty_directory('/tmp/empty')
        True
    """
    path = Path(path)

    if not path.exists():
        return False

    if not path.is_dir():
        return False

    return not any(path.iterdir())


def directory_size(path: Union[str, Path]) -> int:
    """
    Calculate total size of a directory in bytes.

    Args:
        path: Directory path

    Returns:
        Total size in bytes

    Example:
        >>> size = directory_size('/tmp/mydir')
        >>> print(f"Directory is {size / 1024 / 1024:.2f} MB")
    """
    path = Path(path)
    total_size = 0

    for item in path.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    return total_size


# ============================================================================
# File Hashing
# ============================================================================


def compute_file_hash(
    file_path: Union[str, Path], algorithm: str = "sha256", chunk_size: int = 8192
) -> str:
    """
    Compute hash of a file.

    Memory-efficient implementation that reads file in chunks.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('sha256', 'sha1', 'md5')
        chunk_size: Number of bytes to read at once

    Returns:
        Hex digest of the hash

    Example:
        >>> compute_file_hash('download.tar.gz')
        'a3d5f6e8...'
        >>> compute_file_hash('file.zip', 'md5')
        '5d41402a...'
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FilesystemError(f"File not found: {file_path}")

    # Create hash object
    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    # Read and hash in chunks
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


# ============================================================================
# Temporary File/Directory Management
# ============================================================================


@contextmanager
def temporary_directory(prefix: str = "toolchainkit_", cleanup: bool = True):
    """
    Context manager for temporary directory with automatic cleanup.

    Args:
        prefix: Prefix for temp directory name
        cleanup: If True, remove directory on exit

    Yields:
        Path to temporary directory

    Example:
        >>> with temporary_directory() as tmp:
        ...     (tmp / 'file.txt').write_text('test')
        ...     # Directory is automatically cleaned up
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))

    try:
        yield temp_dir
    finally:
        if cleanup and temp_dir.exists():
            safe_rmtree(temp_dir)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Exceptions
    "FilesystemError",
    "LinkCreationError",
    "ArchiveExtractionError",
    "UnsupportedArchiveFormat",
    "InsecureArchiveError",
    # Path utilities
    "normalize_path",
    "make_long_path_safe",
    "is_relative_to",
    "resolve_link",
    "find_executable",
    # Link creation
    "create_link",
    "LinkType",
    # Archive extraction
    "extract_archive",
    # Safe file operations
    "atomic_write",
    "safe_rmtree",
    "recursive_copy",
    "ensure_directory",
    "is_empty_directory",
    "directory_size",
    # Hashing
    "compute_file_hash",
    # Temporary files
    "temporary_directory",
]
