# ToolchainKit Architecture Overview

## Project Purpose

**ToolchainKit** is a hermetic, cross-platform C++ build manager that provides reproducible builds, portable toolchains, and intelligent caching for any CMake-based C++ project without requiring modifications to existing code.

### Core Objectives

1. **Hermetic Builds**: Self-contained, reproducible environments independent of system state
2. **Zero Configuration**: Works with existing CMake projects without modifications
3. **Toolchain Management**: Automatic download, installation, and switching between compilers
4. **Build Acceleration**: Intelligent caching with sccache/ccache integration
5. **Cross-Platform**: Seamless support for Windows, Linux, and macOS
6. **Package Integration**: Built-in support for Conan, vcpkg, and CPM
7. **Cross-Compilation**: Support for Android, iOS, Raspberry Pi, and other embedded platforms

## High-Level Architecture

ToolchainKit follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI & User Interface                      │
│              (tkgen init, configure, build)                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│               Orchestration Layer                            │
│    (CMake Generation, State Management, Configuration)       │
├──────────────────────────────────────────────────────────────┤
│  CMake Generator │ Config Parser │ State Manager │ Lock File │
└───┬─────────┬────┴───────┬───────┴───────┬──────┴───────────┘
    │         │            │               │
┌───▼─────────▼────────────▼───────────────▼──────────────────┐
│              Component Layer (Building Blocks)               │
├─────────────┬────────────┬─────────────┬─────────────────────┤
│  Toolchain  │   CMake    │  Packages   │    Caching          │
│  Management │ Integration│ Management  │   & Build           │
├─────────────┼────────────┼─────────────┼─────────────────────┤
│ • Registry  │ • Toolchain│ • Conan     │ • Detection         │
│ • Downloader│   Generator│ • vcpkg     │ • Launcher          │
│ • Verifier  │ • Compilers│ • Base      │ • Remote Backends   │
│ • Detector  │ • Stdlib   │   Abstraction│                    │
│ • Cleanup   │ • Backends │             │                     │
│ • Upgrader  │            │             │                     │
│ • Linking   │            │             │                     │
└─────────────┴────────────┴─────────────┴─────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                   Foundation Layer                           │
├──────────────────────────────────────────────────────────────┤
│  Core Services (Cross-Platform Primitives)                   │
│  • Directory Management    • Download Manager                │
│  • Filesystem Utilities    • Hash Verification               │
│  • Platform Detection      • Locking & Concurrency           │
│  • Python Environment      • Registry (Shared Cache)         │
│  • State Management        • Configuration Parsing           │
└──────────────────────────────────────────────────────────────┘
```

## Directory Structure

### Global Shared Cache

**Location**:
- Linux/macOS: `~/.toolchainkit/`
- Windows: `%USERPROFILE%\.toolchainkit\`

```
~/.toolchainkit/
├── toolchains/          # Downloaded toolchain installations
│   ├── llvm-18.1.8-linux-x64/
│   ├── gcc-13.2.0-linux-x64/
│   └── msvc-17.8-windows-x64/
├── python/              # Embedded Python interpreter (3.11.7)
├── lock/                # Concurrent access control
└── registry.json        # Toolchain metadata and references
```

### Project-Local Structure

**Location**: `<project-root>/.toolchainkit/`

```
.toolchainkit/
├── packages/            # Package manager caches (Conan/vcpkg)
├── cmake/               # Generated CMake files
│   └── toolchainkit/    # CMake toolchain files
├── state.json           # Current configuration state
└── toolchains -> ~/.toolchainkit/toolchains  # Symlink to shared cache
```

## Core Modules (Foundation Layer)

### 1. Directory Management (`toolchainkit.core.directory`)

**Purpose**: Cross-platform directory structure management for global cache and project-local state.

**Key Functions**:
- `get_global_cache_dir()` - Platform-specific global cache location
- `get_project_local_dir(project_root)` - Project-local `.toolchainkit/` path
- `ensure_global_cache_structure()` - Creates global cache directories
- `ensure_project_structure(project_root)` - Creates project-local directories
- `update_gitignore(project_root)` - Adds `.toolchainkit/` to `.gitignore`

**Design Pattern**: Idempotent operations - safe to call multiple times.

---

### 2. Python Environment (`toolchainkit.core.python_env`)

**Purpose**: Hermetic Python environment with isolated interpreter.

**Key Functions**:
- `setup_python_environment()` - Downloads and sets up Python 3.11.7
- `get_python_executable()` - Returns path to embedded Python
- Platform-specific binary downloads for Windows, Linux, macOS (x64/ARM64)

**Design Pattern**: Download once, use everywhere. Ensures consistent Python version across all machines.

---

### 3. Filesystem Utilities (`toolchainkit.core.filesystem`)

**Purpose**: Cross-platform file operations with security hardening.

**Key Functions**:
- `create_link(target, link_path)` - Platform-aware symlinks/junctions
- `extract_archive(archive_path, dest)` - Secure archive extraction
- `atomic_write(path, content)` - Crash-safe file writes
- `compute_file_hash(path, algorithm)` - File hashing (SHA256, SHA512, MD5)
- `safe_delete(path)` - Safe file/directory deletion with guards
- `find_executable(name)` - Executable search in PATH

**Security Features**: Directory traversal prevention, path validation, long path support (Windows).

---

### 4. Download Manager (`toolchainkit.core.download`)

**Purpose**: HTTP/HTTPS downloads with progress tracking and verification.

**Key Functions**:
- `download_file(url, dest, expected_hash, progress_callback)` - Resumable downloads
- Streaming checksum verification
- Automatic retry with exponential backoff
- TLS verification for secure connections

**Design Pattern**: Memory-efficient streaming - constant memory for any file size.

---

### 5. Hash Verification (`toolchainkit.core.verification`)

**Purpose**: File integrity verification with multiple algorithms.

**Key Functions**:
- `compute_hash(file_path, algorithm)` - Streaming hash computation
- `verify_hash(file_path, expected_hash, algorithm)` - Constant-time comparison
- `verify_hash_file(hash_file_path)` - GNU coreutils format support
- Optional GPG signature verification

**Security**: Timing-attack resistance, path traversal prevention.

---

### 6. Shared Cache Registry (`toolchainkit.core.registry`)

**Purpose**: Thread-safe registry for tracking toolchain installations across projects.

**Key Functions**:
- `register_toolchain(toolchain_id, path, project_root)` - Register toolchain
- `increment_reference(toolchain_id, project_root)` - Reference counting
- `get_toolchain_info(toolchain_id)` - Retrieve toolchain metadata
- `list_unused_toolchains(min_age_days)` - Cleanup analysis

**Concurrency**: File locking ensures safe concurrent access from multiple processes.

---

### 7. Concurrent Access Control (`toolchainkit.core.locking`)

**Purpose**: Cross-platform file-based locking for multi-process coordination.

**Key Classes**:
- `LockManager` - Manages registry, toolchain, and project locks
- `DownloadCoordinator` - Prevents duplicate downloads with wait-and-notify pattern

**Lock Types**:
- **Registry Lock**: Protects global toolchain registry modifications
- **Toolchain Lock**: Prevents duplicate downloads/installations
- **Project Lock**: Protects project-local state modifications

**Features**: Timeout support, automatic cleanup, stale lock detection.

---

### 8. Platform Detection (`toolchainkit.core.platform`)

**Purpose**: Automatic detection of operating system, architecture, and ABI.

**Key Functions**:
- `detect_platform()` - Returns `PlatformInfo` object
- Detects: OS (Windows, Linux, macOS, Android, iOS)
- Detects: Architecture (x64, arm64, x86, arm, riscv64)
- Detects: ABI (glibc/musl on Linux, MSVC on Windows, deployment target on macOS)

**Performance**: LRU caching for instant subsequent calls.

---

### 9. State Management (`toolchainkit.core.state`)

**Purpose**: Project state tracking and change detection.

**Key Functions**:
- `load_state(project_root)` - Load current state
- `save_state(project_root, state)` - Save state atomically
- `detect_changes(project_root, config)` - Detect configuration changes

**State Tracks**:
- Active toolchain and configuration hash
- CMake configuration status
- Package manager and build caching state
- Timestamps for bootstrap and configuration operations

---

### 10. Configuration Parsing (`toolchainkit.config.parser`)

**Purpose**: YAML-based configuration file parsing with validation.

**Key Functions**:
- `parse_config(config_path)` - Parse `toolchainkit.yaml`
- Strongly-typed dataclasses for configuration objects
- Support for toolchains, build settings, package managers, cross-compilation

**Validation**: Comprehensive validation with clear error messages.

## Component Layer (Building Blocks)

### Toolchain Management

#### 1. Toolchain Registry (`toolchainkit.toolchain.registry`)

**Purpose**: Database of available toolchains with download URLs and metadata.

**Key Features**:
- Version resolution (exact, major.minor, major only, "latest")
- Platform compatibility checking
- SHA-256 checksums and size information
- Fast lookup performance (<10ms) with in-memory caching

**Example**:
```python
registry = ToolchainRegistry()
metadata = registry.lookup("llvm", "18", "linux-x64")
# Returns: ToolchainMetadata(url=..., sha256=..., size_mb=...)
```

---

#### 2. Toolchain Downloader (`toolchainkit.toolchain.downloader`)

**Purpose**: Automated toolchain download, extraction, verification, and caching.

**Orchestrates**:
- Download manager for HTTP downloads
- Filesystem utilities for extraction
- Hash verification for integrity
- Registry management for caching

**Progress Reporting**: Two-phase progress (download 0-50%, extraction 50-100%).

---

#### 3. Toolchain Verifier (`toolchainkit.toolchain.verifier`)

**Purpose**: Multi-level verification from quick sanity checks to full compile tests.

**Verification Levels**:
- `MINIMAL` (~1s): File presence checks
- `STANDARD` (~5s): Executability tests, version validation
- `THOROUGH` (~10s): ABI compatibility checks, symlink integrity
- `PARANOID` (~30s): Compile test (compile and run a test program)

---

#### 4. System Toolchain Detector (`toolchainkit.toolchain.system_detector`)

**Purpose**: Automatic detection of compilers already installed on the system.

**Detection Strategies**:
- PATH search
- Standard locations (`/usr/bin`, `C:\Program Files`, etc.)
- Windows registry (for MSVC)
- Package manager queries

**Supports**: LLVM/Clang, GCC, MSVC across all platforms.

---

#### 5. Linking Manager (`toolchainkit.toolchain.linking`)

**Purpose**: Cross-platform filesystem linking for efficient toolchain references.

**Link Types**:
- **Linux/macOS**: Symlinks
- **Windows**: Directory junctions (no admin required)

**Key Functions**:
- `create_link(target, link_path)` - Create link
- `resolve_link(link_path)` - Resolve link target
- `find_broken_links(directory)` - Find and cleanup broken links

---

#### 6. Toolchain Cleanup (`toolchainkit.toolchain.cleanup`)

**Purpose**: Safe removal of unused toolchains from shared cache.

**Features**:
- Reference counting tracks which projects use each toolchain
- Age-based cleanup (remove toolchains not accessed for X days)
- Space-triggered cleanup (when disk space drops below threshold)
- Dry-run mode for preview

**Safety**: Never removes referenced toolchains.

---

#### 7. Toolchain Upgrader (`toolchainkit.toolchain.upgrader`)

**Purpose**: Upgrade toolchains and ToolchainKit itself.

**Features**:
- Semantic version comparison
- Single toolchain upgrade or bulk upgrade of all installed toolchains
- ToolchainKit self-upgrade via pip
- Automatic cleanup of old versions

### CMake Integration

#### 1. CMake Toolchain Generator (`toolchainkit.cmake.toolchain_generator`)

**Purpose**: Generate CMake toolchain files that configure everything.

**Generates**:
- Compiler paths (CC, CXX)
- Compiler flags (stdlib, optimization, warnings)
- Linker settings (lld, gold, mold)
- Build caching configuration (sccache/ccache)
- Package manager integration (Conan/vcpkg)
- Cross-compilation settings (Android, iOS)

**Output Example**:
```cmake
# .toolchainkit/cmake/toolchain-llvm-18.cmake
set(CMAKE_C_COMPILER "${TOOLCHAINKIT_ROOT}/toolchains/llvm-18.1.8-linux-x64/bin/clang")
set(CMAKE_CXX_COMPILER "${TOOLCHAINKIT_ROOT}/toolchains/llvm-18.1.8-linux-x64/bin/clang++")
set(CMAKE_CXX_FLAGS_INIT "-stdlib=libc++")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_C_COMPILER_LAUNCHER sccache)
set(CMAKE_CXX_COMPILER_LAUNCHER sccache)
```

---

#### 2. Compiler Configuration (`toolchainkit.cmake.compilers`)

**Purpose**: Compiler-specific configuration classes for Clang, GCC, and MSVC.

**Classes**:
- `ClangConfig` - Clang/LLVM compiler settings
- `GccConfig` - GCC compiler settings
- `MsvcConfig` - MSVC compiler settings

**Features**:
- Automatic flag generation based on build type (Debug, Release, RelWithDebInfo, MinSizeRel)
- Standard library selection (libc++, libstdc++, MSVC)
- Linker selection (lld, gold, mold, bfd)
- Sanitizer support (ASan, UBSan, TSan)

---

#### 3. Standard Library Configuration (`toolchainkit.cmake.stdlib`)

**Purpose**: Independent C++ standard library configuration decoupled from compiler.

**Supported Standard Libraries**:
- `libc++` (LLVM)
- `libstdc++` (GNU)
- `MSVC` standard library

**Cross-Combinations**: Supports Clang + libstdc++ (common on Linux with custom GCC).

---

#### 4. CMake Build Backends (`toolchainkit.cmake.backends`)

**Purpose**: Automatic detection and configuration of CMake build backends.

**Supported Backends**:
- **Ninja**: Fast, parallel, cross-platform (preferred)
- **Make**: GNU Make on Linux/macOS
- **MSBuild**: Visual Studio integration on Windows
- **Xcode**: macOS native IDE integration
- **NMake**: Windows command-line fallback

**Preference**: Ninja > Platform Native > Make for optimal performance.

### Package Management

#### 1. Package Manager Base (`toolchainkit.packages.base`)

**Purpose**: Abstract base class for package manager integrations.

**Key Classes**:
- `PackageManager` (ABC) - Defines common interface
- `PackageManagerConfig` - Configuration dataclass
- `PackageManagerDetector` - Auto-detection with registry pattern

**Interface**:
```python
class PackageManager(ABC):
    @abstractmethod
    def detect(self) -> bool:
        """Detect if this package manager is used in the project."""

    @abstractmethod
    def install_dependencies(self):
        """Install project dependencies."""

    @abstractmethod
    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """Generate CMake integration file."""
