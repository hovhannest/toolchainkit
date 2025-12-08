# ToolchainKit: Hermetic Cross-Platform C++ Build System

## Executive Summary

ToolchainKit is a toolchain management framework that brings hermetic, reproducible builds to any CMake-based C++ project. It works with both new and existing projects, requiring **zero modifications** to your CMakeLists.txt files. Download and switch between compilers, standard libraries, and build configurations with a single command.

**Key Principle**: ToolchainKit manages toolchains and generates CMake configuration, then developers use standard CMake workflows. Your existing CMake project works as-is.

## Design Goals

### Primary Objectives
- **Works with existing projects**: Drop into any CMake project without changes
- **Hermetic**: Self-contained, reproducible environments independent of system state
- **Zero dependencies**: One-liner bootstrap with no prerequisites
- **CMake-native**: Standard CMake workflow after initial setup
- **Flexible**: Support both preinstalled tools (VS, Xcode, WDK) and downloaded toolchains
- **Easy toolchain switching**: Change compilers, standard libraries, or configurations instantly
- **Shared resources**: Multiple projects share toolchain cache to save disk space

### Target Users
- Developers working on existing CMake projects who want better toolchain management
- Individual developers (simple, fast setup)
- Open source projects (minimal barriers to contribution)
- Teams (shared toolchain configurations)

### Supported Platforms

**Host platforms:**
- Windows 10+ (x64)
- Linux (x64, arm64)
- macOS 11+ (x64, arm64)

**Target platforms:**
- All host platforms plus: Android, iOS, Raspberry Pi
- Architectures: x86, x64, ARM, ARM64, RISC-V

## Quick Start with Existing Projects

### Add ToolchainKit to Your Project

```bash
# In your existing CMake project directory
cd /path/to/your/cmake/project

# Initialize ToolchainKit (detects your current setup)
tkgen init

# This creates:
# - toolchainkit.yaml (configuration)
# - bootstrap.sh / bootstrap.bat (setup script)
# - .toolchainkit/ directory (gitignored, local state)
```

Your existing `CMakeLists.txt` files remain **completely unchanged**.

### Switch Toolchains Effortlessly

```bash
# Use Clang 18 with libc++
tkgen configure --toolchain llvm-18 --stdlib libc++

# Or use GCC 13 with libstdc++
tkgen configure --toolchain gcc-13

# Or use MSVC 2022 (system installation)
tkgen configure --toolchain msvc-2022

# Build as usual
cmake --build build/
```

### That's It!

ToolchainKit works behind the scenes:
- Downloads and validates toolchains
- Generates appropriate CMake toolchain files
- Configures your build directory
- You continue using standard CMake commands

## Architecture

### Directory Structure

```
# Global shared cache
~/.toolchainkit/                        # Linux/macOS
%USERPROFILE%\.toolchainkit\            # Windows
├── toolchains/
│   ├── llvm-18.1.8-linux-x64/
│   ├── gcc-13.2.0-linux-x64/
│   └── msvc-17.8-windows-x64/
├── registry.json                       # Reference counting
└── lock/                               # Concurrent access control

# Your existing project (nothing changes!)
your-project/
├── .toolchainkit/                      # Gitignored (generated)
│   ├── toolchains -> ~/.toolchainkit/toolchains  # Symlink to shared cache
│   ├── packages/                       # Conan/vcpkg cache
│   └── state.json                      # Current configuration
├── toolchainkit.yaml                   # Project manifest (optional, commit this)
├── bootstrap.sh / bootstrap.bat        # Generated setup script
├── CMakeLists.txt                      # YOUR EXISTING FILE - UNCHANGED
├── src/                                # YOUR EXISTING CODE - UNCHANGED
├── include/                            # YOUR EXISTING CODE - UNCHANGED
└── cmake/
    └── toolchainkit/                   # CMake integration layer (generated)
        ├── toolchain-llvm-18.cmake
        ├── conan-integration.cmake
        └── vcpkg-integration.cmake
```

### Two-Phase Operation

**Phase 1: Bootstrap (framework active)**
```bash
# For new contributors to your project
git clone https://github.com/your/project.git
cd project
./bootstrap.sh                         # One-time setup
```

Actions:
1. Parse `toolchainkit.yaml`
2. Download/validate toolchains to shared cache
3. Generate CMake toolchain files
4. Configure package manager (if used)
5. Run initial `cmake -B build/`

**Phase 2: Development (standard CMake)**
```bash
cmake --build build/                   # Standard CMake
cmake --build build/ --target test
cmake --build build/ --target install
```

Framework only reactivates on:
- Toolchain changes (`tkgen reconfigure`)
- New project clone (run `bootstrap.sh` once)
- Dependency updates

## Configuration Format

### Project Manifest (toolchainkit.yaml)

This file is **optional** but recommended for team projects. If not present, ToolchainKit uses sensible defaults.

