# Changelog

All notable changes to ToolchainKit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha] - 2025-11-27

### Added

#### Core Infrastructure
- **Platform Detection** - Comprehensive platform, architecture, and ABI detection for Windows, Linux, macOS
  - OS detection (Windows, Linux, macOS, Android, iOS)
  - Architecture detection (x64, ARM64, x86, ARM, RISC-V)
  - ABI detection (glibc version, musl, MSVC, macOS deployment target)
  - Linux distribution detection (Ubuntu, Debian, CentOS, Arch, etc.)
  - Cached platform detection (<100ms)

- **Directory Management** - Cross-platform directory structure management
  - Global cache directory (`~/.toolchainkit/`)
  - Project-local directory (`<project>/.toolchainkit/`)
  - Automatic directory creation with proper permissions
  - `.gitignore` integration

- **Download Manager** - Resumable HTTP downloads with verification
  - HTTP Range support for resumable downloads
  - SHA256 verification during download (streaming)
  - Progress tracking with ETA
  - Automatic retry with exponential backoff
  - Timeout handling (configurable, default 300s)

- **Locking System** - Multi-process concurrency control
  - File-based locking for cross-process coordination
  - `LockManager` with timeout support
  - `DownloadCoordinator` to prevent duplicate downloads
  - Lock types: registry, toolchain, project

- **Cache Registry** - Shared toolchain registry with reference counting
  - Toolchain registration and metadata tracking
  - Project reference counting (multiple projects can share toolchains)
  - Automatic cleanup of unused toolchains
  - Cache statistics (size, hit rate)
  - JSON-based persistent storage

- **Verification System** - File integrity verification
  - SHA256, SHA512, MD5 hash computation
  - Streaming hash computation for large files
  - BSD/GNU hash file parsing
  - Constant-time comparison for security
  - GPG signature verification support

- **State Management** - Project configuration state tracking
  - Active toolchain tracking
  - CMake configuration status
  - Package manager integration status
  - Build caching configuration
  - Last bootstrap timestamp

#### Toolchain Management
- **Toolchain Downloader** - Download and extract toolchains
  - Metadata-driven downloads
  - Concurrent-safe downloads (via DownloadCoordinator)
  - Progress reporting (download + extraction)
  - Automatic verification (SHA256)
  - Cleanup on failure
  - Returns detailed metrics (time, size, cached status)

- **Metadata Registry** - Toolchain metadata management
  - YAML-based metadata format
  - Modular metadata structure
  - Version resolution (patterns like "18", "18.1", "18.1.8")
  - Platform-specific downloads
  - Toolchain listing and filtering

- **System Detector** - Detect system-installed compilers
  - PATH search
  - Standard installation location search
  - Windows registry search (MSVC, LLVM)
  - Package manager detection (apt, brew, chocolatey)
  - Version extraction from compiler output
  - Clang, GCC, MSVC detection

- **Verification** - Post-installation verification
  - File presence checks
  - Symlink verification
  - Executability checks
  - Version checks
  - ABI checks
  - Compile test checks
  - Multiple verification levels (QUICK, NORMAL, FULL, PARANOID)

- **Link Manager** - Symlink/junction management
  - Symlink creation (Unix)
  - Junction creation (Windows)
  - Hard link support
  - Copy fallback
  - Link verification
  - Cleanup

- **Cleanup Manager** - Remove unused toolchains
  - Reference counting before deletion
  - Age-based cleanup (older than N days)
  - Dry-run mode
  - Safety checks (prevent deletion of in-use toolchains)
  - Cleanup statistics

- **Upgrader** - Upgrade toolchains
  - Version comparison (semantic versioning)
  - Update checking
  - Upgrade strategies (PATCH, MINOR, MAJOR, LATEST)
  - Rollback support

