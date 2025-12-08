# Extension and Contribution Guide

This guide explains how to extend ToolchainKit with new features and how to contribute to the project.

## Extension Points

ToolchainKit is designed with extensibility in mind. Here are the main extension points:

### 1. Adding New Toolchains

To add support for a new compiler toolchain:

#### Step 1: Add Metadata to Registry

Edit `toolchainkit/data/toolchains.json`:

```json
{
  "toolchains": {
    "my-compiler": {
      "1.0.0": {
        "linux-x64": {
          "url": "https://example.com/my-compiler-1.0.0-linux-x64.tar.gz",
          "sha256": "abc123...",
          "size_mb": 1024,
          "stdlib": ["mystdlib"],
          "requires_installer": false
        },
        "windows-x64": {
          "url": "https://example.com/my-compiler-1.0.0-windows-x64.zip",
          "sha256": "def456...",
          "size_mb": 1200,
          "stdlib": ["mystdlib"],
          "requires_installer": false
        }
      }
    }
  }
}
```

#### Step 2: Create Compiler Configuration Class

Add to `toolchainkit/cmake/compilers.py`:

```python
from .compilers import CompilerConfig
from pathlib import Path
from typing import List, Dict

class MyCompilerConfig(CompilerConfig):
    """Configuration for My Custom Compiler."""

    def __init__(
        self,
        compiler_path: Path,
        version: str,
        stdlib: str = 'mystdlib',
        **kwargs
    ):
        super().__init__(compiler_path, version)
        self.stdlib = stdlib

    def get_compiler_type(self) -> str:
        return 'mycompiler'

    def get_flags_for_build_type(self, build_type: str) -> List[str]:
        """Get compiler flags for build type."""
        flags = []

        if build_type == 'Debug':
            flags.extend(['-g', '-O0'])
        elif build_type == 'Release':
            flags.extend(['-O3', '-DNDEBUG'])
        elif build_type == 'RelWithDebInfo':
            flags.extend(['-g', '-O2', '-DNDEBUG'])
        elif build_type == 'MinSizeRel':
            flags.extend(['-Os', '-DNDEBUG'])

        # Add stdlib flag
        flags.append(f'-stdlib={self.stdlib}')

        return flags

    def get_cmake_snippet(self) -> str:
        """Generate CMake snippet for this compiler."""
        return f'''
# My Custom Compiler Configuration
set(CMAKE_C_COMPILER "{self.compiler_path}")
set(CMAKE_CXX_COMPILER "{self.compiler_path}")
set(CMAKE_CXX_FLAGS_INIT "-stdlib={self.stdlib}")
'''
```

#### Step 3: Add to Compiler Factory

Update the compiler factory in `toolchainkit/cmake/compilers.py`:

```python
def create_compiler_config(compiler_type: str, **kwargs) -> CompilerConfig:
    """Factory function to create compiler configuration."""
    factories = {
        'clang': ClangConfig,
        'gcc': GccConfig,
        'msvc': MsvcConfig,
        'mycompiler': MyCompilerConfig,  # Add this line
    }

    factory = factories.get(compiler_type.lower())
    if factory is None:
        raise ValueError(f"Unknown compiler type: {compiler_type}")

    return factory(**kwargs)
```

#### Step 4: Add Verification Logic

Add verification for your toolchain in `toolchainkit/toolchain/verifier.py`:

```python
def _verify_mycompiler_toolchain(self, toolchain_path: Path, level: VerificationLevel) -> VerificationResult:
    """Verify My Custom Compiler toolchain."""
    # Implement verification logic
    pass
```

#### Step 5: Write Tests

Create tests in `tests/toolchain/test_mycompiler.py`:

```python
import pytest
from toolchainkit.cmake.compilers import MyCompilerConfig

def test_mycompiler_config_creation():
    """Test My Compiler configuration creation."""
    config = MyCompilerConfig(
        compiler_path=Path('/usr/bin/mycompiler'),
        version='1.0.0',
        stdlib='mystdlib'
    )

    assert config.get_compiler_type() == 'mycompiler'
    assert '-stdlib=mystdlib' in config.get_flags_for_build_type('Release')
```

---

### 2. Adding New Package Managers

To add support for a new C++ package manager:

#### Step 1: Create Package Manager Class

Create `toolchainkit/packages/mypm.py`:

```python
"""My Package Manager integration."""

from pathlib import Path
from typing import Optional
import subprocess
import logging

from .base import PackageManager, PackageManagerError, PackageManagerInstallError

logger = logging.getLogger(__name__)


class MyPackageManager(PackageManager):
    """Integration for My Package Manager."""

    MANIFEST_FILE = 'mypm.json'

    def detect(self) -> bool:
        """Detect if My PM is used in the project."""
        manifest = self.project_root / self.MANIFEST_FILE
        return manifest.exists()

    def install_dependencies(self):
        """Install dependencies using My PM."""
        logger.info("Installing dependencies with My PM...")

        try:
            result = subprocess.run(
                ['mypm', 'install'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Dependencies installed successfully")
            logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            raise PackageManagerInstallError(
                f"My PM install failed: {e.stderr}"
            )
        except FileNotFoundError:
            raise PackageManagerError(
                "My PM executable not found in PATH"
            )

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """Generate CMake integration for My PM."""
        integration_file = self.project_root / '.toolchainkit' / 'cmake' / 'mypm-integration.cmake'
        integration_file.parent.mkdir(parents=True, exist_ok=True)

        # My PM generates a toolchain file, include it
        mypm_toolchain = self.project_root / 'build' / 'mypm_toolchain.cmake'

        content = f'''# My Package Manager Integration
if(EXISTS "{mypm_toolchain}")
    include("{mypm_toolchain}")
else()
    message(WARNING "My PM toolchain file not found. Run 'mypm install' first.")
endif()
'''

        integration_file.write_text(content)
        logger.info(f"Generated My PM integration: {integration_file}")

        return integration_file

    def get_name(self) -> str:
        """Get package manager name."""
        return 'mypm'
```

#### Step 2: Register Package Manager

Update `toolchainkit/packages/__init__.py`:

```python
"""Package manager integration."""

from .base import (
    PackageManager,
    PackageManagerConfig,
    PackageManagerDetector,
    PackageManagerError,
)
from .conan import ConanPackageManager
from .vcpkg import VcpkgPackageManager
from .mypm import MyPackageManager  # Add this

__all__ = [
    'PackageManager',
    'PackageManagerConfig',
    'PackageManagerDetector',
    'PackageManagerError',
    'ConanPackageManager',
    'VcpkgPackageManager',
    'MyPackageManager',  # Add this
]
```

#### Step 3: Write Tests

Create `tests/packages/test_mypm.py`:

```python
import pytest
from pathlib import Path
from toolchainkit.packages.mypm import MyPackageManager

def test_mypm_detect_manifest_exists(tmp_path):
    """Test My PM detection when manifest exists."""
    manifest = tmp_path / 'mypm.json'
    manifest.write_text('{}')

    mypm = MyPackageManager(project_root=tmp_path)
    assert mypm.detect() is True

def test_mypm_detect_no_manifest(tmp_path):
    """Test My PM detection when manifest doesn't exist."""
    mypm = MyPackageManager(project_root=tmp_path)
    assert mypm.detect() is False

def test_mypm_get_name():
    """Test My PM name."""
    mypm = MyPackageManager(project_root=Path('/tmp'))
    assert mypm.get_name() == 'mypm'
```

---

### 3. Adding New Build Backends

To add support for a new CMake build backend:

#### Step 1: Create Backend Class

Add to `toolchainkit/cmake/backends.py`:

```python
class MyBuildBackend(BuildBackend):
    """My Custom Build System Backend."""

    def detect(self) -> bool:
        """Detect if My Build System is available."""
        try:
            result = subprocess.run(
                ['mybuild', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_cmake_generator(self) -> str:
        """Get CMake generator name."""
        return "My Build System"

    def get_configure_args(self) -> List[str]:
        """Get CMake configure arguments."""
        return ['-G', 'My Build System']

    def get_build_args(self) -> List[str]:
        """Get CMake build arguments."""
        # Parallel build with detected CPU count
        import multiprocessing
        return ['-j', str(multiprocessing.cpu_count())]

    def get_name(self) -> str:
        """Get backend name."""
        return 'mybuild'
```

#### Step 2: Register Backend

Update `BackendDetector` in `toolchainkit/cmake/backends.py`:

```python
def detect_available_backends(self) -> List[BuildBackend]:
    """Detect all available build backends."""
    backends = [
        NinjaBackend(),
        MakeBackend(),
        MSBuildBackend(),
        XcodeBackend(),
        NMakeBackend(),
        MyBuildBackend(),  # Add this
    ]

    return [backend for backend in backends if backend.detect()]
```

---

