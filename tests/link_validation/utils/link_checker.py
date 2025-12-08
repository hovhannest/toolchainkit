"""
Link validation utilities for testing external URLs.

Provides tiered validation:
- HEAD: Quick HTTP HEAD request to check URL exists
- PARTIAL: Download first N bytes to verify content accessibility
- FULL: Complete download for hash validation
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

if TYPE_CHECKING:
    from tests.link_validation.utils.hash_validator import HashValidationResult

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation level for link checking."""

    HEAD = "head"
    PARTIAL = "partial"
    FULL = "full"


class LinkStatus(Enum):
    """Result status of link validation."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"  # 404
    FORBIDDEN = "forbidden"  # 403
    SERVER_ERROR = "server_error"  # 5xx
    NETWORK_ERROR = "network_error"  # Connection/timeout issues
    INVALID_URL = "invalid_url"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ValidationResult:
    """Result of link validation."""

    url: str
    status: LinkStatus
    validation_level: ValidationLevel
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    content_length: Optional[int] = None
    content_type: Optional[str] = None
    redirected_url: Optional[str] = None
    bytes_downloaded: int = 0

    @property
    def is_success(self) -> bool:
        """Check if validation was successful."""
        return self.status == LinkStatus.SUCCESS

    @property
    def is_permanent_failure(self) -> bool:
        """Check if failure is permanent (not transient network issue)."""
        return self.status in [
            LinkStatus.NOT_FOUND,
            LinkStatus.FORBIDDEN,
            LinkStatus.INVALID_URL,
        ]

    @property
    def is_transient_failure(self) -> bool:
        """Check if failure might be transient."""
        return self.status in [
            LinkStatus.NETWORK_ERROR,
            LinkStatus.SERVER_ERROR,
        ]


class LinkChecker:
    """
    Validates external URLs with tiered validation levels.

    Example:
        >>> checker = LinkChecker(timeout=10, max_retries=3)
        >>> result = checker.validate(
        ...     "https://example.com/file.tar.gz",
        ...     level=ValidationLevel.HEAD
        ... )
        >>> assert result.is_success
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        partial_size_bytes: int = 1024 * 1024,  # 1 MB
        user_agent: str = "ToolchainKit-LinkValidator/1.0",
        verify_ssl: bool = True,
    ):
        """
        Initialize link checker.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            partial_size_bytes: Bytes to download for partial validation
            user_agent: User agent string for requests
            verify_ssl: Whether to verify SSL certificates
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.partial_size_bytes = partial_size_bytes
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl

    def validate(
        self,
        url: str,
        level: ValidationLevel = ValidationLevel.HEAD,
        destination: Optional[Path] = None,
    ) -> ValidationResult:
        """
        Validate URL at specified level.

        Args:
            url: URL to validate
            level: Validation level (HEAD, PARTIAL, or FULL)
            destination: Destination path for FULL download (required for FULL)

        Returns:
            ValidationResult with status and details
        """
        # Validate URL format
        if not self._is_valid_url(url):
            return ValidationResult(
                url=url,
                status=LinkStatus.INVALID_URL,
                validation_level=level,
                response_time_ms=0,
                error_message="Invalid URL format",
            )

        # Route to appropriate validation method
        if level == ValidationLevel.HEAD:
            return self._validate_head(url)
        elif level == ValidationLevel.PARTIAL:
            return self._validate_partial(url)
        elif level == ValidationLevel.FULL:
            if not destination:
                raise ValueError("destination required for FULL validation")
            return self._validate_full(url, destination)
        else:
            raise ValueError(f"Unknown validation level: {level}")

    def validate_with_hash(
        self, url: str, expected_hash: str, destination: Path, algorithm: str = "sha256"
    ) -> tuple[ValidationResult, Optional["HashValidationResult"]]:
        """
        Download file and validate hash using existing verification utilities.

        This is a convenience method that combines link validation and hash validation.
        It first downloads the file using FULL validation level, then validates the hash.

        Args:
            url: URL to download and validate
            expected_hash: Expected hash value (hex string, optionally with "algorithm:" prefix)
            destination: Path where file should be saved
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            Tuple of (link_validation_result, hash_validation_result)
            hash_validation_result is None if link validation failed

        Example:
            >>> checker = LinkChecker()
            >>> link_result, hash_result = checker.validate_with_hash(
            ...     'https://example.com/file.tar.gz',
            ...     'abc123...',
            ...     Path('file.tar.gz')
            ... )
            >>> if link_result.is_success and hash_result and hash_result.matches:
            ...     print("File downloaded and validated successfully")
        """
        from tests.link_validation.utils.hash_validator import HashValidator

        # First, download the file
        link_result = self.validate(url, ValidationLevel.FULL, destination)

        # If download failed, return early
        if not link_result.is_success:
            return link_result, None

        # Validate hash
        validator = HashValidator(algorithm=algorithm)
        hash_result = validator.validate_file(destination, expected_hash)

        return link_result, hash_result

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
            ]
        except Exception:
            return False

    def _validate_head(self, url: str) -> ValidationResult:
        """
        Validate URL using HTTP HEAD request.

        Fast check that only verifies URL is accessible.
        """
        for attempt in range(self.max_retries):
            start_time = time.time()

            try:
                response = requests.head(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers={"User-Agent": self.user_agent},
                    verify=self.verify_ssl,
                )

                response_time_ms = (time.time() - start_time) * 1000

                # Check status code
                if response.status_code == 200:
                    return ValidationResult(
                        url=url,
                        status=LinkStatus.SUCCESS,
                        validation_level=ValidationLevel.HEAD,
                        response_time_ms=response_time_ms,
                        status_code=response.status_code,
                        content_length=response.headers.get("Content-Length"),
                        content_type=response.headers.get("Content-Type"),
                        redirected_url=response.url if response.url != url else None,
                    )
                elif response.status_code == 404:
                    return self._create_error_result(
                        url,
                        ValidationLevel.HEAD,
                        LinkStatus.NOT_FOUND,
                        response.status_code,
                        "URL not found",
                        response_time_ms,
                    )
                elif response.status_code == 403:
                    return self._create_error_result(
                        url,
                        ValidationLevel.HEAD,
                        LinkStatus.FORBIDDEN,
                        response.status_code,
                        "Access forbidden",
                        response_time_ms,
                    )
                elif 500 <= response.status_code < 600:
                    # Server error - might be transient
                    if attempt < self.max_retries - 1:
                        self._sleep_with_backoff(attempt)
                        continue
                    return self._create_error_result(
                        url,
                        ValidationLevel.HEAD,
                        LinkStatus.SERVER_ERROR,
                        response.status_code,
                        f"Server error: {response.status_code}",
                        response_time_ms,
                    )
                else:
                    return self._create_error_result(
                        url,
                        ValidationLevel.HEAD,
                        LinkStatus.UNKNOWN_ERROR,
                        response.status_code,
                        f"Unexpected status: {response.status_code}",
                        response_time_ms,
                    )

            except (Timeout, ConnectionError) as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    logger.debug(f"Network error on attempt {attempt + 1}: {e}")
                    self._sleep_with_backoff(attempt)
                    continue
                return self._create_error_result(
                    url,
                    ValidationLevel.HEAD,
                    LinkStatus.NETWORK_ERROR,
                    None,
                    f"Network error: {str(e)}",
                    response_time_ms,
                )

            except RequestException as e:
                response_time_ms = (time.time() - start_time) * 1000
                return self._create_error_result(
                    url,
                    ValidationLevel.HEAD,
                    LinkStatus.UNKNOWN_ERROR,
                    None,
                    f"Request error: {str(e)}",
                    response_time_ms,
                )

        # Should not reach here, but just in case
        return self._create_error_result(
            url,
            ValidationLevel.HEAD,
            LinkStatus.UNKNOWN_ERROR,
            None,
            "Validation failed after retries",
            0,
        )

    def _validate_partial(self, url: str) -> ValidationResult:
        """
        Validate URL by downloading first N bytes.

        Medium-level check that verifies content is accessible.
        """
        for attempt in range(self.max_retries):
            start_time = time.time()

            try:
                headers = {
                    "User-Agent": self.user_agent,
                    "Range": f"bytes=0-{self.partial_size_bytes - 1}",
                }

                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    stream=True,
                    allow_redirects=True,
                    verify=self.verify_ssl,
                )

                response.raise_for_status()

                # Download partial content
                bytes_downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    bytes_downloaded += len(chunk)
                    if bytes_downloaded >= self.partial_size_bytes:
                        break

                response_time_ms = (time.time() - start_time) * 1000

                return ValidationResult(
                    url=url,
                    status=LinkStatus.SUCCESS,
                    validation_level=ValidationLevel.PARTIAL,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    content_length=response.headers.get("Content-Length"),
                    content_type=response.headers.get("Content-Type"),
                    redirected_url=response.url if response.url != url else None,
                    bytes_downloaded=bytes_downloaded,
                )

            except (Timeout, ConnectionError) as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    self._sleep_with_backoff(attempt)
                    continue
                return self._create_error_result(
                    url,
                    ValidationLevel.PARTIAL,
                    LinkStatus.NETWORK_ERROR,
                    None,
                    f"Network error: {str(e)}",
                    response_time_ms,
                )

            except HTTPError as e:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = e.response.status_code if e.response else None

                if status_code == 404:
                    status = LinkStatus.NOT_FOUND
                elif status_code == 403:
                    status = LinkStatus.FORBIDDEN
                elif status_code and 500 <= status_code < 600:
                    if attempt < self.max_retries - 1:
                        self._sleep_with_backoff(attempt)
                        continue
                    status = LinkStatus.SERVER_ERROR
                else:
                    status = LinkStatus.UNKNOWN_ERROR

                return self._create_error_result(
                    url,
                    ValidationLevel.PARTIAL,
                    status,
                    status_code,
                    str(e),
                    response_time_ms,
                )

            except RequestException as e:
                response_time_ms = (time.time() - start_time) * 1000
                return self._create_error_result(
                    url,
                    ValidationLevel.PARTIAL,
                    LinkStatus.UNKNOWN_ERROR,
                    None,
                    f"Request error: {str(e)}",
                    response_time_ms,
                )

        return self._create_error_result(
            url,
            ValidationLevel.PARTIAL,
            LinkStatus.UNKNOWN_ERROR,
            None,
            "Validation failed after retries",
            0,
        )

    def _validate_full(self, url: str, destination: Path) -> ValidationResult:
        """
        Validate URL by downloading complete file.

        Full validation for hash checking (implemented in Task 003).
        """
        for attempt in range(self.max_retries):
            start_time = time.time()

            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    stream=True,
                    allow_redirects=True,
                    headers={"User-Agent": self.user_agent},
                    verify=self.verify_ssl,
                )

                response.raise_for_status()

                # Download complete file
                destination.parent.mkdir(parents=True, exist_ok=True)
                bytes_downloaded = 0

                with open(destination, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)

                response_time_ms = (time.time() - start_time) * 1000

                return ValidationResult(
                    url=url,
                    status=LinkStatus.SUCCESS,
                    validation_level=ValidationLevel.FULL,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    content_length=response.headers.get("Content-Length"),
                    content_type=response.headers.get("Content-Type"),
                    redirected_url=response.url if response.url != url else None,
                    bytes_downloaded=bytes_downloaded,
                )

            except (Timeout, ConnectionError) as e:
                response_time_ms = (time.time() - start_time) * 1000
                if attempt < self.max_retries - 1:
                    self._sleep_with_backoff(attempt)
                    continue
                return self._create_error_result(
                    url,
                    ValidationLevel.FULL,
                    LinkStatus.NETWORK_ERROR,
                    None,
                    f"Network error: {str(e)}",
                    response_time_ms,
                )

            except HTTPError as e:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = e.response.status_code if e.response else None

                if status_code == 404:
                    status = LinkStatus.NOT_FOUND
                elif status_code == 403:
                    status = LinkStatus.FORBIDDEN
                elif status_code and 500 <= status_code < 600:
                    if attempt < self.max_retries - 1:
                        self._sleep_with_backoff(attempt)
                        continue
                    status = LinkStatus.SERVER_ERROR
                else:
                    status = LinkStatus.UNKNOWN_ERROR

                return self._create_error_result(
                    url,
                    ValidationLevel.FULL,
                    status,
                    status_code,
                    str(e),
                    response_time_ms,
                )

            except RequestException as e:
                response_time_ms = (time.time() - start_time) * 1000
                return self._create_error_result(
                    url,
                    ValidationLevel.FULL,
                    LinkStatus.UNKNOWN_ERROR,
                    None,
                    f"Request error: {str(e)}",
                    response_time_ms,
                )

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                return self._create_error_result(
                    url,
                    ValidationLevel.FULL,
                    LinkStatus.UNKNOWN_ERROR,
                    None,
                    f"Unexpected error: {str(e)}",
                    response_time_ms,
                )

        return self._create_error_result(
            url,
            ValidationLevel.FULL,
            LinkStatus.UNKNOWN_ERROR,
            None,
            "Validation failed after retries",
            0,
        )

    def _sleep_with_backoff(self, attempt: int):
        """Sleep with exponential backoff."""
        delay = self.retry_delay * (2**attempt)
        logger.debug(f"Retrying in {delay}s...")
        time.sleep(delay)

    def _create_error_result(
        self,
        url: str,
        level: ValidationLevel,
        status: LinkStatus,
        status_code: Optional[int],
        error_message: str,
        response_time_ms: float,
    ) -> ValidationResult:
        """Create error result."""
        return ValidationResult(
            url=url,
            status=status,
            validation_level=level,
            response_time_ms=response_time_ms,
            status_code=status_code,
            error_message=error_message,
        )


def quick_check_url(url: str, timeout: int = 10) -> bool:
    """
    Quick convenience function to check if URL is accessible.

    Args:
        url: URL to check
        timeout: Timeout in seconds

    Returns:
        True if accessible, False otherwise

    Example:
        >>> assert quick_check_url("https://github.com")
    """
    checker = LinkChecker(timeout=timeout, max_retries=2)
    result = checker.validate(url, level=ValidationLevel.HEAD)
    return result.is_success
