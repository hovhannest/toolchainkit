"""
Network download manager with progress tracking, retry logic, and checksum verification.

This module provides robust downloading capabilities with:
- HTTP/HTTPS downloads with TLS verification
- Resume partial downloads (using Range headers)
- Progress reporting (bytes, percentage, speed, ETA)
- Retry logic with exponential backoff
- Checksum verification during download
- Timeout handling
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Progress information for a download."""

    bytes_downloaded: int
    total_bytes: int
    percentage: float
    speed_bps: float  # bytes per second
    eta_seconds: float  # estimated time remaining

    def __str__(self) -> str:
        """Format progress for display."""
        return format_progress(self)


class DownloadError(Exception):
    """Exception raised when download fails."""

    pass


class ChecksumError(Exception):
    """Exception raised when checksum verification fails."""

    pass


class StreamingHasher:
    """Compute hash incrementally for streaming downloads."""

    def __init__(self, algorithm: str = "sha256"):
        """
        Initialize streaming hasher.

        Args:
            algorithm: Hash algorithm ('sha256', 'sha512', 'md5')

        Raises:
            ValueError: If algorithm is not supported
        """
        self.algorithm = algorithm.lower()

        if self.algorithm == "sha256":
            self.hasher = hashlib.sha256()
        elif self.algorithm == "sha512":
            self.hasher = hashlib.sha512()
        elif self.algorithm == "md5":
            logger.warning("MD5 is cryptographically broken, use SHA256 instead")
            self.hasher = hashlib.md5()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    def update(self, data: bytes):
        """Add data to hash computation."""
        self.hasher.update(data)

    def finalize(self) -> str:
        """Get final hash value as hex string."""
        return self.hasher.hexdigest()

    def verify(self, expected_hash: str) -> bool:
        """
        Check if computed hash matches expected value.

        Args:
            expected_hash: Expected hash value (hex string)

        Returns:
            True if hashes match, False otherwise
        """
        actual = self.finalize()
        return actual.lower() == expected_hash.lower()


def download_file(
    url: str,
    destination: Path,
    expected_sha256: Optional[str] = None,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    resume: bool = True,
    timeout: int = 30,
    max_retries: int = 3,
) -> Path:
    """
    Download file from URL to destination with retry logic and checksum verification.

    Args:
        url: URL to download from
        destination: Local path to save file
        expected_sha256: Expected SHA256 hash (verified during download)
        progress_callback: Optional callback for progress updates
        resume: Whether to resume partial downloads
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        Path to downloaded file

    Raises:
        DownloadError: If download fails after retries
        ChecksumError: If checksum doesn't match expected value
        ValueError: If URL or destination is invalid

    Example:
        >>> from toolchainkit.core.download import download_file
        >>> def on_progress(progress):
        ...     print(f"Downloaded {progress.percentage:.1f}%")
        >>>
        >>> url = "https://example.com/toolchain.tar.gz"
        >>> dest = Path("cache/toolchain.tar.gz")
        >>> expected = "abc123..."
        >>> download_file(url, dest, expected_sha256=expected, progress_callback=on_progress)
    """
    if not url:
        raise ValueError("URL cannot be empty")

    if not destination:
        raise ValueError("Destination path cannot be empty")

    # Ensure destination directory exists
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists with correct hash
    if destination.exists() and expected_sha256:
        logger.info(f"File exists, verifying checksum: {destination}")
        if verify_checksum(destination, expected_sha256):
            logger.info("Checksum verified, skipping download")
            return destination
        else:
            logger.warning("Checksum mismatch, re-downloading")
            destination.unlink()

    # Determine if we can resume
    resume_from = 0
    if resume and destination.exists():
        resume_from = destination.stat().st_size
        logger.info(f"Resuming download from byte {resume_from}")

    # Download with retries
    for attempt in range(max_retries):
        try:
            return _download_with_progress(
                url=url,
                destination=destination,
                resume_from=resume_from,
                expected_sha256=expected_sha256,
                progress_callback=progress_callback,
                timeout=timeout,
            )
        except (Timeout, ConnectionError, RequestException, HTTPError) as e:
            if attempt == max_retries - 1:
                raise DownloadError(
                    f"Download failed after {max_retries} attempts: {e}"
                ) from e

            # Exponential backoff
            backoff_seconds = 2**attempt
            logger.warning(
                f"Download attempt {attempt + 1} failed: {e}. "
                f"Retrying in {backoff_seconds}s..."
            )
            time.sleep(backoff_seconds)

    # Should never reach here, but just in case
    raise DownloadError("Download failed for unknown reason")


