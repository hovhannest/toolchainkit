"""
Caching system for link validation results.

Caches both validation results and downloaded files to avoid
redundant network operations.
"""

import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedValidationResult:
    """Cached validation result with metadata."""

    url: str
    validation_level: str  # "head", "partial", "full"
    is_success: bool
    status_code: Optional[int]
    cached_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp
    hash_expected: Optional[str] = None
    hash_actual: Optional[str] = None
    hash_valid: Optional[bool] = None
    cached_file_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > self.expires_at

    @property
    def age_hours(self) -> float:
        """Get age of cache entry in hours."""
        return (time.time() - self.cached_at) / 3600

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedValidationResult":
        """Create from dictionary."""
        return cls(**data)


class CacheManager:
    """
    Manages cache for link validation results.

    Stores validation results and downloaded files with configurable TTL.
    Uses JSON for metadata index (human-readable, easy to debug).

    Example:
        >>> cache = CacheManager(cache_dir=Path("/tmp/cache"))
        >>> cache.store_validation(
        ...     url="https://example.com/file.tar.gz",
        ...     validation_level="head",
        ...     is_success=True,
        ...     status_code=200,
        ...     ttl_hours=24,
        ... )
        >>> result = cache.get_validation("https://example.com/file.tar.gz", "head")
        >>> assert result is not None and not result.is_expired
    """

    def __init__(
        self,
        cache_dir: Path,
        default_ttl_hours: int = 24,
        auto_cleanup: bool = True,
    ):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
            default_ttl_hours: Default time-to-live for cache entries
            auto_cleanup: Automatically clean expired entries on init
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl_hours = default_ttl_hours
        self.auto_cleanup = auto_cleanup
        self._enabled = True  # Cache enabled by default

        # Create cache directories
        self.metadata_dir = self.cache_dir / "metadata"
        self.files_dir = self.cache_dir / "files"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata index
        self.index_file = self.cache_dir / "index.json"
        self.index: Dict[str, CachedValidationResult] = self._load_index()

        if self.auto_cleanup:
            self._cleanup_expired()

    def _load_index(self) -> Dict[str, CachedValidationResult]:
        """Load cache index from disk."""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            index = {}
            for key, entry_data in data.items():
                try:
                    index[key] = CachedValidationResult.from_dict(entry_data)
                except Exception as e:
                    logger.warning(f"Failed to load cache entry {key}: {e}")

            return index

        except Exception as e:
            logger.warning(f"Failed to load cache index: {e}")
            return {}

    def _save_index(self):
        """Save cache index to disk."""
        try:
            data = {key: entry.to_dict() for key, entry in self.index.items()}

            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def _make_cache_key(self, url: str, validation_level: str) -> str:
        """Create cache key from URL and validation level."""
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{url_hash}_{validation_level}"

    def disable(self):
        """
        Disable cache reads - all get operations will return None (cache miss).
        Store operations will still work to populate cache for future runs.

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cache.disable()
            >>> result = cache.get_validation("url", "head")  # Always returns None
            >>> cache.store_validation(...)  # Still writes to cache
        """
        self._enabled = False
        logger.info("Cache reads disabled - will rebuild cache from fresh validations")

    def enable(self):
        """
        Re-enable cache reads after they were disabled.

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cache.disable()
            >>> cache.enable()
        """
        self._enabled = True
        logger.info("Cache reads enabled")

    def is_enabled(self) -> bool:
        """Check if cache reads are currently enabled."""
        return self._enabled

    def get_validation(
        self,
        url: str,
        validation_level: str,
    ) -> Optional[CachedValidationResult]:
        """
        Get cached validation result.

        Args:
            url: URL that was validated
            validation_level: Validation level ("head", "partial", "full")

        Returns:
            CachedValidationResult if cached and not expired, None otherwise

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> result = cache.get_validation("https://example.com/file.tar.gz", "head")
        """
        if not self._enabled:
            return None

        key = self._make_cache_key(url, validation_level)
        entry = self.index.get(key)

        if entry is None:
            return None

        if entry.is_expired:
            logger.debug(f"Cache entry expired: {url} ({validation_level})")
            return None

        logger.debug(
            f"Cache hit: {url} ({validation_level}, age={entry.age_hours:.1f}h)"
        )
        return entry

    def store_validation(
        self,
        url: str,
        validation_level: str,
        is_success: bool,
        status_code: Optional[int] = None,
        ttl_hours: Optional[int] = None,
        hash_expected: Optional[str] = None,
        hash_actual: Optional[str] = None,
        hash_valid: Optional[bool] = None,
        cached_file_path: Optional[Path] = None,
        error_message: Optional[str] = None,
    ):
        """
        Store validation result in cache.

        Note: Store operations always write to cache, even when cache reads are disabled.
        This allows --no-cache runs to populate cache for future runs.

        Args:
            url: URL that was validated
            validation_level: Validation level ("head", "partial", "full")
            is_success: Whether validation succeeded
            status_code: HTTP status code
            ttl_hours: Time-to-live in hours (uses default if None)
            hash_expected: Expected hash (for full validation)
            hash_actual: Actual hash computed
            hash_valid: Whether hash matched
            cached_file_path: Path to cached downloaded file
            error_message: Error message if validation failed

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cache.store_validation(
            ...     url="https://example.com/file.tar.gz",
            ...     validation_level="head",
            ...     is_success=True,
            ...     status_code=200,
            ... )
        """
        ttl_hours = ttl_hours or self.default_ttl_hours

        key = self._make_cache_key(url, validation_level)
        now = time.time()
        expires_at = now + (ttl_hours * 3600)

        entry = CachedValidationResult(
            url=url,
            validation_level=validation_level,
            is_success=is_success,
            status_code=status_code,
            cached_at=now,
            expires_at=expires_at,
            hash_expected=hash_expected,
            hash_actual=hash_actual,
            hash_valid=hash_valid,
            cached_file_path=str(cached_file_path) if cached_file_path else None,
            error_message=error_message,
        )

        self.index[key] = entry
        self._save_index()

        logger.debug(f"Cache stored: {url} ({validation_level}, ttl={ttl_hours}h)")

    def get_cached_file(self, url: str) -> Optional[Path]:
        """
        Get path to cached downloaded file if it exists.

        Args:
            url: URL of the file

        Returns:
            Path to cached file if exists and valid, None otherwise

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cached_file = cache.get_cached_file("https://example.com/file.tar.gz")
        """
        # Check if we have a full validation entry with cached file
        entry = self.get_validation(url, "full")

        if entry and entry.cached_file_path:
            cached_path = Path(entry.cached_file_path)
            if cached_path.exists():
                return cached_path

        return None

    def store_file(self, url: str, source_file: Path) -> Path:
        """
        Store downloaded file in cache.

        Args:
            url: URL the file was downloaded from
            source_file: Path to source file

        Returns:
            Path to cached file

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cached_path = cache.store_file(
            ...     "https://example.com/file.tar.gz",
            ...     Path("downloaded.tar.gz")
            ... )
        """
        import hashlib

        # Create unique filename based on URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        file_ext = Path(source_file).suffix
        cached_path = self.files_dir / f"{url_hash}{file_ext}"

        # Copy file to cache
        shutil.copy2(source_file, cached_path)
        logger.debug(f"File cached: {url} -> {cached_path}")

        return cached_path

    def invalidate(self, url: str, validation_level: Optional[str] = None):
        """
        Invalidate cache entry.

        Args:
            url: URL to invalidate
            validation_level: Specific level to invalidate, or None for all

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cache.invalidate("https://example.com/file.tar.gz", "head")
        """
        if validation_level:
            key = self._make_cache_key(url, validation_level)
            if key in self.index:
                del self.index[key]
                logger.debug(f"Cache invalidated: {url} ({validation_level})")
        else:
            # Invalidate all levels
            for level in ["head", "partial", "full"]:
                key = self._make_cache_key(url, level)
                if key in self.index:
                    del self.index[key]
            logger.debug(f"Cache invalidated: {url} (all levels)")

        self._save_index()

    def clear_all(self):
        """
        Clear all cache entries.

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> cache.clear_all()
        """
        self.index.clear()
        self._save_index()

        # Remove cached files
        for file in self.files_dir.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove cached file {file}: {e}")

        logger.info("Cache cleared")

    def _cleanup_expired(self):
        """Remove expired cache entries."""
        expired_keys = [key for key, entry in self.index.items() if entry.is_expired]

        for key in expired_keys:
            entry = self.index[key]

            # Remove cached file if exists
            if entry.cached_file_path:
                cached_path = Path(entry.cached_file_path)
                if cached_path.exists():
                    try:
                        cached_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to remove cached file: {e}")

            del self.index[key]

        if expired_keys:
            self._save_index()
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including:
            - total_entries: Total number of cache entries
            - expired_entries: Number of expired entries
            - valid_entries: Number of valid (non-expired) entries
            - success_entries: Number of successful validations
            - cached_files: Number of cached files
            - total_size_mb: Total size of cached files in MB

        Example:
            >>> cache = CacheManager(Path("/tmp/cache"))
            >>> stats = cache.get_stats()
            >>> print(f"Cached files: {stats['cached_files']}")
        """
        total_entries = len(self.index)
        expired_entries = sum(1 for entry in self.index.values() if entry.is_expired)
        success_entries = sum(1 for entry in self.index.values() if entry.is_success)

        cached_files = list(self.files_dir.glob("*"))
        total_size_mb = sum(f.stat().st_size for f in cached_files if f.is_file()) / (
            1024 * 1024
        )

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
            "success_entries": success_entries,
            "cached_files": len(cached_files),
            "total_size_mb": round(total_size_mb, 2),
        }


def get_cache_manager(cache_dir: Optional[Path] = None) -> CacheManager:
    """
    Get cache manager instance.

    Args:
        cache_dir: Cache directory (uses temp dir if None)

    Returns:
        CacheManager instance

    Example:
        >>> cache = get_cache_manager()
        >>> cache.store_validation(
        ...     url="https://example.com/file.tar.gz",
        ...     validation_level="head",
        ...     is_success=True,
        ... )
    """
    if cache_dir is None:
        import tempfile

        cache_dir = Path(tempfile.gettempdir()) / "toolchainkit_link_validation"

    return CacheManager(cache_dir)
