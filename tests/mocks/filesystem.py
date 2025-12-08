"""
Mock filesystem operations for testing.

This module provides a MockFilesystem class that simulates filesystem
operations in memory without touching the actual disk, enabling fast
and isolated testing of file operations.
"""

from pathlib import Path
from typing import Dict, Set


class MockFilesystem:
    """Mock filesystem for testing without touching disk."""

    def __init__(self):
        """Initialize empty mock filesystem."""
        self.files: Dict[Path, bytes] = {}
        self.dirs: Set[Path] = {Path(".")}  # Root always exists

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False):
        """
        Mock directory creation.

        Args:
            path: Directory path to create
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory exists

        Raises:
            FileExistsError: If directory exists and exist_ok=False
            FileNotFoundError: If parent doesn't exist and parents=False
        """
        if path in self.dirs:
            if not exist_ok:
                raise FileExistsError(f"Directory exists: {path}")
            return

        if not parents and path.parent not in self.dirs and path.parent != Path("."):
            raise FileNotFoundError(f"Parent directory not found: {path.parent}")

        if parents:
            # Create all parent directories
            current = path
            to_create = []
            while current != Path(".") and current not in self.dirs:
                to_create.append(current)
                current = current.parent

            for dir_path in reversed(to_create):
                self.dirs.add(dir_path)
        else:
            self.dirs.add(path)

    def write_text(self, path: Path, content: str, encoding: str = "utf-8"):
        """
        Mock file writing.

        Args:
            path: File path to write to
            content: Text content to write
            encoding: Character encoding (default: utf-8)

        Raises:
            FileNotFoundError: If parent directory doesn't exist
        """
        if path.parent not in self.dirs and path.parent != Path("."):
            raise FileNotFoundError(f"Parent directory not found: {path.parent}")

        self.files[path] = content.encode(encoding)

    def write_bytes(self, path: Path, content: bytes):
        """
        Mock binary file writing.

        Args:
            path: File path to write to
            content: Binary content to write

        Raises:
            FileNotFoundError: If parent directory doesn't exist
        """
        if path.parent not in self.dirs and path.parent != Path("."):
            raise FileNotFoundError(f"Parent directory not found: {path.parent}")

        self.files[path] = content

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        """
        Mock file reading.

        Args:
            path: File path to read from
            encoding: Character encoding (default: utf-8)

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")

        return self.files[path].decode(encoding)

    def read_bytes(self, path: Path) -> bytes:
        """
        Mock binary file reading.

        Args:
            path: File path to read from

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")

        return self.files[path]

    def exists(self, path: Path) -> bool:
        """
        Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists (as file or directory)
        """
        return path in self.files or path in self.dirs

    def is_file(self, path: Path) -> bool:
        """
        Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a file
        """
        return path in self.files

    def is_dir(self, path: Path) -> bool:
        """
        Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path exists and is a directory
        """
        return path in self.dirs

    def unlink(self, path: Path, missing_ok: bool = False):
        """
        Mock file deletion.

        Args:
            path: File path to delete
            missing_ok: If True, don't raise error if file doesn't exist

        Raises:
            FileNotFoundError: If file doesn't exist and missing_ok=False
        """
        if path not in self.files:
            if not missing_ok:
                raise FileNotFoundError(f"File not found: {path}")
            return

        del self.files[path]

    def rmdir(self, path: Path):
        """
        Mock directory deletion.

        Args:
            path: Directory path to delete

        Raises:
            FileNotFoundError: If directory doesn't exist
            OSError: If directory is not empty
        """
        if path not in self.dirs:
            raise FileNotFoundError(f"Directory not found: {path}")

        # Check if directory is empty
        for file_path in self.files:
            if path in file_path.parents or file_path == path:
                raise OSError(f"Directory not empty: {path}")

        for dir_path in self.dirs:
            if dir_path != path and path in dir_path.parents:
                raise OSError(f"Directory not empty: {path}")

        self.dirs.remove(path)

    def listdir(self, path: Path) -> list:
        """
        List directory contents.

        Args:
            path: Directory path to list

        Returns:
            List of names in directory

        Raises:
            FileNotFoundError: If directory doesn't exist
            NotADirectoryError: If path is not a directory
        """
        if not self.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")

        if not self.is_dir(path):
            raise NotADirectoryError(f"Not a directory: {path}")

        contents = []

        # Add immediate child files
        for file_path in self.files:
            if file_path.parent == path:
                contents.append(file_path.name)

        # Add immediate child directories
        for dir_path in self.dirs:
            if dir_path.parent == path:
                contents.append(dir_path.name)

        return contents
