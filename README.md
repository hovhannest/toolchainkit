# ToolchainKit

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-2385%20passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange.svg)](https://github.com/hovhannest/toolchainkit/releases)

**Hermetic, cross-platform C++ build manager for reproducible builds**

> **⚠️ Alpha Release (v0.1.0)**: Core library is feature-complete and well-tested (2385 passing tests), but CLI tools are still in development. Suitable for integration into build systems and CI/CD pipelines via Python API.

ToolchainKit is a Python library that manages C++ toolchains, generates CMake configurations, and orchestrates build dependencies. It provides programmatic control over compiler toolchains (LLVM, GCC, MSVC), package managers (Conan, vcpkg), build caching (sccache, ccache), and cross-compilation—all with zero system dependencies.

## Features

- 🔧 **Toolchain Management** - Download, verify, and cache LLVM, GCC, MSVC toolchains
- 🌍 **Cross-Platform** - Windows, Linux, macOS (x64/ARM64) with consistent API
- 🎯 **Cross-Compilation** - Android, iOS, Raspberry Pi, embedded targets
- 📦 **Package Managers** - Conan 2.x and vcpkg integration
- ⚡ **Build Caching** - sccache/ccache with remote backends (S3, Redis, HTTP, GCS)
- 🔒 **Hermetic Builds** - Reproducible builds with SHA256 verification
- 🔌 **Plugin System** - Extend with custom compilers and package managers
- ⚙️ **CMake Integration** - Automatic toolchain file generation
- 🔗 **Concurrent-Safe** - Multi-process locking for shared caches
- 📊 **Comprehensive Testing** - 2385 tests with high coverage

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/hovhannest/toolchainkit.git
cd toolchainkit

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Basic Usage (Python API)

```python
from pathlib import Path
from toolchainkit.core.platform import detect_platform
from toolchainkit.toolchain.downloader import ToolchainDownloader
from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig
)

# 1. Detect platform
platform = detect_platform()
print(f"Platform: {platform.platform_string()}")  # e.g., 'linux-x64'

# 2. Download toolchain
downloader = ToolchainDownloader()
result = downloader.download_toolchain(
    toolchain_name="llvm",
    version="18.1.8",
    platform=platform.platform_string(),
    progress_callback=lambda p: print(f"Progress: {p.percentage:.1f}%")
)
print(f"Toolchain installed: {result.toolchain_path}")

# 3. Generate CMake toolchain file
project_root = Path("/path/to/your/project")
generator = CMakeToolchainGenerator(project_root)

config = ToolchainFileConfig(
    toolchain_id=result.toolchain_id,
    toolchain_path=result.toolchain_path,
    compiler_type="clang",
    stdlib="libc++",
    build_type="Release",
    linker="lld",
    caching_enabled=True,
    cache_tool="sccache"
)

toolchain_file = generator.generate(config)
print(f"CMake toolchain file: {toolchain_file}")

# 4. Use with CMake
# cmake -B build -DCMAKE_TOOLCHAIN_FILE=<toolchain_file>
# cmake --build build
```

### Detecting System Toolchains

```python
from toolchainkit.toolchain.system_detector import SystemToolchainDetector

detector = SystemToolchainDetector()
toolchains = detector.detect_all()

for tc in toolchains:
    print(f"{tc.type} {tc.version} at {tc.path}")
# Output:
# clang 18.1.8 at /usr/bin/clang
# gcc 13.2.0 at /usr/bin/gcc
```

### Package Manager Integration

```python
from toolchainkit.packages.conan import ConanIntegration
from pathlib import Path

conan = ConanIntegration(project_root=Path("/path/to/project"))

# Detect or install Conan
if not conan.detect():
    conan.install()

# Configure for project
conan.configure(
    toolchain_path=Path("/path/to/toolchain"),
    build_type="Release"
)

# Install dependencies (assumes conanfile.txt or conanfile.py exists)
conan.install_dependencies()
```

## Architecture

### Directory Structure

```
~/.toolchainkit/          # Global cache (shared)
├── toolchains/           # Downloaded toolchains
├── python/               # Embedded Python 3.11
└── registry.json         # Metadata & references

<project>/.toolchainkit/  # Project-local
├── cmake/                # Generated CMake files
├── packages/             # Package manager caches
└── state.json            # Current configuration
```

### Core Modules

| Module | Description |
|--------|-------------|
| `core.directory` | Cross-platform directory management |
| `core.download` | Resumable downloads with progress tracking |
| `core.locking` | Concurrent access control |
| `core.platform` | Platform/ABI detection |
| `toolchain.*` | Toolchain download, verification, linking |
| `cmake.*` | CMake toolchain generation |
| `config.*` | YAML configuration & validation |
| `packages.*` | Conan/vcpkg integration |
| `caching.*` | Build cache (sccache/ccache) |
| `cross.*` | Cross-compilation targets |
| `plugins.*` | Plugin system |

## Testing

```bash
# Unit tests
pytest                      # All tests (2385 passing)
pytest tests/core/          # Core functionality tests
pytest tests/e2e/           # End-to-end tests
pytest --cov=toolchainkit   # Coverage report

# Link validation (verify external URLs and hashes)
pytest --link-validation tests/link_validation/                      # Quick check (~10s)
pytest --link-validation --validation-level=full tests/link_validation/  # Full validation (~5 min, 7GB download)
pytest --link-validation --no-cache tests/link_validation/           # Force fresh validation
```

### Test Organization

- **Unit Tests** (1800+): Fast, isolated tests for individual functions/classes
- **Integration Tests** (400+): Multi-component interaction tests
- **E2E Tests** (100+): Full workflow tests
- **Regression Tests** (85+): Prevent regressions

See [`tests/README.md`](tests/README.md) for detailed testing guide.

## CI/CD Integration

ToolchainKit includes automated link validation in CI/CD:

- **Weekly Validation** (Sundays 2 AM UTC): Quick HEAD checks for all external URLs
- **Monthly Full Validation** (1st of month 3 AM UTC): Downloads files and validates SHA256 hashes
- **Manual Triggers**: Run from GitHub Actions tab with selectable validation level

Workflows:
- `.github/workflows/link-validation.yml` - Weekly quick checks
- `.github/workflows/link-validation-full.yml` - Monthly full validation

On failure, an issue is automatically created with details. See [Link Validation Guide](docs/testing/link_validation.md) for more information.

## Documentation

- 📖 [User Guides](docs/) - How-to guides for each feature
- 🔧 [Developer Docs](docs/dev/) - Architecture and extension guides
- 🧪 [Testing Guide](docs/testing/) - Regression testing documentation

## Requirements

- Python 3.9+
- Dependencies: requests, PyYAML, filelock, pytest

## Project Status

### What Works (v0.1.0-alpha)

✅ **Core Infrastructure**
- Platform detection (OS, architecture, ABI)
- Directory management (global cache, project-local)
- Download manager (resumable, verified)
- Locking system (multi-process safe)
- Cache registry (reference counting)

✅ **Toolchain Management**
- Toolchain download and extraction
- Metadata registry
- Installation verification
- System toolchain detection
- Link/junction management
- Cleanup and upgrade

✅ **CMake Integration**
- Toolchain file generation
- Compiler configuration
- Standard library selection
- Build backend selection (Ninja, Make, MSBuild, Xcode)

✅ **Package Managers**
- Conan 2.x integration
- vcpkg integration
- Tool downloader (CMake, Ninja, sccache, ccache, Python, Make, Git, clang-tools, cppcheck)

✅ **Build Caching**
- sccache/ccache detection
- Compiler launcher configuration
- Remote backend configuration (S3, Redis, HTTP, GCS, Azure, Memcached)

✅ **Cross-Compilation**
- Target definitions (Android, iOS, Raspberry Pi, embedded)
- Sysroot management
- CMake cross-compilation configuration

✅ **IDE Integration**
- VS Code settings generation
- CMakePresets.json generation

✅ **Plugin System**
- Plugin loading and management
- Auto-discovery
- Compiler/package manager/build backend plugins

✅ **Configuration**
- YAML parsing and validation
- Layer-based composition
- State management

✅ **Testing**
- 2385 tests passing
- High coverage (>80%)
- CI/CD integration

### In Development

🚧 **CLI Commands** - Command structure exists, individual commands need completion
🚧 **Bootstrap Scripts** - Generation logic partially implemented
🚧 **Toolchain Metadata** - Structure exists, needs more toolchain entries

## Contributing

We welcome contributions! Please see:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development setup and guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community guidelines
- [CHANGELOG.md](CHANGELOG.md) - Version history

### Development Setup

```bash
# Clone and setup
git clone https://github.com/hovhannest/toolchainkit.git
cd toolchainkit

# Install in development mode
pip install -e .
pip install -r requirements.txt  # Install dev dependencies

# Run tests
pytest

# Run pre-commit checks (optional)
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Roadmap

See [docs/VISION.md](docs/VISION.md) and [docs/ROADMAP.md](docs/ROADMAP.md) for future plans and design goals.

## License

MIT License - See [LICENSE](LICENSE) for details.

Copyright (c) 2025 Hovhannes Tsakanyan

## Citation

If you use ToolchainKit in your research or project, please cite:

```bibtex
@software{toolchainkit2025,
  author = {Tsakanyan, Hovhannes and Contributors},
  title = {ToolchainKit: Hermetic Cross-Platform C++ Build Manager},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/hovhannest/toolchainkit},
  version = {0.1.0}
}
```

## Acknowledgments

- LLVM Project for Clang/LLVM toolchains
- GCC Project for GCC toolchains
- Microsoft for MSVC toolchains
- Conan and vcpkg teams for package management
- Mozilla for sccache
- ccache team for ccache

## Links

- **Repository**: https://github.com/hovhannest/toolchainkit
- **Issues**: https://github.com/hovhannest/toolchainkit/issues
- **Discussions**: https://github.com/hovhannest/toolchainkit/discussions
- **Documentation**: [docs/](docs/)

---

**Note**: This is an alpha release (v0.1.0). The core library API is stable and well-tested, but CLI tools are still being developed. For production use, integrate via Python API.
