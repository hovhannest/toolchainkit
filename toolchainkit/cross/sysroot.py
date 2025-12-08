"""
Sysroot management for cross-compilation.

This module provides tools for downloading, verifying, extracting, and caching
sysroots needed for cross-compilation to various target platforms.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, List
import shutil
from toolchainkit.core.download import download_file
from toolchainkit.core.filesystem import extract_archive


@dataclass
class SysrootSpec:
    """
    Sysroot specification.

    This dataclass represents a complete sysroot specification including download
    URL, version, and cryptographic hash for verification.

    Attributes:
        target: Target platform identifier (e.g., 'android-arm64', 'raspberry-pi-armv7')
        version: Sysroot version string
        url: Download URL for the sysroot archive
        hash: SHA-256 hash for verification
        extract_path: Optional path within archive to extract (for nested archives)
    """

    target: str
    version: str
    url: str
    hash: str
    extract_path: Optional[str] = None


class SysrootManagerError(Exception):
    """Base exception for sysroot management errors."""

    pass


class SysrootDownloadError(SysrootManagerError):
    """Error during sysroot download."""

    pass


class SysrootVerificationError(SysrootManagerError):
    """Error during sysroot verification."""

    pass


class SysrootExtractionError(SysrootManagerError):
    """Error during sysroot extraction."""

    pass


class SysrootManager:
    """
    Manage sysroots for cross-compilation.

    This class provides methods to download, verify, extract, and manage sysroots
    in a centralized cache directory.
    """

    def __init__(self, cache_dir: Path, downloader=None):
        """
        Initialize sysroot manager.

        Args:
            cache_dir: Root cache directory (typically ~/.toolchainkit)
            downloader: Optional downloader instance (uses download_file if None)

        Example:
            >>> from pathlib import Path
            >>> from toolchainkit.core.directory import get_global_cache_dir
            >>> cache_dir = get_global_cache_dir()
            >>> manager = SysrootManager(cache_dir)
        """
        self.cache_dir = cache_dir / "sysroots"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir = self.cache_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.downloader = downloader

    def download_sysroot(
        self,
        spec: SysrootSpec,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        force: bool = False,
    ) -> Path:
        """
        Download and extract sysroot.

        This method downloads a sysroot archive, verifies its integrity,
        extracts it to the cache directory, and returns the path to the
        extracted sysroot.

        Args:
            spec: Sysroot specification
            progress_callback: Optional callback for progress reporting (current, total)
            force: Force re-download even if sysroot exists

        Returns:
            Path to extracted sysroot directory

        Raises:
            SysrootDownloadError: If download fails
            SysrootVerificationError: If hash verification fails
            SysrootExtractionError: If extraction fails

        Example:
            >>> spec = SysrootSpec(
            ...     target='raspberry-pi-armv7',
            ...     version='11',
            ...     url='https://example.com/rpi-sysroot.tar.gz',
            ...     hash='abc123...'
            ... )
            >>> sysroot_path = manager.download_sysroot(spec)
        """
        target_dir = self.cache_dir / f"{spec.target}-{spec.version}"

        # Check if already downloaded
        if target_dir.exists() and not force:
            return target_dir

        # Determine archive filename from URL
        url_path = Path(spec.url)
        archive_name = url_path.name or "sysroot.tar.gz"
        archive_path = self.downloads_dir / archive_name

        try:
            # Download archive
            download_file(
                url=spec.url,
                destination=archive_path,
                expected_sha256=spec.hash,
                progress_callback=lambda p: progress_callback(
                    int(p.bytes_downloaded), int(p.total_bytes)
                )
                if progress_callback
                else None,
            )
        except Exception as e:
            raise SysrootDownloadError(
                f"Failed to download sysroot from {spec.url}: {e}"
            ) from e

        # Extract to temporary directory
        temp_dir = self.cache_dir / f"temp_{spec.target}_{spec.version}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            extract_archive(archive_path=archive_path, destination=temp_dir)
        except Exception as e:
            # Cleanup temp directory on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise SysrootExtractionError(
                f"Failed to extract sysroot archive: {e}"
            ) from e

        try:
            # Move to final location
            if spec.extract_path:
                # Extract specific subdirectory
                source_dir = temp_dir / spec.extract_path
                if not source_dir.exists():
                    raise SysrootExtractionError(
                        f"Extract path not found in archive: {spec.extract_path}"
                    )
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.move(str(source_dir), str(target_dir))
            else:
                # Move entire extracted content
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.move(str(temp_dir), str(target_dir))
        except Exception as e:
            # Cleanup on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise SysrootExtractionError(f"Failed to move sysroot to cache: {e}") from e
        finally:
            # Cleanup temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        # Cleanup archive
        if archive_path.exists():
            archive_path.unlink()

        return target_dir

    def get_sysroot_path(self, target: str, version: str) -> Optional[Path]:
        """
        Get path to cached sysroot.

        Args:
            target: Target platform identifier
            version: Sysroot version

        Returns:
            Path to sysroot if it exists in cache, None otherwise

        Example:
            >>> path = manager.get_sysroot_path('android-arm64', '21')
            >>> if path:
            ...     print(f"Sysroot found: {path}")
        """
        path = self.cache_dir / f"{target}-{version}"
        return path if path.exists() else None

    def list_sysroots(self) -> List[str]:
        """
        List all cached sysroots.

        Returns:
            List of sysroot identifiers (target-version)

        Example:
            >>> sysroots = manager.list_sysroots()
            >>> for sysroot in sysroots:
            ...     print(sysroot)
        """
        sysroots = []
        for entry in self.cache_dir.iterdir():
            if entry.is_dir() and entry.name != "downloads":
                sysroots.append(entry.name)
        return sorted(sysroots)

    def remove_sysroot(self, target: str, version: str) -> bool:
        """
        Remove a cached sysroot.

        Args:
            target: Target platform identifier
            version: Sysroot version

        Returns:
            True if sysroot was removed, False if it didn't exist

        Example:
            >>> removed = manager.remove_sysroot('android-arm64', '21')
            >>> if removed:
            ...     print("Sysroot removed")
        """
        path = self.cache_dir / f"{target}-{version}"
        if path.exists():
            shutil.rmtree(path)
            return True
        return False

    def get_cache_size(self) -> int:
        """
        Get total size of cached sysroots in bytes.

        Returns:
            Total size in bytes

        Example:
            >>> size_mb = manager.get_cache_size() / (1024 ** 2)
            >>> print(f"Cache size: {size_mb:.1f} MB")
        """
        total_size = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_dir() and entry.name != "downloads":
                total_size += self._get_dir_size(entry)
        return total_size

    def clear_cache(self) -> int:
        """
        Remove all cached sysroots.

        Returns:
            Number of sysroots removed

        Example:
            >>> count = manager.clear_cache()
            >>> print(f"Removed {count} sysroots")
        """
        count = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_dir() and entry.name != "downloads":
                shutil.rmtree(entry)
                count += 1
        return count

    def _get_dir_size(self, path: Path) -> int:
        """
        Get size of directory and all its contents.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except (OSError, PermissionError):
            # Skip files we can't access
            pass
        return total
