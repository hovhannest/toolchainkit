"""
Integration tests for verification module.

Tests real-world hash verification scenarios with actual files.
"""

import hashlib
import pytest
import subprocess

from toolchainkit.core.verification import (
    compute_file_hash,
    verify_file_hash,
    parse_hash_file,
    verify_hash_file,
    verify_gpg_signature,
    HashVerifier,
)


@pytest.mark.integration
class TestRealFileVerification:
    """Test verification with real files."""

    def test_verify_large_file(self, tmp_path):
        """Test verifying a large file (10MB)."""
        file = tmp_path / "large.bin"
        # Create 10MB file
        size = 10 * 1024 * 1024
        with open(file, "wb") as f:
            f.write(b"\x00" * size)

        # Compute hash
        hash_value = compute_file_hash(file, "sha256")

        # Verify
        assert verify_file_hash(file, hash_value, "sha256") is True

    def test_verify_with_progress(self, tmp_path):
        """Test verification with progress callback on large file."""
        file = tmp_path / "large.bin"
        size = 5 * 1024 * 1024  # 5MB
        with open(file, "wb") as f:
            f.write(b"\x00" * size)

        progress_updates = []

        def on_progress(bytes_read, total_bytes):
            progress_updates.append((bytes_read, total_bytes))

        _hash_value = compute_file_hash(file, "sha256", progress_callback=on_progress)

        # Should have multiple progress updates
        assert len(progress_updates) > 1
        # All updates should have same total
        assert all(total == size for _, total in progress_updates)
        # Last update should be complete
        assert progress_updates[-1][0] == size

    def test_verify_multiple_files_workflow(self, tmp_path):
        """Test complete workflow: download multiple files and verify."""
        # Create test files
        files = {
            "file1.txt": b"Content of file 1",
            "file2.txt": b"Content of file 2",
            "file3.txt": b"Content of file 3",
        }

        hashes = {}
        for filename, content in files.items():
            file_path = tmp_path / filename
            file_path.write_bytes(content)
            hashes[filename] = hashlib.sha256(content).hexdigest()

        # Create hash file
        hash_file = tmp_path / "SHA256SUMS"
        with open(hash_file, "w") as f:
            for filename, hash_value in hashes.items():
                f.write(f"{hash_value}  {filename}\n")

        # Verify all files
        results = verify_hash_file(hash_file, tmp_path, "sha256")

        assert len(results) == 3
        assert all(results.values())

    def test_detect_corrupted_file(self, tmp_path):
        """Test detecting file corruption."""
        file = tmp_path / "file.txt"
        original_content = b"Original content"
        file.write_bytes(original_content)

        # Compute hash of original
        original_hash = compute_file_hash(file, "sha256")

        # Corrupt the file
        corrupted_content = b"Corrupted content"
        file.write_bytes(corrupted_content)

        # Verification should fail
        assert verify_file_hash(file, original_hash, "sha256") is False


@pytest.mark.integration
class TestHashFileFormats:
    """Test different hash file formats."""

    def test_gnu_coreutils_format(self, tmp_path):
        """Test GNU coreutils SHA256SUMS format."""
        # Create files
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_bytes(b"test1")
        file2.write_bytes(b"test2")

        # Create hash file in GNU format
        hash_file = tmp_path / "SHA256SUMS"
        hash1 = hashlib.sha256(b"test1").hexdigest()
        hash2 = hashlib.sha256(b"test2").hexdigest()

        hash_file.write_text(
            f"""{hash1}  test1.txt
{hash2}  test2.txt
"""
        )

        hashes = parse_hash_file(hash_file)
        assert len(hashes) == 2

        results = verify_hash_file(hash_file, tmp_path, "sha256")
        assert all(results.values())

    def test_binary_mode_indicator(self, tmp_path):
        """Test format with binary mode indicator (asterisk)."""
        file = tmp_path / "binary.bin"
        file.write_bytes(b"\x00\x01\x02\x03")

        hash_file = tmp_path / "SHA256SUMS"
        hash_value = hashlib.sha256(b"\x00\x01\x02\x03").hexdigest()
        hash_file.write_text(f"{hash_value} *binary.bin\n")

        results = verify_hash_file(hash_file, tmp_path, "sha256")
        assert results["binary.bin"] is True

    def test_mixed_format_file(self, tmp_path):
        """Test hash file with comments and mixed formats."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        hash_file = tmp_path / "SHA256SUMS"
        hash1 = hashlib.sha256(b"content1").hexdigest()
        hash2 = hashlib.sha256(b"content2").hexdigest()

        hash_file.write_text(
            f"""# Generated on 2024-01-01
# SHA256 checksums

{hash1}  file1.txt

