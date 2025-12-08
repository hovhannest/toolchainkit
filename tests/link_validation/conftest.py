"""
Pytest fixtures for link validation tests.
"""

import warnings
import pytest
import urllib3
from pathlib import Path


# Suppress SSL warnings for link validation tests since we disable SSL verification
# for testing purposes (verify_ssl=False) to avoid certificate issues in test environments
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def pytest_collection_modifyitems(config, items):
    """Auto-apply link_validation marker to all tests in this directory."""
    for item in items:
        # Only apply marker to tests in the link_validation directory
        if (
            "link_validation" in str(item.fspath)
            and "link_validation" not in item.keywords
        ):
            item.add_marker(pytest.mark.link_validation)


@pytest.fixture
def validation_level(request) -> str:
    """
    Get validation level from command line.
    Returns: Validation level: 'head', 'partial', or 'full'
    """
    return request.config.getoption("--validation-level")


@pytest.fixture
def validation_cache_dir(request, tmp_path) -> Path:
    """
    Get or create validation cache directory.
    Uses command-line option if provided, otherwise creates temp directory.
    Returns: Path to cache directory
    """
    cache_dir_option = request.config.getoption("--validation-cache-dir")
    if cache_dir_option:
        cache_dir = Path(cache_dir_option)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    else:
        cache_dir = tmp_path / "link_validation_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


@pytest.fixture
def skip_if_head_only(validation_level):
    """
    Skip test if validation level is 'head' only.
    Use this for tests that require downloading content.
    """
    if validation_level == "head":
        pytest.skip("Skipping: validation-level=head (content download not enabled)")


@pytest.fixture
def skip_if_not_full(validation_level):
    """
    Skip test if validation level is not 'full'.
    Use this for tests that require complete file download.
    """
    if validation_level != "full":
        pytest.skip("Skipping: requires --validation-level=full")


@pytest.fixture(scope="session")
def session_validation_cache(request) -> Path:
    """
    Session-scoped cache directory shared across all tests.

    Uses a persistent directory in the tests/link_validation/.cache folder
    so cache persists across test runs unless --clear-cache is used.

    Returns: Path to session cache directory
    """
    # Use persistent cache directory relative to test file
    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture(scope="session")
def cache_manager(request, session_validation_cache):
    """
    Session-scoped cache manager for link validation.

    Handles --no-cache and --clear-cache options:
    - --no-cache: Returns a disabled cache manager (always misses)
    - --clear-cache: Clears cache before tests
    - Otherwise: Returns normal cache manager

    Returns:
        CacheManager instance
    """
    from tests.link_validation.utils.cache_manager import CacheManager

    no_cache = request.config.getoption("--no-cache")
    clear_cache = request.config.getoption("--clear-cache")

    cache_mgr = CacheManager(session_validation_cache, default_ttl_hours=24)

    # Clear cache if requested
    if clear_cache:
        cache_mgr.clear_all()

    # Disable caching if requested
    if no_cache:
        cache_mgr.disable()

    return cache_mgr
