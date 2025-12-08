# Configuration Layers

Build complex configurations by composing reusable layers.

## Overview

The configuration layer system allows you to compose complex build configurations from small, reusable pieces. Instead of duplicating configuration across projects, you define layers that can be mixed and matched.

**Example:** `base/clang-18 + platform/linux-x64 + stdlib/libc++ + buildtype/release + optimization/lto-thin`

## Quick Start

```python
from toolchainkit.config.composer import LayerComposer

composer = LayerComposer()

# Compose configuration from layers
layer_specs = [
    {"type": "base", "name": "clang-18"},
    {"type": "platform", "name": "linux-x64"},
    {"type": "stdlib", "name": "libc++"},
    {"type": "buildtype", "name": "release"},
    {"type": "optimization", "name": "lto-thin"},
]

config = composer.compose(layer_specs)
print(config.compile_flags)  # ['-O3', '-DNDEBUG', '-flto=thin', ...]
print(config.link_flags)      # ['-fuse-ld=lld', '-flto=thin', ...]
```

## Layer Types

### Base Compiler Layer
Defines the base compiler (Clang, GCC, MSVC).

```yaml
# layers/base/clang-18.yaml
type: base
compiler: clang
version: 18.1.8
compiler_path: /usr/bin/clang-18
cxx_compiler_path: /usr/bin/clang++-18
```

### Platform Layer
Platform-specific settings (architecture, OS).

```yaml
# layers/platform/linux-x64.yaml
type: platform
os: linux
arch: x64
defines:
  - __LINUX__
  - __x86_64__
```

### Standard Library Layer
C++ standard library configuration.

```yaml
# layers/stdlib/libc++.yaml
type: stdlib
name: libc++
compile_flags:
  - -stdlib=libc++
link_flags:
  - -lc++
  - -lc++abi
```

### Build Type Layer
Build type settings (Debug, Release, etc.).

```yaml
# layers/buildtype/release.yaml
type: buildtype
name: release
compile_flags:
  - -O3
  - -DNDEBUG
link_flags:
  - -Wl,-O1
```

### Optimization Layer
Advanced optimization settings.

```yaml
# layers/optimization/lto-thin.yaml
type: optimization
name: lto-thin
compile_flags:
  - -flto=thin
link_flags:
  - -flto=thin
  - -fuse-ld=lld
requires:
  - compiler: [clang, llvm]
```

### Sanitizer Layer
Runtime sanitizers (ASan, TSan, UBSan).

```yaml
# layers/sanitizer/asan.yaml
type: sanitizer
name: asan
compile_flags:
  - -fsanitize=address
  - -fno-omit-frame-pointer
link_flags:
  - -fsanitize=address
defines:
  - ASAN_ENABLED
```

### Allocator Layer
Custom memory allocators.

```yaml
# layers/allocator/jemalloc.yaml
type: allocator
name: jemalloc
link_flags:
  - -ljemalloc
defines:
  - USE_JEMALLOC
```

### Security Layer
Security hardening options.

```yaml
# layers/security/fortify.yaml
type: security
name: fortify
compile_flags:
  - -D_FORTIFY_SOURCE=2
  - -fstack-protector-strong
link_flags:
  - -Wl,-z,relro
  - -Wl,-z,now
```

### Profiling Layer
Profiling and instrumentation.

```yaml
# layers/profiling/gprof.yaml
type: profiling
name: gprof
compile_flags:
  - -pg
link_flags:
  - -pg
```

## LayerComposer API

```python
class LayerComposer:
    """Compose configurations from layers."""

    def __init__(self,
                 project_root: Optional[Path] = None,
                 global_layers_dir: Optional[Path] = None):
        """
        Initialize layer composer.

        Args:
            project_root: Project root for local layers
            global_layers_dir: Global layers directory
        """

    def compose(self, layer_specs: List[Dict[str, str]]) -> ComposedConfig:
        """
        Compose configuration from layer specifications.

        Args:
            layer_specs: List of layer specs like [{"type": "base", "name": "clang-18"}]

        Returns:
            ComposedConfig with merged settings
        """

    def load_layer(self, layer_type: str, layer_name: str) -> ConfigLayer:
        """Load specific layer by type and name."""

    def discover_layers(self, layer_type: Optional[str] = None) -> Dict[str, List[str]]:
        """Discover available layers."""
```

## ComposedConfig

Result of layer composition:

