"""Unit tests for hash validator utilities."""

import hashlib
import pytest
from pathlib import Path

from tests.link_validation.utils.hash_validator import (
    HashValidationResult,
    HashValidator,
    normalize_hash,
    quick_validate_hash,
)


def test_hash_validator_initialization():
    """Test HashValidator can be initialized."""
    validator = HashValidator(chunk_size=4096)
    assert validator.chunk_size == 4096
    assert validator.algorithm == "sha256"


def test_hash_validator_custom_algorithm():
    """Test HashValidator with custom algorithm."""
    validator = HashValidator(algorithm="sha512")
    assert validator.algorithm == "sha512"


def test_compute_hash(tmp_path):
    """Test hash computation."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    validator = HashValidator()
    hash_result = validator.compute_hash(test_file)

    # Verify format
    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)

    # Verify correct hash value
    expected = hashlib.sha256(b"Hello, World!").hexdigest()
    assert hash_result == expected


def test_compute_hash_with_progress(tmp_path):
    """Test hash computation with progress callback."""
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"x" * 10000)

    progress_calls = []

    def progress_callback(bytes_read, total_bytes):
        progress_calls.append((bytes_read, total_bytes))

    validator = HashValidator()
    hash_result = validator.compute_hash(test_file, progress_callback)

    # Verify progress was reported
    assert len(progress_calls) > 0
    # Verify last call shows completion
    assert progress_calls[-1][0] == progress_calls[-1][1]
    # Verify hash is valid
    assert len(hash_result) == 64


def test_validate_matching_hash(tmp_path):
    """Test validation with matching hash."""
    test_file = tmp_path / "test.txt"
    content = b"Test content for hashing"
    test_file.write_bytes(content)

    # Compute expected hash
    expected_hash = hashlib.sha256(content).hexdigest()

    validator = HashValidator()
    result = validator.validate_file(test_file, expected_hash)

    assert result.is_valid
    assert result.matches
    assert result.actual_hash == expected_hash
    assert result.expected_hash == expected_hash
    assert result.error_message is None
    assert result.algorithm == "sha256"
    assert result.computation_time_ms > 0


def test_validate_mismatched_hash(tmp_path):
    """Test validation with mismatched hash."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Content")

    # Use wrong hash
    wrong_hash = "0" * 64

    validator = HashValidator()
    result = validator.validate_file(test_file, wrong_hash)

    assert result.is_valid  # Computation succeeded
    assert not result.matches  # But hash doesn't match
    assert result.actual_hash != wrong_hash
    assert result.error_message is not None
    assert "mismatch" in result.error_message.lower()


def test_validate_nonexistent_file(tmp_path):
    """Test validation of nonexistent file."""
    nonexistent = tmp_path / "does_not_exist.txt"

    validator = HashValidator()
    result = validator.validate_file(nonexistent, "abc123" + "0" * 58)

    assert not result.is_valid
    assert not result.matches
    assert result.actual_hash is None
    assert result.error_message is not None
    assert "not found" in result.error_message.lower()


def test_validate_invalid_hash_format(tmp_path):
    """Test validation with invalid hash format."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Content")

    # Invalid hash (too short)
    validator = HashValidator()
    result = validator.validate_file(test_file, "invalid")

    assert not result.is_valid
    assert not result.matches
    assert result.error_message is not None


def test_normalize_hash():
    """Test hash normalization."""
    # Test with prefix
    normalized = normalize_hash("sha256:ABC123" + "0" * 58)
    assert normalized == "abc123" + "0" * 58

    # Test without prefix
    normalized = normalize_hash("ABC123" + "0" * 58)
    assert normalized == "abc123" + "0" * 58

    # Test with whitespace
    normalized = normalize_hash("  ABC123" + "0" * 58 + "  ")
    assert normalized == "abc123" + "0" * 58


def test_normalize_hash_invalid_length():
    """Test normalize_hash with invalid length."""
    with pytest.raises(ValueError, match="Invalid SHA256 hash length"):
        normalize_hash("abc123")  # Too short


def test_normalize_hash_invalid_characters():
    """Test normalize_hash with invalid characters."""
    with pytest.raises(ValueError, match="non-hex characters"):
        normalize_hash("ZZZZZZ" + "0" * 58)


def test_normalize_hash_different_algorithms():
    """Test normalize_hash with different algorithms."""
    # MD5 (32 chars)
    md5_hash = "a" * 32
    assert normalize_hash(md5_hash, "md5") == md5_hash

    # SHA512 (128 chars)
    sha512_hash = "b" * 128
    assert normalize_hash(sha512_hash, "sha512") == sha512_hash


def test_quick_validate_convenience(tmp_path):
    """Test convenience function."""
    test_file = tmp_path / "test.txt"
    content = b"Quick test"
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    assert quick_validate_hash(test_file, expected_hash)
    assert not quick_validate_hash(test_file, "0" * 64)


def test_quick_validate_nonexistent_file(tmp_path):
    """Test quick_validate with nonexistent file."""
    nonexistent = tmp_path / "does_not_exist.txt"
    assert not quick_validate_hash(nonexistent, "0" * 64)


@pytest.mark.link_validation
def test_validate_stream_with_progress(tmp_path):
    """Test streaming validation with progress."""
    test_file = tmp_path / "large_file.bin"
    content = b"x" * 10000
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    progress_calls = []

    def progress_callback(bytes_read, total_bytes):
        progress_calls.append((bytes_read, total_bytes))

    validator = HashValidator()
    result = validator.validate_stream(test_file, expected_hash, progress_callback)

    assert result.is_valid
    assert result.matches
    assert len(progress_calls) > 0
    assert progress_calls[-1][0] == progress_calls[-1][1]  # Complete


@pytest.mark.link_validation
def test_validate_with_hash_prefix(tmp_path):
    """Test validation with hash algorithm prefix."""
    test_file = tmp_path / "test.txt"
    content = b"Test with prefix"
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    # Test with sha256: prefix
    validator = HashValidator()
    result = validator.validate_file(test_file, f"sha256:{expected_hash}")

    assert result.is_valid
    assert result.matches


@pytest.mark.link_validation
def test_hash_validation_result_properties():
    """Test HashValidationResult properties."""
    result = HashValidationResult(
        is_valid=True,
        matches=True,
        file_path=Path("test.txt"),
        expected_hash="abc123",
        actual_hash="abc123",
        algorithm="sha256",
        error_message=None,
        computation_time_ms=10.5,
    )

    assert result.is_success
    assert result.is_valid
    assert result.matches
    assert result.computation_time_ms == 10.5

    # Test failed result
    failed_result = HashValidationResult(
        is_valid=True,
        matches=False,
        file_path=Path("test.txt"),
        expected_hash="abc123",
        actual_hash="def456",
        algorithm="sha256",
        error_message="Hash mismatch",
        computation_time_ms=10.5,
    )

    assert not failed_result.is_success
    assert failed_result.is_valid
    assert not failed_result.matches
