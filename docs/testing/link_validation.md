# Link Validation Testing

Comprehensive guide to ToolchainKit's link validation testing system for verifying external URLs and file integrity.

## Overview

The link validation system validates all external dependencies referenced in ToolchainKit's configuration files:
- **Toolchain URLs**: Download links for compilers (LLVM, GCC, MSVC)
- **Package Manager Tools**: URLs for Conan, vcpkg installers
- **Git Repositories**: Accessibility of git repositories

This ensures that all external resources are accessible and have correct checksums before they are needed by users.

## Quick Start

```bash
# Quick validation (HEAD requests only, ~10 seconds)
pytest --link-validation tests/link_validation/

# Full validation with hash verification (~5 minutes, downloads ~7GB)
pytest --link-validation --validation-level=full tests/link_validation/

# Rebuild cache from scratch
pytest --link-validation --clear-cache --no-cache tests/link_validation/
```

## Command Line Options

### Core Options

#### `--link-validation`
Enable link validation tests. Without this flag, all link validation tests are skipped.

```bash
pytest --link-validation tests/link_validation/
```

#### `--validation-level=LEVEL`
Set the validation intensity level. Choices: `head`, `partial`, `full` (default: `head`)

- **`head`**: HTTP HEAD request only - checks if URL exists and is accessible (~1 second per URL)
- **`partial`**: Downloads first 1MB of file - verifies content is downloadable (not currently used)
- **`full`**: Complete download with SHA256 hash verification - ensures file integrity (~30-120 seconds per large file)

```bash
# Quick check (default)
pytest --link-validation tests/link_validation/

# Full validation with hash checks
pytest --link-validation --validation-level=full tests/link_validation/
```

**When to use each level:**
- **`head`**: CI/CD pipelines, quick validation before commits
- **`full`**: Before releases, after updating URLs or hashes, periodic integrity checks

### Caching Options

The validation system caches results to avoid redundant network operations. Cache is stored in `tests/link_validation/.cache/`.

#### `--no-cache`
**Ignore existing cache when reading, but still write new results.**

Use this when you want to force fresh validation but still update the cache for future runs.

```bash
# Force fresh validation, update cache
pytest --link-validation --no-cache tests/link_validation/
```

**Use cases:**
- URLs might have changed
- Verifying that old cached results are still valid
- Populating cache after clearing it
- Periodic re-validation (e.g., weekly CI job)

#### `--clear-cache`
**Delete all cached data before running tests.**

Removes all cached validation results and downloaded files. Usually combined with `--no-cache`.

```bash
# Complete fresh start
pytest --link-validation --clear-cache --no-cache tests/link_validation/
```

**Use cases:**
- Cache corruption suspected
- Major URL changes in toolchains.json
- Want to measure actual validation time
- Cleaning up disk space before fresh validation

#### `--validation-cache-dir=DIR`
**Specify custom cache directory.**

By default, cache is stored in `tests/link_validation/.cache/`. This option allows using a different location.

```bash
# Use custom cache location
pytest --link-validation --validation-cache-dir=/tmp/validation-cache tests/link_validation/

# Use shared cache across multiple projects
pytest --link-validation --validation-cache-dir=~/.toolchainkit/validation-cache tests/link_validation/
```

**Use cases:**
- Sharing cache across multiple project clones
- Using faster storage (SSD vs HDD)
- CI/CD with persistent cache volumes
- Debugging cache issues

### Option Combinations

```bash
# Option 1: Use existing cache (fastest)
pytest --link-validation tests/link_validation/

# Option 2: Rebuild cache incrementally (smart)
pytest --link-validation --no-cache tests/link_validation/

# Option 3: Complete fresh validation (slowest, most thorough)
pytest --link-validation --clear-cache --no-cache tests/link_validation/

# Option 4: Full validation with hash checks using cached files
pytest --link-validation --validation-level=full tests/link_validation/

# Option 5: Fresh full validation, rebuild everything
pytest --link-validation --validation-level=full --clear-cache --no-cache tests/link_validation/

# Option 6: Custom cache location for CI
pytest --link-validation --validation-cache-dir=/cache/validation tests/link_validation/
```

