# ToolchainKit Test Suite

This directory contains the complete test suite for ToolchainKit, including unit tests, integration tests, test infrastructure, and test utilities.

## Directory Structure

```
tests/
├── conftest.py                          # Shared pytest fixtures and configuration
├── __init__.py
├── data/                                # Test data files (README.md)
├── fixtures/                            # Test fixtures (README.md)
├── mocks/                               # Mock implementations
│   ├── __init__.py
│   ├── filesystem.py                    # Mock filesystem operations
│   └── network.py                       # Mock HTTP requests/responses
├── utils/                               # Test utilities (README.md)
│   ├── __init__.py
│   ├── assertions.py                    # Custom assertions
│   ├── builders.py                      # Test data builders
│   ├── helpers.py                       # Test helper functions
│   ├── mocks.py                         # Additional mock utilities
│   └── test_utils.py                    # Tests for utilities
├── bootstrap/                           # Tests for bootstrap module
├── caching/                             # Tests for caching module
├── ci/                                  # Tests for CI module
├── cli/                                 # Tests for CLI commands
├── cmake/                               # Tests for CMake generation
├── config/                              # Tests for configuration parsing
├── core/                                # Tests for core modules
├── cross/                               # Tests for cross-compilation
├── e2e/                                 # End-to-end tests (README.md)
├── ide/                                 # Tests for IDE integration
├── integration/                         # Integration tests
├── packages/                            # Tests for package managers
├── plugins/                             # Tests for plugin system
├── regression/                          # Regression tests
├── toolchain/                           # Tests for toolchain management
├── test_filesystem_integration.py       # Filesystem integration tests
├── test_modular_metadata.py             # Modular metadata tests
└── test_python_env_integration.py       # Python environment integration tests
```

## Running Tests

### Run All Tests

```bash
# Run all unit tests (default)
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=toolchainkit --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run platform-specific tests
pytest -m platform_windows
pytest -m platform_linux
pytest -m platform_macos

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Run tests for a specific module
pytest tests/core/test_platform.py

# Run a specific test function
pytest tests/core/test_platform.py::test_detect_platform

# Run a specific test class
pytest tests/core/test_platform.py::TestPlatformInfo
```

### Run Tests with Options

```bash
# Stop on first failure
pytest -x

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Run with detailed output on failure
pytest -vv --tb=long

# Run only tests that failed last time
pytest --lf
```

## Test Markers

ToolchainKit uses pytest markers to categorize tests:

- `@pytest.mark.unit`: Fast, isolated unit tests
- `@pytest.mark.integration`: Integration tests (multiple components)
- `@pytest.mark.e2e`: End-to-end tests (full workflows)
- `@pytest.mark.platform_windows`: Windows-specific tests
- `@pytest.mark.platform_linux`: Linux-specific tests
- `@pytest.mark.platform_macos`: macOS-specific tests
- `@pytest.mark.requires_network`: Tests requiring network access
- `@pytest.mark.requires_toolchain`: Tests requiring actual toolchain
- `@pytest.mark.slow`: Tests that take significant time

Example usage:

```python
import pytest

@pytest.mark.unit
def test_platform_string():
    """Test platform string generation."""
    # Fast unit test...

@pytest.mark.integration
@pytest.mark.slow
def test_toolchain_download():
    """Test complete toolchain download workflow."""
    # Slower integration test...

@pytest.mark.platform_linux
def test_linux_distribution_detection():
    """Test Linux-specific distribution detection."""
    # Linux-only test...
```

## Shared Fixtures

Common fixtures are defined in `conftest.py` and available to all tests:

### `temp_dir`
Provides a temporary directory that is automatically cleaned up:

```python
def test_file_operations(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
```

### `temp_workspace`
Provides a complete workspace structure with CMakeLists.txt and source files:

```python
def test_workspace_setup(temp_workspace):
    assert (temp_workspace / "CMakeLists.txt").exists()
    assert (temp_workspace / ".toolchainkit").is_dir()
    assert (temp_workspace / "src" / "main.cpp").exists()
```

### `sample_config_yaml`
Provides a sample toolchainkit.yaml configuration file:

```python
def test_config_loading(sample_config_yaml):
    # Load and parse configuration...
    config = load_config(sample_config_yaml)
    assert config['project']['name'] == 'test-project'
```

### `isolated_home`
Provides an isolated home directory to avoid affecting user's actual home:

```python
def test_global_cache(isolated_home):
    # Operations use fake home directory
    paths = create_directory_structure()
    assert paths['global_cache'].parent == isolated_home / ".toolchainkit"
```

### `no_network`
Blocks network access to ensure tests don't make real network calls:

```python
@pytest.mark.unit
def test_download_caching(no_network):
    # Network calls will raise RuntimeError
    # Test must use mocked network or cached data
```

### `reset_caches`
Automatically resets module-level caches between tests:

```python
def test_platform_detection():
    # detect_platform() cache is automatically cleared before this test
    platform = detect_platform()
```

## Mock Infrastructure

### MockFilesystem

Mock filesystem for testing without touching disk:

```python
from tests.mocks import MockFilesystem

def test_file_operations():
    fs = MockFilesystem()
    fs.mkdir(Path("test"), parents=True)
    fs.write_text(Path("test/file.txt"), "content")

    assert fs.exists(Path("test/file.txt"))
    assert fs.read_text(Path("test/file.txt")) == "content"
```

### MockDownloader

