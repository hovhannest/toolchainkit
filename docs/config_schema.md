# Configuration Schema

Complete reference for `toolchainkit.yaml` format.

## Minimal Example

```yaml
project:
  name: my-project

toolchains:
  main:
    type: llvm
    version: "18.1.8"

defaults:
  toolchain: main
  build_type: Release
```

## Full Schema

### Project

```yaml
project:
  name: string              # Project name
  cmake_minimum_version: string  # Min CMake (e.g., "3.20")
```

### Toolchains

```yaml
toolchains:
  <name>:
    type: llvm|gcc|msvc     # Compiler type
    version: string         # Version or "latest"
    stdlib: libc++|libstdc++|msvc  # Optional
    linker: lld|gold|mold|bfd      # Optional
    source: prebuilt|system # Optional, default: prebuilt
```

### Defaults

```yaml
defaults:
  toolchain: string         # Default toolchain name
  build_type: Debug|Release|RelWithDebInfo|MinSizeRel
  generator: Ninja|Make|MSBuild|Xcode
```

### Build

```yaml
build:
  types: [Debug, Release, ...]  # Build types
  parallel_jobs: int|auto   # Parallel jobs
  directory: string         # Build dir (default: build)
```

### Toolchain Cache

Configure where toolchains are downloaded and stored:

```yaml
toolchain_cache:
  location: shared|local|custom  # Cache location strategy
  path: string                   # Optional: custom path (for local/custom)
```

**Options:**
- `shared` (default): Use global cache (`~/.toolchainkit/` or `%USERPROFILE%\.toolchainkit\`)
- `local`: Store in project directory (`.toolchainkit/toolchains/`)
- `custom`: Use custom path specified in `path` field

**Examples:**

```yaml
# Use shared global cache (default)
toolchain_cache:
  location: shared

# Store toolchains locally in project
toolchain_cache:
  location: local
  path: .toolchainkit

# Use custom cache directory
toolchain_cache:
  location: custom
  path: /opt/toolchains
```

**Legacy Support:**
For backwards compatibility, `toolchain_dir` and `cache_dir` are supported but deprecated:
```yaml
# Deprecated - use toolchain_cache instead
toolchain_dir: .toolchainkit  # Converted to: location: local, path: .toolchainkit
cache_dir: .toolchainkit      # Converted to: location: local, path: .toolchainkit
```

### Packages

Configure package manager integration for dependency management:

```yaml
packages:
  manager: conan|vcpkg      # Package manager to use
  conan_home: string        # (Conan only) Custom CONAN_HOME directory
  use_system_conan: bool    # (Conan only) Use system Conan vs downloaded

  # Legacy Conan format (still supported):
  conan:
    enabled: bool
    conanfile: string       # conanfile.txt or conanfile.py
    profile: string         # Optional custom profile

  vcpkg:
    enabled: bool
    manifest: string        # vcpkg.json
    triplet: string         # Optional custom triplet
```

**Package Isolation with Conan:**

The `conan_home` field allows you to isolate Conan packages per project by setting the `CONAN_HOME` environment variable:

```yaml
# Example: Project-local Conan packages
packages:
  manager: conan
  conan_home: .toolchainkit/conan  # Relative to project root

# This stores Conan packages in <project>/.toolchainkit/conan/p/
# instead of the system-wide ~/.conan2 directory
```

**Benefits of project-local Conan:**
- **Reproducibility**: Each project has isolated dependencies
- **No conflicts**: Different projects can use different package versions
- **Portability**: Dependencies are self-contained within the project
- **Clean separation**: Conan cache is separate from other toolchain files

**Note:** If `conan_home` is not specified, Conan uses the system default `~/.conan2` directory (shared across all projects). For project-local isolation, use `.toolchainkit/conan` to keep Conan's cache files separate from toolchains and other tools.

### Build Cache

Configure compiler caching (sccache/ccache) for faster rebuilds:

```yaml
cache:
  enabled: bool
  tool: sccache|ccache
  size_gb: int              # Cache size limit
  remote:
    type: s3|redis|http|gcs
    # Backend-specific options
    bucket: string          # S3/GCS bucket
    region: string          # S3 region
    endpoint: string        # Custom S3 endpoint
    redis_url: string       # Redis: redis://host:port
```

### Cross-Compilation

```yaml
cross:
  enabled: bool
  target: android|ios|raspberry-pi
  android:
    abi: arm64-v8a|armeabi-v7a|x86_64|x86
    api_level: int
    ndk_path: string
  ios:
    platform: iphoneos|iphonesimulator
    deployment_target: string
  raspberry_pi:
    arch: armv7l|aarch64
    sysroot: string
```

### Layers (Advanced)

```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: buildtype
      name: release
    - type: security
      name: hardened
    - type: allocator
      name: jemalloc
```

## Validation

```python
from toolchainkit.config.parser import load_config
from toolchainkit.config.validation import validate_config

config = load_config(Path("toolchainkit.yaml"))
issues = validate_config(config)

for issue in issues:
    if issue.level == "error":
        print(f"Error: {issue.message}")
```

## Complete Example

```yaml
project:
  name: game-engine
  cmake_minimum_version: "3.25"

toolchains:
  main:
    type: llvm
    version: "18.1.8"
    stdlib: libc++
    linker: lld

  gcc-fallback:
    type: gcc
    version: "13.2.0"

defaults:
  toolchain: main
  build_type: Release
  generator: Ninja

toolchain_cache:
  location: local
  path: .toolchainkit

build:
  types: [Debug, Release, RelWithDebInfo]
  parallel_jobs: auto

packages:
  conan:
    enabled: true
    conanfile: conanfile.txt

cache:
  enabled: true
  tool: sccache
  remote:
    type: s3
    bucket: my-build-cache
    region: us-east-1
```

See [Configuration Guide](config.md) for usage examples.
