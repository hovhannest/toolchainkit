# Building Blocks and Components

This document provides detailed information about the building blocks that make up ToolchainKit, how they interact, and how to use them in development.

## Module Organization

ToolchainKit is organized into distinct modules with clear responsibilities:

```
toolchainkit/
├── core/          # Foundation services (cross-platform primitives)
├── toolchain/     # Toolchain management (download, verify, cleanup)
├── cmake/         # CMake integration (#generation, compilers, backends)
├── packages/      # Package manager integration (Conan, vcpkg)
├── caching/       # Build caching (sccache, ccache, remote backends)
├── cross/         # Cross-compilation targets (Android, iOS, embedded)
├── config/        # Configuration parsing and validation
├── cli/           # Command-line interface
├── ci/            # CI/CD helpers
├── ide/           # IDE integrations
├── bootstrap/     # Bootstrap scripts
└── data/          # Embedded data files (toolchain metadata)
```

## Core Modules (Foundation)

### Directory Management

**Module**: `toolchainkit.core.directory`

**Responsibilities**:
- Determine platform-specific global cache location
- Create and manage global cache directory structure
- Create and manage project-local `.toolchainkit/` directory
- Update `.gitignore` to exclude local state

**Key Classes/Functions**:

```python
from toolchainkit.core.directory import (
    create_directory_structure,
    get_global_cache_dir,
    get_project_local_dir,
    ensure_global_cache_structure,
    ensure_project_structure,
)

# Get global cache directory (platform-aware)
cache_dir = get_global_cache_dir()
# Linux/macOS: ~/.toolchainkit/
# Windows: %USERPROFILE%\.toolchainkit\

# Create complete directory structure
paths = create_directory_structure(project_root=Path('/my/project'))
# Returns dict with 'global_cache', 'project_local', and subdirectories
```

**Usage Pattern**:
1. Call once at initialization to ensure directories exist
2. Operations are idempotent - safe to call multiple times
3. Automatically creates `.gitignore` entries

---

### Python Environment

**Module**: `toolchainkit.core.python_env`

**Responsibilities**:
- Download platform-specific Python 3.11.7 if not present
- Extract and verify embedded Python installation
- Provide path to embedded Python executable

**Key Functions**:

```python
from toolchainkit.core.python_env import (
    setup_python_environment,
    get_python_executable,
)

# Setup embedded Python (downloads if needed)
python_exe = setup_python_environment()
# Returns: Path to python.exe / python3

# Get Python executable (assumes already setup)
python_exe = get_python_executable()
```

**Platform Support**:
- Windows: x64
- Linux: x64, ARM64
- macOS: x64, ARM64 (M1/M2)

**Usage Pattern**:
1. Call `setup_python_environment()` during bootstrap
2. Use returned executable for running package managers (Conan, etc.)
3. Ensures consistent Python version across all machines

---

### Filesystem Utilities

**Module**: `toolchainkit.core.filesystem`

**Responsibilities**:
- Cross-platform symbolic links and junctions
- Secure archive extraction
- Atomic file writes
- File hashing
- Safe file operations

**Key Functions**:

```python
from toolchainkit.core.filesystem import (
    create_link,
    extract_archive,
    atomic_write,
    compute_file_hash,
    safe_delete,
    find_executable,
)

# Create symlink (Linux/macOS) or junction (Windows)
create_link(target=Path('/global/toolchains/llvm-18'),
            link_path=Path('/project/.toolchainkit/toolchains'))

# Extract archive securely (prevents directory traversal)
extract_archive(archive_path=Path('llvm-18.tar.gz'),
                dest_dir=Path('/global/toolchains'))

# Atomic write (crash-safe)
atomic_write(path=Path('state.json'), content='{"active": "llvm-18"}')

# Compute file hash
hash_value = compute_file_hash(path=Path('llvm-18.tar.gz'), algorithm='sha256')

# Find executable in PATH
ninja_path = find_executable('ninja')
```

**Security Features**:
- **Directory Traversal Prevention**: Archive extraction validates all paths
- **Path Validation**: Rejects paths with `..` components
- **Long Path Support**: Windows long path (>260 chars) support
- **Atomic Writes**: Uses temp file + rename for crash safety

