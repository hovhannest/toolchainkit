# Link Validation Development Guide

Internal architecture and extension guide for the link validation testing system.

## Architecture Overview

The link validation system is built with three main components:

```
tests/link_validation/
├── conftest.py                         # Pytest configuration and fixtures
├── test_toolchain_links.py             # Toolchain URL validation
├── test_tool_downloader_links.py       # Tool downloader URL validation
├── test_git_repositories.py            # Git repository validation
└── utils/
    ├── __init__.py
    ├── link_checker.py                 # Core URL validation logic
    ├── hash_validator.py               # SHA256 hash verification
    └── cache_manager.py                # Validation result caching
```

## Core Components

### LinkChecker (`utils/link_checker.py`)

The central validation engine that performs HTTP requests and validates URLs.

**Key Features:**
- Multiple validation levels (HEAD, PARTIAL, FULL)
- Automatic retries with exponential backoff
- Timeout handling
- Redirect following
- Size validation

**Usage Example:**
```python
from tests.link_validation.utils.link_checker import LinkChecker, ValidationLevel

checker = LinkChecker(timeout=30, max_retries=3)
result = checker.validate(
    url="https://example.com/file.tar.gz",
    level=ValidationLevel.HEAD
)

if result.is_success:
    print(f"✓ URL accessible: {result.status_code}")
else:
    print(f"✗ Failed: {result.error_message}")
```

**Validation Levels:**
- `ValidationLevel.HEAD`: Fast HEAD request (1-2 seconds)
- `ValidationLevel.PARTIAL`: Download first chunk (not currently implemented)
- `ValidationLevel.FULL`: Complete download for hash verification (30-120 seconds)

### HashValidator (`utils/hash_validator.py`)

Validates SHA256 hashes of downloaded files.

**Key Features:**
- Streaming hash computation (memory efficient)
- Size validation with tolerance
- Detailed error reporting with fix suggestions

**Usage Example:**
```python
from tests.link_validation.utils.hash_validator import HashValidator

validator = HashValidator()
result = validator.validate_file_hash(
    file_path=Path("/tmp/download.tar.gz"),
    expected_hash="abc123...",
    expected_size_mb=1024
)

if not result.is_success:
    print(f"Hash mismatch!")
    print(f"Expected: {result.expected_hash}")
    print(f"Actual:   {result.actual_hash}")
    print(f"\nSuggested fix:")
    print(result.suggested_fix)
```

### CacheManager (`utils/cache_manager.py`)

Persistent caching of validation results to avoid redundant checks.

**Key Features:**
- JSON-based index with file storage
- Configurable expiry times
- Cache control (disable/enable/clear)
- Thread-safe operations with file locking

**Usage Example:**
```python
from tests.link_validation.utils.cache_manager import CacheManager

cache = CacheManager(cache_dir=Path(".cache"))

# Store result
cache.store_validation(
    url="https://example.com/file.tar.gz",
    validation_level="head",
    is_success=True,
    status_code=200
)

# Retrieve cached result
cached = cache.get_validation("https://example.com/file.tar.gz", "head")
if cached and cached.is_success:
    print("Using cached result")
```

**Cache Structure:**
```
.cache/
├── index.json              # Metadata index
└── files/                  # Downloaded files (for full validation)
    └── <url_hash>/
        └── <filename>
```

## Writing Tests

### Test Structure

All link validation tests follow this pattern:

```python
@pytest.mark.link_validation
@pytest.mark.parametrize("name,url", TEST_DATA, ids=lambda x: x[0])
def test_urls(name, url, validation_level, cache_manager, record_property):
    """Test URL accessibility."""
    # 1. Check cache
    cached = cache_manager.get_validation(url, "head")
    if cached and cached.is_success:
        record_property("cached", "yes")
        assert True
        return

    record_property("cached", "no")

    # 2. Perform validation
    checker = LinkChecker(timeout=30, max_retries=3)
    result = checker.validate(url, level=ValidationLevel.HEAD)

    # 3. Store in cache
    cache_manager.store_validation(
        url=url,
        validation_level="head",
        is_success=result.is_success,
        status_code=result.status_code,
        error_message=result.error_message,
    )

    # 4. Assert
    assert result.is_success, f"{name} URL not accessible: {url}"
```

