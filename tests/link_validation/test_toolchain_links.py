"""
Link validation tests for toolchainkit/data/toolchains.json

Tests all toolchain download URLs and SHA256 hashes.
"""

import json
import pytest
from pathlib import Path

from tests.link_validation.utils.link_checker import LinkChecker, ValidationLevel
from tests.link_validation.utils.hash_validator import HashValidator


# Load toolchains.json
# Path: tests/link_validation/test_toolchain_links.py -> workspace root -> toolchainkit/data/toolchains.json
# Base path for toolchains
WORKSPACE_ROOT = Path(__file__).parent.parent.parent

# Primary toolchains.json
PRIMARY_TOOLCHAINS_JSON = WORKSPACE_ROOT / "toolchainkit" / "data" / "toolchains.json"

# Plugins directory
PLUGINS_DIR = WORKSPACE_ROOT / "examples" / "plugins"


def load_toolchains():
    """Load toolchain metadata from JSON files."""
    all_toolchains = {}

    # 1. Load primary toolchains
    if PRIMARY_TOOLCHAINS_JSON.exists():
        with open(PRIMARY_TOOLCHAINS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Tag entries with their source file for better debugging
            for tc_name, tc_data in data["toolchains"].items():
                tc_data["_source_file"] = str(PRIMARY_TOOLCHAINS_JSON)
                all_toolchains[tc_name] = tc_data

    # 2. Load plugin toolchains
    if PLUGINS_DIR.exists():
        for path in PLUGINS_DIR.rglob("toolchains.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "toolchains" in data:
                        for tc_name, tc_data in data["toolchains"].items():
                            # For now, we assume unique names or let specific plugins override
                            tc_data["_source_file"] = str(path)
                            all_toolchains[tc_name] = tc_data
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")

    return all_toolchains


def is_placeholder_hash(sha256: str) -> bool:
    """
    Detect if hash is a placeholder or suspicious pattern.

    Placeholder patterns include:
    - Repetitive characters (e.g., '3e3e3e3e...')
    - All zeros, all Fs, etc.
    - Contains 'placeholder' text
    """
    sha256_lower = sha256.lower()

    # Check for repetitive patterns (less than 10 unique characters)
    if len(set(sha256_lower)) < 10:
        return True

    # Check for 'placeholder' text
    if "placeholder" in sha256_lower:
        return True

    # Check for other suspicious patterns (all zeros, all Fs, etc.)
    if sha256_lower in ["0" * 64, "f" * 64, "e" * 64]:
        return True

    return False


def generate_toolchain_entries():
    """Generate test parameters for all toolchain entries."""
    toolchains = load_toolchains()
    entries = []

    for tc_name, tc_data in toolchains.items():
        for version, platforms in tc_data["versions"].items():
            for platform, info in platforms.items():
                # Skip manual install entries
                if info.get("manual_install_required"):
                    continue

                entries.append(
                    {
                        "toolchain": tc_name,
                        "version": version,
                        "platform": platform,
                        "url": info["url"],
                        "sha256": info["sha256"],
                        "size_mb": info["size_mb"],
                    }
                )

    return entries


# Generate test parameters
TOOLCHAIN_ENTRIES = generate_toolchain_entries()


@pytest.mark.link_validation
@pytest.mark.parametrize(
    "entry",
    TOOLCHAIN_ENTRIES,
    ids=lambda e: f"{e['toolchain']}-{e['version']}-{e['platform']}",
)
def test_toolchain_url_head(entry, validation_level, cache_manager, record_property):
    """Test toolchain URL is accessible (HEAD request) and check size."""
    if validation_level not in ["head", "partial", "full"]:
        pytest.skip(f"Skipping: validation level {validation_level}")

    url = entry["url"]
    expected_size_mb = entry.get("size_mb")

    # Check cache first (only use if cache reads are enabled)
    cached = None
    if cache_manager.is_enabled():
        cached = cache_manager.get_validation(url, "head")

    if cached:
        # Use cached result
        result = cached
        record_property("cached", "yes")
        record_property("cache_age_hours", f"{cached.age_hours:.1f}h")
    else:
        # Perform fresh validation
        checker = LinkChecker(timeout=30, max_retries=3)
        result = checker.validate(url, level=ValidationLevel.HEAD)
        record_property("cached", "no")

        # Cache result
        cache_manager.store_validation(
            url=url,
            validation_level="head",
            is_success=result.is_success,
            status_code=result.status_code,
            error_message=result.error_message,
        )

    # Assert URL is accessible
    assert result.is_success, (
        f"URL not accessible: {url}\n"
        f"Toolchain: {entry['toolchain']} {entry['version']} {entry['platform']}\n"
        f"Status: {result.status if hasattr(result, 'status') else result.status_code}\n"
        f"Error: {result.error_message}\n"
        f"{'(Cached result)' if cached else '(Fresh validation)'}"
    )

    # Check file size if available (only for fresh validation results)
    if hasattr(result, "content_length") and result.content_length and expected_size_mb:
        try:
            content_length_bytes = int(result.content_length)
            actual_size_mb = content_length_bytes / (1024 * 1024)
            # Allow 10% variance in size
            size_diff_percent = (
                abs(actual_size_mb - expected_size_mb) / expected_size_mb * 100
            )

            if size_diff_percent > 10:
                pytest.fail(
                    f"File size mismatch for {url}\n"
                    f"Toolchain: {entry['toolchain']} {entry['version']} {entry['platform']}\n"
                    f"Source: {load_toolchains()[entry['toolchain']].get('_source_file', 'unknown')}\n"
                    f"Expected size: {expected_size_mb} MB\n"
                    f"Actual size: {actual_size_mb:.1f} MB\n"
                    f"Difference: {size_diff_percent:.1f}%\n"
                    f"SUGGESTED FIX: Update size_mb in the source file to {round(actual_size_mb)}"
                )
        except (ValueError, TypeError):
            # If content_length can't be converted to int, skip size check
            pass


@pytest.mark.link_validation
@pytest.mark.link_validation_slow
@pytest.mark.parametrize(
    "entry",
    TOOLCHAIN_ENTRIES,
    ids=lambda e: f"{e['toolchain']}-{e['version']}-{e['platform']}",
)
def test_toolchain_hash(
    entry, validation_level, skip_if_not_full, cache_manager, tmp_path, record_property
):
    """Test toolchain hash is correct (full download)."""
    url = entry["url"]
    expected_hash = entry["sha256"]

    # Skip if hash is a placeholder
    if is_placeholder_hash(expected_hash):
        pytest.skip(
            f"Skipping placeholder hash for {entry['toolchain']} {entry['version']} {entry['platform']}"
        )

    # Check cache first (only use if cache reads are enabled)
    cached_validation = None
    if cache_manager.is_enabled():
        cached_validation = cache_manager.get_validation(url, "full")

    if cached_validation and cached_validation.hash_valid is not None:
        # Use cached validation result
        hash_valid = cached_validation.hash_valid
        actual_hash = cached_validation.hash_actual
        record_property("cached", "yes")
        record_property("cache_age_hours", f"{cached_validation.age_hours:.1f}h")
    else:
        # Perform fresh validation
        record_property("cached", "no")

        # Check if we have cached file
        cached_file = cache_manager.get_cached_file(url)

        if cached_file:
            # Validate hash of cached file
            validator = HashValidator()
            result = validator.validate_file(cached_file, expected_hash)
            hash_valid = result.matches
            actual_hash = result.actual_hash
        else:
            # Download and validate
            download_path = (
                tmp_path
                / f"toolchain_{entry['toolchain']}_{entry['version']}_{entry['platform']}.tar.xz"
            )
            checker = LinkChecker(
                timeout=300, max_retries=3
            )  # 5 minutes timeout for large files

            link_result, hash_result = checker.validate_with_hash(
                url, expected_hash, download_path
            )

            assert link_result.is_success, (
                f"Download failed: {link_result.error_message}\n"
                f"Toolchain: {entry['toolchain']} {entry['version']} {entry['platform']}"
            )

            assert hash_result is not None, "Hash validation result is None"

            hash_valid = hash_result.matches
            actual_hash = hash_result.actual_hash

            # Cache file if hash is valid
            if hash_valid:
                cached_path = cache_manager.store_file(url, download_path)
            else:
                cached_path = None

            # Cache validation result
            cache_manager.store_validation(
                url=url,
                validation_level="full",
                is_success=True,
                hash_expected=expected_hash,
                hash_actual=actual_hash,
                hash_valid=hash_valid,
                cached_file_path=cached_path,
            )

    # Assert (pass or fail based on result, whether cached or not)
    if not hash_valid:
        error_msg = (
            f"Hash mismatch for {url}\n"
            f"Toolchain: {entry['toolchain']} {entry['version']} {entry['platform']}\n"
            f"Source: {load_toolchains()[entry['toolchain']].get('_source_file', 'unknown')}\n"
            f"Expected: {expected_hash}\n"
            f"Actual:   {actual_hash}\n"
            f"{'(Cached result)' if cached_validation else '(Fresh validation)'}\n"
            f"\nSUGGESTED FIX: Update sha256 in the source file:\n"
            f'  "sha256": "{actual_hash}"'
        )
        pytest.fail(error_msg)


@pytest.mark.link_validation
def test_all_toolchains_have_required_fields():
    """Test all toolchain entries have required fields and valid data."""
    toolchains = load_toolchains()
    issues = []

    for tc_name, tc_data in toolchains.items():
        if "type" not in tc_data:
            issues.append(f"{tc_name} missing 'type'")
        if "versions" not in tc_data:
            issues.append(f"{tc_name} missing 'versions'")
            continue

        for version, platforms in tc_data["versions"].items():
            for platform, info in platforms.items():
                # Skip manual install
                if info.get("manual_install_required"):
                    continue

                # Check required fields
                if "url" not in info:
                    issues.append(f"{tc_name} {version} {platform} missing 'url'")
                if "sha256" not in info:
                    issues.append(f"{tc_name} {version} {platform} missing 'sha256'")
                    continue
                if "size_mb" not in info:
                    issues.append(f"{tc_name} {version} {platform} missing 'size_mb'")

                # Validate hash format (skip placeholders)
                sha256 = info["sha256"]
                if not is_placeholder_hash(sha256):
                    if len(sha256) != 64:
                        issues.append(
                            f"{tc_name} {version} {platform} invalid hash length: {len(sha256)} (expected 64)\n"
                            f"      Hash: {sha256}"
                        )
                    elif not all(c in "0123456789abcdef" for c in sha256.lower()):
                        issues.append(
                            f"{tc_name} {version} {platform} invalid hash characters"
                        )

    if issues:
        pytest.fail(
            f"\n\n{'='*80}\n"
            f"DATA QUALITY ISSUES in toolchains.json ({len(issues)} total)\n"
            f"{'='*80}\n\n"
            + "\n\n".join(f"{i+1}. {issue}" for i, issue in enumerate(issues))
            + f"\n\n{'='*80}\n"
        )


@pytest.mark.link_validation
def test_detect_placeholder_hashes():
    """Test for placeholder hashes in toolchains.json (informational)."""
    toolchains = load_toolchains()
    placeholder_entries = []

    for tc_name, tc_data in toolchains.items():
        for version, platforms in tc_data["versions"].items():
            for platform, info in platforms.items():
                if info.get("manual_install_required"):
                    continue

                sha256 = info["sha256"]
                if is_placeholder_hash(sha256):
                    placeholder_entries.append(
                        f"  - {tc_name} {version} {platform}: {sha256}"
                    )

    if placeholder_entries:
        msg = (
            "Placeholder or suspicious hashes detected:\n"
            + "\n".join(placeholder_entries)
            + "\n\nThese entries will be skipped in hash validation tests."
        )
        pytest.skip(msg)


@pytest.mark.link_validation
def test_toolchains_json_is_valid():
    """Test toolchains.json is valid JSON and loadable."""
    assert (
        PRIMARY_TOOLCHAINS_JSON.exists()
    ), f"toolchains.json not found: {PRIMARY_TOOLCHAINS_JSON}"

    toolchains = load_toolchains()
    assert isinstance(toolchains, dict), "toolchains should be a dictionary"
    assert len(toolchains) > 0, "No toolchains found in any file"


@pytest.mark.link_validation
@pytest.mark.link_validation_slow
def test_data_quality_report(cache_manager):
    """Generate comprehensive data quality report for toolchains.json.

    This test performs HEAD requests to validate all URLs, so it's marked as slow.
    It reports all data quality issues found including:
    - Invalid/truncated SHA256 hashes
    - Broken or inaccessible URLs
    - Placeholder hashes that need to be filled in
    """
    toolchains = load_toolchains()
    checker = LinkChecker(timeout=30)

    # Collect issues
    hash_issues = []
    url_issues = []
    placeholder_hashes = []

    for tc_name, tc_data in toolchains.items():
        for version, platforms in tc_data["versions"].items():
            for platform, info in platforms.items():
                if info.get("manual_install_required"):
                    continue

                sha256 = info["sha256"]
                url = info["url"]

                # Check hash issues
                if is_placeholder_hash(sha256):
                    placeholder_hashes.append(f"{tc_name} {version} {platform}")
                elif len(sha256) != 64:
                    hash_issues.append(
                        f"{tc_name} {version} {platform}: hash length {len(sha256)} != 64\n"
                        f"        {sha256}"
                    )

                # Quick HEAD check for URLs
                cached = cache_manager.get_validation(url, "head")
                if cached:
                    result = cached
                else:
                    result = checker.validate(url, ValidationLevel.HEAD)
                    cache_manager.store_validation(
                        url=url,
                        validation_level="head",
                        is_success=result.is_success,
                        status_code=result.status_code,
                        error_message=result.error_message,
                    )

                if not result.is_success:
                    url_issues.append(
                        f"{tc_name} {version} {platform}\n"
                        f"        URL: {url}\n"
                        f"        Status: {result.status_code} - {result.error_message}"
                    )

    # Generate report
    report_parts = []

    if hash_issues:
        report_parts.append(
            f"INVALID HASHES ({len(hash_issues)}):\n"
            + "\n".join(f"  - {issue}" for issue in hash_issues)
        )

    if url_issues:
        report_parts.append(
            f"BROKEN URLs ({len(url_issues)}):\n"
            + "\n".join(f"  - {issue}" for issue in url_issues)
        )

    if placeholder_hashes:
        report_parts.append(
            f"PLACEHOLDER HASHES ({len(placeholder_hashes)}):\n"
            + "\n".join(f"  - {entry}" for entry in placeholder_hashes)
        )

    if report_parts:
        report = (
            f"\n\n{'='*80}\n"
            f"TOOLCHAINS.JSON DATA QUALITY REPORT\n"
            f"{'='*80}\n\n" + "\n\n".join(report_parts) + f"\n\n{'='*80}\n"
        )
        pytest.skip(report)


@pytest.mark.link_validation
def test_toolchain_count():
    """Test expected number of toolchain entries."""
    entries = generate_toolchain_entries()

    # This is informational - adjust as toolchains are added/removed
    assert len(entries) > 0, "No toolchain entries found"

    # Count by toolchain type
    by_toolchain = {}
    for entry in entries:
        tc = entry["toolchain"]
        by_toolchain[tc] = by_toolchain.get(tc, 0) + 1

    print("\nToolchain entry counts:")
    for tc, count in sorted(by_toolchain.items()):
        print(f"  {tc}: {count} entries")
    print(f"Total: {len(entries)} entries")