```yaml
version: 1
project: myapp

# Toolchain definitions
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
    stdlib: libc++              # or libstdc++, msvc
    source: prebuilt            # or build-from-source

  - name: gcc-13
    type: gcc
    version: 13.2.0
    stdlib: libstdc++

  - name: msvc-2022
    type: msvc
    version: 17.8
    require_installed: true     # Use system installation only

# Platform defaults
defaults:
  linux: llvm-18
  macos: llvm-18
  windows: msvc-2022

# Shared cache configuration
toolchain_cache:
  location: shared              # 'shared', 'local', or 'custom'
  path: ~/.toolchainkit         # Used if location=custom

# Package management (optional - works with existing package managers)
packages:
  manager: conan                # or vcpkg, cpm, or omit if using find_package
  conan:
    version: 2.0
    profile: auto               # or path to custom profile
  vcpkg:
    registry: https://...

# Build configuration
build:
  backend: ninja                # or make, msbuild, xcode
  parallel: auto                # or specific number

  # Build caching for faster rebuilds
  caching:
    enabled: true
    tool: sccache               # or ccache
    directory: ~/.cache/sccache # local cache directory
    remote:
      type: s3                  # or http, redis, gcs
      endpoint: s3://my-bucket/sccache
      # For HTTP: endpoint: https://cache.example.com
      # For Redis: endpoint: redis://localhost:6379

  # Distributed builds (optional)
  distributed: false
  remote:
    type: sccache               # or buildgrid, IncrediBuild
    endpoint: https://cache.example.com

# Cross-compilation targets (optional)
targets:
  - os: android
    arch: arm64
    toolchain: llvm-18-android
    api_level: 29

  - os: ios
    arch: arm64
    toolchain: llvm-18-ios

# Framework modules (only bundle what's needed)
modules:
  - core                        # Required
  - cmake                       # Required
  - packages-conan              # Optional
  - packages-vcpkg              # Optional
  - caching                     # Optional (sccache/ccache)
  - remote                      # Optional (distributed builds)
  - analysis                    # Optional (clang-tidy, cppcheck)
```

### Minimal Configuration for Existing Projects

For a quick start, you can use a minimal configuration:

```yaml
version: 1
project: your-existing-project

# Just specify which toolchains you want available
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

  - name: gcc-13
    type: gcc
    version: 13.2.0

defaults:
  linux: llvm-18
  macos: llvm-18
  windows: llvm-18
```

Or skip the YAML entirely and use command-line flags:

```bash
# No YAML needed - just specify toolchain on command line
tkgen configure --toolchain llvm-18
```

### State Tracking (.toolchainkit/state.json)

```json
{
  "active_toolchain": "llvm-18.1.8-linux-x64",
  "toolchain_hash": "sha256:abc123...",
  "cmake_configured": true,
  "last_bootstrap": "2025-11-11T10:30:00Z",
  "package_manager": "conan",
  "caching": {
    "enabled": true,
    "tool": "sccache",
    "hit_rate": "87.3%"
  },
  "modules": ["core", "cmake", "packages-conan", "caching"]
}
```

### Global Registry (~/.toolchainkit/registry.json)

```json
{
  "toolchains": {
    "llvm-18.1.8-linux-x64": {
      "path": "/home/user/.toolchainkit/toolchains/llvm-18.1.8-linux-x64",
      "size_mb": 2048,
      "projects": [
        "/home/user/project1",
        "/home/user/existing-cmake-project"
      ],
      "last_used": "2025-11-11T10:30:00Z",
      "hash": "sha256:abc123..."
    }
  },
  "total_size_mb": 5120,
  "cache_stats": {
    "sccache_hits": 15420,
    "sccache_misses": 2180,
    "cache_size_mb": 3840
  }
}
```

## Toolchain Management

### Supported Compilers

- **Clang/LLVM**: 14.x - 18.x (prebuilt or source)
- **GCC**: 11.x - 13.x (prebuilt or source)
- **MSVC**: 2019, 2022 (system installation)
- **Zig**: 0.11+ (uses Zig as C++ compiler)
- **Intel DPC++**: oneAPI toolkits
- **Apple Clang**: Xcode toolchains

### Standard Library Selection

ToolchainKit lets you switch standard libraries independently:

```bash
# Clang with libc++ (LLVM's stdlib)
tkgen configure --toolchain llvm-18 --stdlib libc++

# Clang with libstdc++ (GCC's stdlib)
tkgen configure --toolchain llvm-18 --stdlib libstdc++

# GCC always uses libstdc++
tkgen configure --toolchain gcc-13

# MSVC uses its own standard library
tkgen configure --toolchain msvc-2022
```

### Toolchain Resolution

Priority order:
1. Check shared cache (`~/.toolchainkit/toolchains/`)
2. Check system installations (MSVC, Xcode, WDK)
3. Download prebuilt from CDN
4. Build from source (fallback)

### Shared Cache Strategy

**Default: Shared mode**
- Global cache at `~/.toolchainkit/`
- Projects reference via symlinks (Unix) or junctions (Windows)
- Reference counting tracks usage
- Space savings: ~2GB per shared LLVM toolchain

**Alternative: Local mode**
```bash
./bootstrap.sh --local-toolchains
```
- Toolchains stored in `.toolchainkit/toolchains/`
- Full project isolation
- No shared dependencies

**Alternative: Custom location**
```yaml
toolchain_cache:
  location: custom
  path: /mnt/team-share/toolchains    # Network drive
```

### Platform-Specific Linking

**Linux/macOS:**
- Native symlinks

**Windows:**
1. Junction points (no admin required)
2. NTFS symlinks (if available)
3. Hardlinks for files
4. Copy-on-reference with registry tracking (fallback)

## Build Caching

ToolchainKit integrates compiler caches (sccache or ccache) to dramatically accelerate rebuilds by reusing previous compilation outputs.

### How It Works

Build caching wraps your compiler with a "launcher" that:
1. Computes a hash of the source file + compiler flags + headers
2. Checks if that hash exists in the cache
3. Returns cached object file (cache hit) or compiles normally (cache miss)

**Result**: Typical cache hit rates of 80-95% after the first build, reducing rebuild times from minutes to seconds.

### Supported Tools

**sccache (recommended)**
- Works with Clang, GCC, and MSVC
- Supports remote caching (S3, Redis, HTTP, GCS, Azure)
- Prebuilt binaries for all platforms
- Better Windows/MSVC support than ccache

