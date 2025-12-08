"""
Mock network operations for testing.

This module provides mock HTTP responses and downloaders to enable
testing of network-dependent code without actual network access.
"""

import io
from typing import Dict, Optional, Iterator


class MockResponse:
    """Mock HTTP response."""

    def __init__(
        self,
        content: bytes,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize mock response.

        Args:
            content: Response body content
            status_code: HTTP status code (default: 200)
            headers: Optional response headers
        """
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self._stream = io.BytesIO(content)
        self.ok = 200 <= status_code < 300

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """
        Iterate over content in chunks.

        Args:
            chunk_size: Size of chunks to read

        Yields:
            Chunks of response content
        """
        while True:
            chunk = self._stream.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def raise_for_status(self):
        """
        Raise exception for bad status codes.

        Raises:
            Exception: If status code indicates error (400-599)
        """
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP {self.status_code}")

    @property
    def text(self) -> str:
        """Get response content as text."""
        return self.content.decode("utf-8")

    def json(self) -> dict:
        """Get response content as JSON."""
        import json

        return json.loads(self.content)


class MockDownloader:
    """Mock HTTP downloader for testing."""

    def __init__(self):
        """Initialize mock downloader with empty response map."""
        self.mock_responses: Dict[str, bytes] = {}
        self.request_history: list = []

    def add_mock_response(self, url: str, content: bytes, status_code: int = 200):
        """
        Add mock response for URL.

        Args:
            url: URL to mock
            content: Response content
            status_code: HTTP status code (default: 200)
        """
        self.mock_responses[url] = (content, status_code)

    def get(
        self,
        url: str,
        stream: bool = False,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> MockResponse:
        """
        Mock HTTP GET request.

        Args:
            url: URL to request
            stream: Whether to stream response (ignored in mock)
            headers: Request headers (recorded but not used)
            timeout: Request timeout (ignored in mock)

        Returns:
            MockResponse object
        """
        # Record request for verification
        self.request_history.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
                "stream": stream,
                "timeout": timeout,
            }
        )

        # Return mock response if available
        if url in self.mock_responses:
            content, status_code = self.mock_responses[url]
            return MockResponse(content, status_code)

        # Return 404 for unmocked URLs
        return MockResponse(b"Not Found", status_code=404)

    def head(
        self, url: str, headers: Optional[Dict] = None, timeout: Optional[float] = None
    ) -> MockResponse:
        """
        Mock HTTP HEAD request.

        Args:
            url: URL to request
            headers: Request headers (recorded but not used)
            timeout: Request timeout (ignored in mock)

        Returns:
            MockResponse with empty content
        """
        # Record request
        self.request_history.append(
            {"method": "HEAD", "url": url, "headers": headers, "timeout": timeout}
        )

        # HEAD returns same status but no content
        if url in self.mock_responses:
            _, status_code = self.mock_responses[url]
            return MockResponse(b"", status_code)

        return MockResponse(b"", status_code=404)

    def clear_history(self):
        """Clear request history."""
        self.request_history.clear()
