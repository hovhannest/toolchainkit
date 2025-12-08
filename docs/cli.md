# CLI Reference

> **⚠️ Status: In Development**
> The CLI (`tkgen` command) is currently under development. Most features described in this document are planned for v0.2.0+.
> For v0.1.0, please use the Python API directly. See the main [README.md](../README.md) for current usage examples.

ToolchainKit provides the `tkgen` command-line tool for managing toolchains, configuring projects, and diagnosing issues.

## Installation

After installing ToolchainKit, the `tkgen` command is available:

```bash
pip install toolchainkit
tkgen --version
```

## Global Options

Available for all commands:

```bash
tkgen [OPTIONS] COMMAND [ARGS]

Options:
  --version              Show version and exit
  -v, --verbose          Enable verbose output
  -q, --quiet            Enable minimal output (errors only)
  --config PATH          Path to configuration file (default: ./toolchainkit.yaml)
  --project-root PATH    Project root directory (default: current directory)
```

## Commands

### init

Initialize ToolchainKit in an existing CMake project.

```bash
tkgen init [OPTIONS]

Options:
  --auto-detect          Auto-detect package manager and configuration
  --toolchain NAME       Initial toolchain (e.g., llvm-18, gcc-13, msvc-latest)
  --minimal              Create minimal configuration
  --force                Force reinitialization if already initialized
```

**Example:**
```bash
# Auto-detect configuration
tkgen init --auto-detect

# Initialize with specific toolchain
tkgen init --toolchain llvm-18

# Force reinitialization
tkgen init --force --toolchain gcc-13
```

Creates `toolchainkit.yaml` with detected or specified configuration.

---

### configure

Configure toolchain and run CMake configuration.

```bash
tkgen configure [OPTIONS]

Options:
  --toolchain NAME       Toolchain to use (e.g., llvm-18, gcc-13) [REQUIRED]
  --stdlib STD           C++ standard library (libc++, libstdc++, msvc)
  --build-type TYPE      CMake build type (Debug, Release, RelWithDebInfo, MinSizeRel)
                         Default: Release
  --build-dir DIR        CMake build directory (default: build)
  --cache TOOL           Enable build caching (sccache, ccache, none)
  --target TARGET        Cross-compilation target (e.g., android-arm64, ios-arm64)
  --clean                Clean build directory before configuring
```

**Examples:**
```bash
# Basic configuration
tkgen configure --toolchain llvm-18

# With specific build type and caching
tkgen configure --toolchain gcc-13 --build-type Debug --cache sccache

# Cross-compilation
tkgen configure --toolchain llvm-18 --target android-arm64 --stdlib libc++

# Clean reconfiguration
tkgen configure --toolchain llvm-18 --clean
```

Generates:
- CMake toolchain file in `.toolchainkit/cmake/`
- CMake configuration in `build/`
- Updated `.toolchainkit/state.json`

---

### cleanup

Clean up unused toolchains from shared cache.

```bash
tkgen cleanup [OPTIONS]

Options:
  --dry-run              Show what would be removed without removing
  --unused               Remove toolchains with no project references
  --older-than DAYS      Remove toolchains unused for N days
  --toolchain NAME       Remove specific toolchain
```

**Examples:**
```bash
# Dry run to see what would be removed
tkgen cleanup --dry-run --unused

# Remove toolchains unused for 90+ days
tkgen cleanup --older-than 90

# Remove specific toolchain
tkgen cleanup --toolchain llvm-17.0.0
```

---

### upgrade

Upgrade toolchains to latest versions.

```bash
tkgen upgrade [OPTIONS]

Options:
  --toolchain NAME       Upgrade specific toolchain
  --all                  Upgrade all installed toolchains
  --check                Check for available updates without upgrading
  --version VER          Upgrade to specific version
```

**Examples:**
```bash
# Check for updates
tkgen upgrade --check

# Upgrade specific toolchain
tkgen upgrade --toolchain llvm-18

# Upgrade all toolchains
tkgen upgrade --all

# Upgrade to specific version
tkgen upgrade --toolchain gcc --version 14.1.0
```

See [Upgrade Documentation](upgrade.md) for more details.

---

### verify

Verify toolchain integrity and functionality.

```bash
tkgen verify [OPTIONS]

Options:
  --full                 Full verification including checksums and compile tests
```

**Examples:**
```bash
# Basic verification
tkgen verify

# Full verification with compile tests
tkgen verify --full
```

Checks:
- File presence
- Symlink validity
- Binary executability
- Version matching (with `--full`)
- Compile test (with `--full`)

See [Verification Documentation](verification.md) for more details.

---

### doctor

Diagnose development environment and suggest fixes.

```bash
tkgen doctor [OPTIONS]

Options:
  --fix                  Attempt to fix issues automatically (not yet implemented)
```

**Example:**
```bash
# Run diagnostics
tkgen doctor

# Verbose diagnostics
tkgen doctor --verbose

# CI-friendly output
tkgen doctor --quiet
```

Checks:
- ToolchainKit installation
- Python environment
- CMake availability
- Toolchain configuration
- Build cache setup
- Project configuration
- Lock file consistency

See [Doctor Documentation](doctor.md) for more details.

---

## Environment Variables

ToolchainKit respects the following environment variables:

- `TOOLCHAINKIT_CACHE_DIR` - Override global cache directory
- `TOOLCHAINKIT_PLUGIN_PATH` - Additional plugin search paths (colon/semicolon separated)
- `SCCACHE_DIR` - sccache cache directory
- `CCACHE_DIR` - ccache cache directory

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Toolchain not found
- `4` - Verification failed
- `5` - CMake configuration failed

## See Also

- [Configuration](config.md) - Configuration file format
- [Toolchain Management](toolchains.md) - Toolchain operations
- [Doctor](doctor.md) - Environment diagnostics
- [Upgrade](upgrade.md) - Upgrade procedures