**ccache**
- Works with Clang and GCC natively
- MSVC support (level-B, may require PATH configuration)
- Supports remote caching (HTTP, Redis, NFS)
- Widely used in open source

### Configuration

Enable caching in `toolchainkit.yaml`:

```yaml
build:
  caching:
    enabled: true
    tool: sccache              # or ccache

    # Local cache directory
    directory: ~/.cache/sccache

    # Optional: Remote cache for teams/CI
    remote:
      type: s3                 # AWS S3
      endpoint: s3://my-company-cache/sccache
      # Or use HTTP
      # type: http
      # endpoint: https://cache.example.com
      # Or use Redis
      # type: redis
      # endpoint: redis://cache.example.com:6379
```

Or enable via command line:

```bash
# Enable sccache with default settings
tkgen configure --toolchain llvm-18 --cache sccache

# Enable ccache
tkgen configure --toolchain gcc-13 --cache ccache

# Disable caching
tkgen configure --toolchain llvm-18 --no-cache
```

### How ToolchainKit Configures Caching

ToolchainKit automatically sets up caching by:

1. **Setting CMake launcher variables** in generated toolchain files:
   ```cmake
   # .toolchainkit/cmake/toolchain-llvm-18.cmake
   set(CMAKE_C_COMPILER_LAUNCHER sccache)
   set(CMAKE_CXX_COMPILER_LAUNCHER sccache)
   ```

2. **Configuring cache environment**:
   - sccache: Sets `SCCACHE_DIR`, `SCCACHE_CACHE_SIZE`, remote backend vars
   - ccache: Sets `CCACHE_DIR`, `CCACHE_MAXSIZE`, `CCACHE_REMOTE_STORAGE`

3. **No changes to your CMakeLists.txt** - it just works!

### Remote Caching for Teams

Share cache across machines for even faster builds:

**AWS S3:**
```yaml
build:
  caching:
    enabled: true
    tool: sccache
    remote:
      type: s3
      endpoint: s3://my-company-cache/sccache
      # AWS credentials via standard AWS SDK env vars
```

**HTTP server:**
```yaml
build:
  caching:
    enabled: true
    tool: sccache
    remote:
      type: http
      endpoint: https://cache.example.com
```

**Redis:**
```yaml
build:
  caching:
    enabled: true
    tool: sccache
    remote:
      type: redis
      endpoint: redis://cache.example.com:6379/1
```

**ccache with HTTP:**
```yaml
build:
  caching:
    enabled: true
    tool: ccache
    remote:
      type: http
      endpoint: https://ccache.example.com
```

### Cache Statistics

View cache performance:

```bash
# Show cache stats
tkgen cache stats

# Output:
# Cache: sccache
# Hits: 15,420 (87.6%)
# Misses: 2,180 (12.4%)
# Local cache size: 3.2 GB
# Remote cache: s3://my-company-cache/sccache

# Clear local cache
tkgen cache clear

# Prune old cache entries
tkgen cache prune --older-than 30d
```

### Platform Support

**Clang/GCC:**
- Both sccache and ccache work natively
- Full support on Linux, macOS, Windows (via MSYS2/MinGW)

**MSVC:**
- sccache: Full support, including debug info (PDB files)
- ccache: Level-B support (recent versions), may need compiler wrapper

**Recommendation**: Use sccache for cross-platform projects with MSVC support.

### Performance Tips

1. **Use remote caching in CI** - avoid cold cache on every CI run
2. **Set appropriate cache size** - default 10GB, adjust based on project size
3. **Enable in toolchainkit.yaml** - so all developers get caching automatically
4. **Monitor hit rates** - if below 70%, investigate dependencies/timestamps

## CMake Integration

### Generated Toolchain File

ToolchainKit generates CMake toolchain files that configure everything:

```cmake
# .toolchainkit/cmake/toolchain-llvm-18.cmake
set(TOOLCHAINKIT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../..")

# Compiler configuration
set(CMAKE_C_COMPILER "${TOOLCHAINKIT_ROOT}/toolchains/llvm-18.1.8-linux-x64/bin/clang")
set(CMAKE_CXX_COMPILER "${TOOLCHAINKIT_ROOT}/toolchains/llvm-18.1.8-linux-x64/bin/clang++")
set(CMAKE_CXX_FLAGS_INIT "-stdlib=libc++")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")

# Build caching (if enabled)
set(CMAKE_C_COMPILER_LAUNCHER sccache)
set(CMAKE_CXX_COMPILER_LAUNCHER sccache)

# Package manager integration (if configured)
include(${CMAKE_CURRENT_LIST_DIR}/conan-integration.cmake)

# Cross-compilation (if configured)
if(TOOLCHAINKIT_TARGET_OS)
  set(CMAKE_SYSTEM_NAME ${TOOLCHAINKIT_TARGET_OS})
  set(CMAKE_SYSTEM_PROCESSOR ${TOOLCHAINKIT_TARGET_ARCH})
endif()
```

### Your CMakeLists.txt (Unchanged!)

Your existing CMake project works as-is:

```cmake
cmake_minimum_required(VERSION 3.25)
project(your-existing-project CXX)

# Your existing dependencies work
find_package(Boost REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)

# Your existing targets work
add_executable(myapp
  src/main.cpp
  src/core.cpp
  src/network.cpp
)

target_link_libraries(myapp
  PRIVATE
    Boost::boost
    OpenSSL::SSL
    Threads::Threads
)

target_compile_features(myapp PRIVATE cxx_std_20)

# Your existing tests work
enable_testing()
add_subdirectory(tests)
```

**No changes required!** ToolchainKit works behind the scenes.

## Workflow

### Initial Setup (New Developer on Existing Project)

