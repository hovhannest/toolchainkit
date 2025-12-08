# Testing Strategies

This document describes the testing philosophy, strategies, and best practices for ToolchainKit.

## Testing Philosophy

ToolchainKit follows a comprehensive testing approach with **2385 passing tests** covering:

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test interactions between multiple components
3. **End-to-End (E2E) Tests**: Test complete workflows from start to finish
4. **Smoke Tests**: Fast sanity checks to catch obvious breakage

### Testing Pyramid

```
          /\
         /E2E\
        /------\
       /INTEG- \
      / RATION \
     /----------\
    /   UNIT     \
   / TESTS (80%) \
  /----------------\
```

- **Unit Tests** (80%): Most tests should be fast, isolated unit tests
- **Integration Tests** (15%): Test component interactions
- **E2E Tests** (5%): Test critical user workflows

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── README.md                # Testing documentation
├── core/                    # Core module tests
│   ├── test_directory.py
│   ├── test_python_env.py
│   ├── test_filesystem.py
│   ├── test_download.py
│   ├── test_verification.py
│   ├── test_registry.py
│   ├── test_locking.py
│   ├── test_platform.py
│   └── test_state.py
├── toolchain/               # Toolchain management tests
│   ├── test_registry.py
│   ├── test_downloader.py
│   ├── test_verifier.py
│   ├── test_system_detector.py
│   ├── test_linking.py
│   ├── test_cleanup.py
│   └── test_upgrader.py
├── cmake/                   # CMake integration tests
│   ├── test_toolchain_generator.py
│   ├── test_compilers.py
│   ├── test_stdlib.py
│   ├── test_backends.py
│   └── test_integration.py  # Real CMake builds
├── packages/                # Package manager tests
│   ├── test_base.py
│   ├── test_conan.py
│   └── test_vcpkg.py
├── caching/                 # Build caching tests
│   ├── test_detection.py
│   ├── test_launcher.py
│   └── test_remote.py
├── cross/                   # Cross-compilation tests
│   └── test_targets.py
├── config/                  # Configuration tests
│   ├── test_parser.py
│   ├── test_validation.py
│   └── test_lockfile.py
├── e2e/                     # End-to-end tests
│   ├── test_smoke.py
│   └── test_workflows.py
├── mocks/                   # Test mocks and stubs
│   ├── mock_toolchain.py
│   └── mock_registry.py
└── utils/                   # Test utilities
    └── helpers.py
```

### Test File Naming

- **Unit tests**: `test_<module>.py`
- **Integration tests**: `test_<module>_integration.py`
- **E2E tests**: `test_<feature>.py` in `tests/e2e/`

## Writing Unit Tests

### Basic Structure

```python
"""Tests for toolchainkit.core.directory module."""

import pytest
from pathlib import Path
from toolchainkit.core.directory import (
    create_directory_structure,
    get_global_cache_dir,
)


def test_get_global_cache_dir():
    """Test global cache directory detection."""
    cache_dir = get_global_cache_dir()

    assert cache_dir.exists() or cache_dir.parent.exists()
    assert '.toolchainkit' in str(cache_dir)


def test_create_directory_structure(tmp_path):
    """Test directory structure creation."""
    paths = create_directory_structure(project_root=tmp_path)

    # Verify global cache
    assert paths['global_cache'].exists()
    assert (paths['global_cache'] / 'toolchains').exists()

    # Verify project local
    assert paths['project_local'].exists()
    assert (tmp_path / '.toolchainkit').exists()


def test_create_directory_structure_idempotent(tmp_path):
    """Test that directory creation is idempotent."""
    paths1 = create_directory_structure(project_root=tmp_path)
    paths2 = create_directory_structure(project_root=tmp_path)

    assert paths1 == paths2


@pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
def test_unix_specific_feature(tmp_path):
    """Test Unix-specific functionality."""
    # Unix-specific test
    pass
```

### Test Naming Conventions

- **test_function_name_success**: Test success path
- **test_function_name_error_condition**: Test error handling
- **test_function_name_edge_case**: Test edge cases
- **test_class_method_behavior**: Test class method behavior

### Using Fixtures

**Fixture examples in `conftest.py`**:

```python
"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_toolchain_registry(tmp_path):
    """Create mock toolchain registry."""
    from toolchainkit.core.registry import CacheRegistry

    registry = CacheRegistry(cache_dir=tmp_path / 'cache')
    return registry