---

### Download Manager

**Module**: `toolchainkit.core.download`

**Responsibilities**:
- HTTP/HTTPS downloads with TLS verification
- Resumable downloads using HTTP Range headers
- Real-time progress tracking
- Streaming checksum verification
- Automatic retry with exponential backoff

**Key Classes/Functions**:

```python
from toolchainkit.core.download import download_file, DownloadProgress

def progress_callback(progress: DownloadProgress):
    print(f"{progress.percentage:.1f}% - {progress.speed_bps/1024/1024:.1f} MB/s")

download_file(
    url='https://github.com/llvm/llvm-project/releases/download/...',
    dest_path=Path('/cache/downloads/llvm-18.tar.gz'),
    expected_sha256='abc123...',
    progress_callback=progress_callback
)
```

**Features**:
- **Resumable**: Uses HTTP Range headers to resume interrupted downloads
- **Memory Efficient**: Streaming - constant memory for any file size
- **Verified**: Streaming checksum verification during download
- **Retry Logic**: Automatic retry with exponential backoff (3 attempts)

---

### Hash Verification

**Module**: `toolchainkit.core.verification`

**Responsibilities**:
- File integrity verification
- Multiple hash algorithms (SHA256, SHA512, MD5, SHA1)
- GNU coreutils hash file format support
- Optional GPG signature verification

**Key Classes/Functions**:

```python
from toolchainkit.core.verification import (
    compute_hash,
    verify_hash,
    verify_hash_file,
    HashVerifier,
)

# Compute hash
hash_value = compute_hash(file_path=Path('llvm-18.tar.gz'), algorithm='sha256')

# Verify hash
is_valid = verify_hash(file_path=Path('llvm-18.tar.gz'),
                       expected_hash='abc123...',
                       algorithm='sha256')

# Verify using hash file (SHA256SUMS format)
results = verify_hash_file(hash_file_path=Path('SHA256SUMS'))

# High-level API
verifier = HashVerifier()
verifier.verify(file_path=Path('llvm-18.tar.gz'), expected_hash='sha256:abc123...')
```

**Security**:
- **Constant-Time Comparison**: Prevents timing attacks
- **Streaming Computation**: Efficient for large files
- **Path Traversal Prevention**: Validates all file paths

---

### Shared Cache Registry

**Module**: `toolchainkit.core.registry`

**Responsibilities**:
- Track toolchain installations across multiple projects
- Reference counting to prevent premature deletion
- Thread-safe and process-safe registry access
- Cache statistics and cleanup analysis

**Key Classes/Functions**:

```python
from toolchainkit.core.registry import CacheRegistry

registry = CacheRegistry()

# Register toolchain
registry.register_toolchain(
    toolchain_id='llvm-18.1.8-linux-x64',
    path=Path('/home/user/.toolchainkit/toolchains/llvm-18.1.8-linux-x64'),
    project_root=Path('/home/user/my-project')
)

# Increment reference
registry.increment_reference('llvm-18.1.8-linux-x64', Path('/home/user/another-project'))

# Get toolchain info
info = registry.get_toolchain_info('llvm-18.1.8-linux-x64')
# Returns: ToolchainInfo(path=..., size_mb=..., projects=[...], last_used=...)

# List unused toolchains
unused = registry.list_unused_toolchains(min_age_days=30)
```

**Concurrency**:
- **File Locking**: Uses `filelock` for cross-process safety
- **Thread-Safe**: Locks protect concurrent access
- **Atomic Writes**: Registry updates are atomic

---

### Concurrent Access Control

**Module**: `toolchainkit.core.locking`

**Responsibilities**:
- Cross-platform file-based locking
- Prevent race conditions in multi-process scenarios
- Download coordination to prevent duplicate downloads

**Key Classes**:

