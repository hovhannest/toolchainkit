"""
Unit tests for verification module.

Tests hash computation, verification, and security features.
"""

import hashlib
import pytest
from unittest.mock import patch

from toolchainkit.core.verification import (
    compute_file_hash,
    verify_file_hash,
    verify_multiple_hashes,
    parse_hash_file,
    verify_hash_file,
    verify_gpg_signature,
    HashVerifier,
    VerificationResult,
    HashFormatError,
    _constant_time_compare,
    _is_valid_hash_format,
)


class TestComputeFileHash:
    """Test compute_file_hash function."""

    def test_compute_sha256_hash(self, tmp_path):
        """Test computing SHA256 hash."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        actual = compute_file_hash(file, "sha256")

        assert actual == expected

    def test_compute_sha512_hash(self, tmp_path):
        """Test computing SHA512 hash."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.sha512(content).hexdigest()
        actual = compute_file_hash(file, "sha512")

        assert actual == expected

    def test_compute_md5_hash_with_warning(self, tmp_path):
        """Test computing MD5 hash logs warning."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.md5(content).hexdigest()
        actual = compute_file_hash(file, "md5")

        assert actual == expected

    def test_unsupported_algorithm(self, tmp_path):
        """Test unsupported algorithm raises ValueError."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test")

        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            compute_file_hash(file, "blake2")

    def test_nonexistent_file(self, tmp_path):
        """Test nonexistent file raises FileNotFoundError."""
        file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            compute_file_hash(file, "sha256")

    def test_case_insensitive_algorithm(self, tmp_path):
        """Test algorithm name is case-insensitive."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        hash1 = compute_file_hash(file, "SHA256")
        hash2 = compute_file_hash(file, "sha256")

        assert hash1 == hash2

    def test_progress_callback(self, tmp_path):
        """Test progress callback is called."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"x" * 10000)

        progress_calls = []

        def on_progress(bytes_read, total_bytes):
            progress_calls.append((bytes_read, total_bytes))

        compute_file_hash(file, "sha256", progress_callback=on_progress)

        assert len(progress_calls) > 0
        # Last call should have read all bytes
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_large_file_streaming(self, tmp_path):
        """Test large files are streamed (not loaded into memory)."""
        file = tmp_path / "large.bin"
        # Create 1MB file
        file.write_bytes(b"x" * (1024 * 1024))

        hash_value = compute_file_hash(file, "sha256")

        assert len(hash_value) == 64  # SHA256 is 64 hex chars
        assert hash_value == hashlib.sha256(b"x" * (1024 * 1024)).hexdigest()


class TestVerifyFileHash:
    """Test verify_file_hash function."""

    def test_verify_matching_hash(self, tmp_path):
        """Test verification succeeds with matching hash."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()

        assert verify_file_hash(file, expected, "sha256") is True

    def test_verify_non_matching_hash(self, tmp_path):
        """Test verification fails with non-matching hash."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test content")

        wrong_hash = "a" * 64

        assert verify_file_hash(file, wrong_hash, "sha256") is False

    def test_verify_case_insensitive(self, tmp_path):
        """Test hash comparison is case-insensitive."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()

        assert verify_file_hash(file, expected.upper(), "sha256") is True
        assert verify_file_hash(file, expected.lower(), "sha256") is True

    def test_verify_with_whitespace(self, tmp_path):
        """Test hash with leading/trailing whitespace is handled."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()

        assert verify_file_hash(file, f"  {expected}  ", "sha256") is True

    def test_verify_invalid_hash_format(self, tmp_path):
        """Test invalid hash format raises error."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test")

        with pytest.raises(HashFormatError):
            verify_file_hash(file, "not-a-hex-hash", "sha256")

    def test_verify_nonexistent_file(self, tmp_path):
        """Test nonexistent file raises FileNotFoundError."""
        file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            verify_file_hash(file, "a" * 64, "sha256")


class TestVerifyMultipleHashes:
    """Test verify_multiple_hashes function."""

    def test_verify_multiple_algorithms(self, tmp_path):
        """Test verification with multiple algorithms."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        hashes = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "sha512": hashlib.sha512(content).hexdigest(),
            "md5": hashlib.md5(content).hexdigest(),
        }

        results = verify_multiple_hashes(file, hashes)

        assert all(results.values())
        assert len(results) == 3

    def test_verify_mixed_results(self, tmp_path):
        """Test with some hashes matching and some not."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        hashes = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "sha512": "wrong" + "a" * 120,  # Wrong hash
            "md5": hashlib.md5(content).hexdigest(),
        }

        results = verify_multiple_hashes(file, hashes)

        assert results["sha256"] is True
        assert results["sha512"] is False
        assert results["md5"] is True

    def test_verify_invalid_algorithm(self, tmp_path):
        """Test invalid algorithm is handled gracefully."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test")

        hashes = {"invalid_algo": "abc123"}

        results = verify_multiple_hashes(file, hashes)

        assert results["invalid_algo"] is False