```bash
# Clone existing project
git clone https://github.com/org/existing-cmake-project.git
cd existing-cmake-project

# One-time bootstrap (downloads toolchains)
./bootstrap.sh

# Build (standard CMake)
cmake --build build/

# Test
cmake --build build/ --target test
```

### Daily Development

```bash
# Edit code in your favorite editor
vim src/main.cpp

# Build (standard CMake)
cmake --build build/

# Rebuild specific target
cmake --build build/ --target myapp

# Run tests
cmake --build build/ --target test

# Install
cmake --build build/ --target install
```

**Everything is standard CMake!** Your workflow doesn't change.

### Switching Toolchains

One of ToolchainKit's main benefits: switch compilers instantly.

```bash
# Try your project with different compilers
tkgen configure --toolchain llvm-18
cmake --build build/

# Switch to GCC
tkgen configure --toolchain gcc-13
cmake --build build/

# Try with different standard library
tkgen configure --toolchain llvm-18 --stdlib libstdc++
cmake --build build/

# Back to Clang with libc++
tkgen configure --toolchain llvm-18 --stdlib libc++
cmake --build build/
```

**Use case**: Test your code with multiple compilers to catch portability issues.

### Testing Multiple Configurations

```bash
# Configure multiple build types
tkgen configure --toolchain llvm-18 --build-type Debug --build-dir build-debug
tkgen configure --toolchain llvm-18 --build-type Release --build-dir build-release
tkgen configure --toolchain gcc-13 --build-type Debug --build-dir build-gcc-debug

# Build specific configuration
cmake --build build-debug/
cmake --build build-release/
cmake --build build-gcc-debug/
```

### Adding Dependencies

**If using Conan/vcpkg** (configured in toolchainkit.yaml):

```yaml
packages:
  manager: conan
  conan:
    dependencies:
      - boost/1.83.0
      - fmt/10.1.1
```

Then:
```bash
tkgen reconfigure  # Updates package manager
cmake --build build/
```

**If using CMake's find_package** (most existing projects):

Just use your existing CMakeLists.txt - ToolchainKit ensures the toolchain is configured correctly, so `find_package()` works as expected.

## Working with Existing Projects

### Migration is Simple

1. **No code changes**: Your CMakeLists.txt files remain unchanged
2. **Add ToolchainKit**: Run `tkgen init` in your project
3. **Commit config**: Check in `toolchainkit.yaml` and `bootstrap.sh`
4. **Team benefits**: Everyone gets consistent, reproducible builds

### Common Scenarios

**Scenario 1: Project with system dependencies**

```bash
# Your existing project uses find_package(Boost)
# Just configure with ToolchainKit:
tkgen configure --toolchain llvm-18

# Install Boost via system package manager
sudo apt install libboost-all-dev  # Linux
brew install boost                  # macOS

# Build works as before
cmake --build build/
```

**Scenario 2: Project with Conan**

```bash
# Your existing project has conanfile.txt or conanfile.py
tkgen init --detect-conan

# This adds Conan integration to toolchainkit.yaml
# Build works as before, but now with managed toolchain
cmake --build build/
```

**Scenario 3: Project with vcpkg**

```bash
# Your existing project has vcpkg.json
tkgen init --detect-vcpkg

# This adds vcpkg integration to toolchainkit.yaml
# Build works as before
cmake --build build/
```

**Scenario 4: Large project with multiple compilers**

```bash
# Test your project with different compilers easily
for toolchain in llvm-18 gcc-13 msvc-2022; do
  tkgen configure --toolchain $toolchain --build-dir build-$toolchain
  cmake --build build-$toolchain/ || echo "$toolchain failed"
done
```

### What Gets Committed

**Commit to version control:**
- `toolchainkit.yaml` (team configuration)
- `bootstrap.sh` / `bootstrap.bat` (setup script)
- `toolchainkit.lock` (for reproducibility)
- Your existing project files (unchanged)

**Don't commit (add to .gitignore):**
- `.toolchainkit/` (local state)
- `build/` (build output)
- `.cache/` (compiler cache)

### Team Workflow

```bash
# Developer 1: Sets up preferred toolchain
tkgen configure --toolchain llvm-18 --stdlib libc++
git add toolchainkit.yaml bootstrap.sh
git commit -m "Add ToolchainKit configuration"
git push

# Developer 2: Clones and builds immediately
git clone https://github.com/org/project.git
cd project
./bootstrap.sh              # Downloads llvm-18 automatically
cmake --build build/        # Works first time!
```

Everyone gets the same toolchain, avoiding "works on my machine" issues.

## Cross-Compilation

ToolchainKit makes cross-compilation straightforward.

### Android Example

```yaml
targets:
  - os: android
    arch: arm64
    toolchain: llvm-18-android
    api_level: 29
    ndk_version: 26.1.10909125
```

Build:
```bash
tkgen configure --target android-arm64
cmake --build build-android/
```

### iOS Example

```yaml
targets:
  - os: ios
    arch: arm64
    toolchain: llvm-18-ios
    sdk: iphoneos16.0
```

Build:
```bash
tkgen configure --target ios-arm64
cmake --build build-ios/
```

### Raspberry Pi Example

```yaml
targets:
  - os: linux
    arch: armv7
    toolchain: gcc-13-arm
    sysroot: auto  # Downloads appropriate sysroot
```

Build:
```bash
tkgen configure --target linux-armv7
cmake --build build-pi/
```

## Package Management

ToolchainKit integrates with popular C++ package managers, or works with none if you use system packages.

### Conan 2.x

```yaml
packages:
  manager: conan
  conan:
    version: 2.0
    profile: |
      [settings]
      compiler=clang
      compiler.version=18
      compiler.libcxx=libc++
```

Dependencies declared in `conanfile.py` or `conanfile.txt`.