# Another file
{hash2} *file2.txt
"""
        )

        hashes = parse_hash_file(hash_file)
        assert len(hashes) == 2


@pytest.mark.integration
class TestHashVerifierIntegration:
    """Test HashVerifier class in real scenarios."""

    def test_verifier_with_multiple_algorithms(self, tmp_path):
        """Test verifier with multiple hash algorithms."""
        file = tmp_path / "test.bin"
        content = b"test content for verification"
        file.write_bytes(content)

        verifier = HashVerifier()

        # Verify with SHA256
        sha256_hash = hashlib.sha256(content).hexdigest()
        result = verifier.verify_file(file, f"sha256:{sha256_hash}")
        assert result.valid is True

        # Verify with SHA512
        sha512_hash = hashlib.sha512(content).hexdigest()
        result = verifier.verify_file(file, f"sha512:{sha512_hash}")
        assert result.valid is True

        # Verify with MD5
        md5_hash = hashlib.md5(content).hexdigest()
        result = verifier.verify_file(file, f"md5:{md5_hash}")
        assert result.valid is True

    def test_verifier_workflow(self, tmp_path):
        """Test complete verification workflow."""
        # Simulate download scenario
        file = tmp_path / "downloaded.tar.gz"
        content = b"x" * 1024 * 100  # 100KB
        file.write_bytes(content)

        # Compute expected hash (like from a server)
        expected_hash = hashlib.sha256(content).hexdigest()

        # Verify downloaded file
        verifier = HashVerifier()
        result = verifier.verify_file(file, expected_hash)

        assert result.valid is True
        assert result.algorithm == "sha256"
        assert result.expected_hash == expected_hash
        assert result.actual_hash == expected_hash


@pytest.mark.integration
class TestSecurityFeatures:
    """Test security-related features."""

    def test_timing_attack_resistance(self, tmp_path):
        """Test that hash comparison is timing-attack resistant.

        Tests the constant-time comparison directly to avoid file I/O variance.
        Uses statistical methods to handle measurement noise.
        """
        # Import the private function for testing
        from toolchainkit.core.verification import _constant_time_compare
        import time

        # Use realistic hash strings (SHA256 = 64 hex chars)
        correct_hash = (
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )

        # Test with various wrong hashes that differ at different positions
        wrong_hashes = [
            "a" * 64,  # All wrong
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a00",  # Last char wrong
            "af86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  # First char wrong
            "9f86d081884c7d659a2feaa0c55ad015" + "b" * 32,  # Second half wrong
        ]

        # Warm up - run a few times to stabilize cache and timing
        for _ in range(100):
            _constant_time_compare(correct_hash, wrong_hashes[0])

        median_times = []
        iterations = 1000  # Many iterations for better statistical stability

        for wrong_hash in wrong_hashes:
            iteration_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                _constant_time_compare(correct_hash, wrong_hash)
                elapsed = time.perf_counter() - start
                iteration_times.append(elapsed)

            # Use median instead of mean (more robust to outliers)
            iteration_times.sort()
            median_time = iteration_times[len(iteration_times) // 2]
            median_times.append(median_time)

        # All different wrong hashes should take similar time
        # (constant-time means independent of where the difference is)
        overall_median = sorted(median_times)[len(median_times) // 2]

        # Use very generous tolerance since we're measuring microsecond-level operations
        # where system noise is significant. The goal is to detect timing attacks,
        # not to perfectly measure constant-time behavior under all system conditions.
        # 2x tolerance allows for measurement noise while still catching timing attacks.
        max_ratio = max(t / overall_median for t in median_times)
        assert (
            max_ratio < 2.0
        ), f"Timing variance too high: {median_times}, median={overall_median}, max_ratio={max_ratio:.2f}"

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        hash_file = tmp_path / "SHA256SUMS"

        # Try various path traversal techniques
        hash_file.write_text(
            """abc123  ../../../etc/passwd
def456  ..\\..\\windows\\system32\\config\\sam
ghi789  /etc/shadow
jkl012  C:\\Windows\\System32\\drivers\\etc\\hosts
mno345  safe_file.txt
"""
        )

        hashes = parse_hash_file(hash_file)

        # Only safe file should be parsed
        assert len(hashes) == 1
        assert "safe_file.txt" in hashes

    def test_invalid_hash_rejection(self, tmp_path):
        """Test that invalid hashes are properly rejected."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test")

        from toolchainkit.core.verification import HashFormatError

        # Test various invalid hash formats
        invalid_hashes = [
            "not-a-hash",
            "12345",  # Too short
            "gg" * 32,  # Invalid hex characters
            "123 456",  # Contains space
            "",  # Empty
        ]

        for invalid_hash in invalid_hashes:
            with pytest.raises(HashFormatError):
                verify_file_hash(file, invalid_hash, "sha256")


@pytest.mark.integration
@pytest.mark.slow
class TestGPGIntegration:
    """Test GPG signature verification (if GPG available)."""

    def test_gpg_availability(self):
        """Test checking if GPG is available."""
        try:
            result = subprocess.run(
                ["gpg", "--version"], capture_output=True, timeout=5
            )
            gpg_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            gpg_available = False

        # Just check that we can detect GPG
        assert isinstance(gpg_available, bool)

    def test_gpg_signature_handling(self, tmp_path):
        """Test GPG signature verification handling."""
        file = tmp_path / "file.txt"
        sig_file = tmp_path / "file.txt.asc"

        file.write_bytes(b"test content")
        sig_file.write_bytes(b"fake signature")

        # Should handle gracefully whether GPG is installed or not
        verified, message = verify_gpg_signature(file, sig_file)

        assert isinstance(verified, bool)
        assert isinstance(message, str)
        assert len(message) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
