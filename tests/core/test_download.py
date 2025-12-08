"""
Unit tests for download module.

Tests download functionality with mocked network requests.
"""

import hashlib
import pytest
import responses
from unittest.mock import patch

from toolchainkit.core.download import (
    download_file,
    verify_checksum,
    format_progress,
    DownloadProgress,
    DownloadError,
    ChecksumError,
    StreamingHasher,
)


class TestStreamingHasher:
    """Test StreamingHasher class."""

    def test_create_sha256_hasher(self):
        """Test creating SHA256 hasher."""
        hasher = StreamingHasher("sha256")
        assert hasher.algorithm == "sha256"

    def test_create_sha512_hasher(self):
        """Test creating SHA512 hasher."""
        hasher = StreamingHasher("sha512")
        assert hasher.algorithm == "sha512"

    def test_create_md5_hasher(self):
        """Test creating MD5 hasher."""
        # MD5 logs a warning but doesn't raise
        hasher = StreamingHasher("md5")
        assert hasher.algorithm == "md5"

    def test_unsupported_algorithm(self):
        """Test unsupported algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            StreamingHasher("sha1")

    def test_update_and_finalize(self):
        """Test updating hasher and getting final hash."""
        hasher = StreamingHasher("sha256")
        hasher.update(b"hello ")
        hasher.update(b"world")

        result = hasher.finalize()

        # Verify against known SHA256 of "hello world"
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_verify_matching_hash(self):
        """Test verify returns True for matching hash."""
        hasher = StreamingHasher("sha256")
        data = b"test data"
        hasher.update(data)

        expected = hashlib.sha256(data).hexdigest()
        assert hasher.verify(expected) is True

    def test_verify_non_matching_hash(self):
        """Test verify returns False for non-matching hash."""
        hasher = StreamingHasher("sha256")
        hasher.update(b"test data")

        wrong_hash = "a" * 64  # Invalid hash
        assert hasher.verify(wrong_hash) is False

    def test_case_insensitive_verify(self):
        """Test verify is case-insensitive."""
        hasher = StreamingHasher("sha256")
        data = b"test"
        hasher.update(data)

        expected = hashlib.sha256(data).hexdigest()
        assert hasher.verify(expected.upper()) is True


class TestDownloadProgress:
    """Test DownloadProgress dataclass."""

    def test_create_progress(self):
        """Test creating progress object."""
        progress = DownloadProgress(
            bytes_downloaded=50,
            total_bytes=100,
            percentage=50.0,
            speed_bps=1024,
            eta_seconds=10,
        )

        assert progress.bytes_downloaded == 50
        assert progress.total_bytes == 100
        assert progress.percentage == 50.0
        assert progress.speed_bps == 1024
        assert progress.eta_seconds == 10

    def test_progress_to_string(self):
        """Test progress string representation."""
        progress = DownloadProgress(
            bytes_downloaded=52428800,  # 50 MB
            total_bytes=104857600,  # 100 MB
            percentage=50.0,
            speed_bps=1048576,  # 1 MB/s
            eta_seconds=50,
        )

        result = str(progress)

        assert "50.0/100.0 MB" in result
        assert "50.0%" in result
        assert "1.0 MB/s" in result
        assert "ETA: 50s" in result


class TestFormatProgress:
    """Test format_progress function."""

    def test_format_with_known_size(self):
        """Test formatting progress with known total size."""
        progress = DownloadProgress(
            bytes_downloaded=10485760,  # 10 MB
            total_bytes=104857600,  # 100 MB
            percentage=10.0,
            speed_bps=2097152,  # 2 MB/s
            eta_seconds=45,
        )

        result = format_progress(progress)

        assert "10.0/100.0 MB" in result
        assert "(10.0%)" in result
        assert "2.0 MB/s" in result
        assert "ETA: 45s" in result

    def test_format_with_unknown_size(self):
        """Test formatting progress with unknown total size."""
        progress = DownloadProgress(
            bytes_downloaded=10485760,  # 10 MB
            total_bytes=0,  # Unknown
            percentage=0.0,
            speed_bps=1048576,  # 1 MB/s
            eta_seconds=0,
        )

        result = format_progress(progress)

        assert "10.0 MB" in result
        assert "1.0 MB/s" in result
        assert "ETA" not in result  # No ETA for unknown size


class TestVerifyChecksum:
    """Test verify_checksum function."""

    def test_verify_matching_checksum(self, tmp_path):
        """Test verify returns True for matching checksum."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()

        assert verify_checksum(file, expected) is True

    def test_verify_non_matching_checksum(self, tmp_path):
        """Test verify returns False for non-matching checksum."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"test content")

        wrong_hash = "a" * 64

        assert verify_checksum(file, wrong_hash) is False

    def test_verify_case_insensitive(self, tmp_path):
        """Test verify is case-insensitive."""
        file = tmp_path / "test.txt"
        content = b"test content"
        file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()

        assert verify_checksum(file, expected.upper()) is True

    def test_verify_nonexistent_file(self, tmp_path):
        """Test verify raises FileNotFoundError for nonexistent file."""
        file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            verify_checksum(file, "a" * 64)


class TestDownloadFile:
    """Test download_file function."""

    @responses.activate
    def test_simple_download(self, tmp_path):
        """Test simple download without checksum."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_file(url, destination)

        assert result == destination
        assert destination.read_bytes() == content

    @responses.activate
    def test_download_with_checksum_verification(self, tmp_path):
        """Test download with checksum verification."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"
        expected_hash = hashlib.sha256(content).hexdigest()

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_file(url, destination, expected_sha256=expected_hash)

        assert result == destination
        assert destination.read_bytes() == content

    @responses.activate
    def test_download_with_wrong_checksum(self, tmp_path):
        """Test download fails with wrong checksum."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"
        wrong_hash = "a" * 64

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        with pytest.raises(ChecksumError, match="Checksum mismatch"):
            download_file(url, destination, expected_sha256=wrong_hash)

        # Verify file was cleaned up
        assert not destination.exists()

    @responses.activate
    def test_download_with_progress_callback(self, tmp_path):
        """Test download reports progress."""
        url = "https://example.com/file.txt"
        content = b"x" * 100000  # 100KB
        destination = tmp_path / "file.txt"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        progress_updates = []

        def on_progress(progress):
            progress_updates.append(progress)

        download_file(url, destination, progress_callback=on_progress)

        # Should have received at least one progress update
        assert len(progress_updates) > 0

        # Last update should show 100% complete
        last_progress = progress_updates[-1]
        assert last_progress.bytes_downloaded == len(content)

    def test_skip_download_if_cached_file_valid(self, tmp_path):
        """Test skips download if cached file has correct checksum."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"
        expected_hash = hashlib.sha256(content).hexdigest()

        # Pre-create file with correct content
        destination.write_bytes(content)

        # Don't add responses mock - should not make HTTP request

        result = download_file(url, destination, expected_sha256=expected_hash)

        assert result == destination
        assert destination.read_bytes() == content

    @responses.activate
    def test_redownload_if_cached_file_invalid(self, tmp_path):
        """Test re-downloads if cached file has wrong checksum."""
        url = "https://example.com/file.txt"
        correct_content = b"correct content"
        destination = tmp_path / "file.txt"
        expected_hash = hashlib.sha256(correct_content).hexdigest()

        # Pre-create file with wrong content
        destination.write_bytes(b"wrong content")

        responses.add(
            responses.GET,
            url,
            body=correct_content,
            status=200,
            headers={"content-length": str(len(correct_content))},
        )

        result = download_file(url, destination, expected_sha256=expected_hash)

        assert result == destination
        assert destination.read_bytes() == correct_content

    @responses.activate
    def test_resume_partial_download(self, tmp_path):
        """Test resumes partial download."""
        url = "https://example.com/file.txt"
        full_content = b"x" * 1000
        partial_size = 500
        destination = tmp_path / "file.txt"

        # Pre-create partial file
        destination.write_bytes(full_content[:partial_size])

        # Mock should receive Range header
        def request_callback(request):
            assert "Range" in request.headers
            assert request.headers["Range"] == f"bytes={partial_size}-"
            return (200, {}, full_content[partial_size:])

        responses.add_callback(
            responses.GET,
            url,
            callback=request_callback,
            content_type="application/octet-stream",
        )

        result = download_file(url, destination, resume=True)

        assert result == destination
        assert len(destination.read_bytes()) == len(full_content)

    @responses.activate
    def test_retry_on_network_error(self, tmp_path):
        """Test retries on network error."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"

        # First two requests fail with HTTP errors, third succeeds
        responses.add(responses.GET, url, status=500)  # Server error
        responses.add(responses.GET, url, status=503)  # Service unavailable
        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_file(url, destination, max_retries=3)

        assert result == destination
        assert destination.read_bytes() == content

    @responses.activate
    def test_fail_after_max_retries(self, tmp_path):
        """Test raises DownloadError after max retries."""
        url = "https://example.com/file.txt"
        destination = tmp_path / "file.txt"

        # All requests fail with HTTP errors
        for _ in range(3):
            responses.add(responses.GET, url, status=500)

        with pytest.raises(DownloadError, match="Download failed after 3 attempts"):
            download_file(url, destination, max_retries=3)

    @responses.activate
    def test_http_404_error(self, tmp_path):
        """Test handles HTTP 404 error."""
        url = "https://example.com/notfound.txt"
        destination = tmp_path / "file.txt"

        responses.add(responses.GET, url, status=404)

        with pytest.raises(DownloadError):
            download_file(url, destination)

    @responses.activate
    def test_http_500_error(self, tmp_path):
        """Test handles HTTP 500 error."""
        url = "https://example.com/error.txt"
        destination = tmp_path / "file.txt"

        responses.add(responses.GET, url, status=500)

        with pytest.raises(DownloadError):
            download_file(url, destination)

    def test_empty_url_raises_valueerror(self, tmp_path):
        """Test empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            download_file("", tmp_path / "file.txt")

    def test_empty_destination_raises_valueerror(self):
        """Test empty destination raises ValueError."""
        with pytest.raises(ValueError, match="Destination path cannot be empty"):
            download_file("https://example.com/file.txt", None)

    @responses.activate
    def test_creates_destination_directory(self, tmp_path):
        """Test automatically creates destination directory."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "nested" / "dir" / "file.txt"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_file(url, destination)

        assert result == destination
        assert destination.exists()
        assert destination.parent.exists()

    @responses.activate
    def test_download_without_content_length(self, tmp_path):
        """Test download works without Content-Length header."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            # No content-length header
        )

        result = download_file(url, destination)

        assert result == destination
        assert destination.read_bytes() == content

    @responses.activate
    @patch("time.sleep")  # Mock sleep to speed up test
    def test_exponential_backoff(self, mock_sleep, tmp_path):
        """Test uses exponential backoff between retries."""
        url = "https://example.com/file.txt"
        content = b"test content"
        destination = tmp_path / "file.txt"

        # First two fail with HTTP errors, third succeeds
        responses.add(responses.GET, url, status=500)
        responses.add(responses.GET, url, status=503)
        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        download_file(url, destination, max_retries=3)

        # Verify exponential backoff: 2^0=1s, 2^1=2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2^0
        mock_sleep.assert_any_call(2)  # 2^1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