#### CMake Integration
- **Toolchain Generator** - Generate CMake toolchain files
  - Compiler path configuration (C, C++, linker, archiver, ranlib)
  - Compiler flags (optimization, sanitizers, warnings)
  - Standard library selection (libc++, libstdc++, MSVC STL)
  - Linker selection (lld, gold, mold, bfd)
  - Build type configuration (Debug, Release, RelWithDebInfo, MinSizeRel)
  - Compiler launcher (sccache/ccache) integration
  - Cross-compilation settings
  - Package manager integration (Conan, vcpkg)

- **Compiler Configuration** - Compiler-specific settings
  - Clang configuration
  - GCC configuration
  - MSVC configuration
  - Feature detection

- **Standard Library Selection** - C++ stdlib configuration
  - libc++ (LLVM)
  - libstdc++ (GCC)
  - MSVC STL

- **Backend Selection** - CMake generator selection
  - Ninja
  - Unix Makefiles
  - MSBuild
  - Xcode
  - Auto-detection with fallbacks

#### Configuration System
- **YAML Parser** - Configuration file parsing
  - `toolchainkit.yaml` parsing
  - Schema validation
  - Error reporting with line numbers

- **Validation** - Configuration validation
  - Schema validation
  - Cross-field validation
  - Warning and error reporting
  - Suggestion generation

- **Layer System** - Composable configuration
  - BaseCompilerLayer (Clang, GCC, MSVC)
  - PlatformLayer (platform-specific settings)
  - StdLibLayer (C++ standard library)
  - BuildTypeLayer (Debug, Release, etc.)
  - OptimizationLayer (O0, O1, O2, O3, Os, Oz)
  - SanitizerLayer (AddressSanitizer, UBSan, TSan, MSan)
  - Layer composition and validation

- **Composer** - Layer composition engine
  - Layer ordering
  - Conflict detection
  - Requirement validation
  - Final configuration generation

#### Package Manager Integration
- **Conan Integration** - Conan 2.x support
  - Conan detection
  - Conan installation (download if not found)
  - Profile generation
  - Dependency installation
  - CMake integration
  - Project-local cache

- **vcpkg Integration** - vcpkg support
  - vcpkg detection
  - vcpkg installation (clone and bootstrap)
  - Manifest mode support
  - Dependency installation
  - CMake integration
  - Binary caching

- **Tool Downloader** - Download build tools
  - Conan downloader
  - vcpkg downloader
  - CMake downloader
  - Ninja downloader
  - sccache downloader
  - ccache downloader
  - Python downloader
  - Make downloader
  - Git downloader
  - clang-tidy/clang-format downloader
  - cppcheck downloader
  - SHA256 verification for all downloads
  - Platform-specific binaries

#### Build Caching
- **Cache Detection** - Detect sccache/ccache
  - sccache detection
  - ccache detection
  - Version detection
  - Statistics retrieval

- **Compiler Launcher** - CMake launcher configuration
  - CMAKE_C_COMPILER_LAUNCHER configuration
  - CMAKE_CXX_COMPILER_LAUNCHER configuration
  - Environment variable setup

- **Remote Backends** - Remote cache configuration
  - S3 backend
  - Redis backend
  - HTTP backend
  - GCS backend
  - Azure backend
  - Memcached backend
  - Environment variable configuration

#### Cross-Compilation
- **Target Definitions** - Cross-compile target support
  - Android targets
  - iOS targets
  - Raspberry Pi targets
  - Embedded targets (ARM, RISC-V)
  - CMake system name/processor configuration
  - Sysroot configuration

- **Sysroot Management** - Sysroot download and management
  - Sysroot download
  - Sysroot extraction
  - Sysroot verification
  - Sysroot caching

#### IDE Integration
- **VS Code Integration** - VS Code settings generation
  - `.vscode/settings.json` generation
  - `.vscode/c_cpp_properties.json` generation
  - IntelliSense configuration
  - Compiler path configuration
  - Include path configuration

- **CMake Presets** - CMakePresets.json generation
  - Configure presets
  - Build presets
  - Test presets
  - Multi-configuration support
  - IDE-agnostic

#### Plugin System
- **Plugin Base** - Plugin infrastructure
  - Abstract plugin base class
  - Plugin metadata system
  - Plugin lifecycle (initialize, shutdown)

