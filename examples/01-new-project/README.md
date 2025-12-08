# Example 1: New Project from Scratch

This example demonstrates how to bootstrap a brand new C++ project with ToolchainKit.

## Scenario

You're starting a new C++ project and want:
- Modern C++ toolchain (LLVM 18)
- Cross-platform support (Windows, Linux, macOS)
- Package management (Conan)
- Reproducible builds
- Easy onboarding for new developers

## Project Structure

```
01-new-project/
├── CMakeLists.txt          # CMake build configuration
├── toolchainkit.yaml       # ToolchainKit configuration
├── conanfile.txt          # Conan dependencies
├── src/
│   └── main.cpp           # Application source
├── include/
│   └── mylib/
│       └── mylib.h        # Public headers
└── tests/
    └── test_main.cpp      # Unit tests
```

## Step-by-Step Setup

### 1. Initialize Project

```bash
# Create project directory
mkdir my-new-project
cd my-new-project

# Initialize ToolchainKit
tkgen init --toolchain llvm-18 --auto-detect

# This creates:
# - toolchainkit.yaml (project configuration)
# - .toolchainkit/ (local toolchain cache)
```

### 2. Configure Project

Edit `toolchainkit.yaml`:

```yaml
version: "1.0"

project:
  name: my-new-project
  version: "0.1.0"

toolchain:
  name: llvm-18
  stdlib: libc++

build:
  type: Release
  dir: build

packages:
  manager: conan
  conanfile: conanfile.txt

bootstrap:
  toolchain: llvm-18
  build_type: Release
  package_manager: conan
```

### 3. Create CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyNewProject VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find dependencies from Conan
find_package(fmt REQUIRED)
find_package(spdlog REQUIRED)

# Library
add_library(mylib
    src/mylib.cpp
)

target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(mylib PUBLIC
    fmt::fmt
    spdlog::spdlog
)

# Executable
add_executable(myapp
    src/main.cpp
)

target_link_libraries(myapp PRIVATE mylib)

# Tests
enable_testing()
add_executable(tests tests/test_main.cpp)
target_link_libraries(tests PRIVATE mylib)
add_test(NAME unit_tests COMMAND tests)
```

### 4. Add Dependencies

Create `conanfile.txt`:

```ini
[requires]
fmt/10.1.1
spdlog/1.12.0

[generators]
CMakeDeps
CMakeToolchain

[options]
shared=False
```

### 5. Generate Bootstrap Scripts

```bash
# Generate bootstrap scripts for all platforms
tkgen bootstrap

# This creates:
# - bootstrap.sh (Linux/macOS)
# - bootstrap.bat (Windows)
# - bootstrap.ps1 (PowerShell)
```

### 6. Bootstrap and Build

**On Linux/macOS:**
```bash
./bootstrap.sh
cmake --build build
./build/myapp
```

**On Windows:**
```cmd
bootstrap.bat
cmake --build build --config Release
build\Release\myapp.exe
```

**On Windows (PowerShell):**
```powershell
.\bootstrap.ps1
cmake --build build --config Release
build\Release\myapp.exe
```

## What the Bootstrap Script Does

When you run `bootstrap.sh` or `bootstrap.bat`, it:

1. ✅ Checks Python 3 is installed
2. ✅ Installs/upgrades ToolchainKit
3. ✅ Downloads and configures LLVM 18 toolchain
4. ✅ Installs Conan dependencies (fmt, spdlog)
5. ✅ Configures CMake with ToolchainKit toolchain
6. ✅ Reports success and shows next steps

## New Developer Onboarding

When a new developer joins your project:

```bash
# 1. Clone repository
git clone https://github.com/myorg/my-new-project.git
cd my-new-project

# 2. Run bootstrap (one command!)
./bootstrap.sh  # or bootstrap.bat on Windows

# 3. Build
cmake --build build

# 4. Run tests
ctest --test-dir build
```

That's it! No manual toolchain installation, no environment setup.

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/build.yml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Bootstrap project
        run: |
          chmod +x bootstrap.sh
          ./bootstrap.sh
        shell: bash

      - name: Build
        run: cmake --build build --config Release

      - name: Test
        run: ctest --test-dir build --config Release --output-on-failure
```

## Benefits of This Approach