def _download_with_progress(
    url: str,
    destination: Path,
    resume_from: int,
    expected_sha256: Optional[str],
    progress_callback: Optional[Callable[[DownloadProgress], None]],
    timeout: int,
) -> Path:
    """
    Perform download with streaming and progress updates.

    This is an internal function called by download_file().

    Args:
        url: URL to download
        destination: Destination file path
        resume_from: Byte offset to resume from (0 for new download)
        expected_sha256: Expected SHA256 hash
        progress_callback: Progress callback function
        timeout: Request timeout in seconds

    Returns:
        Path to downloaded file

    Raises:
        ChecksumError: If checksum doesn't match
        RequestException: If HTTP request fails
    """
    headers = {}
    if resume_from > 0:
        headers["Range"] = f"bytes={resume_from}-"

    logger.info(f"Downloading from {url}")

    # Make request with streaming
    response = requests.get(
        url, headers=headers, stream=True, timeout=timeout, allow_redirects=True
    )
    response.raise_for_status()

    # Get total size
    content_length = response.headers.get("content-length")
    if content_length:
        total_size = int(content_length) + resume_from
    else:
        total_size = 0  # Unknown size

    # Open file for writing
    mode = "ab" if resume_from > 0 else "wb"

    # Initialize hasher
    hasher = StreamingHasher("sha256") if expected_sha256 else None

    # If resuming, need to re-read existing bytes for checksum
    if resume_from > 0 and hasher:
        logger.debug(f"Re-computing hash for first {resume_from} bytes")
        with open(destination, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

    downloaded = resume_from
    start_time = time.time()
    last_progress_time = start_time

    try:
        with open(destination, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if hasher:
                        hasher.update(chunk)

                    # Report progress (max once per 0.5 seconds to avoid spam)
                    current_time = time.time()
                    if progress_callback and (
                        current_time - last_progress_time >= 0.5
                        or downloaded == total_size
                    ):
                        elapsed = current_time - start_time
                        speed = (
                            (downloaded - resume_from) / elapsed if elapsed > 0 else 0
                        )
                        remaining = total_size - downloaded if total_size > 0 else 0
                        eta = remaining / speed if speed > 0 else 0

                        progress = DownloadProgress(
                            bytes_downloaded=downloaded,
                            total_bytes=total_size if total_size > 0 else downloaded,
                            percentage=(downloaded / total_size * 100)
                            if total_size > 0
                            else 0,
                            speed_bps=speed,
                            eta_seconds=eta,
                        )
                        progress_callback(progress)
                        last_progress_time = current_time

    except Exception as e:
        # Clean up partial download on error
        logger.error(f"Error during download: {e}")
        raise

    # Verify checksum
    if expected_sha256 and hasher:
        if not hasher.verify(expected_sha256):
            actual_hash = hasher.finalize()
            # Clean up corrupted file
            destination.unlink()
            raise ChecksumError(
                f"Checksum mismatch for {destination.name}: "
                f"expected {expected_sha256}, got {actual_hash}"
            )
        logger.info("Checksum verified successfully")

    logger.info(f"Download complete: {destination}")
    return destination


def verify_checksum(file_path: Path, expected_sha256: str) -> bool:
    """
    Verify file SHA256 checksum.

    Args:
        file_path: Path to file to verify
        expected_sha256: Expected SHA256 hash (hex string)

    Returns:
        True if checksum matches, False otherwise

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    actual_hash = hasher.hexdigest()
    return actual_hash.lower() == expected_sha256.lower()


def format_progress(progress: DownloadProgress) -> str:
    """
    Format progress for display.

    Args:
        progress: Download progress information

    Returns:
        Formatted progress string

    Example:
        >>> progress = DownloadProgress(52428800, 104857600, 50.0, 1048576, 50)
        >>> print(format_progress(progress))
        50.0/100.0 MB (50.0%) at 1.0 MB/s ETA: 50s
    """
    mb_downloaded = progress.bytes_downloaded / 1024 / 1024
    mb_total = progress.total_bytes / 1024 / 1024
    speed_mbps = progress.speed_bps / 1024 / 1024

    if progress.total_bytes > 0:
        return (
            f"{mb_downloaded:.1f}/{mb_total:.1f} MB "
            f"({progress.percentage:.1f}%) "
            f"at {speed_mbps:.1f} MB/s "
            f"ETA: {progress.eta_seconds:.0f}s"
        )
    else:
        # Unknown total size
        return f"{mb_downloaded:.1f} MB " f"at {speed_mbps:.1f} MB/s"