### vcpkg

```yaml
packages:
  manager: vcpkg
  vcpkg:
    registry: https://github.com/microsoft/vcpkg.git
    baseline: 2024-10-01
```

Dependencies in `vcpkg.json`.

### CPM (CMake Package Manager)

```yaml
packages:
  manager: cpm
```

Dependencies in `CMakeLists.txt` using `CPMAddPackage()`.

### System Packages (No Package Manager)

If your project uses system-installed dependencies, just omit the `packages` section:

```yaml
# No packages section needed
version: 1
project: myapp

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
```

Your `find_package()` calls in CMakeLists.txt work as before.

### Multiple Package Managers

```yaml
packages:
  managers:
    - name: conan
      for: [boost, fmt]
    - name: vcpkg
      for: [catch2, nlohmann_json]
```

## CI/CD Integration

ToolchainKit works seamlessly in CI environments.

### GitHub Actions

```yaml
name: Build
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Cache toolchains
        uses: actions/cache@v3
        with:
          path: ~/.toolchainkit
          key: toolchainkit-${{ runner.os }}-${{ hashFiles('toolchainkit.yaml') }}

      - name: Cache sccache
        uses: actions/cache@v3
        with:
          path: ~/.cache/sccache
          key: sccache-${{ runner.os }}-${{ hashFiles('**/*.cpp', '**/*.h') }}

      - name: Bootstrap
        run: |
          curl -sSL https://toolchainkit.dev/install | sh
          ./bootstrap.sh

      - name: Build
        run: cmake --build build/ --parallel

      - name: Test
        run: cmake --build build/ --target test
```

### Matrix Builds

Test across multiple toolchains automatically:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    toolchain: [llvm-18, gcc-13, msvc-2022]
    exclude:
      - os: macos-latest
        toolchain: msvc-2022
      - os: windows-latest
        toolchain: gcc-13

steps:
  - name: Bootstrap
    run: ./bootstrap.sh --toolchain ${{ matrix.toolchain }}

  - name: Build
    run: cmake --build build/
```

### Remote Cache in CI

Enable shared cache across CI runs:

```yaml
# toolchainkit.yaml
build:
  caching:
    enabled: true
    tool: sccache
    remote:
      type: s3
      endpoint: s3://my-ci-cache/sccache

# GitHub Actions
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-west-2

- name: Build with cache
  run: cmake --build build/
  # sccache automatically uses S3 cache
```

**Result**: First CI run compiles everything, subsequent runs hit 90%+ cache rate.

## IDE Integration

ToolchainKit works with all major C++ IDEs.

### Visual Studio Code

`.vscode/settings.json` auto-generated:
```json
{
  "cmake.configureSettings": {
    "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/.toolchainkit/cmake/toolchain-llvm-18.cmake"
  },
  "cmake.buildDirectory": "${workspaceFolder}/build",
  "C_Cpp.default.compilerPath": "${workspaceFolder}/.toolchainkit/toolchains/llvm-18.1.8-linux-x64/bin/clang++"
}
```

Extensions:
- CMake Tools (official)
- C/C++ (official)
- clangd (optional, for better IntelliSense)

### CLion

Opens project via `CMakeLists.txt`, automatically detects toolchain file. Works out of the box.

### Visual Studio

Generate solution:
```bash
tkgen configure --toolchain msvc-2022 --generator "Visual Studio 17 2022"
```

Open `build/YourProject.sln` in Visual Studio.

### Xcode

Generate project:
```bash
tkgen configure --toolchain llvm-18 --generator Xcode
```

Open `build/YourProject.xcodeproj` in Xcode.

### Qt Creator

Qt Creator detects CMake projects automatically. Just open `CMakeLists.txt`.

## Static Analysis

ToolchainKit integrates static analysis tools for code quality.

### Clang-Tidy Integration

```yaml
modules:
  - analysis

analysis:
  clang_tidy:
    enabled: true
    checks: "-*,modernize-*,bugprone-*,performance-*"
    config_file: .clang-tidy
```

Run:
```bash
cmake --build build/ --target clang-tidy
```

### Other Tools

- **cppcheck**: `cmake --build build/ --target cppcheck`
- **include-what-you-use**: Integrated via CMake
- **sanitizers**: ASan, UBSan, TSan via build flags

Enable sanitizers:
```bash
tkgen configure --toolchain llvm-18 --sanitizer address
cmake --build build/
cmake --build build/ --target test  # Tests run with ASan
```

## Advanced Features

### Distributed Builds

Combine build caching with distributed compilation for maximum speed:

```yaml
build:
  distributed: true
  backend: ninja

  # Build caching (object file cache)
  caching:
    enabled: true
    tool: sccache
    remote:
      type: s3
      endpoint: s3://build-cache/sccache

  # Distributed compilation (job distribution)
  remote:
    type: buildgrid        # or IncrediBuild, distcc
    endpoint: https://build.example.com
```

**How it works:**
1. sccache checks cache for compiled objects (fast)
2. On cache miss, job goes to distributed build system
3. Multiple machines compile in parallel
4. Results cached for next time

**Performance**: 10x faster builds on large codebases.

### Reproducible Builds

Lock file pins exact versions and hashes:

```yaml
# toolchainkit.lock (auto-generated, commit this!)
version: 1
generated: 2025-11-11T10:30:00Z

toolchains:
  llvm-18.1.8-linux-x64:
    url: https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-linux-gnu-ubuntu-22.04.tar.xz
    sha256: abc123def456789...
    verified: true

packages:
  boost/1.83.0:
    sha256: def456789abc123...
  fmt/10.1.1:
    sha256: 789abc123def456...