## Understanding Cache Behavior

### Cache Structure

```
tests/link_validation/.cache/
├── index.json          # Validation results metadata
└── files/              # Downloaded toolchain files (for full validation)
    └── <hash>.tar.xz
```

### What Gets Cached

1. **HEAD validation results**: URL accessibility, status codes, file sizes
2. **Full validation results**: Complete download outcomes, SHA256 hashes
3. **Downloaded files**: Actual toolchain archives (only for `--validation-level=full`)

### Cache TTL (Time To Live)

- Default TTL: **24 hours**
- Expired entries are automatically cleaned up
- Cached files are reused if available and valid

### Cache Hit vs Cache Miss

**With cache enabled (default):**
```
test_toolchain_url_head[llvm-18.1.8-linux-x64] PASSED  # Cached, instant
test_toolchain_url_head[gcc-15.2.0-linux-x64] PASSED   # Fresh, ~1 second
```

**With `--no-cache`:**
```
test_toolchain_url_head[llvm-18.1.8-linux-x64] PASSED  # Fresh, ~1 second
test_toolchain_url_head[gcc-15.2.0-linux-x64] PASSED   # Fresh, ~1 second
```

Both runs update the cache for future use.

## Test Output

### Successful Validation
```bash
tests/link_validation/test_toolchain_links.py::test_toolchain_url_head[llvm-18.1.8-linux-x64] PASSED
tests/link_validation/test_toolchain_links.py::test_toolchain_hash[gcc-15.2.0-linux-x64] PASSED
```

### Failed Validation with Error Details

Use `--tb=short` to see detailed error messages:

```bash
pytest --link-validation tests/link_validation/ --tb=short
```

**URL Not Accessible:**
```
FAILED tests/link_validation/test_toolchain_links.py::test_toolchain_url_head[llvm-16.0.6-linux-x64]
E   Failed: URL not accessible: https://github.com/llvm/.../clang+llvm-16.0.6-x86_64-linux.tar.xz
E   Status: 404
E   Error: URL not found
```

**Hash Mismatch:**
```
FAILED tests/link_validation/test_toolchain_links.py::test_toolchain_hash[llvm-18.1.8-linux-arm64]
E   Failed: Hash mismatch for https://github.com/llvm/.../clang+llvm-18.1.8-aarch64-linux-gnu.tar.xz
E   Expected: 5e41b0c40c5b03bf07e524e0e2e4d4deb70d99e8f7c614b4a51e5a8876074a42
E   Actual:   dcaa1bebbfbb86953fdfbdc7f938800229f75ad26c5c9375ef242edad737d999
E
E   SUGGESTED FIX: Update sha256 in toolchains.json:
E     "sha256": "dcaa1bebbfbb86953fdfbdc7f938800229f75ad26c5c9375ef242edad737d999"
```

**Size Mismatch:**
```
FAILED tests/link_validation/test_toolchain_links.py::test_toolchain_url_head[llvm-18.1.8-linux-arm64]
E   Failed: File size mismatch for https://github.com/llvm/.../clang+llvm-18.1.8-aarch64-linux-gnu.tar.xz
E   Expected size: 611 MB
E   Actual size: 1003.0 MB
E   Difference: 64.2%
E   SUGGESTED FIX: Update size_mb in toolchains.json to 1003
```

## Performance Characteristics

### HEAD Validation (Default)

- **Time per URL**: ~0.5-2 seconds
- **Network usage**: <1 KB per URL
- **Disk usage**: ~100 KB (cached metadata)
- **Total time** (12 toolchains): ~10-20 seconds (first run), <1 second (cached)

### Full Validation

- **Time per toolchain**: 30-120 seconds (depending on size and network speed)
- **Network usage**: ~7 GB (all toolchains)
- **Disk usage**: ~7 GB (cached files) + ~1 MB (metadata)
- **Total time** (12 toolchains): ~5-10 minutes (first run), <1 minute (cached, hash-only)

### CI/CD Recommendations

**Pull Request CI:**
```bash
# Quick validation only
pytest --link-validation tests/link_validation/
```

