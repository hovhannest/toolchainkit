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

## Integration

Both package managers work with all toolchains (LLVM, GCC, MSVC).
