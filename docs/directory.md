# Directory Structure

Global cache and project-local directory management.

## Structure

```
~/.toolchainkit/          # Global cache (shared across projects)
├── toolchains/           # Downloaded toolchains
│   ├── llvm-18.1.8-linux-x64/
│   └── gcc-13.2.0-linux-x64/
├── python/               # Embedded Python 3.11
├── downloads/            # Cached downloads
├── lock/                 # Lock files for concurrency
└── registry.json         # Toolchain metadata

<project>/.toolchainkit/  # Project-local (gitignored)
├── cmake/                # Generated CMake files
│   └── toolchain.cmake
├── packages/             # Package manager caches
│   ├── conan/
│   └── vcpkg/
├── cache/                # Build cache (sccache/ccache)
└── state.json            # Current configuration state
```

## API

```python
from toolchainkit.core.directory import (
    get_global_cache_dir,
    get_project_local_dir,
    create_directory_structure
)

# Get directories
global_cache = get_global_cache_dir()
project_local = get_project_local_dir(Path("/my/project"))

# Initialize structure
paths = create_directory_structure(Path("/my/project"))
print(paths["global_cache"])
print(paths["project_local"])
```

## Global Cache

**Location:**
- Linux/macOS: `~/.toolchainkit/`
- Windows: `%USERPROFILE%\.toolchainkit\`

**Contents:**
- Toolchains shared across all projects
- Embedded Python interpreter
- Download cache
- Shared registry

## Project-Local

**Location:** `<project-root>/.toolchainkit/`

**Contents:**
- Generated CMake toolchain files
- Package manager caches
- Build cache directory
- Project state

**Gitignore:** Automatically added to `.git ignore`

## Cleanup

```python
from toolchainkit.toolchain.cleanup import ToolchainCleanupManager

manager = ToolchainCleanupManager()

# List unused toolchains (age > 30 days)
unused = manager.list_unused(min_age_days=30)

# Remove specific toolchain
result = manager.cleanup(toolchain_name="llvm-18.1.8", dry_run=False)

# Auto-cleanup old toolchains
result = manager.auto_cleanup(dry_run=False)
```

## Benefits

- **Space Efficient**: Shared toolchains via symlinks/junctions
- **Isolated**: Project-local state doesn't affect other projects
- **Portable**: Projects work across machines with same toolchain IDs
