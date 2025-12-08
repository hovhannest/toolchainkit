# Example 2: Existing CMake Project

This example demonstrates how to add ToolchainKit to an existing CMake project.

## Scenario

You have an existing C++ project that:
- Already uses CMake
- Has manual toolchain setup instructions
- Has inconsistent builds across developer machines
- Wants to add hermetic, reproducible builds

## Before ToolchainKit

```
legacy-project/
├── CMakeLists.txt           # Existing CMake config
├── src/
│   ├── main.cpp
│   └── utils.cpp
├── include/
│   └── utils.h
├── BUILDING.md              # Manual setup instructions (10+ steps)
└── README.md
```

**Setup was manual:**
1. Install specific GCC version
2. Install Boost from source
3. Set environment variables
4. Configure CMake with many flags
5. Hope it works...

## After ToolchainKit

```
legacy-project/
├── CMakeLists.txt           # Slightly modified
├── toolchainkit.yaml        # ✨ NEW: ToolchainKit config
├── conanfile.txt            # ✨ NEW: Dependencies
├── bootstrap.sh             # ✨ NEW: Automated setup
├── bootstrap.bat            # ✨ NEW: Windows setup
├── src/
│   ├── main.cpp
│   └── utils.cpp
├── include/
│   └── utils.h
├── BUILDING.md              # Updated (2 steps!)
└── README.md
```

**Setup is now automatic:**
1. Run `./bootstrap.sh`
2. Build!

## Step-by-Step Migration

### 1. Initialize ToolchainKit in Existing Project

```bash
cd legacy-project

# Initialize (doesn't modify existing files)
tkgen init --toolchain gcc-13 --auto-detect

# This creates:
# - toolchainkit.yaml
# - .toolchainkit/ directory
# - Does NOT modify CMakeLists.txt yet
```

### 2. Review Generated Configuration

`toolchainkit.yaml`:

```yaml
version: "1.0"

project:
  name: legacy-project
  version: "1.0.0"

toolchain:
  name: gcc-13
  stdlib: libstdc++

build:
  type: Release
  dir: build

# Add package manager if needed
packages:
  manager: conan
  conanfile: conanfile.txt

bootstrap:
  toolchain: gcc-13
  build_type: Release
  package_manager: conan
```

### 3. (Optional) Migrate Dependencies to Conan

If your project has manual dependency setup, migrate to Conan:

**Before (manual):**
```bash
# BUILDING.md
sudo apt-get install libboost-all-dev
wget https://github.com/fmtlib/fmt/...
cd fmt && mkdir build && cmake ...
```

**After (automated):**

Create `conanfile.txt`:
```ini
[requires]
boost/1.83.0
fmt/10.1.1

[generators]
CMakeDeps
CMakeToolchain

[options]
boost:shared=False
```

### 4. Update CMakeLists.txt (Minimal Changes)

**Before:**
```cmake
cmake_minimum_required(VERSION 3.15)
project(LegacyProject)

# Manual dependency paths
find_package(Boost REQUIRED COMPONENTS filesystem system)
find_package(fmt REQUIRED)

add_executable(myapp src/main.cpp src/utils.cpp)
target_link_libraries(myapp Boost::filesystem Boost::system fmt::fmt)
```

**After (add one line at the top):**
```cmake
cmake_minimum_required(VERSION 3.15)

# Optional: Use ToolchainKit toolchain file if available
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/.toolchainkit/cmake/toolchainkit/toolchain.cmake")
    set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/.toolchainkit/cmake/toolchainkit/toolchain.cmake")
endif()

project(LegacyProject)

# Dependencies now come from Conan (via ToolchainKit)
find_package(Boost REQUIRED COMPONENTS filesystem system)
find_package(fmt REQUIRED)

add_executable(myapp src/main.cpp src/utils.cpp)
target_link_libraries(myapp Boost::filesystem Boost::system fmt::fmt)
```

### 5. Generate Bootstrap Scripts

```bash
# Generate bootstrap scripts
tkgen bootstrap

# Review generated scripts
cat bootstrap.sh
cat bootstrap.bat
```