### Dynamic URL Extraction Pattern

Always extract URLs from actual source code to ensure tests validate production code:

```python
def extract_urls_from_source():
    """Extract URLs dynamically from source code."""
    urls = []

    # Read source file
    source_path = Path(__file__).parent.parent.parent / "toolchainkit" / "module.py"
    content = source_path.read_text()

    # Extract with regex
    pattern = r'url = "(https://[^"]+)"'
    matches = re.findall(pattern, content)

    for url in matches:
        urls.append(("name", url))

    return urls

TEST_DATA = extract_urls_from_source()
```

**Benefits:**
- Tests always validate actual production URLs
- No hardcoded test data that can drift
- Breaking a URL in source code immediately breaks tests
- Self-documenting (test shows where URL is used)

### Fixtures

Key pytest fixtures available in `conftest.py`:

#### `validation_level`
Returns the validation level from command line (`--validation-level=LEVEL`).

```python
def test_example(validation_level):
    if validation_level == "full":
        # Run expensive validation
        pass
```

#### `cache_manager`
Provides configured CacheManager instance.

```python
def test_example(cache_manager):
    cached = cache_manager.get_validation(url, "head")
    # ...
```

#### `record_property`
Records test properties for reporting (cached vs fresh).

```python
def test_example(record_property):
    record_property("cached", "yes")
    record_property("validation_time", "1.5s")
```

## Adding New Test Categories

### Step 1: Identify URLs to Test

Find all URLs in source code that need validation:
```bash
# Search for URLs
git grep -E 'https?://[^"'\'']+' toolchainkit/
```

### Step 2: Create Test File

Create `tests/link_validation/test_new_category.py`:

```python
"""
Link validation tests for [category name].

Tests URLs in:
- toolchainkit/path/to/module.py
"""

import re
from pathlib import Path

import pytest

from tests.link_validation.utils.link_checker import LinkChecker, ValidationLevel


def extract_category_urls():
    """Extract URLs from source code."""
    urls = []
    # Extraction logic here
    return urls


CATEGORY_URLS = extract_category_urls()


@pytest.mark.link_validation
@pytest.mark.parametrize("name,url,source", CATEGORY_URLS)
def test_category_urls(name, url, source, cache_manager):
    """Test category URLs are accessible."""
    # Standard test pattern
    pass
```

### Step 3: Run and Verify

```bash
# Run new tests
pytest --link-validation tests/link_validation/test_new_category.py -v

# Verify dynamic extraction
pytest --link-validation --collect-only tests/link_validation/test_new_category.py
```

## Extending Utilities

### Custom Validation Levels

Add new validation level in `link_checker.py`:

```python
class ValidationLevel(Enum):
    HEAD = "head"
    PARTIAL = "partial"
    FULL = "full"
    CUSTOM = "custom"  # New level
```

Then implement in `LinkChecker.validate()`:

```python
def validate(self, url: str, level: ValidationLevel) -> ValidationResult:
    if level == ValidationLevel.CUSTOM:
        return self._validate_custom(url)
    # ... existing code
```

### Custom Link Checker

Extend `LinkChecker` for special requirements:

```python
from tests.link_validation.utils.link_checker import LinkChecker

class AuthenticatedLinkChecker(LinkChecker):
    def __init__(self, token: str, **kwargs):
        super().__init__(**kwargs)
        self.token = token

    def _make_request(self, url: str, method: str) -> requests.Response:
        headers = {"Authorization": f"Bearer {self.token}"}
        return self.session.request(method, url, headers=headers)
```

## Testing the Tests

Unit tests for validation utilities are in `tests/unit/`:

```bash
# Test link checker
pytest tests/unit/test_link_checker.py -v

# Test hash validator
pytest tests/unit/test_hash_validator.py -v

# Test cache manager
pytest tests/unit/test_cache_manager.py -v
```

## Debugging

### Enable Debug Logging

```bash
pytest --link-validation --log-cli-level=DEBUG tests/link_validation/ -v
```

### Verbose Output

```bash
# Show full error traces
pytest --link-validation --tb=long tests/link_validation/ -v

# Show captured output
pytest --link-validation -vv -s tests/link_validation/
```

