# Linker Layer Definitions

This directory contains YAML-based linker configuration files that define different linkers available for use with compilers.

## Structure

```
layers/linker/
├── README.md           # This file
├── lld.yaml            # LLVM linker (lld)
├── gold.yaml           # GNU Gold linker
├── mold.yaml           # Modern linker (mold)
└── ld.yaml             # Default GNU linker
```

## Purpose

Linker layers allow users to independently select linkers without being tied to compiler defaults:

```bash
# Use Clang with mold linker (much faster than default)
tkgen configure --layers base/clang-18,linker/mold

# Use GCC with lld linker
tkgen configure --layers base/gcc-13,linker/lld
```

## Available Linkers

### lld (LLVM Linker)
- **Speed**: 2-3x faster than GNU ld
- **Platforms**: Linux, Windows, macOS
- **Best For**: Clang toolchains
- **File**: `lld.yaml`

### gold (GNU Gold Linker)
- **Speed**: 1.5-2x faster than GNU ld
- **Platforms**: Linux only
- **Best For**: GCC toolchains with LTO
- **File**: `gold.yaml`

### mold (Modern Linker)
- **Speed**: 5-10x faster than GNU ld
- **Platforms**: Linux only
- **Best For**: Large projects, fast iteration
- **File**: `mold.yaml`

### ld (GNU Linker)
- **Speed**: Baseline (slowest)
- **Platforms**: Linux, macOS
- **Best For**: Maximum compatibility, fallback
- **File**: `ld.yaml`

## Performance Comparison

For a large C++ project (Chromium-scale):

| Linker | Link Time | Speed vs ld |
|--------|-----------|-------------|
| mold   | 2 seconds | 10x faster  |
| lld    | 6 seconds | 3x faster   |
| gold   | 10 seconds| 2x faster   |
| ld     | 20 seconds| 1x (baseline)|

## Usage

### Automatic Selection

ToolchainKit automatically selects the best available linker:

1. User-specified linker (if provided)
2. mold (if available on Linux)
3. lld (if compiler is Clang)
4. gold (if compiler is GCC on Linux)
5. ld (fallback)

### Manual Selection

```bash
# Explicitly select mold
tkgen configure --linker mold

# Or use layer syntax
tkgen configure --layers base/clang-18,linker/mold
```

### From Python API

```python
from toolchainkit.cmake.toolchain_generator import CMakeToolchainGenerator

generator = CMakeToolchainGenerator()
generator.set_linker("mold")
```

## Linker YAML Schema

Each linker YAML file defines:

```yaml
name: "linker_name"
display_name: "Human-Readable Name"
type: "linker"
description: |
  Multi-line description

flag: "-fuse-ld=linker"  # Compiler flag to select this linker
supported_platforms: ["linux", "windows", "macos"]
supported_compilers: ["gcc", "clang"]

linker_flags:
  performance: [...]
  debug: [...]
  optimization: [...]

platform_overrides:
  windows:
    executable: "different-name.exe"

performance:
  speed: "fast|moderate|slow|very_fast"
  memory_usage: "low|moderate|high"
  parallel: true|false

features:
  thin_lto: true|false
  full_lto: true|false
  gc_sections: true|false
  # etc.
```

## Installation Instructions

### mold
```bash
# Ubuntu/Debian
sudo apt install mold

# Fedora
sudo dnf install mold

# Arch Linux
sudo pacman -S mold

# From source
git clone https://github.com/rui314/mold.git
cd mold && make -j$(nproc) && sudo make install
```

### lld
```bash
# Usually comes with LLVM/Clang
sudo apt install lld      # Ubuntu/Debian
sudo dnf install lld      # Fedora
sudo pacman -S lld        # Arch Linux
```

### gold
```bash
# Usually included in binutils-gold
sudo apt install binutils-gold  # Ubuntu/Debian
sudo dnf install binutils-gold  # Fedora
```

### ld
```bash
# Already installed (part of binutils)
```

## When to Use Each Linker

**Development Builds (Fast Iteration)**:
- Use **mold** - Fastest link times
- Fallback to **lld** if mold unavailable

**Production Builds (Maximum Optimization)**:
- Use **lld** - Good speed + full feature support
- Use **gold** for GCC with LTO

**Compatibility (When Others Fail)**:
- Use **ld** - Most compatible, works everywhere

**Cross-Compilation**:
- Use **lld** - Best cross-platform support

## Troubleshooting

### mold Not Found
```bash
# Check if mold is installed
which mold

# If not, install it (see Installation Instructions above)
```

### Linker Errors with LTO
```bash
# Ensure you're using a linker that supports LTO
# lld: Full LTO support
# gold: LTO support with plugin
# mold: LTO support
# ld: Limited LTO support
```

### Windows Linker Issues
```bash
# On Windows, use lld (included with Clang)
# MSVC uses link.exe (automatic)
```

## References

- [Linker YAML Examples](../../../enhancement/examples/)
- [Compiler Schema Documentation](../../../enhancement/compiler-schema.md)
- [mold Project](https://github.com/rui314/mold)
- [LLVM lld Documentation](https://lld.llvm.org/)
- [GNU Gold Documentation](https://www.gnu.org/software/binutils/)
