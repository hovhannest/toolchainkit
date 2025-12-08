# Developer Documentation

Welcome to the ToolchainKit developer documentation. This directory contains comprehensive guides for developing, extending, and maintaining ToolchainKit.

## Documentation Index

### 1. [Architecture Overview](./architecture.md)

**Purpose**: Understand the high-level architecture and design of ToolchainKit.

**Topics Covered**:
- Project purpose and core objectives
- High-level architecture with layered design
- Directory structure (global cache and project-local)
- Core modules (foundation layer)
- Component layer (toolchain, CMake, packages, caching)
- Design patterns used throughout the codebase
- Extensibility points
- Key abstractions and dependencies

**Read this first** to understand how ToolchainKit is structured.

---

### 2. [Building Blocks and Components](./building_blocks.md)

**Purpose**: Detailed reference for all modules and components.

**Topics Covered**:
- Module organization
- Core modules (directory, python_env, filesystem, download, verification, registry, locking, platform, state, config)
- Toolchain management (registry, downloader, verifier, system_detector, linking, cleanup, upgrader)
- CMake integration (toolchain_generator, compilers, stdlib, backends)
- Package management (base, conan, vcpkg)
- Build caching (detection, launcher, remote backends)
- Module dependencies
- Error handling and logging
- Testing modules
- Performance considerations

**Use this** when implementing features or understanding how specific components work.

---

### 3. [Extension and Contribution Guide](./extending.md)

**Purpose**: Learn how to extend ToolchainKit and contribute to the project.

**Topics Covered**:
- Extension points:
  - Adding new toolchains
  - Adding new package managers
  - Adding new build backends
  - Adding new cross-compilation targets
  - Adding new remote cache backends
- Contribution guidelines
- Code style and conventions
- Testing requirements
- Writing tests
- Pull request process
- Commit message guidelines
- Code review process
- Versioning
- Advanced topics (CLI commands, performance optimization)
- Security considerations

**Read this** before contributing code or extending ToolchainKit.

---

### 4. [Testing Strategies](./testing.md)

**Purpose**: Understand the testing philosophy and how to write effective tests.

**Topics Covered**:
- Testing philosophy and pyramid
- Test organization
- Writing unit tests
- Writing integration tests
- Writing end-to-end (E2E) tests
- Test markers and categorization
- Code coverage
- Test utilities and helpers
- Continuous integration (CI)
- Testing best practices
- Debugging tests

**Use this** when writing tests for new features or fixing bugs.

---

### 5. [Maintenance Guide](./maintenance.md)

**Purpose**: Maintain and troubleshoot ToolchainKit.

**Topics Covered**:
- Routine maintenance tasks:
  - Updating toolchain metadata
  - Dependency updates
  - Security updates
  - Documentation updates
- Troubleshooting common issues:
  - Download failures
  - Verification failures
  - Locking issues
  - CMake configuration failures
  - Package manager integration failures
- Performance optimization
- Debugging techniques
- Backup and recovery
- Release process
- Monitoring and metrics
- Common maintenance commands

**Use this** for troubleshooting issues and maintaining the project.

---

## Quick Start for Developers

### 1. Set Up Development Environment

```bash
# Clone repository
git clone https://github.com/hovhannest/toolchainkit.git
cd toolchainkit

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 2. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/core/test_directory.py -v

# Run with coverage
pytest tests/ --cov=toolchainkit --cov-report=html
```

### 3. Explore the Codebase

```python
# Import core modules
from toolchainkit.core.directory import create_directory_structure
from toolchainkit.core.platform import detect_platform
from toolchainkit.toolchain.registry import ToolchainRegistry

# Detect platform
platform = detect_platform()
print(f"Platform: {platform.platform_string()}")

# Create directory structure
paths = create_directory_structure()
print(f"Global cache: {paths['global_cache']}")

# Look up toolchain
registry = ToolchainRegistry()
metadata = registry.lookup('llvm', '18', platform.platform_string())
print(f"Found LLVM 18: {metadata.url}")
```

### 4. Make Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Write tests for your changes
4. Ensure all tests pass: `pytest tests/ -v`
5. Commit your changes: `git commit -m "feat: add my feature"`
6. Push to GitHub: `git push origin feature/my-feature`
7. Create a pull request

## Project Structure Overview