```python
from toolchainkit.core.locking import LockManager, DownloadCoordinator

lock_manager = LockManager()

# Registry lock (protects global registry)
with lock_manager.registry_lock():
    # Modify global registry
    pass

# Toolchain lock (prevents duplicate downloads)
with lock_manager.toolchain_lock('llvm-18.1.8-linux-x64'):
    # Download and install toolchain
    pass

# Project lock (protects project-local state)
with lock_manager.project_lock(Path('/my/project')):
    # Modify project state
    pass

# Download coordination (wait-and-notify pattern)
coordinator = DownloadCoordinator(lock_manager)
with coordinator.coordinate_download('llvm-18.1.8-linux-x64', dest_dir) as should_download:
    if should_download:
        # I'm the first process, download toolchain
        download_toolchain()
    else:
        # Another process is downloading, just wait
        pass
```

**Lock Types**:
- **Registry Lock**: Global lock for registry modifications
- **Toolchain Lock**: Per-toolchain lock for downloads/installations
- **Project Lock**: Per-project lock for state modifications

**Features**:
- **Timeout Support**: Configurable timeout to prevent hangs
- **Stale Lock Detection**: Automatic cleanup of stale locks
- **Try-Lock**: Non-blocking lock acquisition

---

### Platform Detection

**Module**: `toolchainkit.core.platform`

**Responsibilities**:
- Detect operating system, architecture, and ABI
- Provide standard platform strings for toolchain selection
- Performance-optimized with LRU caching

**Key Classes/Functions**:

```python
from toolchainkit.core.platform import detect_platform, PlatformInfo

platform = detect_platform()

print(platform.os)           # 'linux', 'windows', 'macos', 'android', 'ios'
print(platform.architecture) # 'x64', 'arm64', 'x86', 'arm', 'riscv64'
print(platform.abi)          # 'glibc', 'musl', 'msvc', None

# Standard platform string for toolchain selection
print(platform.platform_string())  # e.g., 'linux-x64-glibc'

# Check platform support
if platform.is_supported():
    print("Platform is supported")
```

**Platform String Examples**:
- Linux x64: `linux-x64-glibc` or `linux-x64-musl`
- Windows x64: `windows-x64-msvc`
- macOS ARM64: `macos-arm64`
- Android ARM64: `android-arm64`

---

### State Management

**Module**: `toolchainkit.core.state`

**Responsibilities**:
- Track project state (active toolchain, configuration)
- Detect configuration changes for automatic reconfiguration
- Atomic state updates for crash safety

**Key Classes/Functions**:

```python
from toolchainkit.core.state import ProjectState, load_state, save_state

# Load current state
state = load_state(project_root=Path('/my/project'))

# Access state
print(state.active_toolchain)    # 'llvm-18.1.8-linux-x64'
print(state.cmake_configured)    # True/False

# Modify state
state.active_toolchain = 'gcc-13.2.0-linux-x64'
state.cmake_configured = False

# Save state (atomic write)
save_state(project_root=Path('/my/project'), state=state)
```

**State Tracks**:
- Active toolchain and configuration hash
- CMake configuration status
- Package manager (Conan, vcpkg)
- Build caching (enabled, tool, hit rate)
- Timestamps (bootstrap, configuration)

---

### Configuration Parsing

**Module**: `toolchainkit.config.parser`

**Responsibilities**:
- Parse `toolchainkit.yaml` configuration files
- Validate configuration with clear error messages
- Provide strongly-typed configuration objects

**Key Classes/Functions**:

```python
from toolchainkit.config.parser import parse_config, Config

# Parse configuration file
config = parse_config(config_path=Path('/my/project/toolchainkit.yaml'))

# Access configuration
print(config.project)                # Project name
print(config.toolchains)             # List[ToolchainConfig]
print(config.defaults)               # Default toolchains by platform
print(config.build.caching.enabled)  # Build caching enabled?
```

**Configuration Structure**:
- `Config` - Top-level configuration
- `ToolchainConfig` - Toolchain definition
- `BuildConfig` - Build settings
- `CachingConfig` - Caching settings
- `PackagesConfig` - Package manager settings

## Toolchain Management

### Toolchain Registry

**Module**: `toolchainkit.toolchain.registry`

**Responsibilities**:
- Maintain database of available toolchains
- Resolve version patterns to specific versions
- Lookup download URLs and metadata

**Key Classes/Functions**:

```python
from toolchainkit.toolchain.registry import ToolchainRegistry

registry = ToolchainRegistry()

# Lookup toolchain
metadata = registry.lookup(
    toolchain_name='llvm',
    version='18',           # Can be: '18', '18.1', '18.1.8', 'latest'
    platform='linux-x64'
)

print(metadata.url)      # Download URL
print(metadata.sha256)   # SHA-256 checksum
print(metadata.size_mb)  # Size in MB
print(metadata.stdlib)   # Supported standard libraries

# Resolve version
resolved = registry.resolve_version('llvm', '18')  # Returns '18.1.8'

# List versions
versions = registry.list_versions('llvm')  # ['18.1.8', '17.0.6', ...]

# List toolchains
toolchains = registry.list_toolchains()    # ['llvm', 'gcc']
```

**Version Resolution**:
- `latest` → newest version
- `18` → newest `18.x.x`
- `18.1` → newest `18.1.x`
- `18.1.8` → exact version

---

### Toolchain Downloader

**Module**: `toolchainkit.toolchain.downloader`

**Responsibilities**:
- Orchestrate toolchain download, extraction, verification
- Coordinate downloads across multiple processes
- Manage cache and registry

**Key Classes**:

```python
from toolchainkit.toolchain.downloader import ToolchainDownloader

downloader = ToolchainDownloader()

def progress_callback(phase: str, progress: float):
    print(f"{phase}: {progress * 100:.1f}%")

# Download and install toolchain
toolchain_path = downloader.download(
    toolchain_name='llvm',
    version='18.1.8',
    platform='linux-x64',
    progress_callback=progress_callback
)

# Returns: Path to installed toolchain
```

**Download Process**:
1. Check if toolchain exists in cache (fast path)
2. Acquire toolchain lock
3. Download archive with progress reporting (0-50%)
4. Verify checksum
5. Extract archive with progress reporting (50-100%)
6. Register in cache registry
7. Return toolchain path

---

### Toolchain Verifier

**Module**: `toolchainkit.toolchain.verifier`

**Responsibilities**:
- Verify toolchain integrity and functionality
- Multi-level verification from quick to thorough

**Key Classes/Functions**:

```python
from toolchainkit.toolchain.verifier import ToolchainVerifier, VerificationLevel

verifier = ToolchainVerifier()

# Verify toolchain (default: STANDARD level)
result = verifier.verify(
    toolchain_path=Path('/cache/toolchains/llvm-18.1.8-linux-x64'),
    toolchain_type='clang',
    expected_version='18.1.8',
    level=VerificationLevel.STANDARD
)

if result.passed:
    print("Toolchain verified!")
else:
    print(f"Verification failed: {result.errors}")
```

**Verification Levels**:
- `MINIMAL` (~1s): File presence checks
- `STANDARD` (~5s): Executability tests, version validation
- `THOROUGH` (~10s): ABI compatibility, symlink integrity
- `PARANOID` (~30s): Compile and run a test program

---

### System Toolchain Detector

**Module**: `toolchainkit.toolchain.system_detector`

**Responsibilities**:
- Detect compilers already installed on the system
- Extract version and target information
- Provide "best toolchain" recommendation

**Key Classes/Functions**:

```python
from toolchainkit.toolchain.system_detector import SystemToolchainDetector

detector = SystemToolchainDetector()

# Detect all toolchains
toolchains = detector.detect_all()

for tc in toolchains:
    print(f"{tc.type} {tc.version} at {tc.compiler_path}")

# Get best toolchain (prefers LLVM > GCC > MSVC, newest version)
best = detector.get_best_toolchain()
```

**Detection Strategies**:
- **PATH Search**: Find compilers in PATH
- **Standard Locations**: Check `/usr/bin`, `C:\Program Files`, etc.
- **Registry**: Windows registry for MSVC
- **Package Managers**: Query apt, brew, etc.

---

### Linking Manager

**Module**: `toolchainkit.toolchain.linking`

**Responsibilities**:
- Create cross-platform filesystem links
- Manage symlinks (Unix) and junctions (Windows)

**Key Functions**:

```python
from toolchainkit.toolchain.linking import (
    create_link,
    resolve_link,
    is_link,
    remove_link,
    find_broken_links,
)

# Create link (symlink on Unix, junction on Windows)
create_link(
    target=Path('/global/toolchains/llvm-18.1.8-linux-x64'),
    link_path=Path('/project/.toolchainkit/toolchains/llvm')
)

# Resolve link target
target = resolve_link(Path('/project/.toolchainkit/toolchains/llvm'))

# Check if path is a link
if is_link(Path('/project/.toolchainkit/toolchains/llvm')):
    print("It's a link")

# Find broken links in directory
broken = find_broken_links(Path('/project/.toolchainkit'))
```

---

### Toolchain Cleanup

**Module**: `toolchainkit.toolchain.cleanup`

**Responsibilities**:
- Remove unused toolchains from shared cache
- Reference counting-based cleanup
- Age-based and space-based cleanup

**Key Classes**:

```python
from toolchainkit.toolchain.cleanup import ToolchainCleaner

cleaner = ToolchainCleaner()

# Cleanup unused toolchains older than 30 days
removed = cleaner.cleanup_by_age(min_age_days=30, dry_run=False)

# Cleanup until free space threshold met
removed = cleaner.cleanup_by_space(min_free_gb=10, dry_run=False)

# Get cache statistics
stats = cleaner.get_cache_stats()
print(f"Total size: {stats.total_size_mb} MB")
print(f"Unused size: {stats.unused_size_mb} MB")
print(f"Free space: {stats.free_space_mb} MB")
```

**Safety**:
- **Never removes referenced toolchains**
- **Dry-run mode** for preview
- **Detailed reporting** of what will be removed

## CMake Integration

### CMake Toolchain Generator

**Module**: `toolchainkit.cmake.toolchain_generator`

**Responsibilities**:
- Generate CMake toolchain files
- Configure compilers, flags, linkers
- Integrate caching, package managers, cross-compilation

**Key Classes**:

```python
from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
)

generator = CMakeToolchainGenerator(project_root=Path('/my/project'))

config = ToolchainFileConfig(
    toolchain_id='llvm-18.1.8-linux-x64',
    toolchain_root=Path('/cache/toolchains/llvm-18.1.8-linux-x64'),
    compiler_type='clang',
    c_compiler=Path('/.../bin/clang'),
    cxx_compiler=Path('/.../bin/clang++'),
    stdlib='libc++',
    linker='lld',
    caching_enabled=True,
    cache_tool='sccache',
)

# Generate toolchain file
toolchain_file = generator.generate(config)
# Returns: Path to generated .toolchainkit/cmake/toolchain-llvm-18.cmake
```

---

### Compiler Configuration

**Module**: `toolchainkit.cmake.compilers`

**Responsibilities**:
- Compiler-specific configuration for Clang, GCC, MSVC
- Automatic flag generation based on build type

**Key Classes**:

```python
from toolchainkit.cmake.compilers import ClangConfig, GccConfig, MsvcConfig

# Clang configuration
clang = ClangConfig(
    compiler_path=Path('/.../bin/clang++'),
    version='18.1.8',
    stdlib='libc++',
    linker='lld',
    sanitizers=['address', 'undefined'],
)

# Get CMake snippet
snippet = clang.get_cmake_snippet()
# Returns CMake code to configure Clang

# Get compiler flags for build type
flags = clang.get_flags_for_build_type('Release')
# Returns: ['-O3', '-DNDEBUG', '-stdlib=libc++', '-fuse-ld=lld']
```

---

### Standard Library Configuration

**Module**: `toolchainkit.cmake.stdlib`

**Responsibilities**:
- Independent standard library configuration
- Support for libc++, libstdc++, MSVC stdlib

**Key Classes**:

```python
from toolchainkit.cmake.stdlib import LibcxxConfig, LibstdcxxConfig

# libc++ configuration
libcxx = LibcxxConfig(installation_path=Path('/.../lib/libc++'))

# Get compile flags
compile_flags = libcxx.get_compile_flags()  # ['-stdlib=libc++']

# Get link flags
link_flags = libcxx.get_link_flags()        # ['-lc++', '-lc++abi']

# Get CMake snippet
snippet = libcxx.get_cmake_snippet()
```

