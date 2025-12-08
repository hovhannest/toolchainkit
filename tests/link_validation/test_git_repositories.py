"""
Link validation tests for git repositories.

Tests git clone accessibility for repositories used in ToolchainKit.
Dynamically extracts git URLs from source code to ensure tests match production.
"""

import re
import subprocess
from pathlib import Path

import pytest

from tests.link_validation.utils.link_checker import LinkChecker, ValidationLevel


def extract_git_urls_from_source():
    """
    Extract all git clone URLs from source code.

    Returns:
        List of tuples (name, url, source_file)
    """
    repos = []

    # Extract from tool_downloader.py (vcpkg)
    tool_downloader_path = (
        Path(__file__).parent.parent.parent
        / "toolchainkit"
        / "packages"
        / "tool_downloader.py"
    )
    content = tool_downloader_path.read_text()

    # Find git clone URLs
    vcpkg_match = re.search(
        r'git_cmd = \["git", "clone", "(https://github\.com/microsoft/vcpkg\.git)"\]',
        content,
    )
    if vcpkg_match:
        repos.append(("vcpkg", vcpkg_match.group(1), "tool_downloader.py"))

    # Extract from layer configs (mold, FlameGraph)
    layers_dir = (
        Path(__file__).parent.parent.parent / "toolchainkit" / "data" / "layers"
    )

    if layers_dir.exists():
        for yaml_file in layers_dir.rglob("*.yaml"):
            content = yaml_file.read_text()
            # Find git clone commands in yaml
            git_matches = re.findall(r"git clone (https://github\.com/[^\s]+)", content)
            for url in git_matches:
                # Clean up URL (remove trailing chars)
                url = url.rstrip(",;")
                # Determine name from URL
                name = url.split("/")[-1].replace(".git", "")
                repos.append((name, url, f"layers/{yaml_file.name}"))

    return repos


GIT_REPOSITORIES = extract_git_urls_from_source()


@pytest.mark.link_validation
@pytest.mark.parametrize(
    "name,git_url,source",
    GIT_REPOSITORIES,
    ids=lambda x: x[0] if isinstance(x, tuple) else str(x),
)
def test_git_repository_accessible_http(
    name, git_url, source, cache_manager, record_property
):
    """Test git repository is accessible via HTTP HEAD check (fast)."""
    # Convert git URL to web URL for HTTP check
    web_url = git_url.replace(".git", "")

    # Check cache
    cached = cache_manager.get_validation(web_url, "head")
    if cached and cached.is_success:
        record_property("cached", "yes")
        assert True
        return

    record_property("cached", "no")

    # Validate HTTP accessibility
    checker = LinkChecker(timeout=30, max_retries=3)
    result = checker.validate(web_url, level=ValidationLevel.HEAD)

    # Cache result
    cache_manager.store_validation(
        url=web_url,
        validation_level="head",
        is_success=result.is_success,
        status_code=result.status_code,
        error_message=result.error_message,
    )

    assert result.is_success, (
        f"Git repository not accessible via HTTP: {name}\n"
        f"URL: {web_url}\n"
        f"Source: {source}\n"
        f"Error: {result.error_message}"
    )


@pytest.mark.link_validation
def test_git_command_available():
    """Test that git command is available."""
    result = subprocess.run(
        ["git", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        "git command not available\n"
        "Install git to run git repository tests\n"
        f"Error: {result.stderr}"
    )


@pytest.mark.link_validation
@pytest.mark.parametrize(
    "name,git_url,source",
    GIT_REPOSITORIES,
    ids=lambda x: x[0] if isinstance(x, tuple) else str(x),
)
def test_git_ls_remote_accessible(name, git_url, source):
    """Test git remote is accessible using git ls-remote (fast, no clone)."""
    # Skip if git not available
    git_check = subprocess.run(["git", "--version"], capture_output=True, timeout=10)
    if git_check.returncode != 0:
        pytest.skip("git command not available")

    result = subprocess.run(
        ["git", "ls-remote", "--heads", git_url],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"git ls-remote failed for {name}\n"
        f"URL: {git_url}\n"
        f"Source: {source}\n"
        f"Stderr: {result.stderr}\n"
        f"Stdout: {result.stdout}"
    )


@pytest.mark.link_validation
@pytest.mark.link_validation_slow
@pytest.mark.parametrize(
    "name,git_url,source",
    GIT_REPOSITORIES,
    ids=lambda x: x[0] if isinstance(x, tuple) else str(x),
)
def test_git_repository_clonable(name, git_url, source, tmp_path, validation_level):
    """Test git repository can be cloned (slow test - requires --validation-level=full)."""
    if validation_level != "full":
        pytest.skip("Requires --validation-level=full")

    # Skip if git not available
    git_check = subprocess.run(["git", "--version"], capture_output=True, timeout=10)
    if git_check.returncode != 0:
        pytest.skip("git command not available")

    clone_dir = tmp_path / name

    # Attempt shallow clone (faster)
    result = subprocess.run(
        ["git", "clone", "--depth=1", git_url, str(clone_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"Failed to clone {name}\n"
        f"URL: {git_url}\n"
        f"Source: {source}\n"
        f"Stderr: {result.stderr}\n"
        f"Stdout: {result.stdout}"
    )

    assert clone_dir.exists(), f"Clone directory not created: {clone_dir}"
    assert (clone_dir / ".git").exists(), f"No .git directory in {clone_dir}"


@pytest.mark.link_validation
def test_vcpkg_url_consistency():
    """Verify vcpkg URL is consistent across source files."""
    # This test ensures vcpkg URL is the same everywhere it's used
    vcpkg_repos = [repo for repo in GIT_REPOSITORIES if repo[0].lower() == "vcpkg"]

    assert len(vcpkg_repos) >= 1, "vcpkg repository should be found in source code"

    # All vcpkg URLs should be identical
    vcpkg_urls = {repo[1] for repo in vcpkg_repos}
    assert len(vcpkg_urls) == 1, f"vcpkg URLs are inconsistent:\n" f"{vcpkg_urls}"


@pytest.mark.link_validation
def test_all_git_urls_use_https():
    """Verify all git URLs use HTTPS (not git:// or ssh://)."""
    for name, url, source in GIT_REPOSITORIES:
        assert url.startswith("https://"), (
            f"Git URL should use HTTPS: {name}\n" f"URL: {url}\n" f"Source: {source}"
        )