```

**Benefits:**
- Bit-for-bit reproducible builds
- Security: Detect supply chain attacks
- Compliance: Audit exact build inputs

### Hermetic Python (for build scripts)

Some projects use Python build scripts. ToolchainKit can provide isolated Python:

```yaml
python:
  version: 3.11.5
  source: prebuilt
```

Downloads Python to `.toolchainkit/python/` - completely isolated from system Python.

### Precompiled Headers

ToolchainKit respects CMake's precompiled header settings:

```cmake
# In your existing CMakeLists.txt
target_precompile_headers(myapp PRIVATE
  <vector>
  <string>
  <map>
  "common.h"
)
```

Combined with caching, PCH dramatically speeds up rebuilds.

### Unity Builds

Enable unity builds for faster compilation:

```cmake
# In your existing CMakeLists.txt
set_target_properties(myapp PROPERTIES
  UNITY_BUILD ON
  UNITY_BUILD_BATCH_SIZE 16
)
```

Or via ToolchainKit:
```bash
tkgen configure --toolchain llvm-18 --unity-build
```

## Modular Design

ToolchainKit only includes what you need.

### Core Modules

1. **core** (required): Toolchain download, validation, management
2. **cmake** (required): CMake integration, toolchain file generation
3. **packages-conan**: Conan 2.x support
4. **packages-vcpkg**: vcpkg support
5. **packages-cpm**: CPM support
6. **caching**: Build caching (sccache/ccache)
7. **remote**: Distributed builds
8. **analysis**: Static analysis tools
9. **cross**: Cross-compilation helpers

### Module Selection

Project specifies needed modules:
```yaml
modules:
  - core
  - cmake
  - caching         # Want build caching
  - analysis        # Want clang-tidy
```

Bootstrap script only bundles selected modules → smaller, faster downloads.

### Automatic Detection

```bash
# Detects what your project needs
tkgen init --auto-detect

# Finds:
# - Existing package manager (Conan/vcpkg)
# - Cross-compilation targets
# - Analysis tools (.clang-tidy file)
# - Suggests appropriate modules
```

## Dependency Minimization

### Absolute Minimum Requirements

**Before bootstrap:**
- None (self-extracting shell script)

**Bootstrap downloads:**
- Python 3.8+ (embedded, isolated)
- CMake 3.25+
- curl/wget (if missing)

**Everything else on-demand:**
- Toolchains (compilers)
- Build backend (Ninja)
- Package managers (Conan/vcpkg)
- Build cache (sccache/ccache)

### Bootstrap Script

```bash
#!/bin/bash
# Fully self-contained - embeds Python + tkgen
# Extracts to /tmp, runs, cleans up

EMBEDDED_PAYLOAD="
<base64-encoded tkgen + python>
"

echo "$EMBEDDED_PAYLOAD" | base64 -d | tar xz -C /tmp
/tmp/tkgen/python /tmp/tkgen/tkgen.py bootstrap
rm -rf /tmp/tkgen
```

**Result**: Contributors need nothing installed - one command sets up everything.

## Cleanup and Maintenance

### Remove Unused Toolchains

```bash
# Show what would be removed
tkgen cleanup --dry-run

# Remove toolchains not referenced by any project
tkgen cleanup --unused

# Remove toolchains unused for 30+ days
tkgen cleanup --older-than 30d

# Force remove specific toolchain
tkgen cleanup --toolchain llvm-17.0.6
```

### Cache Management

```bash
# Show cache statistics
tkgen cache stats
# Output:
# Build cache (sccache): 3.2 GB, 87% hit rate
# Toolchains: 5.1 GB (3 versions)
# Total: 8.3 GB

# Clear build cache
tkgen cache clear

# Prune old entries
tkgen cache prune --older-than 30d

# Set cache size limit
tkgen cache config --max-size 10GB
```

### Upgrade Toolchains

```bash
# Upgrade to latest patch version
tkgen upgrade --toolchain llvm-18

# Upgrade all toolchains
tkgen upgrade --all

# Upgrade framework itself
tkgen self-update
```

### Verify Integrity

```bash
# Check toolchain hashes
tkgen verify

# Repair corrupted downloads
tkgen repair

# Verify entire project configuration
tkgen verify --full
```

## Security Considerations

### Toolchain Verification

- SHA256 hashes for all downloads
- GPG signatures (when available from vendor)
- TLS for all network requests
- Reproducible build verification

### Lockfile for Security

```yaml
# toolchainkit.lock (commit this!)
version: 1
generated: 2025-11-11T10:30:00Z

toolchains:
  llvm-18.1.8-linux-x64:
    url: https://github.com/llvm/llvm-project/releases/download/...
    sha256: abc123def456789...
    gpg_signature: https://github.com/llvm/llvm-project/releases/download/.../signature.asc
    verified: true
    verification_date: 2025-11-11T10:30:00Z
```

**Benefits:**
- Detect tampered downloads
- Audit trail for compliance
- Supply chain security

### Sandboxing

ToolchainKit runs toolchains in isolated environments:
- Separate directories (`.toolchainkit/toolchains/`)
- No system PATH pollution
- No global installation changes

## Large Project Support

### Incremental Builds

- CMake's native incremental build intelligence
- Ninja backend (default) for fast, parallel builds
- Build caching (sccache/ccache) for cross-machine speedup
- Distributed builds for large-scale parallelism

### Monorepo Support

```
monorepo/
├── toolchainkit.yaml          # Shared configuration
├── bootstrap.sh
└── projects/
    ├── libcore/
    │   └── CMakeLists.txt
    ├── libui/
    │   └── CMakeLists.txt
    ├── backend/
    │   └── CMakeLists.txt
    └── frontend/
        └── CMakeLists.txt
