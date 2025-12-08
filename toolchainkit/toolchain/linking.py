"""
toolchainkit/toolchain/linking.py

Symlink and junction management for toolchain references.

This module provides cross-platform filesystem linking functionality to create
efficient references from project directories to the shared toolchain cache.
Uses symlinks on Unix-like systems and directory junctions on Windows.
"""

import os
from pathlib import Path
from typing import Optional, List
from enum import Enum
import logging

from ..core.platform import detect_platform

logger = logging.getLogger(__name__)


class LinkType(Enum):
    """Types of filesystem links."""

    SYMLINK = "symlink"  # Symbolic link (Unix)
    JUNCTION = "junction"  # Directory junction (Windows)
    HARDLINK = "hardlink"  # Hard link
    COPY = "copy"  # Fallback: actual copy


class ToolchainLinkManager:
    """Manages symlinks/junctions to shared toolchain cache."""

    def __init__(self, platform=None):
        """
        Initialize link manager.

        Args:
            platform: PlatformInfo instance (auto-detected if None)
        """
        self.platform = platform or detect_platform()
        self._use_junctions = self.platform.os == "windows"

    def create_link(
        self, link_path: Path, target_path: Path, force: bool = False
    ) -> bool:
        """
        Create symlink (Unix) or junction (Windows).

        Args:
            link_path: Path where link should be created
            target_path: Path that link should point to
            force: Remove existing link/file if present

        Returns:
            True if link created successfully

        Raises:
            FileNotFoundError: If target doesn't exist
            FileExistsError: If link_path exists and force=False
            PermissionError: If insufficient permissions
            OSError: If link creation fails
        """
        # Convert to absolute paths
        link_path = link_path.absolute()
        target_path = target_path.resolve()

        # Check if target exists
        if not target_path.exists():
            raise FileNotFoundError(f"Target does not exist: {target_path}")

        # Handle existing link/file
        # Check for existing link (including junctions which may have missing targets)
        if link_path.exists() or link_path.is_symlink() or self._is_junction(link_path):
            if force:
                self.remove_link(link_path)
            else:
                raise FileExistsError(f"Link path already exists: {link_path}")

        # Create parent directory if needed
        link_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self._use_junctions:
                return self._create_junction(link_path, target_path)
            else:
                return self._create_symlink(link_path, target_path)
        except Exception as e:
            logger.error(f"Failed to create link {link_path} -> {target_path}: {e}")
            raise

    def _create_symlink(self, link_path: Path, target_path: Path) -> bool:
        """Create symbolic link (Unix)."""
        try:
            os.symlink(target_path, link_path, target_is_directory=target_path.is_dir())
            logger.info(f"Created symlink: {link_path} -> {target_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to create symlink: {e}")
            raise

    def _create_junction(self, link_path: Path, target_path: Path) -> bool:
        """Create directory junction (Windows)."""
        if not self._use_junctions:
            raise RuntimeError("Junctions are only supported on Windows")

        # Try using _winapi (Python 3.8+)
        try:
            if hasattr(os, "_winapi") and hasattr(os._winapi, "CreateJunction"):
                import _winapi

                _winapi.CreateJunction(str(target_path), str(link_path))  # type: ignore
                logger.info(f"Created junction: {link_path} -> {target_path}")
                return True
        except Exception as e:
            logger.debug(f"_winapi.CreateJunction failed: {e}, trying mklink")

        # Fall back to mklink command
        try:
            import subprocess

            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Created junction: {link_path} -> {target_path}")
                return True
            else:
                logger.error(f"mklink failed: {result.stderr}")
                raise OSError(f"Failed to create junction: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to create junction: {e}")
            raise

    def resolve_link(self, link_path: Path) -> Optional[Path]:
        """
        Resolve link to absolute target path.

        Args:
            link_path: Path to link

        Returns:
            Absolute path to link target, or None if not a link
        """
        if not link_path.exists() and not link_path.is_symlink():
            return None

        try:
            # For symlinks, use readlink
            if link_path.is_symlink():
                target_str = os.readlink(link_path)
                # Convert to absolute path if relative
                if not Path(target_str).is_absolute():
                    target = str((link_path.parent / target_str).resolve())
                else:
                    target = target_str
                return Path(target)

            # For junctions on Windows, check if it's a junction
            if self._use_junctions and self._is_junction(link_path):
                try:
                    target = os.readlink(link_path)
                    # Normalize Windows UNC paths (//? prefix)
                    target_path = Path(target)
                    # Remove UNC prefix if present
                    target_str = str(target_path)
                    if target_str.startswith("//?/"):
                        target_str = target_str[4:]
                    elif target_str.startswith("\\\\?\\"):
                        target_str = target_str[4:]
                    return Path(target_str)
                except Exception:
                    pass

            return None
        except Exception as e:
            logger.debug(f"Failed to resolve link {link_path}: {e}")
            return None

    def is_valid_link(self, link_path: Path) -> bool:
        """
        Check if link exists and points to valid target.

        Args:
            link_path: Path to check

        Returns:
            True if link is valid and target exists
        """
        if not (link_path.is_symlink() or self._is_junction(link_path)):
            return False

        target = self.resolve_link(link_path)
        return target is not None and target.exists()

    def is_broken_link(self, link_path: Path) -> bool:
        """
        Check if link is broken (target doesn't exist).

        Args:
            link_path: Path to check

        Returns:
            True if link is broken
        """
        if not (link_path.is_symlink() or self._is_junction(link_path)):
            return False

        target = self.resolve_link(link_path)
        return target is None or not target.exists()

    def remove_link(self, link_path: Path) -> bool:
        """
        Remove symlink/junction.

        Args:
            link_path: Path to link to remove

        Returns:
            True if removed successfully
        """
        # Check if it's a link (including junctions which may be broken)
        if (
            not link_path.exists()
            and not link_path.is_symlink()
            and not self._is_junction(link_path)
        ):
            return False

        try:
            if self._use_junctions and self._is_junction(link_path):
                # On Windows, remove junction with rmdir (not unlink!)
                os.rmdir(link_path)
            elif link_path.is_dir() and not link_path.is_symlink():
                # On Windows, if it's a regular directory (not junction/symlink)
                # Use rmdir
                os.rmdir(link_path)
            else:
                # Remove symlink
                link_path.unlink()

            logger.info(f"Removed link: {link_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove link {link_path}: {e}")
            raise

    def find_links(self, directory: Path) -> List[Path]:
        """
        Find all symlinks/junctions in directory tree.

        Args:
            directory: Directory to search

        Returns:
            List of paths that are symlinks/junctions
        """
        links = []

        try:
            # Use os.walk to avoid traversing into broken junctions/symlinks
            for root, dirs, files in os.walk(directory, followlinks=False):
                root_path = Path(root)

                # Check directories (junctions are directories)
                for d in dirs:
                    path = root_path / d
                    if path.is_symlink() or self._is_junction(path):
                        links.append(path)

                # Check files (symlinks can be files)
                for f in files:
                    path = root_path / f
                    if path.is_symlink():
                        links.append(path)

        except Exception as e:
            logger.error(f"Error searching for links: {e}")

        return links

    def find_broken_links(self, directory: Path) -> List[Path]:
        """
        Find all broken symlinks/junctions in directory tree.

        Args:
            directory: Directory to search

        Returns:
            List of broken links
        """
        broken = []

        for link in self.find_links(directory):
            if self.is_broken_link(link):
                broken.append(link)

        return broken

    def cleanup_broken_links(self, directory: Path, dry_run: bool = False) -> int:
        """
        Remove all broken links in directory tree.

        Args:
            directory: Directory to clean
            dry_run: If True, only report what would be removed

        Returns:
            Number of links removed (or would be removed in dry-run)
        """
        broken = self.find_broken_links(directory)

        if dry_run:
            logger.info(f"Would remove {len(broken)} broken links")
            for link in broken:
                logger.info(f"  {link}")
            return len(broken)

        removed = 0
        for link in broken:
            try:
                if self.remove_link(link):
                    removed += 1
            except Exception as e:
                logger.error(f"Failed to remove broken link {link}: {e}")

        logger.info(f"Removed {removed} broken links")
        return removed

    def _is_junction(self, path: Path) -> bool:
        """
        Check if path is a Windows directory junction.

        Args:
            path: Path to check

        Returns:
            True if path is a junction
        """
        if not self._use_junctions:
            return False

        try:
            # On Windows, junctions have reparse point attribute
            # Attribute 0x400 = FILE_ATTRIBUTE_REPARSE_POINT

            # First try to check if it's a directory-like entry
            # Use stat without follow_symlinks to detect junctions even if target is missing
            try:
                st = os.stat(path, follow_symlinks=False)
            except FileNotFoundError:
                return False

            # Check if it has reparse point attribute
            if hasattr(st, "st_file_attributes"):
                return bool(st.st_file_attributes & 0x400)  # type: ignore

            # Fallback: try to read as symlink
            try:
                os.readlink(path)
                return True
            except OSError:
                return False

        except Exception as e:
            logger.debug(f"Error checking junction {path}: {e}")
            return False

    def link_toolchain_to_project(
        self, toolchain_path: Path, project_dir: Path, link_name: str = ".toolchain"
    ) -> Path:
        """
        Create a link from project to toolchain in cache.

        Args:
            toolchain_path: Path to toolchain in cache
            project_dir: Project directory
            link_name: Name for the link (default: .toolchain)

        Returns:
            Path to created link

        Raises:
            FileNotFoundError: If toolchain_path doesn't exist
            OSError: If link creation fails
        """
        link_path = project_dir / link_name

        # Create link
        self.create_link(link_path, toolchain_path, force=True)

        logger.info(f"Linked toolchain to project: {link_path}")
        return link_path


# Example usage
def example_usage():
    """Example: Create and manage toolchain links."""
    from ..core.platform import detect_platform

    platform = detect_platform()
    link_mgr = ToolchainLinkManager(platform)

    # Paths
    toolchain_cache = Path.home() / ".toolchainkit" / "toolchains" / "llvm-17.0.6"
    project_dir = Path.cwd()

    # Create link from project to toolchain
    link_path = link_mgr.link_toolchain_to_project(toolchain_cache, project_dir)

    # Verify link
    if link_mgr.is_valid_link(link_path):
        target = link_mgr.resolve_link(link_path)
        print(f"✓ Link valid: {link_path} -> {target}")
    else:
        print(f"✗ Link broken: {link_path}")

    # Find all links in project
    links = link_mgr.find_links(project_dir)
    print(f"\nFound {len(links)} links in project:")
    for link in links:
        target = link_mgr.resolve_link(link)
        status = "✓" if link_mgr.is_valid_link(link) else "✗"
        print(f"  {status} {link} -> {target}")

    # Cleanup broken links
    removed = link_mgr.cleanup_broken_links(project_dir, dry_run=True)
    print(f"\nWould remove {removed} broken links")


if __name__ == "__main__":
    example_usage()