### 6. Test Bootstrap Process

```bash
# Clean environment to test
rm -rf build .toolchainkit

# Run bootstrap
./bootstrap.sh

# Verify it worked
cmake --build build
./build/myapp
```

### 7. Update Documentation

**Update BUILDING.md:**

```markdown
# Building Legacy Project

## Quick Start

### Prerequisites
- Python 3.8+

### Build

**Linux/macOS:**
```bash
./bootstrap.sh
cmake --build build
```

**Windows:**
```cmd
bootstrap.bat
cmake --build build --config Release
```

That's it!

## What the Bootstrap Script Does

The bootstrap script automatically:
1. Installs ToolchainKit
2. Downloads GCC 13 toolchain
3. Installs dependencies (Boost, fmt)
4. Configures CMake

## Manual Build (Advanced)

If you want to use your system toolchain instead:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```
```

### 8. Update CI/CD

**Before (complex setup):**
```yaml
# .github/workflows/build.yml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-13 g++-13 libboost-all-dev

      - name: Install fmt
        run: |
          git clone https://github.com/fmtlib/fmt.git
          cd fmt && mkdir build && cd build
          cmake .. && make && sudo make install

      - name: Configure
        run: |
          export CC=gcc-13
          export CXX=g++-13
          cmake -B build

      - name: Build
        run: cmake --build build
```

**After (simple):**
```yaml
# .github/workflows/build.yml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Bootstrap
        run: ./bootstrap.sh

      - name: Build
        run: cmake --build build
```

## Migration Checklist

- [x] Run `tkgen init` in project root
- [x] Review generated `toolchainkit.yaml`
- [x] Migrate dependencies to Conan (optional)
- [x] Update CMakeLists.txt (minimal changes)
- [x] Generate bootstrap scripts with `tkgen bootstrap`
- [x] Test bootstrap on clean environment
- [x] Update BUILDING.md documentation
- [x] Update CI/CD workflows
- [x] Commit changes to repository

## Benefits After Migration

✅ **Reproducible Builds**: Everyone uses same toolchain and dependencies
✅ **Fast Onboarding**: New developers up in minutes, not hours
✅ **Cross-Platform**: Works on Windows, Linux, macOS
✅ **CI-Friendly**: Simpler, faster CI workflows
✅ **No Manual Setup**: No more "install GCC 13, then Boost, then..."
✅ **Isolated Environment**: Doesn't break system packages
✅ **Lockfile Support**: Pin exact versions for security

## Common Migration Issues

### Issue: Existing System Dependencies

**Problem**: Project depends on system libraries (OpenGL, X11, etc.)

**Solution**: Keep system dependencies, use ToolchainKit for toolchain and third-party libs:

```yaml
# toolchainkit.yaml
packages:
  manager: conan
  system_deps:
    - libgl-dev
    - libx11-dev
```

### Issue: Custom Compiler Flags

**Problem**: Project needs specific compiler flags

**Solution**: Add to CMakeLists.txt or toolchainkit.yaml:

```yaml
# toolchainkit.yaml
build:
  cmake_args:
    - "-DCMAKE_CXX_FLAGS=-Wall -Wextra -O3"
```

### Issue: Multiple Build Configurations

**Problem**: Project supports Debug, Release, RelWithDebInfo

**Solution**: Generate multiple bootstrap scripts or use CLI args:

```bash
# Debug build
tkgen bootstrap --build-type Debug

# Release build
tkgen bootstrap --build-type Release
```

## Rollback Plan

If migration doesn't work, you can easily rollback:

```bash
# Remove ToolchainKit files
rm -rf .toolchainkit toolchainkit.yaml bootstrap.sh bootstrap.bat conanfile.txt

# Revert CMakeLists.txt changes
git checkout CMakeLists.txt

# Continue using manual setup
```

ToolchainKit doesn't modify your source code, so rollback is safe.

## See Also

- [Configuration Guide](../../docs/config.md)
- [Conan Integration](../../docs/package_managers.md#conan)
- [CMake Integration](../../docs/cmake_toolchain.md)
- [Migration Best Practices](../../docs/dev/README.md)