```

**Benefits:**
- Single toolchain configuration for entire monorepo
- Shared build cache across all projects
- Consistent compiler versions
- Simplified CI/CD

### Build Performance

**Techniques ToolchainKit enables:**
1. **Precompiled headers**: CMake `target_precompile_headers()`
2. **Unity builds**: CMake `UNITY_BUILD`
3. **Build caching**: sccache/ccache (80-95% hit rate)
4. **Distributed compilation**: buildgrid/IncrediBuild
5. **Parallel builds**: `cmake --build --parallel`

**Real-world example:**
- Project: 500k LOC C++ codebase
- Without ToolchainKit: 45 min clean build
- With ToolchainKit + caching: 2 min rebuild (after first build)
- With distributed builds: 8 min clean build

### Multiple Configurations

Large projects often need multiple build configurations:

```bash
# Configure all combinations
for toolchain in llvm-18 gcc-13; do
  for build_type in Debug Release RelWithDebInfo; do
    tkgen configure \
      --toolchain $toolchain \
      --build-type $build_type \
      --build-dir build-$toolchain-$build_type
  done
done

# Build specific configuration
cmake --build build-llvm-18-Release/
```

## Licensing

**Framework itself:** MIT License (permissive, commercial-friendly)

**Projects using ToolchainKit:** Any license (framework imposes no restrictions)

**Toolchains:** Respect individual compiler licenses:
- LLVM: Apache 2.0 with LLVM exception
- GCC: GPL with runtime library exception
- MSVC: Microsoft Visual Studio license

ToolchainKit only manages toolchains - it doesn't affect your project's licensing.

## Migration Path

### From Existing CMake Project

This is the primary use case! Migration is trivial:

1. **Initialize ToolchainKit** (30 seconds):
   ```bash
   cd your-existing-cmake-project
   tkgen init --auto-detect
   ```

2. **Review generated config** (optional):
   ```bash
   cat toolchainkit.yaml
   # Adjust if needed (usually defaults are fine)
   ```

3. **Bootstrap** (first time setup):
   ```bash
   ./bootstrap.sh
   ```

4. **Build as usual**:
   ```bash
   cmake --build build/
   ```

5. **Commit configuration**:
   ```bash
   git add toolchainkit.yaml bootstrap.sh .gitignore
   git commit -m "Add ToolchainKit for reproducible builds"
   ```

**Your CMakeLists.txt remains completely unchanged!**

### From Other Build Systems

**Make:**
Convert to CMake first (standard process), then add ToolchainKit.

**Bazel:**
Use Bazel-to-CMake converters, then add ToolchainKit.

**Meson:**
CMake alternatives exist; migrate then add ToolchainKit.

**Custom build scripts:**
Wrap with CMake, then add ToolchainKit.

### Common Migration Scenarios

**Scenario: Project uses system compiler**

Before:
```bash
# Developers manually install compilers
sudo apt install build-essential  # Hope everyone has same version!
cmake -B build/
cmake --build build/
```

After:
```bash
# ToolchainKit manages compilers
./bootstrap.sh  # Downloads exact compiler version
cmake --build build/
```

**Scenario: Project uses Docker for hermetic builds**

Before:
```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y build-essential cmake
# Build inside container
```

After:
```bash
# No Docker needed - ToolchainKit provides hermetic builds
./bootstrap.sh
cmake --build build/
```

**Benefit**: Faster, no Docker overhead, works natively on Windows/macOS.

**Scenario: Project has "works on my machine" issues**

Before:
- Developer A uses Clang 14
- Developer B uses GCC 11
- CI uses GCC 9
- Different bugs on each setup

After:
```yaml
# toolchainkit.yaml - everyone uses same toolchain
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
```

**Result**: Consistent builds across all machines.

## Real-World Examples

### Example 1: Minimal Existing Project

Existing project structure:
```
my-project/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── app.cpp
└── include/
    └── app.h
```

Add ToolchainKit:
```bash
cd my-project
tkgen init

# Generates:
# - toolchainkit.yaml (minimal config)
# - bootstrap.sh
# - .gitignore entries

./bootstrap.sh
cmake --build build/
```

**Total time**: 2 minutes

### Example 2: Project with Dependencies

Existing project with Conan:
```
my-project/
├── CMakeLists.txt
├── conanfile.txt
└── src/
    └── main.cpp
```

Add ToolchainKit:
```bash
cd my-project
tkgen init --detect-conan

# Detects Conan, generates integrated config
./bootstrap.sh
cmake --build build/
```

Dependencies automatically managed with hermetic toolchain.

### Example 3: Large Multi-Platform Project

Existing cross-platform project:
```
game-engine/
├── CMakeLists.txt
├── engine/
├── tools/
└── platforms/
    ├── windows/
    ├── linux/
    └── macos/
```

Add ToolchainKit with multiple targets:
```yaml
# toolchainkit.yaml
version: 1
project: game-engine

toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

  - name: msvc-2022
    type: msvc
    version: 17.8
    require_installed: true

defaults:
  linux: llvm-18
  macos: llvm-18
  windows: msvc-2022

build:
  backend: ninja
  parallel: auto

  caching:
    enabled: true
    tool: sccache
    remote:
      type: s3
      endpoint: s3://game-engine-cache/sccache

targets:
  - os: windows
    arch: x64
  - os: linux
    arch: x64
  - os: macos
    arch: arm64
  - os: android
    arch: arm64
    api_level: 29

modules:
  - core
  - cmake
  - caching
  - cross
```

Build for all platforms:
```bash
# Windows
tkgen configure --target windows-x64
cmake --build build-windows/

# Linux
tkgen configure --target linux-x64
cmake --build build-linux/

# macOS
tkgen configure --target macos-arm64
cmake --build build-macos/