```

---

#### 2. Conan Integration (`toolchainkit.packages.conan`)

**Purpose**: Conan 2.x package manager integration.

**Features**:
- Automatic platform mapping (OS, architecture)
- Compiler detection and profile generation
- Standard library configuration
- Dependency installation via `conan install`
- CMake integration using Conan toolchain files

---

#### 3. vcpkg Integration (`toolchainkit.packages.vcpkg`)

**Purpose**: vcpkg package manager integration with manifest mode.

**Features**:
- VCPKG_ROOT detection from environment and common paths
- Automatic triplet selection for 17+ platform combinations
- Manifest mode dependency installation
- CMake toolchain chaining via `VCPKG_CHAINLOAD_TOOLCHAIN_FILE`

### Build Caching

#### 1. Cache Detection (`toolchainkit.caching.detection`)

**Purpose**: Automatic detection of sccache/ccache on system.

**Features**:
- Detection in PATH, local tools, standard locations
- Download and installation of sccache from GitHub releases
- Version detection and validation
- Graceful fallback when cache tools unavailable

---

#### 2. Compiler Launcher Configuration (`toolchainkit.caching.launcher`)

**Purpose**: CMake variable generation for compiler launchers.

**Generates**:
- `CMAKE_C_COMPILER_LAUNCHER`, `CMAKE_CXX_COMPILER_LAUNCHER`
- Environment variables (SCCACHE_DIR, CCACHE_DIR, cache size, etc.)
- Cache statistics parsing and retrieval

---

#### 3. Remote Cache Backends (`toolchainkit.caching.remote`)

**Purpose**: Remote cache backend configuration for team builds.

**Supported Backends**:
- **S3**: AWS S3, MinIO, DigitalOcean Spaces, Wasabi
- **Redis**: Redis server with authentication
- **HTTP**: HTTP server with token-based auth
- **Memcached**: Multiple server support
- **GCS**: Google Cloud Storage with service account auth

## Design Patterns

### 1. Factory Pattern
Used extensively for creating instances based on type:
- Compiler configuration factory (Clang/GCC/MSVC)
- Standard library factory (libc++/libstdc++/MSVC)
- Package manager detector registry

### 2. Strategy Pattern
Different strategies for same operation:
- Build backend selection (Ninja/Make/MSBuild/Xcode)
- Toolchain detection (PATH search, registry, package managers)
- Hash algorithms (SHA256, SHA512, MD5)

### 3. Registry Pattern
Central registries for managing resources:
- Toolchain metadata registry
- Shared cache registry with reference counting
- Package manager detector registry

### 4. Coordinator Pattern
Download coordinator prevents duplicate downloads using wait-and-notify pattern.

### 5. Template Method Pattern
Abstract base classes with template methods:
- `PackageManager` base class with abstract methods
- Verification levels with different validation steps

## Extensibility Points

ToolchainKit is designed to be extensible at multiple levels:

### 1. Adding New Toolchains

**Metadata Registry** (`toolchainkit/data/toolchains.json`):
```json
{
  "toolchains": {
    "my-custom-toolchain": {
      "18.0.0": {
        "linux-x64": {
          "url": "https://example.com/my-toolchain-18.0.0-linux-x64.tar.gz",
          "sha256": "abc123...",
          "size_mb": 2048,
          "stdlib": ["mylib++"],
          "requires_installer": false
        }
      }
    }
  }
}
```

### 2. Adding New Package Managers

**Inherit from `PackageManager`**:
```python
from toolchainkit.packages.base import PackageManager

