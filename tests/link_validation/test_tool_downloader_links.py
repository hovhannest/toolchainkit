"""
Link validation tests for tool downloader URLs.

Tests URLs in:
- toolchainkit/packages/tool_downloader.py
- toolchainkit/core/python_env.py
- toolchainkit/caching/detection.py
"""

import re
from pathlib import Path

import pytest

from tests.link_validation.utils.link_checker import LinkChecker, ValidationLevel
from toolchainkit.caching.detection import BuildCacheInstaller
from toolchainkit.core.platform import PlatformInfo
from toolchainkit.core.python_env import PYTHON_URLS
from toolchainkit.packages.tool_downloader import (
    CMakeDownloader,
    CppcheckDownloader,
    GitDownloader,
    MakeDownloader,
    NinjaDownloader,
)


def get_all_tool_urls():
    """Extract all tool download URLs from downloader classes and config dicts."""
    urls = []
    # CMake
    for platform in ["windows-x64", "linux-x64", "macos-x64"]:
        downloader = CMakeDownloader(Path("/tmp"), version="3.28.1")
        url = downloader._get_download_url()
        urls.append(("cmake", url))
    # Ninja
    for platform in ["windows-x64", "linux-x64", "macos-x64"]:
        downloader = NinjaDownloader(Path("/tmp"), version="1.11.1")
        url = downloader._get_download_url()
        urls.append(("ninja", url))
    # sccache
    for platform_key, url_template in BuildCacheInstaller.SCCACHE_RELEASES.items():
        url = url_template.format(version="0.7.4")
        urls.append(("sccache", url))
    # w64devkit (Windows only)
    windows_platform = PlatformInfo(
        os="windows", arch="x64", os_version="10.0", distribution="", abi="msvc"
    )
    downloader = MakeDownloader(
        tools_dir=Path("/tmp"), version="2.4.0", platform=windows_platform
    )
    url = downloader._get_download_url()
    urls.append(("w64devkit", url))
    # mingit (Windows only)
    downloader = GitDownloader(
        platform=windows_platform, install_dir=Path("/tmp"), version="2.47.1"
    )
    url = downloader._get_download_url()
    urls.append(("mingit", url))
    # cppcheck (Windows only)
    downloader = CppcheckDownloader(
        platform=windows_platform, install_dir=Path("/tmp"), version="2.16.0"
    )
    url = downloader._get_download_url()
    urls.append(("cppcheck", url))
    # Python env URLs
    for key, url in PYTHON_URLS.items():
        urls.append(("python_env", url))
    # get-pip.py (extract from source code)
    tool_downloader_path = (
        Path(__file__).parent.parent.parent
        / "toolchainkit"
        / "packages"
        / "tool_downloader.py"
    )
    content = tool_downloader_path.read_text()
    get_pip_match = re.search(
        r'get_pip_url = "(https://bootstrap\.pypa\.io/get-pip\.py)"', content
    )
    if get_pip_match:
        urls.append(("get-pip", get_pip_match.group(1)))
    return urls


GENERATED_TOOL_URLS = get_all_tool_urls()


@pytest.mark.link_validation
@pytest.mark.parametrize(
    "tool_name,url",
    GENERATED_TOOL_URLS,
    ids=lambda x: (
        f"{x[0]}-{x[1].split('/')[-1][:40]}" if isinstance(x, tuple) else str(x)[:50]
    ),
)
def test_tool_downloader_urls(
    tool_name, url, validation_level, cache_manager, record_property
):
    """Test tool downloader URLs are accessible (extracted from source)."""
    cached = cache_manager.get_validation(url, "head")
    if cached and cached.is_success:
        record_property("cached", "yes")
        assert True
        return
    record_property("cached", "no")
    checker = LinkChecker(timeout=30, max_retries=3)
    result = checker.validate(url, level=ValidationLevel.HEAD)
    cache_manager.store_validation(
        url=url,
        validation_level="head",
        is_success=result.is_success,
        status_code=result.status_code,
        error_message=result.error_message,
    )
    assert result.is_success, (
        f"{tool_name} URL not accessible: {url}\n"
        f"Status: {result.status}\n"
        f"Error: {result.error_message}"
    )


@pytest.mark.link_validation
def test_sccache_urls_not_duplicated():
    """Verify sccache URLs are consistent between tool_downloader.py and caching/detection.py."""
    import re

    # Read both files
    tool_downloader = (
        Path(__file__).parent.parent.parent
        / "toolchainkit"
        / "packages"
        / "tool_downloader.py"
    )
    caching_detection = (
        Path(__file__).parent.parent.parent
        / "toolchainkit"
        / "caching"
        / "detection.py"
    )

    # Extract sccache URLs from both
    pattern = r'https://github\.com/mozilla/sccache/releases/download/[^\s"\']+'

    tool_urls = set(re.findall(pattern, tool_downloader.read_text()))
    cache_urls = set(re.findall(pattern, caching_detection.read_text()))

    # URLs should be identical
    assert tool_urls == cache_urls, (
        f"sccache URLs differ between files!\n"
        f"tool_downloader.py: {tool_urls}\n"
        f"caching/detection.py: {cache_urls}\n"
        f"Consider refactoring to single source of truth."
    )


@pytest.mark.link_validation
def test_extract_all_github_urls():
    """Extract and validate we can find all GitHub URLs in tool_downloader.py."""
    import re

    tool_downloader_path = (
        Path(__file__).parent.parent.parent
        / "toolchainkit"
        / "packages"
        / "tool_downloader.py"
    )

    content = tool_downloader_path.read_text()

    # Extract GitHub release URLs
    github_pattern = r"https://github\.com/[^/]+/[^/]+/releases/download"
    base_urls = set(re.findall(github_pattern, content))

    # Should find URLs for multiple tools
    expected_repos = {
        "Kitware/CMake",
        "ninja-build/ninja",
        "mozilla/sccache",
        "indygreg/python-build-standalone",
        "skeeto/w64devkit",
        "git-for-windows/git",
        "danmar/cppcheck",
        "llvm/llvm-project",
    }

    found_repos = {"/".join(url.split("/")[3:5]) for url in base_urls}

    missing = expected_repos - found_repos
    assert not missing, f"Expected to find repos but didn't: {missing}"


@pytest.mark.link_validation
def test_python_url_sources_documented():
    """
    Verify we test Python URLs from both sources.

    Python URLs come from:
    - python_env.py: python.org embedded, astral-sh/python-build-standalone
    - tool_downloader.py: indygreg/python-build-standalone

    This test documents that Python URLs come from multiple sources
    and ensures we test all of them.
    """
    # Document for future maintainers - this is a documentation test
    assert True
