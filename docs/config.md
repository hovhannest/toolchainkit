# Configuration

YAML-based project configuration for toolchains, build settings, and dependencies.

By default, ToolchainKit looks for `toolchainkit.yaml` in the project root. You can specify a different file using the `--config` CLI option.

## Quick Start

```yaml
# toolchainkit.yaml
project:
  name: my-project
  cmake_minimum_version: "3.20"

toolchains:
  llvm-18:
    type: llvm
    version: "18.1.8"
    stdlib: libc++

  gcc-13:
    type: gcc
    version: "13.2.0"

defaults:
  toolchain: llvm-18
  build_type: Release
  generator: Ninja

build:
  types: [Debug, Release]
  parallel_jobs: 8

packages:
  conan:
    enabled: true
    conanfile: conanfile.txt
```

```python
from toolchainkit.config.parser import load_config

config = load_config(Path("toolchainkit.yaml"))
print(f"Project: {config.project.name}")
print(f"Default toolchain: {config.defaults.toolchain}")
```

## Schema

### Project Section

```yaml
project:
  name: string              # Project name
  cmake_minimum_version: string  # Min CMake version
```

### Toolchains Section

```yaml
toolchains:
  <name>:
    type: llvm|gcc|msvc     # Compiler type
    version: string         # Version (e.g., "18.1.8", "latest")
    stdlib: libc++|libstdc++|msvc  # Optional: standard library
    linker: lld|gold|mold   # Optional: linker
```

### Defaults Section

```yaml
defaults:
  toolchain: string         # Default toolchain name
  build_type: Debug|Release|RelWithDebInfo|MinSizeRel
  generator: Ninja|Make|MSBuild|Xcode
```

### Build Section

```yaml
build:
  types: [Debug, Release, ...]  # Build types to generate
  parallel_jobs: int        # Parallel build jobs
  directory: string         # Build directory (default: build)
```

### Packages Section

```yaml
packages:
  conan:
    enabled: bool
    conanfile: string       # conanfile.txt or conanfile.py

  vcpkg:
    enabled: bool
    manifest: string        # vcpkg.json
```

### Cache Section

```yaml
cache:
  enabled: bool
  tool: sccache|ccache
  remote:
    type: s3|redis|http
    # ... backend-specific options
```

### Cross-Compilation

```yaml
cross:
  enabled: bool
  target: android|ios|raspberry-pi
  # ... target-specific options
```

## Validation

```python
from toolchainkit.config.validation import validate_config

issues = validate_config(config)
for issue in issues:
    print(f"{issue.level}: {issue.message}")
```

## Example

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

defaults:
  toolchain: main
  build_type: Release
  generator: Ninja

build:
  types: [Debug, Release, RelWithDebInfo]
  parallel_jobs: 16

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
```

See `docs/config_schema.md` for complete schema reference.