class MyPackageManager(PackageManager):
    def detect(self) -> bool:
        # Check for manifest file
        return (self.project_root / 'mypm.json').exists()

    def install_dependencies(self):
        # Run package manager install command
        pass

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        # Generate CMake integration file
        pass

    def get_name(self) -> str:
        return 'mypm'
```

### 3. Adding New Build Backends

**Inherit from `BuildBackend`** (in `toolchainkit.cmake.backends`):
```python
class MyBackend(BuildBackend):
    def detect(self) -> bool:
        # Check if backend is available
        pass

    def get_cmake_generator(self) -> str:
        return "My Generator"

    def get_configure_args(self) -> List[str]:
        # Return CMake configure arguments
        pass

    def get_build_args(self) -> List[str]:
        # Return CMake build arguments
        pass
```

### 4. Adding New Cross-Compilation Targets

**Add to `toolchainkit.cross.targets`**:
```python
from toolchainkit.cross.targets import CrossCompileTarget

class MyEmbeddedTarget(CrossCompileTarget):
    def get_cmake_system_name(self) -> str:
        return "MyEmbeddedOS"

    def get_toolchain_variables(self) -> Dict[str, str]:
        return {
            "CMAKE_SYSTEM_NAME": "MyEmbeddedOS",
            "CMAKE_SYSTEM_PROCESSOR": "myarch",
            "CMAKE_SYSROOT": "/path/to/sysroot"
        }