class TestParseHashFile:
    """Test parse_hash_file function."""

    def test_parse_simple_format(self, tmp_path):
        """Test parsing simple hash file format."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """abc123def456  file1.txt
789fedcba  file2.txt
"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        assert len(hashes) == 2
        assert hashes["file1.txt"] == "abc123def456"
        assert hashes["file2.txt"] == "789fedcba"

    def test_parse_with_asterisk(self, tmp_path):
        """Test parsing hash file with asterisk (binary mode indicator)."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """abc123 *file1.txt
def456 *file2.txt
"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        assert hashes["file1.txt"] == "abc123"
        assert hashes["file2.txt"] == "def456"

    def test_parse_with_comments(self, tmp_path):
        """Test parsing hash file with comments."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """# This is a comment
abc123  file1.txt
# Another comment
def456  file2.txt
"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        assert len(hashes) == 2

    def test_parse_with_empty_lines(self, tmp_path):
        """Test parsing hash file with empty lines."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """abc123  file1.txt

def456  file2.txt

"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        assert len(hashes) == 2

    def test_parse_rejects_path_traversal(self, tmp_path):
        """Test path traversal attempts are rejected."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """abc123  ../etc/passwd
def456  file.txt
ghi789  /etc/shadow
"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        # Only safe filename should be parsed
        assert len(hashes) == 1
        assert "file.txt" in hashes

    def test_parse_invalid_lines_skipped(self, tmp_path):
        """Test invalid lines are skipped with warning."""
        hash_file = tmp_path / "SHA256SUMS"
        content = """abc123  file1.txt
invalid_line_without_space
def456  file2.txt
"""
        hash_file.write_text(content)

        hashes = parse_hash_file(hash_file)

        assert len(hashes) == 2

    def test_parse_nonexistent_file(self, tmp_path):
        """Test nonexistent hash file raises error."""
        hash_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            parse_hash_file(hash_file)


class TestVerifyHashFile:
    """Test verify_hash_file function."""

    def test_verify_all_files(self, tmp_path):
        """Test verifying all files in hash file."""
        # Create files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        # Create hash file
        hash_file = tmp_path / "SHA256SUMS"
        hash1 = hashlib.sha256(b"content1").hexdigest()
        hash2 = hashlib.sha256(b"content2").hexdigest()
        hash_file.write_text(f"{hash1}  file1.txt\n{hash2}  file2.txt\n")

        results = verify_hash_file(hash_file, tmp_path, "sha256")

        assert len(results) == 2
        assert results["file1.txt"] is True
        assert results["file2.txt"] is True

    def test_verify_missing_file(self, tmp_path):
        """Test verification fails for missing file."""
        hash_file = tmp_path / "SHA256SUMS"
        hash_file.write_text("abc123  missing.txt\n")

        results = verify_hash_file(hash_file, tmp_path, "sha256")

        assert results["missing.txt"] is False

    def test_verify_corrupted_file(self, tmp_path):
        """Test verification fails for corrupted file."""
        file = tmp_path / "file.txt"
        file.write_bytes(b"original content")

        hash_file = tmp_path / "SHA256SUMS"
        hash_value = hashlib.sha256(b"original content").hexdigest()
        hash_file.write_text(f"{hash_value}  file.txt\n")

        # Corrupt the file
        file.write_bytes(b"corrupted content")

        results = verify_hash_file(hash_file, tmp_path, "sha256")

        assert results["file.txt"] is False


class TestVerifyGpgSignature:
    """Test verify_gpg_signature function."""

    def test_gpg_not_installed(self, tmp_path):
        """Test handles GPG not being installed."""
        file = tmp_path / "file.txt"
        sig = tmp_path / "file.txt.asc"
        file.write_bytes(b"test")
        sig.write_bytes(b"fake signature")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            verified, message = verify_gpg_signature(file, sig)

        assert verified is False
        assert "not installed" in message.lower()

    def test_gpg_timeout(self, tmp_path):
        """Test handles GPG timeout."""
        file = tmp_path / "file.txt"
        sig = tmp_path / "file.txt.asc"
        file.write_bytes(b"test")
        sig.write_bytes(b"fake signature")

        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gpg", 30)):
            verified, message = verify_gpg_signature(file, sig)

        assert verified is False
        assert "timeout" in message.lower()

    def test_missing_file(self, tmp_path):
        """Test missing file is handled."""
        file = tmp_path / "nonexistent.txt"
        sig = tmp_path / "file.asc"

        verified, message = verify_gpg_signature(file, sig)

        assert verified is False
        assert "not found" in message.lower()

    def test_missing_signature(self, tmp_path):
        """Test missing signature is handled."""
        file = tmp_path / "file.txt"
        file.write_bytes(b"test")
        sig = tmp_path / "nonexistent.asc"

        verified, message = verify_gpg_signature(file, sig)

        assert verified is False
        assert "not found" in message.lower()