---

### CMake Build Backends

**Module**: `toolchainkit.cmake.backends`

**Responsibilities**:
- Detect and configure CMake build backends
- Support for Ninja, Make, MSBuild, Xcode, NMake

**Key Classes**:

```python
from toolchainkit.cmake.backends import BackendDetector, NinjaBackend

detector = BackendDetector()

# Detect available backends
available = detector.detect_available_backends()

# Get best backend (Ninja > Platform Native > Make)
best = detector.get_best_backend()

# Use specific backend
ninja = NinjaBackend()
if ninja.detect():
    cmake_args = ninja.get_configure_args()  # ['-G', 'Ninja']
    build_args = ninja.get_build_args()      # ['-j', '8']
```

## Package Management

### Package Manager Base

**Module**: `toolchainkit.packages.base`

**Extensibility Point**: Inherit from `PackageManager` to add new package managers.

```python
from toolchainkit.packages.base import PackageManager

class MyPackageManager(PackageManager):
    def detect(self) -> bool:
        """Detect if this package manager is used in the project."""
        return (self.project_root / 'mypm.json').exists()

    def install_dependencies(self):
        """Install project dependencies."""
        # Run package manager install command
        pass

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """Generate CMake integration file."""
        # Create CMake file that includes package manager toolchain
        pass

    def get_name(self) -> str:
        return 'mypm'
```

---

### Conan Integration

**Module**: `toolchainkit.packages.conan`

**Usage**:

```python
from toolchainkit.packages.conan import ConanPackageManager

conan = ConanPackageManager(project_root=Path('/my/project'))

# Detect if Conan is used
if conan.detect():
    # Install dependencies
    conan.install_dependencies()

    # Generate CMake integration
    integration_file = conan.generate_toolchain_integration(
        toolchain_file=Path('/.toolchainkit/cmake/toolchain-llvm-18.cmake')
    )
```

---

### vcpkg Integration

**Module**: `toolchainkit.packages.vcpkg`

**Usage**:

```python
from toolchainkit.packages.vcpkg import VcpkgPackageManager

vcpkg = VcpkgPackageManager(project_root=Path('/my/project'))

# Detect if vcpkg is used
if vcpkg.detect():
    # Install dependencies
    vcpkg.install_dependencies()

    # Generate CMake integration (toolchain chaining)
    integration_file = vcpkg.generate_toolchain_integration(
        toolchain_file=Path('/.toolchainkit/cmake/toolchain-llvm-18.cmake')
    )
```

## Build Caching

### Cache Detection

**Module**: `toolchainkit.caching.detection`

```python
from toolchainkit.caching.detection import CacheDetector

detector = CacheDetector()

# Detect sccache or ccache
cache_tool = detector.detect()  # Returns 'sccache', 'ccache', or None

if cache_tool is None:
    # Download and install sccache
    cache_path = detector.install_sccache()
```

---

### Compiler Launcher Configuration

**Module**: `toolchainkit.caching.launcher`

```python
from toolchainkit.caching.launcher import CachingLauncher

launcher = CachingLauncher(cache_tool='sccache', cache_dir=Path('/.cache/sccache'))

# Get CMake variables
cmake_vars = launcher.get_cmake_variables()
# Returns: {'CMAKE_C_COMPILER_LAUNCHER': 'sccache', 'CMAKE_CXX_COMPILER_LAUNCHER': 'sccache'}

# Get environment variables
env_vars = launcher.get_environment_variables()
# Returns: {'SCCACHE_DIR': '...', 'SCCACHE_CACHE_SIZE': '10G'}

# Get cache statistics
stats = launcher.get_stats()
print(f"Cache hit rate: {stats.hit_rate}%")
```

---

### Remote Cache Backends

**Module**: `toolchainkit.caching.remote`