```

### 5. Adding New Remote Cache Backends

**Add to `toolchainkit.caching.remote`**:
```python
from toolchainkit.caching.remote import RemoteCacheBackend

class MyCustomCacheBackend(RemoteCacheBackend):
    def get_environment_variables(self) -> Dict[str, str]:
        return {
            "SCCACHE_MY_BACKEND_ENDPOINT": self.endpoint,
            "SCCACHE_MY_BACKEND_TOKEN": self.credentials.get("token")
        }
```

## Testing Strategy

ToolchainKit has a comprehensive testing strategy with **2385 passing tests**:

### Test Organization

```
tests/
├── core/                # Core module tests (directory, filesystem, etc.)
├── toolchain/           # Toolchain management tests
├── cmake/               # CMake integration tests
├── packages/            # Package manager tests
├── caching/             # Build caching tests
├── cross/               # Cross-compilation tests
├── config/              # Configuration parsing tests
├── integration/         # Integration tests
├── e2e/                 # End-to-end tests
├── mocks/               # Test mocks and fixtures
└── utils/               # Test utilities
```

### Test Types

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test interaction between multiple components
3. **End-to-End (E2E) Tests**: Test complete workflows from start to finish
4. **Smoke Tests**: Fast sanity checks to catch obvious breakage

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/core/test_directory.py -v

# Run with coverage
python -m pytest tests/ --cov=toolchainkit --cov-report=html

# Run smoke tests only
python -m pytest tests/e2e/test_smoke.py -v

# Run E2E tests
python -m pytest tests/e2e/ -v -m e2e
```

## Key Abstractions

### 1. Path Handling
All paths are `pathlib.Path` objects for cross-platform compatibility.

### 2. Atomic Operations
File writes use atomic operations to prevent corruption on crashes.

### 3. Idempotent Operations
Operations can be called multiple times safely (e.g., directory creation).

### 4. Graceful Degradation
Optional features fail gracefully (e.g., build caching unavailable).

### 5. Progress Reporting
Long-running operations provide progress callbacks for user feedback.

### 6. Concurrent Safety
File locking and coordination prevent race conditions in multi-process scenarios.

## Dependencies

### Required
- `requests` >= 2.31.0 - HTTP downloads
- `filelock` >= 3.12.0 - File-based locking

### Development
- `pytest` >= 7.0.0 - Testing framework
- `pytest-cov` >= 4.0.0 - Code coverage
- `pytest-mock` >= 3.11.0 - Mocking
- `responses` >= 0.23.0 - HTTP mocking

### Embedded
- **Python 3.11.7**: Downloaded and managed by ToolchainKit itself

## References

- [README.md](../../README.md) - User-facing documentation
- [VISION.md](../VISION.md) - Complete specification and future vision
- [pyproject.toml](file:///d:/workplace/cpp/toolchainkit/pyproject.toml) - Project configuration
