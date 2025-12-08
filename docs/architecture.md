# Architecture

ToolchainKit system architecture and design principles.

## Three-Layer Python Architecture

```
System Python (Layer 3)
  ↓ isolated from
Bootstrap Python (Layer 1) - Future: minimal embedded Python
  ↓ manages
Managed Python (Layer 2) - Python 3.11 in ~/.toolchainkit/python/
```

### Layers

**Layer 1: Bootstrap (Future)**
- Minimal embedded Python (~5-10 MB)
- Self-extracting executable
- Manages Layer 2

**Layer 2: Managed Python (Current)**
- Full Python 3.11 environment
- Downloaded to `~/.toolchainkit/python/`
- Used for toolchain scripts and package managers
- Hermetic and versioned

**Layer 3: System Python (Ignored)**
- User's installed Python (may not exist)
- ToolchainKit doesn't depend on it

## Component Architecture

```
┌─────────────────────────────────────────┐
│           CLI Commands                   │
│  (init, configure, doctor, upgrade)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Core Components                  │
│  • Platform Detection                    │
│  • Directory Management                  │
│  • Unified Download Manager              │
│  • Lock Manager                          │
│  • Cache Registry                        │
│  • Unified Exception Hierarchy (new)    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Toolchain Management               │
│  • Downloader                            │
│  • Metadata Registry                     │
│  • Verifier                              │
│  • System Detector                       │
│  • Cleanup                               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       CMake Integration                  │
│  • Toolchain Generator                   │
│  • YAML Compiler Configuration           │
│  • Backend Selection                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Build Acceleration                 │
│  • Package Managers (Conan/vcpkg)       │
│  • Build Cache (sccache/ccache)         │
│  • Cross-Compilation                     │
└──────────────────────────────────────────┘
```

## Design Principles

1. **Hermetic Builds**: All dependencies versioned and cached
2. **Zero System Dependencies**: Works without pre-installed tools
3. **Platform Agnostic**: Same API across Windows/Linux/macOS
4. **Concurrent-Safe**: File locking for multi-process safety
5. **Fail-Fast**: Early validation with clear error messages
6. **Extensible**: Plugin system for custom toolchains
7. **Single Responsibility**: Each module has one clear purpose
8. **Unified APIs**: Consistent patterns across modules
9. **Metadata-Driven**: Configuration via data files, not code

## Directory Layout

```
~/.toolchainkit/             # Global shared cache
├── toolchains/              # Downloaded toolchains
├── python/                  # Managed Python 3.11
├── downloads/               # Download cache
├── lock/                    # Lock files
└── registry.json            # Cache metadata

<project>/.toolchainkit/     # Project-local (gitignored)
├── cmake/toolchain.cmake    # Generated CMake config
├── packages/                # Conan/vcpkg cache
├── cache/                   # Build cache
└── state.json               # Current state
```

## Module Structure

```
toolchainkit/
├── cli/                     # Command-line interface
│   ├── commands/            # Individual commands
│   └── utils.py             # Shared CLI utilities
├── core/                    # Core utilities
│   ├── cache_registry.py   # Cache management
│   ├── directory.py         # Directory structure
│   ├── download.py          # Unified downloads
│   ├── exceptions.py        # Exception hierarchy
│   ├── filesystem.py        # File operations
│   ├── locking.py           # Concurrent access control
│   ├── platform.py          # Platform detection
│   └── verification.py      # Checksum verification
├── toolchain/               # Toolchain management
│   ├── downloader.py        # Toolchain download logic
│   ├── metadata_registry.py # Metadata management
│   ├── verifier.py          # Installation verification
│   ├── system_detector.py   # System toolchain detection
│   └── cleanup.py           # Cleanup unused toolchains
├── cmake/                   # CMake integration
│   ├── generator.py         # Toolchain file generation
│   └── backends.py          # Build backend selection
├── packages/                # Package manager integration
│   ├── conan.py             # Conan support
│   └── vcpkg.py             # vcpkg support
├── config/                  # Configuration management
│   └── layers.py            # Configuration layer system
└── data/                    # Toolchain and tool metadata
    └── toolchains/          # Modular metadata (v2.0)
```

## Data Flow

### Configuration Flow (v2.0)

```
CLI Command
    ↓
CLI Utils (load config, validate)
    ↓
Core Platform Detection
    ↓
Metadata Registry (lookup toolchain)
    ↓
Downloader (fetch if needed)
    ↓
Cache Registry (register installation)
    ↓
CMake Generator (create toolchain file)
    ↓
Package Manager Setup (if configured)
    ↓
Ready to Build
```

### Key Operations

1. **Bootstrap**: Initialize directories, verify Python
2. **Configure**: Parse config → Download toolchain → Generate CMake
3. **Build**: CMake reads toolchain → Compiler builds → Cache stores
4. **Clean**: Remove unused toolchains, clear cache
5. **Doctor**: Diagnose environment and toolchain setup

## Concurrency Model

- **File-based locking**: Cross-process coordination
- **Registry lock**: Protects global registry modifications
- **Toolchain lock**: Prevents duplicate downloads
- **Project lock**: Protects project state
- **Wait-notify**: Efficient coordination pattern

## Error Handling (v2.0)

### Exception Hierarchy

```
ToolchainKitError (base)
├── ConfigurationError
├── ToolchainError
│   ├── ToolchainNotFoundError
│   └── ToolchainDownloadError
├── PackageManagerError
└── BuildBackendError
```

All exceptions in `core.exceptions` for consistent error handling.

### Error Recovery

- **Automatic retry**: Downloads retry with exponential backoff
- **Lock timeout**: Prevents deadlocks in concurrent scenarios
- **Clear messages**: All errors include context and suggestions
- **Doctor command**: Diagnose and suggest fixes

## Extension Points

- **CompilerPlugin**: Add custom compilers (Zig, Rust, etc.)
- **PackageManagerPlugin**: Add package managers (Hunter, CPM)
- **Custom backends**: Add build systems beyond Ninja/Make/MSBuild
- **Configuration hooks**: Extend via YAML configuration

See [Plugins](plugins.md) for details.