### 4. Adding New Cross-Compilation Targets

To add support for a new cross-compilation target:

#### Step 1: Create Target Class

Add to `toolchainkit/cross/targets.py`:

```python
class MyEmbeddedTarget(CrossCompileTarget):
    """Cross-compilation target for My Embedded Platform."""

    def __init__(
        self,
        arch: str,
        sysroot: Path,
        toolchain_prefix: str = 'myarch-none-eabi-',
        **kwargs
    ):
        super().__init__(os='myembedded', arch=arch)
        self.sysroot = sysroot
        self.toolchain_prefix = toolchain_prefix

    def get_cmake_system_name(self) -> str:
        """Get CMake system name."""
        return 'Generic'

    def get_cmake_system_processor(self) -> str:
        """Get CMake system processor."""
        return self.arch

    def get_toolchain_variables(self) -> Dict[str, str]:
        """Get CMake toolchain variables."""
        return {
            'CMAKE_SYSTEM_NAME': 'Generic',
            'CMAKE_SYSTEM_PROCESSOR': self.arch,
            'CMAKE_SYSROOT': str(self.sysroot),
            'CMAKE_C_COMPILER': f'{self.toolchain_prefix}gcc',
            'CMAKE_CXX_COMPILER': f'{self.toolchain_prefix}g++',
            'CMAKE_FIND_ROOT_PATH_MODE_PROGRAM': 'NEVER',
            'CMAKE_FIND_ROOT_PATH_MODE_LIBRARY': 'ONLY',
            'CMAKE_FIND_ROOT_PATH_MODE_INCLUDE': 'ONLY',
        }

    def get_cmake_snippet(self) -> str:
        """Generate CMake snippet for this target."""
        vars = self.get_toolchain_variables()
        lines = ['# My Embedded Platform Cross-Compilation Configuration']
        for key, value in vars.items():
            lines.append(f'set({key} "{value}")')
        return '\n'.join(lines)
```

---

### 5. Adding New Remote Cache Backends

To add support for a new remote cache backend:

#### Step 1: Create Backend Class

Add to `toolchainkit/caching/remote.py`:

```python
class MyCustomCacheBackend(RemoteCacheBackend):
    """My Custom Remote Cache Backend."""

    def __init__(
        self,
        endpoint: str,
        credentials: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(endpoint, credentials, **kwargs)

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for this backend."""
        env = {
            'SCCACHE_MY_BACKEND_ENDPOINT': self.endpoint,
        }

        if self.credentials:
            if 'token' in self.credentials:
                env['SCCACHE_MY_BACKEND_TOKEN'] = self.credentials['token']
            if 'api_key' in self.credentials:
                env['SCCACHE_MY_BACKEND_API_KEY'] = self.credentials['api_key']

        return env

    def test_connection(self) -> bool:
        """Test connection to the backend."""
        try:
            # Implement connection test logic
            import requests
            response = requests.get(self.endpoint, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
```

## Contribution Guidelines

### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hovhannest/toolchainkit.git
   cd toolchainkit
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

4. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Code Style

ToolchainKit follows these style guidelines:

- **PEP 8**: Python code style guide
- **Type hints**: Use type hints for all function signatures
- **Docstrings**: Use Google-style docstrings
- **Line length**: 100 characters maximum
- **Import order**: Standard library, third-party, local modules

**Example**:

```python
"""
Module for doing something useful.

This module provides...
"""

import os
from pathlib import Path
from typing import Optional, List, Dict

import requests  # Third-party

from toolchainkit.core.platform import detect_platform  # Local


def my_function(param1: str, param2: Optional[int] = None) -> List[str]:
    """
    Do something useful.

    Args:
        param1: Description of param1
        param2: Description of param2 (optional)

    Returns:
        List of result strings

    Raises:
        ValueError: If param1 is invalid

    Example:
        >>> result = my_function("test")
        >>> print(result)
        ['result1', 'result2']
    """
    # Implementation
    pass
```

### Testing Requirements

All contributions must include tests:

1. **Unit tests**: Test individual functions/classes
2. **Integration tests**: Test component interactions (if applicable)
3. **Test coverage**: Aim for 80%+ coverage for new code

**Running tests**:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/core/test_directory.py -v

# Run with coverage
python -m pytest tests/ --cov=toolchainkit --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Writing Tests

**Test file structure**:

```python
"""Tests for my_module."""

import pytest
from pathlib import Path
from toolchainkit.my_module import MyClass, my_function


class TestMyClass:
    """Tests for MyClass."""

    def test_initialization(self):
        """Test MyClass initialization."""
        obj = MyClass(param="value")
        assert obj.param == "value"

    def test_method_success(self):
        """Test method on success path."""
        obj = MyClass(param="value")
        result = obj.method()
        assert result == "expected"

    def test_method_error_handling(self):
        """Test method error handling."""
        obj = MyClass(param="invalid")
        with pytest.raises(ValueError, match="Invalid param"):
            obj.method()


def test_my_function_default_args():
    """Test my_function with default arguments."""
    result = my_function("input")
    assert len(result) > 0


def test_my_function_with_optional_args():
    """Test my_function with optional arguments."""
    result = my_function("input", optional_param=42)
    assert result[0] == "42"


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for tests."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    return test_dir


def test_with_fixture(temp_dir):
    """Test using fixture."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("test content")
    assert file_path.exists()
```

### Documentation Requirements

All contributions should include documentation:

1. **Docstrings**: All public functions, classes, and methods
2. **User guides**: If adding user-facing features (in `docs/`)
3. **Integration guides**: If adding new integrations (in `docs/`)
4. **README updates**: If changing project structure or requirements

### Pull Request Process

1. **Create a branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make changes**: Implement your feature or fix

3. **Write tests**: Ensure all tests pass

4. **Update documentation**: Add/update relevant docs

5. **Run pre-commit checks**:
   ```bash
   pre-commit run --all-files
   ```

6. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add my new feature"
   ```

7. **Push to GitHub**:
   ```bash
   git push origin feature/my-new-feature
   ```

8. **Create Pull Request**: On GitHub, create a PR with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to any related issues
   - Screenshots/examples if applicable

### Commit Message Guidelines

Use conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Build process, dependencies, etc.

**Examples**:

```
feat(toolchain): add support for Zig compiler

Implements Zig compiler integration including:
- Toolchain metadata
- Compiler configuration class
- Verification logic

Closes #123
```

```
fix(download): handle network timeout correctly

Previously, network timeouts would crash the download process.
Now they trigger a retry with exponential backoff.
```

### Code Review Process

All pull requests go through code review:

1. **Automated checks**: CI runs tests, linting, type checking
2. **Manual review**: Maintainers review code for quality and design
3. **Feedback**: Address any comments or requested changes
4. **Approval**: Once approved, PR will be merged

### Versioning

ToolchainKit follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Advanced Topics

### Adding New CLI Commands

To add a new CLI command:

1. **Create command module** in `toolchainkit/cli/commands/`:

```python
"""My new command implementation."""

import argparse
from pathlib import Path
from toolchainkit.cli.base import Command


class MyCommand(Command):
    """My custom command."""

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        """Add command arguments."""
        parser.add_argument(
            '--option',
            type=str,
            help='An option for my command'
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute command."""
        print(f"Executing my command with option: {args.option}")
        # Implementation
        return 0  # Success
```

2. **Register command** in `toolchainkit/cli/main.py`:

```python
from toolchainkit.cli.commands.mycommand import MyCommand

def main():
    parser = argparse.ArgumentParser(description='ToolchainKit')
    subparsers = parser.add_subparsers(dest='command')

    # Existing commands...

    # My command
    my_parser = subparsers.add_parser('mycommand', help='My custom command')
    MyCommand.add_arguments(my_parser)
    my_parser.set_defaults(func=MyCommand().execute)
```

### Performance Optimization

When optimizing code:

1. **Profile first**: Use `cProfile` to find bottlenecks
2. **Cache wisely**: Use LRU cache for expensive computations
3. **Stream when possible**: Avoid loading large files into memory
4. **Parallelize carefully**: Use multiprocessing for CPU-bound tasks

**Example profiling**:

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
my_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Security Considerations

When adding features that handle external data:

1. **Validate inputs**: Never trust user input or external data
2. **Sanitize paths**: Prevent directory traversal attacks
3. **Verify downloads**: Always verify checksums
4. **Use TLS**: Always use HTTPS for downloads
5. **Handle credentials securely**: Never log or print credentials

## Getting Help

- **Documentation**: Check existing docs in `docs/`
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Pull Requests**: Review existing PRs for examples

## Resources

- [README.md](../../README.md) - Project overview
- [architecture.md](./architecture.md) - Architecture documentation
- [building_blocks.md](./building_blocks.md) - Component documentation
- [VISION.md](../VISION.md) - Complete specification and future vision
