# Testing Documentation

Comprehensive testing guides for ToolchainKit.

## Overview

ToolchainKit has a multi-layered testing strategy:

1. **Unit Tests** - Fast, isolated component tests
2. **Integration Tests** - Cross-component functionality tests
3. **End-to-End Tests** - Complete workflow validation
4. **Link Validation** - External dependency verification
5. **Regression Tests** - Prevent reintroduction of bugs

## Quick Start

```bash
# Run all unit tests
pytest

# Run with coverage
pytest --cov=toolchainkit --cov-report=html

# Run integration tests
pytest --integration

# Run link validation
pytest --link-validation

# Run everything
pytest --integration --link-validation
```

## Test Categories

### Unit Tests (`tests/`)

Fast, isolated tests for individual components. These run on every commit.

**Location:** `tests/core/`, `tests/packages/`, `tests/cmake/`, etc.

**Run:**
```bash
pytest tests/core/          # Core module tests
pytest tests/packages/      # Package manager tests
pytest -k "test_platform"   # Specific test pattern
```

**Features:**
- Fast execution (<1 minute for all tests)
- No external dependencies
- Mock external calls
- High code coverage

### Integration Tests (`tests/integration/`)

Tests that verify multiple components work together correctly.

**Run:**
```bash
pytest --integration tests/integration/
```

**Features:**
- May download small files
- Tests cross-component interactions
- Verifies configuration flows
- ~5-10 minutes execution time

### End-to-End Tests (`tests/e2e/`)

Complete workflow tests that simulate real user scenarios.

**Run:**
```bash
pytest tests/e2e/
```

**Features:**
- Tests complete workflows
- May create temporary projects
- Validates user-facing functionality
- ~10-15 minutes execution time

### Link Validation (`tests/link_validation/`)

Validates all external URLs and file hashes to ensure dependencies are accessible.

**Run:**
```bash
# Quick validation
pytest --link-validation

# Full validation with hash checks
pytest --link-validation --validation-level=full
```

**Features:**
- Validates toolchain download URLs
- Checks package manager tool URLs
- Tests git repository accessibility
- Verifies SHA256 hashes
- Caches results for performance

**Documentation:** See [link_validation.md](link_validation.md) for comprehensive guide.

### Regression Tests

Prevents reintroduction of previously fixed bugs.

**Documentation:** See [regression.md](regression.md)

## Test Organization

```
tests/
├── __init__.py
├── conftest.py                     # Global pytest configuration
├── core/                           # Core functionality tests
│   ├── test_platform.py
│   ├── test_directory.py
│   └── test_state.py
├── packages/                       # Package manager tests
│   ├── test_conan.py
│   └── test_vcpkg.py
├── cmake/                          # CMake generation tests
│   └── test_generator.py
├── config/                         # Configuration tests
│   └── test_parser.py
├── integration/                    # Integration tests
│   └── test_full_workflow.py
├── e2e/                           # End-to-end tests
│   └── test_user_workflows.py
└── link_validation/               # External URL validation
    ├── conftest.py
    ├── test_toolchain_links.py
    ├── test_tool_downloader_links.py
    ├── test_git_repositories.py
    └── utils/
        ├── link_checker.py
        ├── hash_validator.py
        └── cache_manager.py
```

## Running Tests

### Basic Commands

```bash
# All unit tests (default)
pytest

# Specific test file
pytest tests/core/test_platform.py

# Specific test function
pytest tests/core/test_platform.py::test_detect_platform

# Pattern matching
pytest -k "platform"                    # Run tests matching "platform"
pytest -k "not slow"                    # Skip slow tests
```

### Parallel Execution

Speed up test execution with `pytest-xdist`:

```bash
# Auto-detect CPU count
pytest -n auto

# Specific worker count
pytest -n 4
```

### Coverage Reports

Generate code coverage reports:

```bash
# Terminal report
pytest --cov=toolchainkit

# HTML report
pytest --cov=toolchainkit --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest --cov=toolchainkit --cov-report=xml
```

### Markers

Tests can be marked for selective execution:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run slow tests only
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

**Available Markers:**
- `unit` - Fast unit tests
- `integration` - Integration tests requiring `--integration`
- `slow` - Slow-running tests
- `link_validation` - External URL validation tests
- `link_validation_slow` - Slow link validation (git clone, large downloads)

### Output Control

```bash
# Verbose output
pytest -v

# Very verbose (show stdout)
pytest -vv

# Show print statements
pytest -s

# Short traceback
pytest --tb=short

# Full traceback
pytest --tb=long

# Stop on first failure
pytest -x

# Show all failures
pytest --maxfail=5                      # Stop after 5 failures
```

## CI/CD Integration

### GitHub Actions Workflows

ToolchainKit uses multiple CI workflows:

1. **Unit Tests** (`.github/workflows/unit-tests.yml`)
   - Runs on every push/PR
   - Fast feedback (<2 minutes)
   - Python 3.9, 3.10, 3.11

2. **Integration Tests** (`.github/workflows/integration-tests.yml`)
   - Runs on PR to main/dev
   - ~10 minutes

