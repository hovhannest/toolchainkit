# Bootstrap Script Generation

> **⚠️ Status: Partially Implemented**
> Bootstrap functionality is partially implemented in v0.1.0. The core `BootstrapGenerator` class exists but the CLI integration is planned for v0.2.0+.
> Use the Python API directly to generate bootstrap scripts.

ToolchainKit can generate platform-specific bootstrap scripts to automate project setup.

## Overview

The `BootstrapGenerator` creates `bootstrap.sh` (Unix) and `bootstrap.bat` (Windows) scripts that automate:
- Python availability check
- ToolchainKit installation
- Toolchain configuration
- Dependency installation
- CMake configuration

## Python Virtual Environments and Package Isolation

### Bootstrap Scripts Do NOT Create Python Virtual Environments

The generated bootstrap scripts (`bootstrap.sh`, `bootstrap.bat`, `bootstrap.ps1`) **do not create or activate Python virtual environments**. They expect:

1. **Python is already installed** and available in the system PATH
2. **ToolchainKit (`tkgen`)** is either already installed or will be installed via `pip install --user`
3. **System Python** or **active virtual environment** (if you activated one before running the script) will be used

If you want to use a Python virtual environment:
- Create and activate it **before** running the bootstrap script
- The bootstrap script will use whatever Python environment is currently active

```bash
# Example: Using a virtual environment (Linux/macOS)
python3 -m venv .venv
source .venv/bin/activate
./bootstrap.sh

# Example: Using a virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate
bootstrap.bat
```

**Note:** While bootstrap scripts don't create venvs, if Conan is downloaded to `.toolchainkit/tools/conan` (when `use_system_conan: false`), ToolchainKit creates an isolated Python venv for that Conan installation at `.toolchainkit/tools/conan/venv`.

### Conan Package Isolation

When using Conan as the package manager, ToolchainKit supports **project-local package isolation** through the `conan_home` configuration:

```yaml
packages:
  manager: conan
  conan_home: .toolchainkit/conan  # Project-local Conan home
```

**How it works:**
1. The `conan_home` setting sets the `CONAN_HOME` environment variable when running Conan
2. By setting it to `.toolchainkit/conan` (relative path), packages are stored in `<project>/.toolchainkit/conan/p/`
3. This isolates project dependencies from system-wide Conan packages in `~/.conan2`
4. The `CONAN_HOME` environment variable is automatically set when running `tkgen configure` or bootstrap
5. Conan stores its configuration, profiles, and package cache within `CONAN_HOME`

**Benefits:**
- **Reproducibility**: Project has its own isolated set of dependencies
- **No conflicts**: Different projects can use different versions of the same packages
- **Portability**: The entire `.toolchainkit` directory can be committed (if desired) or cleaned independently
- **Clean separation**: Conan files are kept separate from toolchains and tools

**Example:**
```bash
# System Conan cache (default, without conan_home)
conan cache path fmt/10.2.1
# → C:\Users\username\.conan2\p\fmtXXXXXXX\e

# Project-local Conan cache (with conan_home: .toolchainkit/conan)
# After running bootstrap with the configuration above:
cd <project>
dir .toolchainkit\conan\p
# → .toolchainkit\conan\p\fmtXXXXXXX\  (packages stored locally)
```

**Recommendation:** Use `.toolchainkit/conan` instead of `.toolchainkit` directly to keep Conan's files (cache, profiles, settings) separate from toolchains and other ToolchainKit artifacts.

**Note:** If you don't specify `conan_home`, Conan uses the system default `~/.conan2` directory (shared across all projects).

## Usage

```python
from toolchainkit.bootstrap import BootstrapGenerator
from pathlib import Path

# Create generator
generator = BootstrapGenerator(
    project_root=Path("/path/to/project"),
    config={
        "toolchain": "llvm-18",
        "build_type": "Release",
        "build_dir": "build",
        "package_manager": "conan"
    }
)

# Generate scripts
generator.generate_all()
```

## Configuration

Configuration dict accepts:

- **toolchain**: Toolchain name (e.g., `'llvm-18'`, `'gcc-13'`)
- **build_type**: Build type (`'Debug'`, `'Release'`, `'RelWithDebInfo'`, `'MinSizeRel'`)
- **build_dir**: Build directory name (default: `'build'`)
- **package_manager**: Package manager name (`'conan'`, `'vcpkg'`, or `None`)
- **cmake_args**: List of additional CMake arguments (e.g., `['-DENABLE_TESTS=ON']`)
- **env**: List of environment variables to set (e.g., `[['CC', 'clang']]`)
- **pre_configure_hook**: Path to script to run before configuration
- **post_configure_hook**: Path to script to run after configuration

## API Reference

### BootstrapGenerator

```python
class BootstrapGenerator:
    """Generate platform-specific bootstrap scripts."""

    def __init__(self, project_root: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize bootstrap generator.

        Args:
            project_root: Project root directory
            config: Project configuration dict
        """

    def generate_all(self) -> Dict[str, Path]:
        """
        Generate all bootstrap scripts.

        Returns:
            Dict mapping script names to their paths
        """

    def generate_unix_script(self) -> Path:
        """
        Generate bootstrap.sh for Unix systems.

        Returns:
            Path to generated bootstrap.sh
        """

    def generate_windows_script(self) -> Path:
        """
        Generate bootstrap.bat for Windows.

        Returns:
            Path to generated bootstrap.bat
        """
```