Mock HTTP downloader for testing network operations:

```python
from tests.mocks import MockDownloader

def test_download():
    downloader = MockDownloader()
    downloader.add_mock_response(
        "https://example.com/file.tar.gz",
        b"fake archive content"
    )

    response = downloader.get("https://example.com/file.tar.gz")
    assert response.status_code == 200
    assert response.content == b"fake archive content"
```

## Test Utilities

### Custom Assertions

```python
from tests.utils.assertions import (
    assert_file_exists,
    assert_dir_exists,
    assert_files_equal,
    assert_cmake_variable,
)

def test_file_creation(temp_dir):
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")

    assert_file_exists(file_path)

def test_cmake_generation(temp_workspace):
    cmake_file = temp_workspace / "toolchain.cmake"
    # Generate CMake file...

    assert_cmake_variable(cmake_file, "CMAKE_C_COMPILER", "/usr/bin/clang")
```

### Test Data Builders

```python
from tests.utils.builders import ToolchainBuilder, ConfigBuilder

def test_toolchain_configuration():
    toolchain = (ToolchainBuilder()
                 .with_name("gcc-13")
                 .with_type("gcc")
                 .with_version("13.2.0")
                 .with_path(Path("/usr/local/gcc-13"))
                 .build())

    assert toolchain['name'] == "gcc-13"
    assert toolchain['type'] == "gcc"
    assert toolchain['compilers']['c'] == "/usr/local/gcc-13/bin/gcc"

def test_config_validation():
    config = (ConfigBuilder()
              .with_project_name("my-project")
              .with_toolchain("llvm-18", "llvm", "18.1.8")
              .with_generator("Ninja")
              .build())

    # Validate config...
```

## Writing New Tests

### Test Structure (AAA Pattern)

Follow the Arrange-Act-Assert pattern:

```python
def test_something(temp_dir):
    # Arrange: Set up test data and environment
    test_file = temp_dir / "test.txt"
    expected_content = "Hello, World!"

    # Act: Execute the code being tested
    test_file.write_text(expected_content)
    actual_content = test_file.read_text()

    # Assert: Verify the results
    assert actual_content == expected_content
```

### Test Naming

- Use descriptive names that explain what is being tested
- Prefix with `test_`
- Use underscores to separate words
- Be specific about the scenario

```python
# Good
def test_detect_platform_returns_platform_info():
    """Test that detect_platform() returns PlatformInfo instance."""

# Bad
def test_platform():
    """Test platform."""
```

### Docstrings

Add docstrings to tests explaining what they test:

```python
def test_lock_acquisition_prevents_concurrent_access(temp_dir):
    """
    Test that acquiring a lock prevents other processes from
    accessing the same resource concurrently.
    """
    # Test implementation...
```

### Using Fixtures

Request fixtures as function parameters:

```python
def test_workspace_structure(temp_workspace):
    """Temp_workspace fixture provides a complete workspace."""
    assert (temp_workspace / "CMakeLists.txt").exists()
```

### Parameterized Tests

Use `@pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("os_name,arch,expected", [
    ("linux", "x64", "linux-x64"),
    ("windows", "x64", "windows-x64"),
    ("macos", "arm64", "macos-arm64"),
])
def test_platform_strings(os_name, arch, expected):
    """Test platform string generation for various platforms."""
    # Test implementation...
```

## Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Modules**: 90%+ coverage for core modules
- **Integration Tests**: Don't count towards coverage (test the tests)

View coverage report:

```bash
pytest --cov=toolchainkit --cov-report=html
# Open htmlcov/index.html in browser
```

## Continuous Integration

Tests run automatically on:
- Push to main/dev branches
- Pull requests
- Scheduled nightly builds

CI runs:
- Unit tests on all platforms (Windows, Linux, macOS)
- Integration tests
- Coverage analysis
- Lint checks

## Best Practices

1. **Isolation**: Each test should be independent and not affect others
2. **Speed**: Unit tests should be fast (<100ms each)
3. **Determinism**: Tests should produce same results every run
4. **Cleanup**: Use fixtures to ensure cleanup even if test fails
5. **Mocking**: Mock external dependencies (network, filesystem) in unit tests
6. **Documentation**: Add docstrings explaining what and why
7. **One Assertion**: Each test should verify one behavior
8. **Descriptive Names**: Test names should describe what they test
9. **Fast Feedback**: Run relevant tests frequently during development
10. **Coverage**: Aim for high coverage, but focus on meaningful tests

## Troubleshooting

### Tests Pass Locally But Fail in CI

- Check platform-specific behavior
- Verify all dependencies are in requirements.txt
- Check for timing issues (use proper waits, not sleep)
- Review CI logs for environment differences

### Slow Tests

- Mark as `@pytest.mark.slow`
- Consider mocking instead of real operations
- Check for unnecessary sleeps or waits
- Run with `-v` to see which tests are slow

### Flaky Tests

- Check for race conditions
- Ensure proper cleanup between tests
- Verify fixture isolation
- Add retry logic for legitimate flakiness (network tests)

### Import Errors

- Ensure `__init__.py` files exist in all package directories
- Check sys.path includes project root
- Verify all dependencies are installed

## Contributing

When adding new tests:

1. Follow existing patterns and conventions
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Use shared fixtures and utilities
4. Update this README if adding new test categories
5. Ensure tests pass on all platforms
6. Maintain or improve coverage

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [Test Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