3. **Code Quality** (`.github/workflows/code-quality.yml`)
   - Linting (ruff, mypy)
   - Formatting checks
   - Security scans

4. **Link Validation** (`.github/workflows/link-validation.yml`)
   - Weekly schedule (Sundays 2 AM UTC)
   - Manual trigger available
   - HEAD checks only (~1 minute)

5. **Full Link Validation** (`.github/workflows/link-validation-full.yml`)
   - Monthly schedule (1st of month 3 AM UTC)
   - Downloads files and validates hashes
   - ~30-60 minutes

### Running Locally Like CI

Mimic CI environment locally:

```bash
# Unit tests (like CI)
pytest --tb=short -v

# Integration tests (like CI)
pytest --integration --tb=short -v

# Link validation (like CI weekly)
pytest --link-validation --validation-level=head -n auto

# Full validation (like CI monthly)
pytest --link-validation --validation-level=full -n 4
```

## Writing Tests

### Test Structure

Standard test structure:

```python
"""
Tests for [module name].

[Brief description of what is being tested]
"""

import pytest
from toolchainkit.module import Component


class TestComponent:
    """Tests for Component class."""

    def test_basic_functionality(self):
        """Test basic functionality works."""
        component = Component()
        result = component.do_something()
        assert result == expected_value

    def test_error_handling(self):
        """Test error handling."""
        component = Component()
        with pytest.raises(ValueError):
            component.do_invalid_thing()

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_parameterized(self, input, expected):
        """Test with multiple inputs."""
        component = Component()
        result = component.double(input)
        assert result == expected
```

### Fixtures

Use fixtures for setup/teardown:

```python
@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory."""
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    yield test_dir
    # Cleanup happens automatically

def test_with_fixture(temp_dir):
    """Test using fixture."""
    file = temp_dir / "test.txt"
    file.write_text("test")
    assert file.exists()
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked dependency."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "success"

        result = download_file("https://example.com/file")
        assert result == "success"
        mock_get.assert_called_once()
```

## Debugging Tests

### PDB Debugger

Drop into debugger on failure:

```bash
# Stop at first failure
pytest --pdb

# Stop at first failure, then continue
pytest --pdbcls=IPython.terminal.debugger:TerminalPdb --pdb
```

### Logging

Enable debug logging:

```bash
pytest --log-cli-level=DEBUG
```

### Capture Control

Show stdout during tests:

```bash
# Disable capture
pytest -s

# Show captured output even on pass
pytest --capture=no
```

## Performance

### Test Execution Times

Typical execution times:

| Test Suite | Time | Downloads |
|-----------|------|-----------|
| Unit tests | <1 min | None |
| Integration tests | 5-10 min | Small (<100MB) |
| E2E tests | 10-15 min | Medium (<500MB) |
| Link validation (HEAD) | 1-2 min | None |
| Link validation (full) | 30-60 min | Large (~7GB) |

### Optimization Tips

1. **Run selectively** - Use `-k` patterns to run subset
2. **Use parallel execution** - `pytest -n auto` for multicore
3. **Cache validation results** - Link validation caching saves time
4. **Mark slow tests** - Skip with `pytest -m "not slow"`
5. **Use `--lf`** - Only run last failed tests

## Best Practices

### Test Writing

1. **One concept per test** - Keep tests focused
2. **Clear test names** - Describe what is being tested
3. **Use fixtures** - Avoid duplication in setup
4. **Test edge cases** - Not just happy paths
5. **Fast tests** - Prefer mocking over real I/O
6. **Independent tests** - No dependencies between tests

### Test Organization

1. **Mirror source structure** - `tests/core/` for `toolchainkit/core/`
2. **Group related tests** - Use test classes
3. **Mark appropriately** - Use pytest markers for categorization
4. **Document tests** - Docstrings explain intent

### Maintenance

1. **Fix broken tests immediately** - Don't let them linger
2. **Update tests with code changes** - Keep in sync
3. **Review coverage** - Aim for >80% coverage
4. **Refactor test code** - DRY principle applies to tests too

## Troubleshooting

### Common Issues

**Tests fail with import errors:**
```bash
# Ensure toolchainkit is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

**Cache issues in link validation:**
```bash
# Clear cache
rm -rf tests/link_validation/.cache/
pytest --link-validation --clear-cache
```

**Parallel test failures:**
```bash
# Some tests may not be parallel-safe
pytest -n 0  # Disable parallel execution
```

**Flaky tests:**
```bash
# Retry failed tests
pytest --flaky --max-runs=3
```

## Resources

### Documentation

- [Link Validation Guide](link_validation.md) - Comprehensive link validation guide
- [Regression Testing](regression.md) - Regression testing procedures

### External Resources

- [Pytest Documentation](https://docs.pytest.org/) - Official pytest docs
- [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) - Parallel execution plugin
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage plugin

## Contributing

When contributing tests:

1. Add tests for new features
2. Update tests for bug fixes
3. Maintain or improve coverage
4. Follow existing patterns
5. Document complex test setups
6. Mark slow/integration tests appropriately

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for full guidelines.
