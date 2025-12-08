# Link Validation Tests

This directory contains tests that validate external URLs and SHA256 hashes used throughout ToolchainKit.

## Purpose
- Verify download URLs are accessible
- Validate SHA256 checksums match actual file content
- Test git repository accessibility
- Detect broken links before users encounter them

## Running Tests

### Basic Usage
```bash
pytest --link-validation
pytest --link-validation tests/link_validation/test_toolchain_links.py
pytest --link-validation -n auto
```

### Validation Levels
- **head**: HTTP HEAD request only (fast, checks URL exists)
- **partial**: Download first 1MB (medium, checks URL and partial content)
- **full**: Complete download with hash validation (slow, full verification)

```bash
pytest --link-validation --validation-level=head
pytest --link-validation --validation-level=partial
pytest --link-validation --validation-level=full
```

### Caching
Results are cached to avoid redundant downloads:
```bash
pytest --link-validation --validation-cache-dir=/tmp/link-cache
rm -rf /tmp/link-cache
```

## Test Categories
- `test_toolchain_links.py`: Validates toolchains.json entries
- `test_package_manager_links.py`: Validates package manager download URLs
- `test_git_repositories.py`: Tests git clone accessibility

## Writing New Tests
```python
import pytest
@pytest.mark.link_validation
def test_my_link(validation_level):
    url = "https://example.com/file.tar.gz"
    if validation_level == "head":
        assert check_url_exists(url)
    elif validation_level == "full":
        assert validate_url_and_hash(url, expected_hash)
```

## CI Integration
Link validation tests run on a schedule (weekly) in CI, not on every commit.
See `.github/workflows/link-validation.yml` for CI configuration.
