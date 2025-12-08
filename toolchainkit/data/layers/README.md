# Built-in Configuration Layers

This directory contains the built-in layer library for ToolchainKit's composable configuration system.

## Overview

Configuration layers allow you to compose complex build configurations from reusable components. Instead of manually specifying every compiler flag, you stack layers to build your configuration.

**Example:**
```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: stdlib
      name: libc++
    - type: buildtype
      name: release
    - type: optimization
      name: lto-thin
```

## Layer Types

### Allocator Layers (`allocator/`)
Alternative memory allocators for performance tuning. See [allocator/README.md](allocator/README.md) for details.
- `default` - System default allocator
- `jemalloc` - Facebook's jemalloc
- `tcmalloc` - Google's tcmalloc
- `mimalloc` - Microsoft's mimalloc
- `snmalloc` - Microsoft's snmalloc
- `tbbmalloc` - Intel TBB malloc
- `hoard` - Hoard memory allocator
- `nedmalloc` - nedmalloc allocator

### Base Compiler Layers (`base/`)
Foundation compiler toolchains with default flags.

### Build Type Layers (`buildtype/`)
Optimization level and debug information.
- `debug` - No optimization, full debug info
- `release` - Maximum optimization
- `relwithdebinfo` - Optimized with debug info
- `minsizerel` - Minimum size

### Linker Layers (`linker/`)
Alternative linkers for faster linking. See [linker/README.md](linker/README.md) for details.

### Optimization Layers (`optimization/`)
Advanced optimization techniques (LTO, PGO, etc.).

### Platform Layers (`platform/`)
Platform-specific settings for target OS and architecture.

### Profiling Layers (`profiling/`)
Performance profiling and instrumentation. See [profiling/README.md](profiling/README.md) for details.
- `gprof` - GNU profiler
- `perf` - Linux perf integration
- `asan-profile` - AddressSanitizer profiling mode
- `instrument-functions` - Function instrumentation

### Sanitizer Layers (`sanitizer/`)
Runtime error detection tools (ASAN, TSAN, UBSAN, MSAN).

### Security Layers (`security/`)
Security hardening options. See [security/README.md](security/README.md) for details.
- `hardened` - Full security hardening
- `pie` - Position Independent Executable
- `relro-full` - Full RELRO
- `stack-protector-all` - Stack protector (all functions)
- `stack-protector-strong` - Stack protector (strong)
- `fortify` - FORTIFY_SOURCE=2
- `fortify-3` - FORTIFY_SOURCE=3 (GCC 12+)

### Standard Library Layers (`stdlib/`)
C++ standard library selection (libc++, libstdc++, MSVC).

## Layer Composition Rules

Layers are applied in strict order:

1. **Base Compiler** (required)
2. **Platform** (required)
3. **Standard Library** (optional)
4. **Build Type** (required)
5. **Optimizations** (optional, multiple allowed)
6. **Sanitizers** (optional, multiple allowed with restrictions)

Later layers can override settings from earlier layers.

## Common Configurations

### Development Build (Debug + ASAN)

```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: stdlib
      name: libc++
    - type: buildtype
      name: debug
    - type: sanitizer
      name: address
```

### Production Release (Release + LTO)

```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: stdlib
      name: libc++
    - type: buildtype
      name: release
    - type: optimization
      name: lto-thin
```

### Profiling Build

```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: stdlib
      name: libc++
    - type: buildtype
      name: relwithdebinfo
```

### Multi-Sanitizer Testing

```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: stdlib
      name: libc++
    - type: buildtype
      name: debug
    - type: sanitizer
      name: address
    - type: sanitizer
      name: undefined  # UBSAN can combine with ASAN
```

## Using Layers Programmatically

```python
from toolchainkit.config import LayerComposer

# Create composer
composer = LayerComposer()

# Define layers
layer_specs = [
    {"type": "base", "name": "clang-18"},
    {"type": "platform", "name": "linux-x64"},
    {"type": "buildtype", "name": "release"},
]

# Compose configuration
config = composer.compose(layer_specs)

# Access configuration
print(config.compile_flags)  # ["-O3", "-DNDEBUG", ...]
print(config.compiler)       # "clang"
print(config.platform)       # "linux-x64"
```

## Creating Custom Layers

You can create custom layers for project-specific needs:

1. Create layer file: `.toolchainkit/layers/{type}/{name}.yaml`
2. Follow the YAML schema (see design spec)
3. Use in your configuration

**Example Custom Layer:**
`.toolchainkit/layers/optimization/my-opt.yaml`:
```yaml
type: optimization
name: my-opt
description: "Project-specific optimizations"

flags:
  compile:
    - "-march=native"
    - "-mtune=native"

defines:
  - "CUSTOM_OPT=1"
```

**Usage:**
```yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: buildtype
      name: release
    - type: optimization
      name: my-opt  # Custom layer
```

## Variable Interpolation

Layers support variable interpolation using `{{variable}}` syntax:

**Available Variables:**
- `{{toolchain_root}}` - Path to toolchain installation
- `{{compiler_version}}` - Compiler version
- `{{platform}}` - Platform string
- `{{pgo_dir}}` - PGO profile directory
- `{{project_root}}` - Project root directory

**Example:**
```yaml
cmake_variables:
  CMAKE_CXX_COMPILER: "{{toolchain_root}}/bin/clang++"
```

## Layer Discovery

Layers are searched in order:
1. Project-local: `.toolchainkit/layers/{type}/{name}.yaml`
2. Global: `~/.toolchainkit/layers/{type}/{name}.yaml`
3. Built-in: `toolchainkit/data/layers/{type}/{name}.yaml` (this directory)

## See Also

- [Configuration Layers Design](../../../enhancement/config-layers.md) - Complete design specification
- [User Guide](../../../docs/user_guide_config_layers.md) - Detailed usage guide
- [Integration Guide](../../../docs/integration_guide_config_layers.md) - API reference

## Layer Directories

This directory contains the following layer categories:
- `allocator/` - Alternative memory allocators (8+ layers)
- `base/` - Base compiler configurations
- `buildtype/` - Build type configurations (4 layers)
- `linker/` - Alternative linkers
- `optimization/` - Advanced optimizations
- `platform/` - Platform-specific settings
- `profiling/` - Performance profiling tools (4+ layers)
- `sanitizer/` - Runtime sanitizers
- `security/` - Security hardening (7+ layers)
- `stdlib/` - C++ standard library selection

For detailed information about specific layer categories, see the README.md files in each subdirectory.