```
toolchainkit/
├── toolchainkit/          # Main package
│   ├── core/              # Foundation layer (9 modules)
│   ├── toolchain/         # Toolchain management (7 modules)
│   ├── cmake/             # CMake integration (4 modules)
│   ├── packages/          # Package managers (3 modules)
│   ├── caching/           # Build caching (3 modules)
│   ├── cross/             # Cross-compilation (1 module)
│   ├── config/            # Configuration (3 modules)
│   ├── cli/               # Command-line interface
│   ├── ci/                # CI/CD helpers
│   ├── ide/               # IDE integrations
│   ├── bootstrap/         # Bootstrap scripts
│   └── data/              # Embedded data (toolchain metadata)
├── tests/                 # Test suite (2385 tests)
│   ├── core/              # Core module tests
│   ├── toolchain/         # Toolchain tests
│   ├── cmake/             # CMake tests
│   ├── packages/          # Package manager tests
│   ├── caching/           # Caching tests
│   ├── e2e/               # End-to-end tests
│   └── utils/             # Test utilities
├── docs/                  # Documentation
│   ├── dev/               # Developer documentation (you are here!)
│   ├── user_guide_*.md    # User guides
│   └── integration_guide_*.md  # Integration guides
├── README.md              # Project README
├── pyproject.toml         # Project configuration
├── requirements.txt       # Python dependencies
└── pytest.ini             # Test configuration
```

## Key Concepts

### 1. Hermetic Builds

ToolchainKit provides **hermetic builds** - builds that are completely isolated from the system and reproducible across machines. This means:

- **No system dependencies**: Toolchains are downloaded and managed by ToolchainKit
- **Version-locked**: Exact toolchain versions are tracked in lock files
- **Isolated state**: Project-local state is separate from global cache
- **Reproducible**: Same configuration produces same build on any machine

### 2. Shared Cache

Toolchains are stored in a **global shared cache** (`~/.toolchainkit/`) and referenced by projects via symlinks/junctions. This:

- **Saves disk space**: One toolchain can be used by multiple projects
- **Reference counting**: Toolchains are only removed when no projects use them
- **Thread-safe**: File locking ensures safe concurrent access
- **Cross-platform**: Works on Windows, Linux, and macOS

### 3. Zero Configuration

ToolchainKit works with **existing CMake projects** without modifications:

- **No CMakeLists.txt changes**: Your existing CMake code is unchanged
- **Standard CMake workflow**: Use normal `cmake` and `cmake --build` commands
- **Optional configuration**: `toolchainkit.yaml` is optional, can use CLI flags
- **Auto-detection**: Detects system toolchains, package managers, build backends

### 4. Extensibility

ToolchainKit is designed to be **easily extensible**:

- **Abstract base classes**: Defined interfaces for toolchains, package managers, backends
- **Registry pattern**: Easy registration of new components
- **Plugin architecture**: Add new functionality without modifying core
- **Clear extension points**: Documented in [extending.md](./extending.md)

## Coding Standards

### Code Style

- **PEP 8**: Follow Python style guide
- **Type hints**: Use type hints for all function signatures
- **Docstrings**: Google-style docstrings for all public APIs
- **Line length**: 100 characters maximum
- **Import order**: Standard library, third-party, local modules

### Testing

- **Write tests**: All new code must have tests
- **Coverage goal**: 80%+ overall coverage
- **Test independence**: Tests should not depend on each other
- **Fast tests**: Unit tests should be fast (<100ms)
- **Mock externals**: Mock network, filesystem, external processes

### Documentation

- **Docstrings**: All public functions, classes, methods
- **User guides**: For user-facing features
- **Integration guides**: For APIs and integrations
- **Update README**: When structure or requirements change

## Getting Help

- **Documentation**: Check existing docs in `docs/`
- **Architecture**: Read [architecture.md](./architecture.md) for high-level understanding
- **Building Blocks**: Read [building_blocks.md](./building_blocks.md) for detailed module info
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions

## Resources

### Project Documentation

- [README.md](../../README.md) - User-facing project overview
- [VISION.md](../VISION.md) - Complete specification and future vision
- [pyproject.toml](../../pyproject.toml) - Project configuration

### GitHub

- **Repository**: https://github.com/hovhannest/toolchainkit
- **Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Pull Requests**: Contribute code

## Contributing

We welcome contributions! Before contributing:

1. **Read [extending.md](./extending.md)** for contribution guidelines
2. **Check existing issues** to avoid duplicates
3. **Discuss major changes** in GitHub Discussions first
4. **Follow code style** and testing requirements
5. **Write tests** for all changes
6. **Update documentation** as needed

## License

ToolchainKit is released under the MIT License. See [LICENSE](../../LICENSE) for details.

---

**Happy coding!** If you have questions or need help, don't hesitate to ask in GitHub Discussions.
