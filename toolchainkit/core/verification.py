"""
Hash verification system with support for multiple algorithms and hash file parsing.

This module provides cryptographic hash verification capabilities including:
- SHA256, SHA512, MD5 hash computation and verification
- Hash file parsing (SHA256SUMS format)
- Multi-algorithm verification
- Security features (timing-attack resistant comparison)
- Optional GPG signature verification
"""

import hashlib
import logging
import secrets
import subprocess
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HashVerificationError(Exception):
    """Exception raised when hash verification fails."""

    pass


class HashFormatError(Exception):
    """Exception raised when hash format is invalid."""

    pass


def compute_file_hash(
    file_path: Path,
    algorithm: str = "sha256",
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Compute cryptographic hash of file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('sha256', 'sha512', 'md5')
        progress_callback: Optional progress callback (bytes_read, total_bytes)

    Returns:
        Hex string of hash

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported

    Example:
        >>> from pathlib import Path
        >>> hash_value = compute_file_hash(Path('file.tar.gz'), 'sha256')
        >>> print(f"SHA256: {hash_value}")
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    algorithm = algorithm.lower()

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "sha512":
        hasher = hashlib.sha512()
    elif algorithm == "md5":
        logger.warning(
            "MD5 is cryptographically broken and should not be used for security. "
            "Use SHA256 or SHA512 instead."
        )
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        logger.warning(
            "SHA1 is cryptographically weak and should not be used for security. "
            "Use SHA256 or SHA512 instead."
        )
        hasher = hashlib.sha1()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    file_size = file_path.stat().st_size
    bytes_read = 0

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
            bytes_read += len(chunk)

            if progress_callback:
                progress_callback(bytes_read, file_size)

    return hasher.hexdigest()


def verify_file_hash(
    file_path: Path, expected_hash: str, algorithm: str = "sha256"
) -> bool:
    """
    Verify file matches expected hash using constant-time comparison.

    Args:
        file_path: Path to file
        expected_hash: Expected hash value (hex string)
        algorithm: Hash algorithm ('sha256', 'sha512', 'md5')

    Returns:
        True if hash matches, False otherwise

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported

    Example:
        >>> if verify_file_hash(Path('file.tar.gz'), expected_hash):
        ...     print("File is valid")
    """
    # Validate hash format
    expected_hash = expected_hash.lower().strip()
    if not _is_valid_hash_format(expected_hash, algorithm):
        raise HashFormatError(f"Invalid hash format for {algorithm}: {expected_hash}")

    actual_hash = compute_file_hash(file_path, algorithm)

    # Use constant-time comparison to prevent timing attacks
    return _constant_time_compare(actual_hash, expected_hash)


def verify_multiple_hashes(file_path: Path, hashes: dict[str, str]) -> dict[str, bool]:
    """
    Verify file against multiple hash algorithms.

    Args:
        file_path: Path to file
        hashes: Dict of algorithm -> expected_hash

    Returns:
        Dict of algorithm -> verification_result

    Example:
        >>> hashes = {
        ...     'sha256': 'abc123...',
        ...     'sha512': 'def456...'
        ... }
        >>> results = verify_multiple_hashes(Path('file.tar.gz'), hashes)
        >>> if all(results.values()):
        ...     print("All hashes valid")
    """
    results = {}
    for algorithm, expected in hashes.items():
        try:
            results[algorithm] = verify_file_hash(file_path, expected, algorithm)
        except Exception as e:
            logger.error(f"Failed to verify {algorithm} hash: {e}")
            results[algorithm] = False

    return results


def parse_hash_file(hash_file_path: Path) -> dict[str, str]:
    """
    Parse hash file (e.g., SHA256SUMS format).

    Supports formats:
    - hash  filename
    - hash *filename
    - hash filename (with multiple spaces/tabs)

    Args:
        hash_file_path: Path to hash file

    Returns:
        Dict of filename -> hash

    Raises:
        FileNotFoundError: If hash file doesn't exist

    Example:
        >>> hashes = parse_hash_file(Path('SHA256SUMS'))
        >>> for filename, hash_value in hashes.items():
        ...     print(f"{filename}: {hash_value}")
    """
    if not hash_file_path.exists():
        raise FileNotFoundError(f"Hash file not found: {hash_file_path}")

    hashes = {}

    with open(hash_file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse line: "hash  filename" or "hash *filename"
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                logger.warning(
                    f"Skipping invalid line {line_num} in {hash_file_path.name}: {line}"
                )
                continue

            hash_value = parts[0].strip()
            filename = parts[1].strip()

            # Remove leading asterisk if present (binary mode indicator)
            if filename.startswith("*"):
                filename = filename[1:].strip()

            # Security: prevent path traversal and absolute paths
            # Check for: parent directory refs, absolute paths, drive letters
            is_suspicious = (
                ".." in filename
                or filename.startswith("/")
                or filename.startswith("\\")
                or (len(filename) > 1 and filename[1] == ":")  # Windows drive letter
            )

            if is_suspicious:
                logger.warning(
                    f"Skipping suspicious filename at line {line_num}: {filename}"
                )
                continue

            hashes[filename] = hash_value

    return hashes


def verify_hash_file(
    hash_file_path: Path, files_directory: Path, algorithm: str = "sha256"
) -> dict[str, bool]:
    """
    Verify all files listed in a hash file.

    Args:
        hash_file_path: Path to hash file
        files_directory: Directory containing files to verify
        algorithm: Hash algorithm used in hash file

    Returns:
        Dict of filename -> verification_result

    Example:
        >>> results = verify_hash_file(Path('SHA256SUMS'), Path('.'))
        >>> failed = [f for f, ok in results.items() if not ok]
        >>> if failed:
        ...     print(f"Failed: {failed}")
    """
    hashes = parse_hash_file(hash_file_path)
    results = {}

    for filename, expected_hash in hashes.items():
        file_path = files_directory / filename

        if not file_path.exists():
            logger.warning(f"File not found: {filename}")
            results[filename] = False
            continue

        try:
            results[filename] = verify_file_hash(file_path, expected_hash, algorithm)
        except Exception as e:
            logger.error(f"Failed to verify {filename}: {e}")
            results[filename] = False

    return results


def verify_gpg_signature(
    file_path: Path, signature_path: Path, keyring_path: Optional[Path] = None
) -> tuple[bool, str]:
    """
    Verify GPG signature of file (optional feature).

    Args:
        file_path: File to verify
        signature_path: Detached signature file (.asc)
        keyring_path: Optional path to GPG keyring

    Returns:
        (verified: bool, message: str)

    Note:
        Requires GPG to be installed. Returns (False, error) if GPG not available.

    Example:
        >>> verified, msg = verify_gpg_signature(
        ...     Path('llvm.tar.xz'),
        ...     Path('llvm.tar.xz.asc')
        ... )
        >>> if verified:
        ...     print("Signature valid")
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    if not signature_path.exists():
        return False, f"Signature file not found: {signature_path}"

    cmd = ["gpg", "--verify"]

    if keyring_path:
        if not keyring_path.exists():
            return False, f"Keyring not found: {keyring_path}"
        cmd.extend(["--keyring", str(keyring_path)])

    cmd.extend([str(signature_path), str(file_path)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        verified = result.returncode == 0

        if verified:
            message = "GPG signature verified successfully"
        else:
            message = f"GPG verification failed: {result.stderr}"

        return verified, message

    except FileNotFoundError:
        return False, "GPG not installed. Install gpg to verify signatures."
    except subprocess.TimeoutExpired:
        return False, "GPG verification timeout"
    except Exception as e:
        return False, f"GPG verification error: {e}"


def _constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    # Use secrets.compare_digest for constant-time comparison
    # Convert to bytes for comparison
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _is_valid_hash_format(hash_str: str, algorithm: str) -> bool:
    """
    Validate hash string format.

    Args:
        hash_str: Hash string to validate
        algorithm: Algorithm name

    Returns:
        True if format is valid
    """
    if not hash_str:
        return False

    # Check if contains only hex characters
    if not all(c in "0123456789abcdef" for c in hash_str.lower()):
        return False

    # Check expected length for algorithm
    expected_lengths = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}

    expected_len = expected_lengths.get(algorithm.lower())
    if expected_len and len(hash_str) != expected_len:
        # Reject if length doesn't match - this is a security issue
        logger.error(
            f"Hash length {len(hash_str)} doesn't match expected {expected_len} for {algorithm}"
        )
        return False

    return True


class HashVerifier:
    """
    High-level hash verification interface.

    Example:
        >>> verifier = HashVerifier()
        >>> result = verifier.verify_file(Path('file.tar.gz'), 'sha256:abc123...')
        >>> if result.valid:
        ...     print("File verified")
    """

    def __init__(self, default_algorithm: str = "sha256"):
        """
        Initialize hash verifier.

        Args:
            default_algorithm: Default hash algorithm to use
        """
        self.default_algorithm = default_algorithm

    def verify_file(
        self, file_path: Path, expected_hash: str, algorithm: Optional[str] = None
    ) -> "VerificationResult":
        """
        Verify file with automatic algorithm detection.

        Supports hash format: "algorithm:hash" or just "hash"

        Args:
            file_path: File to verify
            expected_hash: Expected hash (with optional "algorithm:" prefix)
            algorithm: Override algorithm (if not in expected_hash)

        Returns:
            VerificationResult object
        """
        # Parse algorithm from hash if present
        if ":" in expected_hash:
            algo, hash_value = expected_hash.split(":", 1)
            algorithm = algo.lower()
        else:
            hash_value = expected_hash
            algorithm = algorithm or self.default_algorithm

        try:
            valid = verify_file_hash(file_path, hash_value, algorithm)
            return VerificationResult(
                valid=valid,
                algorithm=algorithm,
                expected_hash=hash_value,
                actual_hash=compute_file_hash(file_path, algorithm)
                if not valid
                else hash_value,
                error=None,
            )
        except Exception as e:
            return VerificationResult(
                valid=False,
                algorithm=algorithm,
                expected_hash=hash_value,
                actual_hash=None,
                error=str(e),
            )


class VerificationResult:
    """Result of hash verification."""

    def __init__(
        self,
        valid: bool,
        algorithm: str,
        expected_hash: str,
        actual_hash: Optional[str],
        error: Optional[str],
    ):
        self.valid = valid
        self.algorithm = algorithm
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.error = error

    def __bool__(self):
        """Allow using result in boolean context."""
        return self.valid

    def __str__(self):
        """String representation."""
        if self.valid:
            return f"✓ {self.algorithm.upper()} verification passed"
        else:
            msg = f"✗ {self.algorithm.upper()} verification failed"
            if self.error:
                msg += f": {self.error}"
            return msg