### Disable Caching

```bash
# Force fresh validation
pytest --link-validation --no-cache tests/link_validation/
```

### Test Single URL

```bash
# Test specific URL by name
pytest --link-validation -k "llvm-18.1.8-linux" -vv
```

## Performance Optimization

### Parallel Execution

Use `pytest-xdist` for parallel execution:

```bash
# Auto-detect CPU count
pytest --link-validation -n auto tests/link_validation/

# Specific worker count
pytest --link-validation -n 4 tests/link_validation/
```

### Selective Testing

```bash
# Only failed tests from last run
pytest --link-validation --lf tests/link_validation/

# Only new/modified tests
pytest --link-validation --nf tests/link_validation/

# Stop on first failure
pytest --link-validation -x tests/link_validation/
```

### Caching Strategy

Default cache expiry:
- HEAD checks: 24 hours
- Full downloads: 7 days

Adjust in `conftest.py`:
```python
@pytest.fixture
def cache_manager(request, tmp_path):
    cache_expiry_hours = 48  # Custom expiry
    # ...
```

## CI/CD Considerations

### Weekly HEAD Checks

Fast validation to catch broken links:
```yaml
- run: pytest --link-validation --validation-level=head -n auto
```

### Monthly Full Validation

Complete validation with hash checks:
```yaml
- run: pytest --link-validation --validation-level=full -n 4
```

### Cache Strategy

Use GitHub Actions cache:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/toolchainkit-link-validation
    key: link-validation-${{ github.run_id }}
    restore-keys: link-validation-
```

## Common Patterns

### Retry Flaky URLs

```python
@pytest.mark.flaky(reruns=3, reruns_delay=2)
@pytest.mark.link_validation
def test_flaky_url(url):
    """Test URL that may have transient failures."""
    # Will retry up to 3 times with 2 second delay
    pass
```

### Skip Slow Tests

```python
@pytest.mark.link_validation
@pytest.mark.link_validation_slow
def test_large_download(url, validation_level):
    if validation_level != "full":
        pytest.skip("Requires --validation-level=full")
    # Expensive operation
```

### Consistency Checks

```python
@pytest.mark.link_validation
def test_url_consistency():
    """Verify URL is same across all source files."""
    urls = extract_all_urls_for_tool()
    unique_urls = set(urls)
    assert len(unique_urls) == 1, f"Inconsistent URLs: {unique_urls}"
```

## Best Practices

1. **Always extract URLs dynamically** - Never hardcode test URLs
2. **Use caching extensively** - Speeds up development significantly
3. **Provide detailed error messages** - Include URL, source file, and suggested fix
4. **Test at appropriate levels** - HEAD for quick checks, FULL for releases
5. **Document source of URLs** - Make it easy to find where URL is used
6. **Use parametrize** - One test function, many URLs
7. **Record properties** - Track cached vs fresh validations
8. **Handle git gracefully** - Skip tests if git not available

## Troubleshooting

### Import Errors

Ensure pytest can find the utils module:
```python
# In conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### Cache Not Working

Check cache directory permissions:
```bash
ls -la tests/link_validation/.cache/
```

Clear and rebuild:
```bash
rm -rf tests/link_validation/.cache/
pytest --link-validation --clear-cache
```

### Hash Mismatches

Verify expected hash is correct:
```bash
# Download file manually
curl -L -o file.tar.gz <url>

# Compute hash
sha256sum file.tar.gz
```

Update in source code and re-run tests.

## Future Enhancements

Potential improvements to the validation system:

1. **Bandwidth tracking** - Monitor total download size
2. **Rate limiting** - Respect server rate limits
3. **Mirror validation** - Test backup URLs
4. **Version tracking** - Detect when new versions available
5. **Notification system** - Alert on broken links
6. **Dashboard** - Visualize link health over time
7. **Automatic fixes** - PR to update broken URLs
8. **CDN validation** - Test multiple CDN endpoints

## References

- User Guide: `docs/testing/link_validation.md`
- Test Files: `tests/link_validation/`
- CI Workflows: `.github/workflows/link-validation*.yml`
- Cache Implementation: `tests/link_validation/utils/cache_manager.py`
