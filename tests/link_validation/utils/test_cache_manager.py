"""Unit tests for cache manager."""

import time

import pytest

from tests.link_validation.utils.cache_manager import (
    CacheManager,
    CachedValidationResult,
    get_cache_manager,
)


def test_cache_manager_initialization(tmp_path):
    """Test cache manager can be initialized."""
    cache = CacheManager(tmp_path)
    assert cache.cache_dir == tmp_path
    assert cache.metadata_dir.exists()
    assert cache.files_dir.exists()
    # Index file is created only when entries are saved
    assert cache.index == {}


def test_cache_manager_default_ttl(tmp_path):
    """Test cache manager with custom default TTL."""
    cache = CacheManager(tmp_path, default_ttl_hours=48)
    assert cache.default_ttl_hours == 48


def test_store_and_retrieve_validation(tmp_path):
    """Test storing and retrieving validation results."""
    cache = CacheManager(tmp_path, default_ttl_hours=24)

    url = "https://example.com/file.tar.gz"
    cache.store_validation(
        url=url,
        validation_level="head",
        is_success=True,
        status_code=200,
    )

    result = cache.get_validation(url, "head")
    assert result is not None
    assert result.url == url
    assert result.is_success
    assert result.status_code == 200
    assert not result.is_expired
    assert result.validation_level == "head"


def test_store_validation_with_hash(tmp_path):
    """Test storing validation with hash information."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"
    cache.store_validation(
        url=url,
        validation_level="full",
        is_success=True,
        status_code=200,
        hash_expected="abc123",
        hash_actual="abc123",
        hash_valid=True,
    )

    result = cache.get_validation(url, "full")
    assert result is not None
    assert result.hash_expected == "abc123"
    assert result.hash_actual == "abc123"
    assert result.hash_valid is True


def test_cache_expiration(tmp_path):
    """Test cache entries expire correctly."""
    cache = CacheManager(
        tmp_path, default_ttl_hours=0.0001, auto_cleanup=False
    )  # 0.36 seconds

    url = "https://example.com/file.tar.gz"
    cache.store_validation(
        url=url,
        validation_level="head",
        is_success=True,
        status_code=200,
    )

    # Wait for expiration (0.0001 hours = 0.36 seconds)
    time.sleep(0.5)

    result = cache.get_validation(url, "head")
    assert result is None  # Expired


def test_cached_validation_result_properties(tmp_path):
    """Test CachedValidationResult properties."""
    now = time.time()
    result = CachedValidationResult(
        url="https://example.com/file.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
        cached_at=now,
        expires_at=now + 3600,
    )

    assert not result.is_expired
    assert result.age_hours < 0.1  # Just created

    # Test expired
    expired_result = CachedValidationResult(
        url="https://example.com/file.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
        cached_at=now - 7200,
        expires_at=now - 3600,
    )
    assert expired_result.is_expired


def test_cached_validation_result_serialization():
    """Test CachedValidationResult to/from dict."""
    now = time.time()
    result = CachedValidationResult(
        url="https://example.com/file.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
        cached_at=now,
        expires_at=now + 3600,
        hash_expected="abc123",
        hash_actual="abc123",
        hash_valid=True,
    )

    # Test to_dict
    data = result.to_dict()
    assert data["url"] == result.url
    assert data["validation_level"] == result.validation_level
    assert data["hash_expected"] == "abc123"

    # Test from_dict
    restored = CachedValidationResult.from_dict(data)
    assert restored.url == result.url
    assert restored.hash_expected == result.hash_expected


def test_cache_invalidation(tmp_path):
    """Test cache invalidation."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"
    cache.store_validation(
        url=url, validation_level="head", is_success=True, status_code=200
    )

    # Verify it's cached
    result = cache.get_validation(url, "head")
    assert result is not None

    # Invalidate specific level
    cache.invalidate(url, "head")

    result = cache.get_validation(url, "head")
    assert result is None


def test_cache_invalidate_all_levels(tmp_path):
    """Test invalidating all validation levels for a URL."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"
    cache.store_validation(
        url=url, validation_level="head", is_success=True, status_code=200
    )
    cache.store_validation(
        url=url, validation_level="partial", is_success=True, status_code=206
    )
    cache.store_validation(
        url=url, validation_level="full", is_success=True, status_code=200
    )

    # Invalidate all levels
    cache.invalidate(url)

    assert cache.get_validation(url, "head") is None
    assert cache.get_validation(url, "partial") is None
    assert cache.get_validation(url, "full") is None


def test_file_caching(tmp_path):
    """Test file caching."""
    cache = CacheManager(tmp_path)

    # Create test file
    source_file = tmp_path / "source.txt"
    source_file.write_text("test content")

    url = "https://example.com/file.tar.gz"
    cached_path = cache.store_file(url, source_file)

    assert cached_path.exists()
    assert cached_path.read_text() == "test content"
    assert cached_path.parent == cache.files_dir


def test_get_cached_file(tmp_path):
    """Test retrieving cached file."""
    cache = CacheManager(tmp_path)

    # Create and cache a file
    source_file = tmp_path / "source.txt"
    source_file.write_text("test content")

    url = "https://example.com/file.tar.gz"
    cached_path = cache.store_file(url, source_file)

    # Store validation entry with cached file path
    cache.store_validation(
        url=url,
        validation_level="full",
        is_success=True,
        status_code=200,
        cached_file_path=cached_path,
    )

    # Retrieve cached file
    retrieved_path = cache.get_cached_file(url)
    assert retrieved_path is not None
    assert retrieved_path == cached_path
    assert retrieved_path.read_text() == "test content"


def test_get_cached_file_not_found(tmp_path):
    """Test getting cached file when none exists."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"
    cached_path = cache.get_cached_file(url)
    assert cached_path is None


