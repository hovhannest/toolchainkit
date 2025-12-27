# Package Managers

Integration with Conan and vcpkg for C++ dependency management.

## Conan

```python
from toolchainkit.packages.conan import ConanIntegration

conan = ConanIntegration(project_root)

# Generate Conan profile from toolchain
conan.generate_profile(
    toolchain_dir=Path("/opt/llvm-18"),
    toolchain_type="llvm",
    output_path=Path(".toolchainkit/conan/profiles/default")
)

# Install dependencies
conan.install_dependencies(
    conanfile=Path("conanfile.txt"),
    build_dir=Path("build")
)
```

### Conan Profile Example

```ini
[settings]
os=Linux
arch=x86_64
compiler=clang
compiler.version=18
compiler.libcxx=libc++
build_type=Release

[conf]
tools.cmake.cmaketoolchain:generator=Ninja
```

## vcpkg

```python
from toolchainkit.packages.vcpkg import VcpkgIntegration

vcpkg = VcpkgIntegration(project_root, vcpkg_root=Path("~/vcpkg"))

# Install from manifest
vcpkg.install_dependencies(
    manifest=Path("vcpkg.json"),
    triplet="x64-linux"
)

# Get CMake toolchain file
toolchain_file = vcpkg.get_toolchain_file()
```

### vcpkg Manifest Example

```json
{
  "dependencies": [
    "fmt",
    "spdlog",
    "catch2"
  ]
}
```

## Triplet Selection

ToolchainKit auto-selects triplets:

| Platform | vcpkg Triplet |
|----------|---------------|
| Linux x64 | x64-linux |
| Linux ARM64 | arm64-linux |
| Windows x64 | x64-windows |
| macOS x64 | x64-osx |
| macOS ARM64 | arm64-osx |

## CMake Integration

```cmake
# Conan
include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake)

# vcpkg
set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake")
```

## Configuration

```yaml
# toolchainkit.yaml
packages:
  conan:
    enabled: true
    conanfile: conanfile.txt

  vcpkg:
    enabled: true
    manifest: vcpkg.json
```

## Conan Best Practices with ToolchainKit

When using Conan with ToolchainKit, follow these best practices to avoid common issues:

### 1. Disable `cmake_layout()` in conanfile.py

If using `conanfile.py`, **do not use `cmake_layout()`** as it conflicts with ToolchainKit's build directory management:

```python
# conanfile.py
from conan import ConanFile

class MyProjectConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires("fmt/10.2.1")
        self.requires("spdlog/1.12.0")

    def build_requirements(self):
        self.tool_requires("cmake/3.28.1")

    def layout(self):
        # Do NOT use cmake_layout() with ToolchainKit
        # cmake_layout(self)  # This causes nested build/ directories
        pass
```

**Why?** `cmake_layout()` tells Conan to create profile-specific subfolders (e.g., `build/Debug`, `build/Release`), but ToolchainKit uses a flat `build/` directory. This mismatch causes generators to end up in nested paths like `build/generators/generators/`.

### 2. Use `test_requires()` for Test Dependencies

Test-only dependencies like GTest should use `test_requires()`, not `requires()`:

```python
def requirements(self):
    self.requires("fmt/10.2.1")      # Library dependency

def build_requirements(self):
    self.test_requires("gtest/1.14.0")  # Test-only dependency
```

**Important:** When using `test_requires()`, make `find_package(GTest)` conditional in CMakeLists.txt:

```cmake
# Only find GTest when building tests
option(BUILD_TESTING "Build tests" ON)
if(BUILD_TESTING)
    find_package(GTest REQUIRED)
    add_executable(tests tests/test_main.cpp)
    target_link_libraries(tests PRIVATE GTest::gtest GTest::gtest_main mylib)
endif()
```

### 3. CONAN_HOME Configuration

ToolchainKit only sets `CONAN_HOME` when explicitly configured:

```yaml
# toolchainkit.yaml
packages:
  manager: conan
  conan_home: .toolchainkit/conan  # Optional: project-local Conan home
```

- **Without `conan_home`**: Uses system default `~/.conan2` (shared across projects)
- **With `conan_home`**: Uses project-local cache for isolation

### 4. Prefer conanfile.txt for Simple Projects

For projects that only need dependencies (no custom build logic), use `conanfile.txt`:

```ini
[requires]
fmt/10.2.1
spdlog/1.12.0

[test_requires]
gtest/1.14.0

[generators]
CMakeDeps
CMakeToolchain

[options]
*:shared=False
```

This avoids layout conflicts and keeps configuration simple.

## Integration

Both package managers work with all toolchains (LLVM, GCC, MSVC).