# Android
tkgen configure --target android-arm64
cmake --build build-android/
```

### Example 4: Testing Compiler Compatibility

Existing project wants to test with multiple compilers:

```bash
# Test with various compilers
for toolchain in llvm-18 llvm-17 gcc-13 gcc-12; do
  echo "Testing with $toolchain..."
  tkgen configure --toolchain $toolchain --build-dir build-$toolchain

  if cmake --build build-$toolchain/; then
    echo "✓ $toolchain: PASS"
  else
    echo "✗ $toolchain: FAIL"
  fi
done
```

**Result**: Quickly identify compiler-specific issues.

## FAQ

**Q: Do I need to change my CMakeLists.txt files?**
A: No! ToolchainKit works with existing CMake projects without modifications.

**Q: Do I need Docker?**
A: No. Hermetic toolchains provide isolation without containers.

**Q: Can I use system-installed compilers?**
A: Yes. Set `require_installed: true` for MSVC, Xcode, etc.

**Q: How much disk space for shared cache?**
A: ~2GB per LLVM version, ~1.5GB per GCC version, plus build cache (configurable). Shared across all projects.

**Q: Does this replace CMake?**
A: No. It manages toolchains and generates CMake configuration. You still use CMake normally.

**Q: Can I use this in closed-source projects?**
A: Yes. MIT license allows commercial use.

**Q: How does build caching work?**
A: ToolchainKit integrates sccache or ccache as compiler launchers. They cache compiled object files by hash of source + flags + headers. Typical hit rates: 80-95% after first build.

**Q: Can I use remote build cache?**
A: Yes! Configure S3, HTTP, Redis, or other backends in toolchainkit.yaml. Great for teams and CI.

**Q: What if my project doesn't use package managers?**
A: No problem! Just omit the `packages` section. Use system libraries or `find_package()` as usual.

**Q: How do I switch compilers?**
A: `tkgen configure --toolchain <name>` - takes seconds, no rebuild needed.

**Q: How do I update the framework?**
A: `tkgen self-update` downloads latest version.

**Q: What if CDN is down?**
A: Falls back to official mirrors (llvm.org, gnu.org), or builds from source.

**Q: Can I fork and customize?**
A: Yes. Open source, extensible design, MIT licensed.

**Q: Does this work with existing CI/CD?**
A: Yes! Add bootstrap step to CI, then use standard CMake commands. See CI/CD Integration section.

**Q: Can I use this with IDEs?**
A: Yes! VSCode, CLion, Visual Studio, Xcode all work. IDE auto-detects generated toolchain files.

**Q: What about Windows without Visual Studio?**
A: ToolchainKit can download and use Clang or GCC on Windows - no Visual Studio required.

**Q: Can multiple projects share toolchains?**
A: Yes! Default shared cache mode saves disk space. 10 projects using LLVM 18 = one 2GB download.

**Q: How do I test my code with different standard libraries?**
A: `tkgen configure --toolchain llvm-18 --stdlib libc++` or `--stdlib libstdc++`. Instant switch.

**Q: Does this slow down builds?**
A: No! After initial setup, ToolchainKit is inactive. With caching enabled, builds are often faster than system compilers.

**Q: Can I use this in air-gapped environments?**
A: Yes. Download toolchains once, then use `--local-toolchains` or copy shared cache to air-gapped network.

**Q: What about compiler-specific flags?**
A: ToolchainKit generates appropriate flags for each toolchain. Your CMakeLists.txt uses standard CMake features.

**Q: Can I contribute toolchain definitions?**
A: Yes! Toolchain definitions are open source. Submit PRs for new compilers or platforms.

## Roadmap

### Phase 1: MVP (Q1 2026)
- Core toolchain management (LLVM, GCC)
- CMake integration
- Build caching (sccache/ccache)
- Conan support
- Linux, macOS, Windows support
- Shared cache
- **Focus**: Existing CMake project support

### Phase 2: Enhanced Support (Q2 2026)
- vcpkg, CPM support
- Cross-compilation (Android, iOS)
- MSVC, Xcode detection
- Static analysis integration
- Visual Studio, Xcode project generation
- Remote cache backends (S3, Redis, HTTP)
- IDE plugins (VSCode extension)

### Phase 3: Advanced Features (Q3 2026)
- Distributed builds (buildgrid, IncrediBuild)
- Advanced caching strategies
- Additional compilers (Zig, Intel DPC++)
- Multi-configuration builds
- Binary artifact caching

### Phase 4: Enterprise (Q4 2026)
- Private CDN support
- Air-gapped environments
- SBOM generation
- Security scanning
- Compliance reporting

## Contributing

ToolchainKit is open source! Contributions welcome:

- **Toolchain definitions**: Add support for new compilers
- **Platform support**: Port to new platforms
- **Package managers**: Integrate new package systems
- **IDE plugins**: VSCode, CLion extensions
- **Documentation**: Examples, tutorials, guides

See `CONTRIBUTING.md` in the repository.

## Conclusion

ToolchainKit brings modern, hermetic build practices to any CMake project:

✓ **No code changes** - works with existing projects
✓ **Instant toolchain switching** - test multiple compilers easily
✓ **Reproducible builds** - everyone gets the same toolchain
✓ **Fast rebuilds** - integrated build caching
✓ **Cross-platform** - Windows, Linux, macOS
✓ **Team-friendly** - shared cache, consistent environments
✓ **CI/CD ready** - simple integration

**Get started in 60 seconds:**

```bash
cd your-cmake-project
curl -sSL https://toolchainkit.dev/install | sh
tkgen init
./bootstrap.sh
cmake --build build/
```

**Your CMake project, now with superpowers.**