```python
from toolchainkit.caching.remote import S3Backend, RedisBackend

# S3 backend
s3 = S3Backend(
    endpoint='s3://my-company-cache/sccache',
    credentials={'aws_access_key_id': '...', 'aws_secret_access_key': '...'}
)

env_vars = s3.get_environment_variables()
# Returns: {'SCCACHE_S3_BUCKET': 'my-company-cache', ...}

# Redis backend
redis = RedisBackend(
    endpoint='redis://cache.example.com:6379/1',
    credentials={'password': '...'}
)

env_vars = redis.get_environment_variables()
# Returns: {'SCCACHE_REDIS': 'redis://...', ...}
```

## Module Dependencies

Understanding module dependencies is crucial for maintenance:

```
CLI (cli/)
  ↓
Orchestration (config/, state)
  ↓
Components (toolchain/, cmake/, packages/, caching/)
  ↓
Foundation (core/)
```

**Dependency Rules**:
1. **Foundation modules** have no dependencies on other ToolchainKit modules
2. **Component modules** depend only on foundation modules
3. **Orchestration modules** depend on component and foundation modules
4. **CLI modules** depend on all layers

## Error Handling

All modules follow a consistent error handling pattern:

```python
# Module-specific exceptions
class ModuleError(Exception):
    """Base exception for module errors."""
    pass

class SpecificError(ModuleError):
    """Specific error condition."""
    pass

# Usage
try:
    result = some_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

**Exception Hierarchy**:
- `DirectoryError` → `PermissionError`, `DirectoryCreationError`
- `ToolchainRegistryError` → `ToolchainNotFoundError`, `InvalidVersionError`
- `PackageManagerError` → `PackageManagerNotFoundError`, `PackageManagerInstallError`

## Logging

All modules use Python's standard `logging` module:

```python
import logging

logger = logging.getLogger(__name__)

# Usage
logger.debug("Detailed debug information")
logger.info("Informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
```

**Log Levels** (recommended usage):
- `DEBUG`: Detailed debugging (function entry/exit, variable values)
- `INFO`: Progress updates (downloading, extracting, configuring)
- `WARNING`: Non-fatal issues (fallback to default, optional feature unavailable)
- `ERROR`: Fatal errors (file not found, invalid configuration)

## Testing Modules

When developing or modifying modules:

1. **Write unit tests** in `tests/<module>/test_<file>.py`
2. **Use mocks** for external dependencies (network, filesystem)
3. **Test error conditions** (invalid input, missing files, network errors)
4. **Test cross-platform behavior** (Windows, Linux, macOS)

Example test structure:

```python
import pytest
from toolchainkit.core.directory import create_directory_structure

def test_create_directory_structure(tmp_path):
    """Test directory structure creation."""
    paths = create_directory_structure(project_root=tmp_path)

    assert paths['global_cache'].exists()
    assert paths['project_local'].exists()
    assert (tmp_path / '.toolchainkit').exists()

def test_create_directory_structure_idempotent(tmp_path):
    """Test that directory creation is idempotent."""
    paths1 = create_directory_structure(project_root=tmp_path)
    paths2 = create_directory_structure(project_root=tmp_path)

    assert paths1 == paths2
```

## Performance Considerations

### Caching
- **Platform detection**: LRU cached for instant subsequent calls
- **Toolchain metadata**: In-memory cache for fast lookups
- **File hashing**: Streaming computation for memory efficiency

### Concurrency
- **File locking**: Use locks only when necessary (registry modifications, downloads)
- **Download coordination**: Wait-and-notify pattern prevents duplicate downloads
- **Atomic operations**: Use atomic writes for crash safety without excessive locking

### Filesystem
- **Symlinks**: Preferred over copying for space efficiency
- **Streaming**: Use streaming for large files (downloads, hash computation)
- **Bulk operations**: Batch file operations where possible

## Summary

ToolchainKit's building blocks are designed to be:

1. **Modular**: Clear separation of concerns with well-defined interfaces
2. **Reusable**: Each module solves a specific problem and can be used independently
3. **Testable**: All modules have comprehensive unit and integration tests
4. **Extensible**: Abstract base classes and registries for easy extension
5. **Cross-Platform**: Platform-aware implementations for Windows, Linux, macOS
6. **Concurrent-Safe**: File locking and coordination for multi-process scenarios
7. **Performant**: Caching, streaming, and efficient algorithms

When adding new features or extending existing ones, follow these principles to maintain consistency and quality.