@pytest.fixture
def sample_config():
    """Sample configuration for tests."""
    return {
        'project': 'test-project',
        'toolchains': [
            {'name': 'llvm-18', 'type': 'clang', 'version': '18.1.8'}
        ],
        'defaults': {'linux': 'llvm-18'}
    }
```

### Mocking External Dependencies

**Mocking HTTP requests**:

```python
import pytest
import responses
from toolchainkit.core.download import download_file


@responses.activate
def test_download_file_success(tmp_path):
    """Test successful file download."""
    url = 'https://example.com/file.tar.gz'
    dest = tmp_path / 'file.tar.gz'

    responses.add(
        responses.GET,
        url,
        body=b'file content',
        status=200,
        headers={'Content-Length': '12'}
    )

    download_file(url, dest)

    assert dest.exists()
    assert dest.read_bytes() == b'file content'
```

**Mocking filesystem operations**:

```python
from unittest.mock import patch, MagicMock


def test_filesystem_operation_with_mock():
    """Test filesystem operation with mocked Path."""
    with patch('pathlib.Path.exists') as mock_exists:
        mock_exists.return_value = True

        # Test code that checks if path exists
        result = my_function()

        assert result is True
        mock_exists.assert_called_once()
```

### Testing Error Conditions

```python
import pytest
from toolchainkit.core.download import DownloadError


def test_download_invalid_url():
    """Test download with invalid URL."""
    with pytest.raises(DownloadError, match="Invalid URL"):
        download_file('invalid-url', Path('/tmp/file'))


def test_download_network_timeout(tmp_path):
    """Test download with network timeout."""
    with pytest.raises(DownloadError, match="Timeout"):
        download_file(
            'https://slow-server.com/file',
            tmp_path / 'file',
            timeout=0.001  # Very short timeout
        )
```

## Integration Tests

Integration tests verify that multiple components work together correctly.

### Example Integration Test

```python
"""Integration tests for toolchain download and verification."""

import pytest
from pathlib import Path
from toolchainkit.toolchain.downloader import ToolchainDownloader
from toolchainkit.toolchain.verifier import ToolchainVerifier, VerificationLevel


@pytest.mark.integration
@pytest.mark.slow
def test_download_and_verify_toolchain(tmp_path):
    """Test complete download and verification workflow."""
    downloader = ToolchainDownloader(cache_dir=tmp_path / 'cache')
    verifier = ToolchainVerifier()

    # Download toolchain (uses real network)
    toolchain_path = downloader.download(
        toolchain_name='llvm',
        version='18.1.8',
        platform='linux-x64'
    )

    # Verify toolchain
    result = verifier.verify(
        toolchain_path=toolchain_path,
        toolchain_type='clang',
        expected_version='18.1.8',
        level=VerificationLevel.STANDARD
    )

    assert result.passed
    assert toolchain_path.exists()
```

### Testing with Real CMake

```python
"""Integration tests with real CMake builds."""

import pytest
import subprocess
from pathlib import Path