```python
@dataclass
class ComposedConfig:
    compiler: str
    compiler_version: str
    compile_flags: List[str]
    link_flags: List[str]
    defines: List[str]
    includes: List[Path]
    libraries: List[str]
    system_libraries: List[str]
    cmake_variables: Dict[str, str]
    environment: Dict[str, str]
```

## Layer Discovery

Layers are discovered from:
1. **Project-local**: `<project>/.toolchainkit/layers/`
2. **Global**: `~/.toolchainkit/layers/`
3. **Built-in**: `toolchainkit/data/layers/`

Priority: Project-local > Global > Built-in

## Using with toolchainkit.yaml

```yaml
# toolchainkit.yaml
version: 1.0

toolchains:
  - name: clang-release
    layers:
      - {type: base, name: clang-18}
      - {type: platform, name: linux-x64}
      - {type: stdlib, name: libc++}
      - {type: buildtype, name: release}
      - {type: optimization, name: lto-thin}
      - {type: security, name: fortify}

  - name: gcc-debug
    layers:
      - {type: base, name: gcc-13}
      - {type: platform, name: linux-x64}
      - {type: stdlib, name: libstdc++}
      - {type: buildtype, name: debug}
      - {type: sanitizer, name: asan}
      - {type: sanitizer, name: ubsan}
```

## Layer Validation

Layers can specify requirements and conflicts:

```yaml
# layers/optimization/lto-thin.yaml
type: optimization
name: lto-thin
compile_flags:
  - -flto=thin
requires:
  compiler: [clang, llvm]  # Only for Clang
conflicts:
  sanitizer: [msan]        # Incompatible with MSan
```

Validation happens during composition:
```python
try:
    config = composer.compose(layer_specs)
except LayerValidationError as e:
    print(f"Validation error: {e}")
except LayerConflictError as e:
    print(f"Layer conflict: {e}")
```

## Custom Layers

Create custom layers for your project:

```yaml
# .toolchainkit/layers/custom/myproject.yaml
type: custom
name: myproject
compile_flags:
  - -DMYPROJECT_VERSION=1.0.0
  - -ffast-math
defines:
  - MYPROJECT_CUSTOM_BUILD
includes:
  - ${project_root}/include/custom
```

## Complete Example

```python
from toolchainkit.config.composer import LayerComposer
from pathlib import Path

def configure_release_build():
    """Configure optimized release build."""
    composer = LayerComposer(project_root=Path.cwd())

    # Compose aggressive optimization configuration
    config = composer.compose([
        {"type": "base", "name": "clang-18"},
        {"type": "platform", "name": "linux-x64"},
        {"type": "stdlib", "name": "libc++"},
        {"type": "buildtype", "name": "release"},
        {"type": "optimization", "name": "lto-thin"},
        {"type": "optimization", "name": "pgo"},
        {"type": "security", "name": "fortify"},
        {"type": "allocator", "name": "jemalloc"},
    ])

    # Generate CMake configuration
    cmake_vars = config.cmake_variables
    cmake_vars['CMAKE_C_COMPILER'] = config.compiler
    cmake_vars['CMAKE_C_FLAGS'] = ' '.join(config.compile_flags)
    cmake_vars['CMAKE_EXE_LINKER_FLAGS'] = ' '.join(config.link_flags)

    return cmake_vars

def configure_debug_build():
    """Configure debug build with sanitizers."""
    composer = LayerComposer(project_root=Path.cwd())

    config = composer.compose([
        {"type": "base", "name": "clang-18"},
        {"type": "platform", "name": "linux-x64"},
        {"type": "stdlib", "name": "libc++"},
        {"type": "buildtype", "name": "debug"},
        {"type": "sanitizer", "name": "asan"},
        {"type": "sanitizer", "name": "ubsan"},
        {"type": "profiling", "name": "gprof"},
    ])

    return config.cmake_variables
```

## Benefits

1. **Reusability**: Define layers once, use everywhere
2. **Composability**: Mix and match for different builds
3. **Validation**: Automatic conflict detection
4. **Maintainability**: Update layers independently
5. **Discoverability**: List all available layers
6. **Sharing**: Share layers across projects and teams

## See Also

- [Configuration](config.md) - Configuration file format
- [Build Cache](build_cache.md) - Build optimization
- [CMake Toolchain](cmake_toolchain.md) - CMake integration
- [Layer Data](../toolchainkit/data/layers/README.md) - Built-in layers reference