## Generated Script Contents

### Unix (bootstrap.sh)

```bash
#!/bin/bash
set -e

echo "=== Project Bootstrap ==="
echo "Project: my-project"
# Toolchain: llvm-18
echo "Toolchain: llvm-18"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Install ToolchainKit
echo "Installing ToolchainKit..."
pip install --upgrade toolchainkit

# Configure toolchain
echo "Configuring toolchain..."
python3 -m toolchainkit configure \
    --toolchain llvm-18 \
    --build-type Release

# Install dependencies (if package manager configured)
if [ -f conanfile.txt ] || [ -f conanfile.py ]; then
    echo "Installing dependencies with Conan..."
    conan install . --build=missing
fi

# Configure CMake
echo "Configuring CMake..."
cmake -B build -S .

echo ""
echo "=== Bootstrap complete ==="
echo "Build with: cmake --build build"
```

### Windows (bootstrap.bat)

```batch
@echo off
setlocal

echo === Project Bootstrap ===
echo Project: my-project
REM Toolchain: llvm-18
echo Toolchain: llvm-18
echo.

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found
    exit /b 1
)

REM Install ToolchainKit
echo Installing ToolchainKit...
pip install --upgrade toolchainkit

REM Configure toolchain
echo Configuring toolchain...
python -m toolchainkit configure ^
    --toolchain llvm-18 ^
    --build-type Release

REM Install dependencies (if package manager configured)
if exist conanfile.txt (
    echo Installing dependencies with Conan...
    conan install . --build=missing
)

REM Configure CMake
echo Configuring CMake...
cmake -B build -S .

echo.
echo === Bootstrap complete ===
echo Build with: cmake --build build
```

## Example Integration

### In Python Script

```python
from toolchainkit.bootstrap import BootstrapGenerator
from pathlib import Path

def setup_project():
    """Generate bootstrap scripts for project."""
    generator = BootstrapGenerator(
        project_root=Path.cwd(),
        config={
            "toolchain": "llvm-18",
            "build_type": "Release",
            "package_manager": "conan"
        }
    )

    scripts = generator.generate_all()
    print(f"Generated {len(scripts)} bootstrap scripts:")
    for name, path in scripts.items():
        print(f"  - {name}: {path}")

if __name__ == "__main__":
    setup_project()
```

### As Part of Project Setup

```python
# setup_project.py
from toolchainkit.bootstrap import BootstrapGenerator
from toolchainkit.core.directory import create_directory_structure
from pathlib import Path

def initialize_project():
    """Initialize project with ToolchainKit."""
    project_root = Path.cwd()

    # Create directory structure
    print("Creating directory structure...")
    create_directory_structure(project_root)

    # Generate bootstrap scripts
    print("Generating bootstrap scripts...")
    generator = BootstrapGenerator(
        project_root=project_root,
        config={
            "toolchain": "llvm-18",
            "build_type": "Release",
            "build_dir": "build",
            "package_manager": "conan"
        }
    )
    generator.generate_all()

    print("Project initialized successfully!")
    print("Run './bootstrap.sh' (Unix) or 'bootstrap.bat' (Windows) to bootstrap.")

if __name__ == "__main__":
    initialize_project()
```

## Use Cases

### CI/CD Integration

Bootstrap scripts are useful in CI/CD pipelines:

```yaml
# .github/workflows/build.yml
name: Build
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Bootstrap project
        run: ./bootstrap.sh
      - name: Build
        run: cmake --build build
```

### New Developer Onboarding

New developers can set up the project with a single command:

```bash
# Clone and bootstrap
git clone https://github.com/myorg/myproject.git
cd myproject
./bootstrap.sh
```

### Reproducible Environments

Bootstrap scripts ensure consistent setup across:
- Development machines
- CI/CD systems
- Docker containers
- Virtual machines

## Customization

You can customize generated scripts by modifying the configuration:

```python
generator = BootstrapGenerator(
    project_root=Path.cwd(),
    config={
        "toolchain": "gcc-14",
        "build_type": "Debug",
        "build_dir": "build-debug",
        "package_manager": "vcpkg",
        # Additional custom options
        "cmake_options": ["-DENABLE_TESTS=ON", "-DENABLE_COVERAGE=ON"],
        "install_deps_first": True,
    }
)
```

## Error Handling

Bootstrap scripts include error checking:

- Python availability
- ToolchainKit installation success
- Toolchain configuration success
- Dependency installation success (if applicable)
- CMake configuration success

Scripts exit with non-zero code on error, suitable for CI/CD failure detection.

## See Also

- [CLI Reference](cli.md) - Command-line interface
- [Configuration](config.md) - Configuration file format
- [CI/CD Templates](ci_cd.md) - CI/CD integration
- [Directory Structure](directory.md) - Project layout