@pytest.mark.integration
@pytest.mark.skipif(not has_cmake(), reason="CMake not available")
def test_cmake_build_with_generated_toolchain(tmp_path):
    """Test CMake build with generated toolchain file."""
    from toolchainkit.cmake.toolchain_generator import (
        CMakeToolchainGenerator,
        ToolchainFileConfig
    )

    # Create simple CMake project
    project_dir = tmp_path / 'project'
    project_dir.mkdir()

    (project_dir / 'CMakeLists.txt').write_text('''
cmake_minimum_required(VERSION 3.20)
project(TestProject CXX)
add_executable(test main.cpp)
''')

    (project_dir / 'main.cpp').write_text('''
#include <iostream>
int main() { std::cout << "Hello\\n"; return 0; }
''')

    # Generate toolchain file
    generator = CMakeToolchainGenerator(project_root=project_dir)
    config = ToolchainFileConfig(
        toolchain_id='llvm-18.1.8-linux-x64',
        toolchain_root=Path('/usr'),
        compiler_type='clang',
        c_compiler=Path('/usr/bin/clang'),
        cxx_compiler=Path('/usr/bin/clang++'),
    )
    toolchain_file = generator.generate(config)

    # Configure CMake
    build_dir = project_dir / 'build'
    result = subprocess.run(
        ['cmake', '-B', str(build_dir), '-DCMAKE_TOOLCHAIN_FILE=' + str(toolchain_file)],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert 'Configuring done' in result.stdout or result.stderr
```

## End-to-End (E2E) Tests

E2E tests verify complete user workflows from start to finish.

### Smoke Tests

Fast sanity checks to catch obvious breakage:

```python
"""Smoke tests for critical functionality."""

import pytest


class TestSmoke:
    """Fast sanity checks (<1s total)."""

    def test_imports(self):
        """Test that all modules can be imported."""
        import toolchainkit
        import toolchainkit.core
        import toolchainkit.toolchain
        import toolchainkit.cmake
        import toolchainkit.packages
        import toolchainkit.caching

        assert toolchainkit.__version__

    def test_platform_detection(self):
        """Test platform detection works."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        assert platform.os in ['linux', 'windows', 'macos']
        assert platform.architecture in ['x64', 'arm64', 'x86', 'arm']

    def test_directory_creation(self, tmp_path):
        """Test directory structure creation."""
        from toolchainkit.core.directory import create_directory_structure

        paths = create_directory_structure(project_root=tmp_path)
        assert paths['global_cache'].exists()
        assert paths['project_local'].exists()
```

### Workflow Tests

Test complete user workflows:

```python
"""E2E workflow tests."""

import pytest
from pathlib import Path


@pytest.mark.e2e
class TestBootstrapWorkflow:
    """Test complete bootstrap workflow."""

    def test_new_project_bootstrap(self, tmp_path):
        """Test bootstrapping a new project."""
        # 1. Create directory structure
        from toolchainkit.core.directory import create_directory_structure
        paths = create_directory_structure(project_root=tmp_path)

        # 2. Parse configuration (or use defaults)
        from toolchainkit.config.parser import parse_config
        config = parse_config(tmp_path / 'toolchainkit.yaml', use_defaults=True)

        # 3. Download and install toolchain
        from toolchainkit.toolchain.downloader import ToolchainDownloader
        downloader = ToolchainDownloader()
        toolchain_path = downloader.download(
            toolchain_name='llvm',
            version='18',
            platform='linux-x64'
        )

        # 4. Generate CMake toolchain file
        from toolchainkit.cmake.toolchain_generator import (
            CMakeToolchainGenerator,
            ToolchainFileConfig
        )
        generator = CMakeToolchainGenerator(project_root=tmp_path)
        toolchain_config = ToolchainFileConfig(
            toolchain_id='llvm-18.1.8-linux-x64',
            toolchain_root=toolchain_path,
            compiler_type='clang',
            c_compiler=toolchain_path / 'bin' / 'clang',
            cxx_compiler=toolchain_path / 'bin' / 'clang++',
        )
        toolchain_file = generator.generate(toolchain_config)

        # Verify everything was created
        assert toolchain_path.exists()
        assert toolchain_file.exists()
        assert paths['project_local'].exists()
```

## Test Markers

Use pytest markers to categorize tests:

```python
# In pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, multiple components)
    e2e: End-to-end tests (slowest, full workflows)
    slow: Slow tests (>5s)
    network: Tests requiring network access
    skipci: Tests to skip in CI
```

**Using markers**:

```python
import pytest


@pytest.mark.unit
def test_fast_unit_test():
    """Fast unit test."""
    pass


@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration():
    """Slow integration test."""
    pass


@pytest.mark.e2e
@pytest.mark.network
def test_e2e_with_network():
    """E2E test requiring network."""
    pass
```

**Running specific markers**:

```bash
# Run only unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Run everything except slow tests
pytest -m "not slow"

# Run unit and integration tests
pytest -m "unit or integration"
```

## Code Coverage

### Measuring Coverage

```bash
# Run tests with coverage
pytest tests/ --cov=toolchainkit --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Goals

- **Overall**: 80%+ coverage
- **Core modules**: 90%+ coverage
- **New code**: 85%+ coverage

### Coverage Configuration

In `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["toolchainkit"]
branch = true
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Test Utilities

### Helper Functions

Create reusable test utilities in `tests/utils/helpers.py`:

```python
"""Test helper functions."""

from pathlib import Path
import subprocess


def has_cmake() -> bool:
    """Check if CMake is available."""
    try:
        subprocess.run(['cmake', '--version'],
                      capture_output=True,
                      timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def has_ninja() -> bool:
    """Check if Ninja is available."""
    try:
        subprocess.run(['ninja', '--version'],
                      capture_output=True,
                      timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def create_test_project(project_dir: Path, has_tests: bool = False):
    """Create a minimal CMake test project."""
    project_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / 'CMakeLists.txt').write_text('''
cmake_minimum_required(VERSION 3.20)
project(TestProject CXX)

add_executable(main src/main.cpp)

if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()
''')

    src_dir = project_dir / 'src'
    src_dir.mkdir(exist_ok=True)
    (src_dir / 'main.cpp').write_text('''
#include <iostream>
int main() {
    std::cout << "Hello, World!\\n";
    return 0;
}
''')

    if has_tests:
        tests_dir = project_dir / 'tests'
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / 'CMakeLists.txt').write_text('''
add_executable(test_main test_main.cpp)
add_test(NAME test_main COMMAND test_main)
''')
        (tests_dir / 'test_main.cpp').write_text('''
#include <cassert>
int main() {
    assert(1 + 1 == 2);
    return 0;
}
''')
```

## Continuous Integration

### CI Configuration

ToolchainKit uses GitHub Actions for CI. Tests run on:

- **Windows**: Latest Windows Server
- **Linux**: Ubuntu 22.04, Ubuntu 20.04
- **macOS**: Latest macOS

### CI Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/ -v --cov=toolchainkit --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Testing Best Practices

### 1. Test Independence

Each test should be independent and not rely on other tests:

```python
# BAD - Tests depend on order
def test_step1():
    global state
    state = "initialized"

def test_step2():
    # Assumes test_step1 ran first
    assert state == "initialized"

# GOOD - Tests are independent
def test_step1():
    state = initialize()
    assert state == "initialized"

def test_step2():
    state = initialize()
    assert state == "initialized"
```

### 2. Use Temporary Directories

Always use temporary directories for test files:

```python
# BAD - Writing to fixed location
def test_file_creation():
    path = Path('/tmp/test.txt')
    path.write_text('test')
    assert path.exists()

# GOOD - Using tmp_path fixture
def test_file_creation(tmp_path):
    path = tmp_path / 'test.txt'
    path.write_text('test')
    assert path.exists()
```

### 3. Clear Test Names

Test names should clearly describe what they test:

```python
# BAD - Unclear names
def test_1():
    pass

def test_function():
    pass

# GOOD - Descriptive names
def test_download_file_creates_file_on_success():
    pass

def test_download_file_raises_error_on_invalid_url():
    pass
```

### 4. Fast Tests

Keep unit tests fast (<100ms each):

```python
# BAD - Unnecessarily slow
def test_function():
    time.sleep(5)  # Don't do this
    result = my_function()
    assert result

# GOOD - Fast and focused
def test_function():
    result = my_function()
    assert result
```

### 5. Mock External Dependencies

Mock network, filesystem, external processes:

```python
import responses


@responses.activate
def test_api_call():
    """Test API call with mocked response."""
    responses.add(
        responses.GET,
        'https://api.example.com/data',
        json={'status': 'ok'},
        status=200
    )

    result = fetch_data()
    assert result['status'] == 'ok'
```

## Debugging Tests

### Running Single Test

```bash
# Run specific test file
pytest tests/core/test_directory.py -v

# Run specific test function
pytest tests/core/test_directory.py::test_get_global_cache_dir -v

# Run specific test class
pytest tests/core/test_directory.py::TestDirectoryCreation -v
```

### Debugging with pdb

```python
def test_something():
    """Test with debugger."""
    import pdb; pdb.set_trace()  # Breakpoint
    result = my_function()
    assert result
```

Run with:

```bash
pytest tests/test_file.py -s  # -s disables output capture
```

### Verbose Output

```bash
# Show print statements
pytest -s

# Show test names
pytest -v

# Show both
pytest -sv

# Show local variables on failure
pytest -l
```

## Summary

ToolchainKit's testing strategy emphasizes:

1. **Comprehensive Coverage**: 2385+ tests covering all modules
2. **Test Pyramid**: Mostly unit tests, some integration tests, few E2E tests
3. **Independence**: Tests don't depend on each other
4. **Speed**: Unit tests are fast, slow tests are marked
5. **Mocking**: External dependencies are mocked
6. **CI Integration**: All tests run on push/PR

When contributing:
- Write tests for all new code
- Follow existing test patterns
- Use appropriate test markers
- Ensure tests pass on all platforms
- Maintain or improve code coverage
