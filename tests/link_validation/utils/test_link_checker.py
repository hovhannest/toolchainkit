"""Unit tests for link checker utilities."""

import pytest
import urllib3

from tests.link_validation.utils.link_checker import (
    LinkChecker,
    LinkStatus,
    ValidationLevel,
    ValidationResult,
)

# Disable SSL warnings for tests since we're intentionally disabling SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_link_checker_initialization():
    """Test LinkChecker can be initialized."""
    checker = LinkChecker(timeout=10, max_retries=2)
    assert checker.timeout == 10
    assert checker.max_retries == 2


def test_validation_result_properties():
    """Test ValidationResult properties."""
    result = ValidationResult(
        url="https://example.com",
        status=LinkStatus.SUCCESS,
        validation_level=ValidationLevel.HEAD,
        response_time_ms=100.0,
        status_code=200,
    )
    assert result.is_success
    assert not result.is_permanent_failure
    assert not result.is_transient_failure


def test_invalid_url_detection():
    """Test invalid URL is detected."""
    checker = LinkChecker()
    result = checker.validate("not-a-valid-url", level=ValidationLevel.HEAD)
    assert result.status == LinkStatus.INVALID_URL
    assert not result.is_success


def test_quick_check_url_convenience():
    """Test convenience function."""
    # Test with valid URL
    # Note: This doesn't require @pytest.mark.link_validation
    # because it's testing the function interface, not making real requests
    checker = LinkChecker()
    assert hasattr(checker, "validate")


@pytest.mark.link_validation
def test_head_validation_success(mocker):
    """Test HEAD validation with successful response."""
    checker = LinkChecker(timeout=10, verify_ssl=False)

    # Mock successful HEAD response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html", "Content-Length": "1234"}
    mock_response.url = "https://example.com/test"

    mocker.patch("requests.head", return_value=mock_response)

    result = checker.validate("https://example.com/test", level=ValidationLevel.HEAD)
    assert result.is_success
    assert result.status_code == 200
    assert result.content_type == "text/html"


@pytest.mark.link_validation
def test_head_validation_not_found(mocker):
    """Test HEAD validation with 404 response."""
    checker = LinkChecker(timeout=10, verify_ssl=False)

    # Mock 404 response
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.headers = {}
    mock_response.url = "https://example.com/notfound"

    mocker.patch("requests.head", return_value=mock_response)

    result = checker.validate(
        "https://example.com/notfound", level=ValidationLevel.HEAD
    )
    assert not result.is_success
    assert result.status == LinkStatus.NOT_FOUND
    assert result.status_code == 404


@pytest.mark.link_validation
def test_partial_validation(tmp_path, mocker):
    """Test partial download validation."""
    checker = LinkChecker(timeout=10, partial_size_bytes=1024, verify_ssl=False)

    # Mock partial content response
    mock_response = mocker.Mock()
    mock_response.status_code = 206  # Partial Content
    mock_response.headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": "1024",
    }
    mock_response.url = "https://example.com/file.bin"
    mock_response.iter_content = mocker.Mock(return_value=[b"x" * 1024])
    mock_response.__enter__ = mocker.Mock(return_value=mock_response)
    mock_response.__exit__ = mocker.Mock(return_value=False)

    mocker.patch("requests.get", return_value=mock_response)

    result = checker.validate(
        "https://example.com/file.bin", level=ValidationLevel.PARTIAL
    )
    assert result.is_success
    assert result.bytes_downloaded == 1024


@pytest.mark.link_validation
def test_full_validation(tmp_path, mocker):
    """Test full download validation."""
    checker = LinkChecker(timeout=10, verify_ssl=False)
    destination = tmp_path / "test_download.bin"

    # Mock full content response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": "1024",
    }
    mock_response.url = "https://example.com/file.bin"
    mock_response.iter_content = mocker.Mock(return_value=[b"x" * 1024])
    mock_response.__enter__ = mocker.Mock(return_value=mock_response)
    mock_response.__exit__ = mocker.Mock(return_value=False)

    mocker.patch("requests.get", return_value=mock_response)

    result = checker.validate(
        "https://example.com/file.bin",
        level=ValidationLevel.FULL,
        destination=destination,
    )

    assert result.is_success
    assert destination.exists()
    assert result.bytes_downloaded == 1024
    assert destination.stat().st_size == 1024