def test_cache_clear_all(tmp_path):
    """Test clearing all cache entries."""
    cache = CacheManager(tmp_path)

    # Add some entries
    cache.store_validation(
        url="https://example.com/file1.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
    )
    cache.store_validation(
        url="https://example.com/file2.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
    )

    # Create cached file
    source_file = tmp_path / "source.txt"
    source_file.write_text("test")
    cache.store_file("https://example.com/file.tar.gz", source_file)

    # Clear all
    cache.clear_all()

    assert len(cache.index) == 0
    assert len(list(cache.files_dir.iterdir())) == 0


def test_cache_stats(tmp_path):
    """Test cache statistics."""
    cache = CacheManager(tmp_path, auto_cleanup=False)

    cache.store_validation(
        url="https://example.com/file1.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
    )
    cache.store_validation(
        url="https://example.com/file2.tar.gz",
        validation_level="head",
        is_success=False,
        status_code=404,
        error_message="Not found",
    )

    # Add expired entry
    cache.store_validation(
        url="https://example.com/file3.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
        ttl_hours=-1,  # Already expired
    )

    stats = cache.get_stats()
    assert stats["total_entries"] == 3
    assert stats["success_entries"] == 2
    assert stats["expired_entries"] == 1
    assert stats["valid_entries"] == 2


def test_cache_stats_with_files(tmp_path):
    """Test cache statistics with cached files."""
    cache = CacheManager(tmp_path)

    # Create and cache files
    for i in range(3):
        source_file = tmp_path / f"source{i}.txt"
        source_file.write_text("x" * 1000)
        cache.store_file(f"https://example.com/file{i}.tar.gz", source_file)

    stats = cache.get_stats()
    assert stats["cached_files"] == 3
    # Each file is ~1000 bytes, total ~3KB = 0.003MB
    assert stats["total_size_mb"] >= 0.0


def test_cache_persistence(tmp_path):
    """Test cache persists across manager instances."""
    url = "https://example.com/file.tar.gz"

    # Create first manager and store entry
    cache1 = CacheManager(tmp_path)
    cache1.store_validation(
        url=url, validation_level="head", is_success=True, status_code=200
    )

    # Create second manager (should load existing cache)
    cache2 = CacheManager(tmp_path)
    result = cache2.get_validation(url, "head")

    assert result is not None
    assert result.url == url
    assert result.is_success


def test_cache_cleanup_expired(tmp_path):
    """Test automatic cleanup of expired entries."""
    cache = CacheManager(tmp_path, auto_cleanup=False)

    # Add expired entry
    url = "https://example.com/expired.tar.gz"
    cache.store_validation(
        url=url,
        validation_level="head",
        is_success=True,
        status_code=200,
        ttl_hours=-1,  # Already expired
    )

    # Add valid entry
    cache.store_validation(
        url="https://example.com/valid.tar.gz",
        validation_level="head",
        is_success=True,
        status_code=200,
    )

    assert len(cache.index) == 2

    # Cleanup
    cache._cleanup_expired()

    assert len(cache.index) == 1


def test_cache_key_generation(tmp_path):
    """Test cache key generation is consistent."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"
    key1 = cache._make_cache_key(url, "head")
    key2 = cache._make_cache_key(url, "head")
    key3 = cache._make_cache_key(url, "partial")

    assert key1 == key2  # Same URL and level
    assert key1 != key3  # Different level


def test_get_cache_manager_default():
    """Test get_cache_manager with default temp directory."""
    cache = get_cache_manager()
    assert cache.cache_dir.exists()
    assert "toolchainkit_link_validation" in str(cache.cache_dir)


def test_get_cache_manager_custom_dir(tmp_path):
    """Test get_cache_manager with custom directory."""
    cache = get_cache_manager(tmp_path)
    assert cache.cache_dir == tmp_path


@pytest.mark.link_validation
def test_cache_with_error_message(tmp_path):
    """Test caching failed validation with error message."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/notfound.tar.gz"
    cache.store_validation(
        url=url,
        validation_level="head",
        is_success=False,
        status_code=404,
        error_message="Not found",
    )

    result = cache.get_validation(url, "head")
    assert result is not None
    assert not result.is_success
    assert result.error_message == "Not found"


@pytest.mark.link_validation
def test_cache_different_validation_levels(tmp_path):
    """Test caching different validation levels for same URL."""
    cache = CacheManager(tmp_path)

    url = "https://example.com/file.tar.gz"

    # Store different levels
    cache.store_validation(
        url=url, validation_level="head", is_success=True, status_code=200
    )
    cache.store_validation(
        url=url, validation_level="partial", is_success=True, status_code=206
    )
    cache.store_validation(
        url=url, validation_level="full", is_success=True, status_code=200
    )

    # Retrieve each level
    head_result = cache.get_validation(url, "head")
    partial_result = cache.get_validation(url, "partial")
    full_result = cache.get_validation(url, "full")

    assert head_result is not None
    assert partial_result is not None
    assert full_result is not None
    assert partial_result.status_code == 206
