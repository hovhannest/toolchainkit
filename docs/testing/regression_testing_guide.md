# Regression Testing Guide

This guide explains ToolchainKit's regression test suite and how to use it.

## Overview

The regression test suite ensures critical functionality remains stable across versions. It covers:

- **Directory Structure** - File system layout and directory creation
- **Config Parsing** - Configuration file format compatibility
- **State Files** - State file format compatibility and persistence
- **Python Compatibility** - Cross-version Python support (3.8-3.13)
- **Platform Specific** - Windows and Unix platform behaviors
- **CMake Generation** - CMake toolchain file generation
- **Test Infrastructure** - Shared fixtures and test data

## Test Organization

```
tests/regression/
├── __init__.py                          # Package initialization
├── conftest.py                          # Shared fixtures
├── test_directory_structure.py          # Directory regression tests (20 tests)
├── test_config_parsing.py               # Config parsing tests (30 tests)
├── test_state_file_compatibility.py     # State file tests (22 tests)
├── test_python_compatibility.py         # Python version tests (9 tests)
├── test_platform_windows.py             # Windows-specific tests (5 tests)
├── test_platform_unix.py                # Unix-specific tests (33 tests)
├── test_cmake_generation.py             # CMake generation tests (25 tests)
└── test_fixtures.py                     # Fixture validation (1 test)
```

## Running Regression Tests

### Run All Regression Tests

```bash
pytest tests/regression/ -v
```

### Run Specific Test Category

```bash
# Directory structure tests
pytest tests/regression/test_directory_structure.py -v

# Config parsing tests
pytest tests/regression/test_config_parsing.py -v

# State file compatibility tests
pytest tests/regression/test_state_file_compatibility.py -v

# Python compatibility
pytest tests/regression/test_python_compatibility.py -v

# Platform-specific (Windows only)
pytest tests/regression/test_platform_windows.py -v

# Platform-specific (Unix only)
pytest tests/regression/test_platform_unix.py -v

# CMake generation tests
pytest tests/regression/test_cmake_generation.py -v
```

### Run with Markers

```bash
# All regression tests
pytest -m regression -v

# Platform-specific tests
pytest -m platform_windows -v
```

### Run with Coverage

```bash
pytest tests/regression/ --cov=toolchainkit --cov-report=html
```

## Test Fixtures

Regression tests use shared fixtures defined in `tests/regression/conftest.py`:

### `regression_workspace`
Creates a complete test workspace with minimal CMake project.

```python
def test_example(regression_workspace):
    assert regression_workspace.exists()
    assert (regression_workspace / 'CMakeLists.txt').exists()
```

### `legacy_config_v1`
Provides a legacy v1 configuration file for compatibility testing.

### `legacy_state_file`
Provides a legacy state file for migration testing.

### `known_good_cmake_toolchain`
Snapshot of known good CMake toolchain file for comparison.

### `sample_toolchain_metadata`
Sample toolchain metadata dictionary.

## Adding New Regression Tests

### 1. Choose the Right File

Add tests to the appropriate file based on what you're testing:
- Directory operations → `test_directory_structure.py`
- Python compatibility → `test_python_compatibility.py`
- Windows behavior → `test_platform_windows.py`

### 2. Use the Regression Marker

```python
@pytest.mark.regression
def test_new_feature_stability():
    """Verify new feature remains stable."""
    # Your test code
```

### 3. Follow Naming Convention

Test names should clearly indicate what is being tested:

```python
@pytest.mark.regression
def test_directory_structure_idempotent():
    """Verify calling initialize multiple times is safe."""
    # Test implementation
```

### 4. Document What You're Testing

Include a docstring explaining:
- What functionality is being tested
- Why it's important for regression
- What would break if this test fails

## Platform-Specific Tests

### Windows Tests

Use `skipif` and `platform_windows` marker:

```python
import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32',
    reason="Windows-only tests"
)

@pytest.mark.regression
@pytest.mark.platform_windows
def test_windows_feature():
    # Test Windows-specific behavior
    pass
```

## Best Practices

### 1. Keep Tests Fast
- Use `tmp_path` for file operations (automatic cleanup)
- Mock external dependencies
- Avoid unnecessary I/O

### 2. Make Tests Deterministic
- Don't rely on system time (mock `datetime`)
- Don't depend on network
- Clean up resources properly

### 3. Test Both Success and Failure
```python
def test_valid_operation():
    # Test valid case
    pass

def test_invalid_operation_raises_error():
    # Test error handling
    with pytest.raises(ValueError):
        # Test invalid case
        pass
```

### 4. Use Fixtures for Setup
```python
@pytest.fixture
def test_data(tmp_path):
    data_file = tmp_path / 'data.json'
    data_file.write_text('{"test": true}')
    return data_file

def test_example(test_data):
    # Use fixture
    assert test_data.exists()
```

## Debugging Failed Tests

### View Full Output
```bash
pytest tests/regression/test_example.py -v -s
```

### Run Single Test
```bash
pytest tests/regression/test_example.py::test_specific_case -v
```

### Drop into Debugger on Failure
```bash
pytest tests/regression/test_example.py --pdb
```

### Show Local Variables
```bash
pytest tests/regression/test_example.py -v -l
```

## Test Metrics

Current regression test coverage:

```
Tests by File:
- test_cmake_generation.py: 25 tests
- test_config_parsing.py: 30 tests
- test_directory_structure.py: 20 tests
- test_fixtures.py: 1 test
- test_platform_unix.py: 33 tests
- test_platform_windows.py: 5 tests
- test_python_compatibility.py: 9 tests
- test_state_file_compatibility.py: 22 tests

Total: 145 regression tests
```

## CI/CD Integration

Tests run automatically on:
- All pull requests
- Main branch commits
- Multiple platforms (Windows, Linux, macOS)
- Multiple Python versions (3.8-3.13)

## Maintenance

### When to Update Regression Tests

1. **Breaking Change** - Update tests to reflect new behavior, document in migration guide
2. **New Feature** - Add regression test to ensure stability
3. **Bug Fix** - Add regression test to prevent reoccurrence

## Questions?

See:
- [Contributing Guide](../../CONTRIBUTING.md)
- [Testing Overview](README.md)
