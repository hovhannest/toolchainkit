"""
Toolchain download and extraction system.

This module orchestrates downloading and extracting toolchains from remote sources,
coordinating with the download manager, filesystem utilities, verification system,
and shared cache registry.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from toolchainkit.core.download import download_file, DownloadProgress
from toolchainkit.core.filesystem import extract_archive, safe_rmtree
from toolchainkit.core.cache_registry import ToolchainCacheRegistry as CoreRegistry
from toolchainkit.core.locking import DownloadCoordinator, LockManager
from toolchainkit.core.directory import get_global_cache_dir
from toolchainkit.toolchain.metadata_registry import (
    ToolchainMetadataRegistry,
    ToolchainMetadata,
)

logger = logging.getLogger(__name__)


class ToolchainDownloadError(Exception):
    """Base exception for toolchain download errors."""

    pass


class ToolchainExtractionError(Exception):
    """Exception for toolchain extraction errors."""

    pass


@dataclass
class DownloadResult:
    """Result of toolchain download operation."""

    toolchain_id: str
    """Unique identifier for the toolchain"""

    toolchain_path: Path
    """Path to installed toolchain directory"""

    download_time: float
    """Time spent downloading in seconds"""

    extraction_time: float
    """Time spent extracting in seconds"""

    total_size_bytes: int
    """Total size of extracted toolchain in bytes"""

    was_cached: bool
    """Whether toolchain was already cached (no download needed)"""


@dataclass
class ProgressInfo:
    """Unified progress information for download and extraction."""

    phase: str
    """Current phase: 'downloading', 'extracting', 'complete'"""

    percentage: float
    """Overall progress percentage (0-100)"""

    current_bytes: int
    """Current bytes processed"""

    total_bytes: int
    """Total bytes to process"""

    speed_bps: float
    """Current speed in bytes per second"""

    eta_seconds: Optional[float]
    """Estimated time remaining in seconds"""


class ToolchainDownloader:
    """
    Downloads and extracts toolchains from remote sources.

    This class orchestrates the complete toolchain download workflow:
    1. Lookup metadata from toolchain registry
    2. Check if already cached
    3. Download archive with progress reporting
    4. Verify checksum
    5. Extract to target directory
    6. Register in shared cache
    7. Cleanup temporary files

    Example:
        >>> downloader = ToolchainDownloader()
        >>> result = downloader.download_toolchain(
        ...     toolchain_name="llvm",
        ...     version="18",
        ...     platform="linux-x64",
        ...     progress_callback=lambda p: print(f"{p.percentage:.1f}%")
        ... )
        >>> print(f"Installed at: {result.toolchain_path}")
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        lock_manager: Optional[LockManager] = None,
    ):
        """
        Initialize toolchain downloader.

        Args:
            cache_dir: Optional cache directory. If None, uses global cache.
            lock_manager: Optional lock manager. If None, creates new one.
        """
        self.cache_dir = cache_dir or get_global_cache_dir()
        self.toolchains_dir = self.cache_dir / "toolchains"
        self.downloads_dir = self.cache_dir / "downloads"
        self.lock_manager = lock_manager or LockManager()
        self.coordinator = DownloadCoordinator(self.lock_manager)

        # Create directories if needed
        self.toolchains_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        # Initialize registries
        self.metadata_registry = ToolchainMetadataRegistry()
        self.cache_registry = CoreRegistry(self.cache_dir / "registry.json")

        logger.debug(f"Initialized downloader with cache: {self.cache_dir}")

    def download_toolchain(
        self,
        toolchain_name: str,
        version: str,
        platform: str,
        force: bool = False,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> DownloadResult:
        """
        Download and extract a toolchain.

        Args:
            toolchain_name: Name of toolchain (e.g., "llvm", "gcc")
            version: Version string or pattern (e.g., "18", "18.1.8")
            platform: Platform string (e.g., "linux-x64")
            force: Force re-download even if cached
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with installation details

        Raises:
            ToolchainDownloadError: If download fails
            ToolchainExtractionError: If extraction fails

        Example:
            >>> downloader = ToolchainDownloader()
            >>> result = downloader.download_toolchain("llvm", "18", "linux-x64")
            >>> print(f"Installed at: {result.toolchain_path}")
        """
        # Lookup metadata
        metadata = self.metadata_registry.lookup(toolchain_name, version, platform)
        if not metadata:
            raise ToolchainDownloadError(
                f"Toolchain not found: {toolchain_name} {version} for {platform}\n"
                f"Use ToolchainRegistry.list_versions() to see available versions."
            )

        # Resolve version for toolchain ID
        resolved_version = self.metadata_registry.resolve_version(
            toolchain_name, version
        )
        toolchain_id = f"{toolchain_name}-{resolved_version}-{platform}"
        install_dir = self.toolchains_dir / toolchain_id

        logger.info(f"Downloading toolchain: {toolchain_id}")

        # Check if already cached
        if not force and install_dir.exists():
            logger.info(f"Toolchain already cached: {install_dir}")

            # Calculate size
            total_size = sum(
                f.stat().st_size for f in install_dir.rglob("*") if f.is_file()
            )

            return DownloadResult(
                toolchain_id=toolchain_id,
                toolchain_path=install_dir,
                download_time=0.0,
                extraction_time=0.0,
                total_size_bytes=total_size,
                was_cached=True,
            )

        # Use download coordinator for safe concurrent access
        with self.coordinator.coordinate_download(
            toolchain_id, install_dir
        ) as should_download:
            if not should_download:
                # Another process completed the download
                logger.info(f"Toolchain downloaded by another process: {toolchain_id}")
                total_size = sum(
                    f.stat().st_size for f in install_dir.rglob("*") if f.is_file()
                )
                return DownloadResult(
                    toolchain_id=toolchain_id,
                    toolchain_path=install_dir,
                    download_time=0.0,
                    extraction_time=0.0,
                    total_size_bytes=total_size,
                    was_cached=True,
                )

            # This process won the race - perform download
            return self._download_and_extract(
                toolchain_id, metadata, install_dir, progress_callback
            )

    def _download_and_extract(
        self,
        toolchain_id: str,
        metadata: ToolchainMetadata,
        install_dir: Path,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
    ) -> DownloadResult:
        """
        Perform the actual download and extraction.

        Args:
            toolchain_id: Unique toolchain identifier
            metadata: Toolchain metadata with URL and checksum
            install_dir: Target installation directory
            progress_callback: Optional progress callback

        Returns:
            DownloadResult with timing and size information
        """
        archive_name = metadata.url.split("/")[-1]
        archive_path = self.downloads_dir / archive_name
        temp_extract_dir = self.downloads_dir / f"{toolchain_id}_extract"

        download_time = 0.0
        extraction_time = 0.0

        try:
            # Phase 1: Download
            logger.info(f"Downloading from: {metadata.url}")
            download_start = time.time()

            def download_progress(dp: DownloadProgress):
                """Wrap download progress to report 0-50% of total."""
                if progress_callback:
                    progress_callback(
                        ProgressInfo(
                            phase="downloading",
                            percentage=dp.percentage * 0.5,
                            current_bytes=dp.bytes_downloaded,
                            total_bytes=dp.total_bytes,
                            speed_bps=dp.speed_bps,
                            eta_seconds=dp.eta_seconds,
                        )
                    )

            download_file(
                url=metadata.url,
                destination=archive_path,
                expected_sha256=metadata.sha256,
                progress_callback=download_progress if progress_callback else None,
            )

            download_time = time.time() - download_start
            logger.info(f"Download complete in {download_time:.2f}s")

            # Phase 2: Extract
            logger.info(f"Extracting to: {install_dir}")
            extraction_start = time.time()

            def extraction_progress(current: int, total: int):
                """Wrap extraction progress to report 50-100% of total."""
                if progress_callback:
                    progress_pct = (current / total * 100) if total > 0 else 0
                    progress_callback(
                        ProgressInfo(
                            phase="extracting",
                            percentage=50.0 + (progress_pct * 0.5),
                            current_bytes=current,
                            total_bytes=total,
                            speed_bps=0.0,
                            eta_seconds=None,
                        )
                    )

            # Extract to temporary directory first
            temp_extract_dir.mkdir(parents=True, exist_ok=True)
            extract_archive(
                archive_path=archive_path,
                destination=temp_extract_dir,
                progress_callback=extraction_progress if progress_callback else None,
            )

            # Normalize root directory
            final_root = self._normalize_root_directory(temp_extract_dir)

            # Move to final location
            if install_dir.exists():
                safe_rmtree(install_dir, require_prefix=self.cache_dir)
            final_root.rename(install_dir)

            extraction_time = time.time() - extraction_start
            logger.info(f"Extraction complete in {extraction_time:.2f}s")

            # Calculate total size
            total_size = sum(
                f.stat().st_size for f in install_dir.rglob("*") if f.is_file()
            )

            # Register in cache
            self.cache_registry.register_toolchain(
                toolchain_id=toolchain_id,
                path=install_dir,
                size_mb=total_size / (1024 * 1024),  # Convert bytes to MB
                hash_value=f"sha256:{metadata.sha256}",
                source_url=metadata.url,
                verified=True,
            )

            logger.info(f"Registered toolchain: {toolchain_id}")

            # Report completion
            if progress_callback:
                progress_callback(
                    ProgressInfo(
                        phase="complete",
                        percentage=100.0,
                        current_bytes=total_size,
                        total_bytes=total_size,
                        speed_bps=0.0,
                        eta_seconds=0.0,
                    )
                )

            return DownloadResult(
                toolchain_id=toolchain_id,
                toolchain_path=install_dir,
                download_time=download_time,
                extraction_time=extraction_time,
                total_size_bytes=total_size,
                was_cached=False,
            )

        except Exception as e:
            # Cleanup on error
            logger.error(f"Download/extraction failed: {e}")
            self._cleanup_on_error(archive_path, temp_extract_dir, install_dir)
            raise ToolchainDownloadError(
                f"Failed to download {toolchain_id}: {e}"
            ) from e

        finally:
            # Always cleanup temporary extraction directory
            if temp_extract_dir.exists():
                safe_rmtree(temp_extract_dir, require_prefix=self.downloads_dir)

    def _normalize_root_directory(self, extract_dir: Path) -> Path:
        """
        Normalize extracted directory structure.

        Some archives have a single root folder, others extract directly.
        This function returns the actual toolchain root directory.

        Args:
            extract_dir: Directory where archive was extracted

        Returns:
            Path to toolchain root directory
        """
        items = list(extract_dir.iterdir())

        # If single directory, that's likely the root
        if len(items) == 1 and items[0].is_dir():
            return items[0]

        # Otherwise, the extract_dir itself is the root
        return extract_dir

    def _cleanup_on_error(
        self, archive_path: Path, temp_extract_dir: Path, install_dir: Path
    ):
        """
        Clean up temporary files after error.

        Args:
            archive_path: Downloaded archive file
            temp_extract_dir: Temporary extraction directory
            install_dir: Target installation directory
        """
        logger.info("Cleaning up after error...")

        # Remove archive
        if archive_path.exists():
            try:
                archive_path.unlink()
                logger.debug(f"Removed archive: {archive_path}")
            except Exception as e:
                logger.warning(f"Failed to remove archive: {e}")

        # Remove temporary extraction directory
        if temp_extract_dir.exists():
            try:
                safe_rmtree(temp_extract_dir, require_prefix=self.downloads_dir)
                logger.debug(f"Removed temp extraction: {temp_extract_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temp extraction: {e}")

        # Remove partial installation
        if install_dir.exists():
            try:
                safe_rmtree(install_dir, require_prefix=self.toolchains_dir)
                logger.debug(f"Removed partial installation: {install_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove partial installation: {e}")

    def is_cached(self, toolchain_name: str, version: str, platform: str) -> bool:
        """
        Check if toolchain is already cached.

        Args:
            toolchain_name: Name of toolchain
            version: Version string or pattern
            platform: Platform string

        Returns:
            True if toolchain is cached, False otherwise
        """
        resolved_version = self.metadata_registry.resolve_version(
            toolchain_name, version
        )
        if not resolved_version:
            return False

        toolchain_id = f"{toolchain_name}-{resolved_version}-{platform}"
        install_dir = self.toolchains_dir / toolchain_id

        return install_dir.exists()

    def get_toolchain_path(
        self, toolchain_name: str, version: str, platform: str
    ) -> Optional[Path]:
        """
        Get path to cached toolchain if it exists.

        Args:
            toolchain_name: Name of toolchain
            version: Version string or pattern
            platform: Platform string

        Returns:
            Path to toolchain directory if cached, None otherwise
        """
        resolved_version = self.metadata_registry.resolve_version(
            toolchain_name, version
        )
        if not resolved_version:
            return None

        toolchain_id = f"{toolchain_name}-{resolved_version}-{platform}"
        install_dir = self.toolchains_dir / toolchain_id

        return install_dir if install_dir.exists() else None


# Convenience function for quick downloads
def download_toolchain(
    toolchain_name: str,
    version: str,
    platform: str,
    force: bool = False,
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
) -> DownloadResult:
    """
    Convenience function to download a toolchain.

    Creates a downloader instance and performs the download in one call.
    For multiple downloads, create a ToolchainDownloader instance and reuse it.

    Args:
        toolchain_name: Name of toolchain
        version: Version string or pattern
        platform: Platform string
        force: Force re-download even if cached
        progress_callback: Optional progress callback

    Returns:
        DownloadResult with installation details

    Example:
        >>> from toolchainkit.toolchain.downloader import download_toolchain
        >>> result = download_toolchain("llvm", "18", "linux-x64")
        >>> print(f"Installed at: {result.toolchain_path}")
    """
    downloader = ToolchainDownloader()
    return downloader.download_toolchain(
        toolchain_name, version, platform, force, progress_callback
    )
