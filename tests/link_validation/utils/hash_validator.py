"""
SHA256 hash validation utilities for link validation tests.

Wraps existing functions/classes from toolchainkit.core.verification.
Provides hash computation and verification with clear error reporting for tests.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from toolchainkit.core.verification import (
    HashFormatError,
    HashVerifier,
    compute_file_hash,
    verify_file_hash,
)

logger = logging.getLogger(__name__)


@dataclass
class HashValidationResult:
    """Result of hash validation operation."""

    is_valid: bool
    matches: bool
    file_path: Path
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    algorithm: str
    error_message: Optional[str] = None
    computation_time_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if validation was successful."""
        return self.is_valid and self.matches


class HashValidator:
    """
    SHA256 hash validator for link validation tests.

    Wraps existing hash verification utilities from toolchainkit.core.verification
    with a test-specific interface and clear error reporting.

    Example:
        >>> validator = HashValidator()
        >>> result = validator.validate_file(Path('file.tar.gz'), 'abc123...')
        >>> if result.is_valid:
        ...     print(f"Hash: {result.actual_hash}")
    """

    def __init__(self, chunk_size: int = 8192, algorithm: str = "sha256"):
        """
        Initialize hash validator.

        Args:
            chunk_size: Chunk size for streaming (defaults to 8192)
            algorithm: Hash algorithm to use (default: sha256)
        """
        self.chunk_size = chunk_size
        self.algorithm = algorithm.lower()
        self._verifier = HashVerifier(default_algorithm=self.algorithm)

    def compute_hash(
        self,
        file_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Compute hash of file using existing verification utilities.

        Args:
            file_path: Path to file
            progress_callback: Optional progress callback (bytes_read, total_bytes)

        Returns:
            Hex string of hash

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If algorithm is not supported

        Example:
            >>> validator = HashValidator()
            >>> hash_value = validator.compute_hash(Path('file.tar.gz'))
        """
        return compute_file_hash(file_path, self.algorithm, progress_callback)

    def validate_file(
        self,
        file_path: Path,
        expected_hash: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> HashValidationResult:
        """
        Validate file hash against expected value.

        Args:
            file_path: Path to file to validate
            expected_hash: Expected hash value (hex string, optionally with "sha256:" prefix)
            progress_callback: Optional progress callback for hash computation

        Returns:
            HashValidationResult with detailed information

        Example:
            >>> validator = HashValidator()
            >>> result = validator.validate_file(Path('file.tar.gz'), 'abc123...')
            >>> if result.matches:
            ...     print("Hash matches!")
        """
        import time

        start_time = time.perf_counter()

        # Check if file exists
        if not file_path.exists():
            return HashValidationResult(
                is_valid=False,
                matches=False,
                file_path=file_path,
                expected_hash=expected_hash,
                actual_hash=None,
                algorithm=self.algorithm,
                error_message=f"File not found: {file_path}",
                computation_time_ms=0.0,
            )

        # Normalize expected hash
        try:
            expected_hash = normalize_hash(expected_hash, self.algorithm)
        except ValueError as e:
            return HashValidationResult(
                is_valid=False,
                matches=False,
                file_path=file_path,
                expected_hash=expected_hash,
                actual_hash=None,
                algorithm=self.algorithm,
                error_message=str(e),
                computation_time_ms=0.0,
            )

        # Compute actual hash
        try:
            actual_hash = self.compute_hash(file_path, progress_callback)
        except Exception as e:
            end_time = time.perf_counter()
            computation_time_ms = (end_time - start_time) * 1000
            return HashValidationResult(
                is_valid=False,
                matches=False,
                file_path=file_path,
                expected_hash=expected_hash,
                actual_hash=None,
                algorithm=self.algorithm,
                error_message=f"Hash computation failed: {e}",
                computation_time_ms=computation_time_ms,
            )

        # Compare hashes using constant-time comparison from verify_file_hash
        try:
            matches = verify_file_hash(file_path, expected_hash, self.algorithm)
        except HashFormatError as e:
            end_time = time.perf_counter()
            computation_time_ms = (end_time - start_time) * 1000
            return HashValidationResult(
                is_valid=False,
                matches=False,
                file_path=file_path,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                algorithm=self.algorithm,
                error_message=f"Hash format error: {e}",
                computation_time_ms=computation_time_ms,
            )

        end_time = time.perf_counter()
        computation_time_ms = (end_time - start_time) * 1000

        error_message = None
        if not matches:
            error_message = (
                f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
            )

        return HashValidationResult(
            is_valid=True,
            matches=matches,
            file_path=file_path,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            algorithm=self.algorithm,
            error_message=error_message,
            computation_time_ms=computation_time_ms,
        )

    def validate_stream(
        self,
        file_path: Path,
        expected_hash: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> HashValidationResult:
        """
        Validate file hash with streaming and progress reporting.

        This is an alias for validate_file() since the underlying compute_file_hash()
        already supports streaming with progress callbacks.

        Args:
            file_path: Path to file to validate
            expected_hash: Expected hash value
            progress_callback: Progress callback (bytes_read, total_bytes)

        Returns:
            HashValidationResult

        Example:
            >>> def on_progress(read, total):
            ...     print(f"{read}/{total} bytes")
            >>> validator = HashValidator()
            >>> result = validator.validate_stream(Path('large.tar.gz'), 'abc123...', on_progress)
        """
        return self.validate_file(file_path, expected_hash, progress_callback)


def normalize_hash(hash_str: str, algorithm: str = "sha256") -> str:
    """
    Normalize hash string to lowercase without prefixes.

    Args:
        hash_str: Hash string (may have "sha256:" or similar prefix)
        algorithm: Algorithm name for validation (default: sha256)

    Returns:
        Normalized hash string

    Raises:
        ValueError: If hash format is invalid

    Example:
        >>> normalize_hash("sha256:ABC123" + "0" * 58)
        'abc123' + '0' * 58
        >>> normalize_hash("ABC123" + "0" * 58)
        'abc123' + '0' * 58
    """
    # Convert to lowercase
    hash_str = hash_str.lower()

    # Remove algorithm prefix if present
    if ":" in hash_str:
        prefix, hash_value = hash_str.split(":", 1)
        # Validate prefix matches algorithm
        if prefix != algorithm.lower():
            logger.warning(
                f"Hash prefix '{prefix}' doesn't match algorithm '{algorithm}', using hash value anyway"
            )
        hash_str = hash_value

    # Remove whitespace
    hash_str = hash_str.strip()

    # Validate format based on algorithm
    expected_lengths = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}

    expected_len = expected_lengths.get(algorithm.lower())
    if expected_len is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    # Check length
    if len(hash_str) != expected_len:
        raise ValueError(
            f"Invalid {algorithm.upper()} hash length: expected {expected_len}, got {len(hash_str)}"
        )

    # Check if all characters are valid hex
    if not all(c in "0123456789abcdef" for c in hash_str):
        raise ValueError(
            f"Invalid {algorithm.upper()} hash format: contains non-hex characters"
        )

    return hash_str


def quick_validate_hash(
    file_path: Path, expected_hash: str, algorithm: str = "sha256"
) -> bool:
    """
    Convenience function to quickly validate a file hash.

    Args:
        file_path: Path to file
        expected_hash: Expected hash value
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if hash matches, False otherwise

    Example:
        >>> if quick_validate_hash(Path('file.tar.gz'), 'abc123...'):
        ...     print("File is valid")
    """
    try:
        validator = HashValidator(algorithm=algorithm)
        result = validator.validate_file(file_path, expected_hash)
        return result.matches
    except Exception as e:
        logger.error(f"Hash validation failed: {e}")
        return False