✅ **Zero Manual Setup**: No need to install compilers manually
✅ **Cross-Platform**: Same workflow on Windows, Linux, macOS
✅ **Reproducible**: Lock files ensure everyone uses same versions
✅ **Fast Onboarding**: New developers up and running in minutes
✅ **CI-Ready**: Bootstrap script works in CI/CD pipelines
✅ **Isolated**: Doesn't interfere with system toolchains

## Next Steps

- Add more dependencies in `conanfile.txt`
- Configure different build types (Debug, RelWithDebInfo)
- Add cross-compilation targets
- Set up IDE integration (VS Code, CLion)
- Add static analysis tools

## Common Commands

```bash
# Regenerate bootstrap scripts (after config changes)
tkgen bootstrap --force

# Check environment health
tkgen doctor

# Upgrade toolchain
tkgen upgrade --toolchain llvm-18

# Verify toolchain integrity
tkgen verify

# Clean up unused toolchains
tkgen cleanup --unused
```

## Troubleshooting

**Problem**: Bootstrap script fails with "Python not found"
**Solution**: Install Python 3.8+ from https://www.python.org/

**Problem**: Conan dependencies fail to install
**Solution**: Check `conanfile.txt` syntax and package availability

**Problem**: CMake can't find toolchain file
**Solution**: Run `tkgen doctor --fix` to diagnose and fix issues

## See Also

- [ToolchainKit Documentation](../../docs/)
- [Configuration Reference](../../docs/config.md)
- [Bootstrap Scripts Guide](../../docs/bootstrap.md)
- [CI/CD Templates](../../docs/ci_cd.md)

## Configuration Reference

### 1. Component Availability by OS

| Component | Linux | macOS | Windows | Notes |
|-----------|:-----:|:-----:|:-------:|-------|
| **Compilers** | | | | |
| LLVM (Clang) | ✅ | ✅ | ✅ | |
| GCC | ✅ | ✅ | ❌ | MinGW not yet supported |
| MSVC | ❌ | ❌ | ✅ | |
| **Allocators** | | | | |
| jemalloc | ✅ | ✅ | ✅ | Link-time only on Windows |
| mimalloc | ✅ | ✅ | ✅ | |
| tbbmalloc | ✅ | ✅ | ✅ | |
| tcmalloc | ✅ | ✅ | ❌ | Use mimalloc on Windows |
| snmalloc | ✅ | ✅ | ✅ | |
| **Build Tools** | | | | |
| Ninja | ✅ | ✅ | ✅ | Recommended default |
| Make | ✅ | ✅ | ❌ | |
| MSBuild | ❌ | ❌ | ✅ | |
| Xcode | ❌ | ✅ | ❌ | |

### 2. Compiler & Build Tool Compatibility

| Build Tool | LLVM (Clang) | GCC | MSVC | Notes |
|------------|:------------:|:---:|:----:|-------|
| **Ninja** | ✅ | ✅ | ✅ | Best performance, cross-platform |
| **Make** | ✅ | ✅ | ❌ | Standard on Unix |
| **MSBuild** | ✅ (clang-cl) | ❌ | ✅ | Windows standard |
| **Xcode** | ✅ | ❌ | ❌ | macOS standard |

### 3. Sanitizer Compatibility

| Sanitizer | Clang | GCC | MSVC | Conflicts With |
|-----------|:-----:|:---:|:----:|----------------|
| Address (ASan) | ✅ | ✅ | ⚠️ | Allocators, TSan, MSan |
| Memory (MSan) | ✅ | ❌ | ❌ | Allocators, ASan, TSan |
| Thread (TSan) | ✅ | ✅ | ❌ | Allocators, ASan, MSan |
| Undefined (UBSan)| ✅ | ✅ | ⚠️ | |

*(Note: MSVC support for ASan is version-dependent)*

### 4. Package Managers

| Package Manager | Linux | macOS | Windows | Notes |
|-----------------|:-----:|:-----:|:-------:|-------|
| **Conan** | ✅ | ✅ | ✅ | Python-based, highly configurable |
| **Vcpkg** | ✅ | ✅ | ✅ | Microsoft-maintained, easy integration |
| **None** | ✅ | ✅ | ✅ | Use system libraries or submodules |
