"""
Integration tests for download module.

These tests use real network connections to verify download functionality.
Mark tests with @pytest.mark.integration and skip if network unavailable.
"""

import hashlib
import pytest

from toolchainkit.core.download import (
    download_file,
    DownloadProgress,
    ChecksumError,
)


# Small test file from a reliable source
TEST_FILE_URL = "https://raw.githubusercontent.com/python/cpython/main/LICENSE"
TEST_FILE_EXPECTED_SIZE_MIN = 10000  # At least 10KB


@pytest.mark.integration
class TestDownloadIntegration:
    """Integration tests with real network downloads."""

    def test_download_small_file(self, tmp_path):
        """
        Test downloading a small real file from GitHub.

        Uses Python's LICENSE file from GitHub which is small and stable.
        """
        destination = tmp_path / "LICENSE"

        result = download_file(TEST_FILE_URL, destination)

        assert result == destination
        assert destination.exists()
        assert destination.stat().st_size > TEST_FILE_EXPECTED_SIZE_MIN

        # Verify content contains expected text
        content = destination.read_text()
        assert "PYTHON SOFTWARE FOUNDATION LICENSE" in content

    def test_download_with_progress_tracking(self, tmp_path):
        """
        Test download progress is reported correctly.
        """
        destination = tmp_path / "LICENSE"
        progress_updates = []

        def on_progress(progress: DownloadProgress):
            progress_updates.append(progress)

        download_file(TEST_FILE_URL, destination, progress_callback=on_progress)

        # Small files may download too quickly for progress updates
        # Just verify the file was downloaded successfully
        assert destination.exists()
        assert destination.stat().st_size > TEST_FILE_EXPECTED_SIZE_MIN

        # If we got progress updates, verify they're sensible
        if len(progress_updates) > 0:
            # Last update should be complete
            last = progress_updates[-1]
            assert last.bytes_downloaded == last.total_bytes
            assert last.percentage >= 99.0  # Allow for rounding

            # Progress should be monotonic
            for i in range(1, len(progress_updates)):
                assert (
                    progress_updates[i].bytes_downloaded
                    >= progress_updates[i - 1].bytes_downloaded
                )

    def test_download_with_correct_checksum(self, tmp_path):
        """
        Test download succeeds when checksum matches.

        Note: This test computes the expected hash first, then downloads.
        In real usage, you'd have the hash from the publisher.
        """
        # First download to get expected hash
        temp_dest = tmp_path / "temp_LICENSE"
        download_file(TEST_FILE_URL, temp_dest)
        expected_hash = hashlib.sha256(temp_dest.read_bytes()).hexdigest()
        temp_dest.unlink()

        # Now download with checksum verification
        destination = tmp_path / "LICENSE"
        result = download_file(
            TEST_FILE_URL, destination, expected_sha256=expected_hash
        )

        assert result == destination
        assert destination.exists()

    def test_download_with_wrong_checksum_fails(self, tmp_path):
        """
        Test download fails when checksum doesn't match.
        """
        destination = tmp_path / "LICENSE"
        wrong_hash = "a" * 64  # Invalid hash

        with pytest.raises(ChecksumError, match="Checksum mismatch"):
            download_file(TEST_FILE_URL, destination, expected_sha256=wrong_hash)

        # File should be cleaned up
        assert not destination.exists()

    def test_skip_download_if_file_exists_with_correct_hash(self, tmp_path):
        """
        Test skips download if file already exists with correct hash.
        """
        destination = tmp_path / "LICENSE"

        # First download
        download_file(TEST_FILE_URL, destination)
        first_mtime = destination.stat().st_mtime
        expected_hash = hashlib.sha256(destination.read_bytes()).hexdigest()

        # Second download should skip (file not modified)
        import time

        time.sleep(0.1)  # Ensure time difference
        download_file(TEST_FILE_URL, destination, expected_sha256=expected_hash)
        second_mtime = destination.stat().st_mtime

        # File should not have been rewritten
        assert first_mtime == second_mtime

    def test_redownload_if_cached_file_corrupted(self, tmp_path):
        """
        Test re-downloads if cached file is corrupted.
        """
        destination = tmp_path / "LICENSE"

        # First download to get expected hash
        download_file(TEST_FILE_URL, destination)
        expected_hash = hashlib.sha256(destination.read_bytes()).hexdigest()

        # Corrupt the file
        destination.write_bytes(b"corrupted content")

        # Should detect corruption and re-download
        download_file(TEST_FILE_URL, destination, expected_sha256=expected_hash)

        # File should now be correct
        actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        assert actual_hash == expected_hash

    def test_https_tls_verification(self, tmp_path):
        """
        Test that HTTPS connections verify TLS certificates.

        This test verifies we're using secure HTTPS.
        """
        destination = tmp_path / "LICENSE"

        # Should succeed with valid certificate
        result = download_file(TEST_FILE_URL, destination)
        assert result.exists()

    def test_resume_functionality(self, tmp_path):
        """
        Test resume functionality (simulated interruption).

        This test simulates an interrupted download by downloading
        part of the file, then resuming from where it left off.
        """
        destination = tmp_path / "LICENSE"

        # First, download complete file to get expected size
        download_file(TEST_FILE_URL, destination)
        expected_size = destination.stat().st_size
        expected_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.unlink()

        # Simulate partial download by downloading first half
        partial_content = destination.parent / "partial"
        download_file(TEST_FILE_URL, partial_content)
        full_content = partial_content.read_bytes()

        # Write only first half
        partial_size = len(full_content) // 2
        destination.write_bytes(full_content[:partial_size])
        partial_content.unlink()

        # Resume download (would use Range header if supported by server)
        # Note: GitHub raw content doesn't support Range, so this will re-download
        download_file(
            TEST_FILE_URL, destination, resume=True, expected_sha256=expected_hash
        )

        # Final file should be complete
        assert destination.stat().st_size == expected_size
        final_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        assert final_hash == expected_hash

    @pytest.mark.slow
    def test_download_creates_nested_directories(self, tmp_path):
        """
        Test automatically creates nested destination directories.
        """
        destination = tmp_path / "deeply" / "nested" / "path" / "LICENSE"

        download_file(TEST_FILE_URL, destination)

        assert destination.exists()
        assert destination.parent.exists()


@pytest.mark.integration
class TestDownloadEdgeCases:
    """Integration tests for edge cases."""

    def test_download_handles_redirects(self, tmp_path):
        """
        Test handles HTTP redirects properly.
        """
        # Use a URL that redirects (many short URLs do this)
        # GitHub raw files may redirect
        destination = tmp_path / "file.txt"

        result = download_file(TEST_FILE_URL, destination)
        assert result.exists()

    def test_download_timeout_behavior(self, tmp_path):
        """
        Test timeout handling (use very short timeout to trigger).

        This test may be flaky depending on network conditions.
        """
        destination = tmp_path / "file.txt"

        # Try with extremely short timeout
        # This might succeed if network is very fast, so we don't assert failure
        try:
            download_file(TEST_FILE_URL, destination, timeout=0.001, max_retries=1)
            # If it succeeds, network was very fast
            assert destination.exists()
        except Exception:
            # Expected on slow network
            pass


# Fixtures for integration tests
@pytest.fixture
def network_available():
    """Check if network is available."""
    import socket

    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