class TestConstantTimeCompare:
    """Test _constant_time_compare function."""

    def test_equal_strings(self):
        """Test equal strings return True."""
        assert _constant_time_compare("abc123", "abc123") is True

    def test_unequal_strings(self):
        """Test unequal strings return False."""
        assert _constant_time_compare("abc123", "def456") is False

    def test_case_sensitive(self):
        """Test comparison is case-sensitive."""
        assert _constant_time_compare("ABC", "abc") is False

    def test_different_lengths(self):
        """Test strings of different lengths return False."""
        assert _constant_time_compare("abc", "abcdef") is False


class TestIsValidHashFormat:
    """Test _is_valid_hash_format function."""

    def test_valid_sha256(self):
        """Test valid SHA256 hash format."""
        hash_str = "a" * 64
        assert _is_valid_hash_format(hash_str, "sha256") is True

    def test_valid_md5(self):
        """Test valid MD5 hash format."""
        hash_str = "a" * 32
        assert _is_valid_hash_format(hash_str, "md5") is True

    def test_invalid_characters(self):
        """Test invalid characters are rejected."""
        assert _is_valid_hash_format("ghijkl", "sha256") is False

    def test_empty_string(self):
        """Test empty string is rejected."""
        assert _is_valid_hash_format("", "sha256") is False

    def test_wrong_length_rejected(self):
        """Test wrong length is rejected."""
        # SHA256 should be 64 chars, but we provide 32
        hash_str = "a" * 32
        # Should return False for security
        assert _is_valid_hash_format(hash_str, "sha256") is False


class TestHashVerifier:
    """Test HashVerifier class."""

    def test_create_verifier(self):
        """Test creating hash verifier."""
        verifier = HashVerifier()
        assert verifier.default_algorithm == "sha256"

    def test_create_with_custom_algorithm(self):
        """Test creating with custom default algorithm."""
        verifier = HashVerifier(default_algorithm="sha512")
        assert verifier.default_algorithm == "sha512"

    def test_verify_with_prefix(self, tmp_path):
        """Test verification with algorithm prefix."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        hash_value = hashlib.sha256(content).hexdigest()

        verifier = HashVerifier()
        result = verifier.verify_file(file, f"sha256:{hash_value}")

        assert result.valid is True
        assert result.algorithm == "sha256"

    def test_verify_without_prefix(self, tmp_path):
        """Test verification without algorithm prefix uses default."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        hash_value = hashlib.sha256(content).hexdigest()

        verifier = HashVerifier(default_algorithm="sha256")
        result = verifier.verify_file(file, hash_value)

        assert result.valid is True
        assert result.algorithm == "sha256"

    def test_verify_override_algorithm(self, tmp_path):
        """Test explicitly specifying algorithm."""
        file = tmp_path / "test.txt"
        content = b"test"
        file.write_bytes(content)

        hash_value = hashlib.sha512(content).hexdigest()

        verifier = HashVerifier()
        result = verifier.verify_file(file, hash_value, algorithm="sha512")

        assert result.valid is True
        assert result.algorithm == "sha512"

    def test_verify_failure(self, tmp_path):
        """Test verification failure."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test")

        wrong_hash = "a" * 64

        verifier = HashVerifier()
        result = verifier.verify_file(file, f"sha256:{wrong_hash}")

        assert result.valid is False
        assert result.error is None
        assert result.actual_hash != result.expected_hash


class TestVerificationResult:
    """Test VerificationResult class."""

    def test_successful_result(self):
        """Test successful verification result."""
        result = VerificationResult(
            valid=True,
            algorithm="sha256",
            expected_hash="abc123",
            actual_hash="abc123",
            error=None,
        )

        assert result.valid is True
        assert bool(result) is True
        assert "✓" in str(result)

    def test_failed_result(self):
        """Test failed verification result."""
        result = VerificationResult(
            valid=False,
            algorithm="sha256",
            expected_hash="abc123",
            actual_hash="def456",
            error=None,
        )

        assert result.valid is False
        assert bool(result) is False
        assert "✗" in str(result)

    def test_result_with_error(self):
        """Test result with error message."""
        result = VerificationResult(
            valid=False,
            algorithm="sha256",
            expected_hash="abc123",
            actual_hash=None,
            error="File not found",
        )

        assert result.error == "File not found"
        assert "File not found" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