**Nightly/Weekly CI:**
```bash
# Full validation, rebuild cache
pytest --link-validation --validation-level=full --no-cache tests/link_validation/
```

**Pre-Release CI:**
```bash
# Complete fresh validation
pytest --link-validation --validation-level=full --clear-cache --no-cache tests/link_validation/
```

## Troubleshooting

### Cache Issues

**Problem**: Tests pass but should fail (stale cache)

**Solution**: Force fresh validation
```bash
pytest --link-validation --no-cache tests/link_validation/
```

**Problem**: Cache taking too much disk space

**Solution**: Clear cache
```bash
# Clear and rebuild
pytest --link-validation --clear-cache --no-cache tests/link_validation/

# Or manually delete
rm -rf tests/link_validation/.cache
```

**Problem**: Cache corruption errors

**Solution**: Clear cache and use custom location
```bash
pytest --link-validation --clear-cache --validation-cache-dir=/tmp/new-cache tests/link_validation/
```

### Network Issues

**Problem**: Timeouts or connection errors

**Solution**: The tests automatically retry failed requests (default: 3 retries with exponential backoff)

**Problem**: Corporate proxy/firewall blocking requests

**Solution**: Configure proxy environment variables:
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
pytest --link-validation tests/link_validation/
```

### Verification SSL Issues

The tests disable SSL verification by default for testing environments. This is configured in `tests/link_validation/conftest.py`.

## Updating Toolchain Data

When you need to update `toolchainkit/data/toolchains.json`:

1. **Update URLs and versions** in the JSON file

2. **Run validation without cache** to get actual hashes and sizes:
```bash
pytest --link-validation --validation-level=full --no-cache tests/link_validation/ --tb=short
```

3. **Copy suggested fixes** from error messages into `toolchains.json`

4. **Verify fixes**:
```bash
pytest --link-validation --validation-level=full --no-cache tests/link_validation/
```

5. **Commit changes** with updated URLs, hashes, and sizes

## Advanced Usage

### Running Specific Tests

```bash
# Test only LLVM toolchains
pytest --link-validation tests/link_validation/test_toolchain_links.py -k llvm

# Test specific version
pytest --link-validation tests/link_validation/test_toolchain_links.py -k "llvm-18.1.8"

# Test only GCC toolchains
pytest --link-validation tests/link_validation/test_toolchain_links.py -k gcc

# Test only hash validation (requires --validation-level=full)
pytest --link-validation --validation-level=full tests/link_validation/test_toolchain_links.py::test_toolchain_hash
```

### Verbose Output

```bash
# See detailed output
pytest --link-validation tests/link_validation/ -v

# See very verbose output with cache info
pytest --link-validation tests/link_validation/ -vv

# Show all output (including print statements)
pytest --link-validation tests/link_validation/ -v -s
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest --link-validation tests/link_validation/ -n auto

# Parallel with full validation (careful with bandwidth!)
pytest --link-validation --validation-level=full tests/link_validation/ -n 4
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Link Validation

on:
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  validate-links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest

      - name: Cache validation results
        uses: actions/cache@v4
        with:
          path: tests/link_validation/.cache
          key: validation-${{ github.run_id }}
          restore-keys: validation-

      - name: Run quick validation (PR)
        if: github.event_name == 'pull_request'
        run: pytest --link-validation tests/link_validation/

      - name: Run full validation (Weekly)
        if: github.event_name == 'schedule'
        run: pytest --link-validation --validation-level=full --no-cache tests/link_validation/
```

## Best Practices

1. **Use HEAD validation by default** - Fast and catches most issues
2. **Run full validation before releases** - Ensures file integrity
3. **Enable caching in CI** - Speeds up subsequent runs
4. **Clear cache periodically** - Prevents stale data (weekly/monthly)
5. **Use `--no-cache` for important validations** - When accuracy matters more than speed
6. **Check test output carefully** - Error messages include suggested fixes
7. **Update cache after major changes** - New URLs, versions, or configurations

## See Also

- [Testing Overview](../testing/README.md)
- [CI/CD Integration](../ci_cd.md)
- [Toolchain Registry](../toolchains.md)
- [Package Managers](../package_managers.md)