- **Plugin Manager** - Plugin management
  - Plugin loading (dynamic import)
  - Plugin registration
  - Plugin discovery (auto-discovery)
  - Plugin context management

- **Plugin Types** - Plugin interfaces
  - Compiler plugins (custom compilers)
  - Package manager plugins (custom package managers)
  - Build backend plugins (custom build systems)

- **Plugin Loader** - Dynamic loading
  - Python module loading
  - Plugin validation
  - Dependency resolution

- **Plugin Registry** - Plugin catalog
  - Global plugin registry
  - Plugin lookup
  - Version tracking

- **Plugin Discovery** - Auto-discovery
  - Search paths configuration
  - Plugin scanning
  - Metadata parsing

#### Testing Infrastructure
- **Test Suite** - Comprehensive testing (2385 tests)
  - Unit tests (1800+)
  - Integration tests (400+)
  - End-to-end tests (100+)
  - Regression tests (85+)
  - Platform-specific tests
  - Link validation tests

- **Test Fixtures** - Shared test infrastructure
  - `temp_dir` fixture
  - `temp_workspace` fixture
  - `sample_config_yaml` fixture
  - `isolated_home` fixture
  - `no_network` fixture
  - `reset_caches` fixture

- **Mock Infrastructure** - Testing utilities
  - MockFilesystem
  - MockDownloader
  - Custom assertions
  - Test builders

- **Test Markers** - Test categorization
  - `@pytest.mark.unit`
  - `@pytest.mark.integration`
  - `@pytest.mark.e2e`
  - `@pytest.mark.regression`
  - `@pytest.mark.platform_*`
  - `@pytest.mark.requires_*`
  - `@pytest.mark.slow`

- **Coverage** - Code coverage tracking
  - pytest-cov integration
  - HTML coverage reports
  - >80% coverage target

#### Documentation
- **User Documentation** - Complete user guides
  - Platform detection guide
  - Directory structure guide
  - Download manager guide
  - Toolchain management guide
  - CMake integration guide
  - Package manager guide
  - Build caching guide
  - Cross-compilation guide
  - Configuration guide

- **Developer Documentation** - Developer resources
  - Architecture overview
  - Building blocks reference
  - Extension guide
  - Testing strategies
  - Maintenance guide

- **API Documentation** - API reference (in progress)
  - Module documentation
  - Class documentation
  - Function documentation
  - Code examples

### Known Limitations

- **CLI Commands** - Command structure exists but individual commands need completion
- **Bootstrap Scripts** - Generation logic partially implemented
- **Toolchain Metadata** - Limited toolchain entries (structure ready for expansion)
- **Python Environment** - Managed Python 3.11 code exists but not actively used
- **API Documentation** - Sphinx-based API docs not yet generated

### Notes

This is an **alpha release** (v0.1.0). The core library is feature-complete and well-tested (2385 passing tests), but CLI tools are still in development. The library is suitable for integration into build systems and CI/CD pipelines via the Python API.

For production use, integrate ToolchainKit via the Python API rather than CLI commands. See README.md and ANALYSIS_REPORT.md for detailed implementation status.

### Supported Platforms

- **Operating Systems**: Windows 10+, Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+, Arch), macOS 11+
- **Architectures**: x64 (x86_64), ARM64 (aarch64), x86 (i686), ARM (armv7l)
- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13

### Dependencies

#### Runtime Dependencies
- `requests >= 2.31.0` - HTTP downloads
- `filelock >= 3.12.0` - Concurrent access control

#### Development Dependencies
- `pytest >= 7.0.0` - Testing framework
- `pytest-cov >= 4.0.0` - Coverage reporting
- `pytest-mock >= 3.11.0` - Mocking utilities
- `responses >= 0.23.0` - HTTP mocking


[Unreleased]: https://github.com/hovhannest/toolchainkit/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/hovhannest/toolchainkit/releases/tag/v0.1.0-alpha
