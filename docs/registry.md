# Shared Cache Registry

Track toolchain installations with reference counting across projects.

## Quick Start

```python
from toolchainkit.core.cache_registry import ToolchainCacheRegistry
from pathlib import Path

registry = ToolchainCacheRegistry()

# Add toolchain entry
registry.add_entry(
    toolchain_id="llvm-18.1.8-linux-x64",
    toolchain_dir=Path("/opt/llvm-18.1.8"),
    metadata={"version": "18.1.8", "type": "llvm"}
)

# Increment reference (project starts using toolchain)
registry.increment_reference("llvm-18.1.8-linux-x64", Path("/my/project"))

# Query
entry = registry.get_entry("llvm-18.1.8-linux-x64")
print(f"Used by {entry.reference_count} projects")

# Decrement reference (project stops using toolchain)
registry.decrement_reference("llvm-18.1.8-linux-x64", Path("/my/project"))

# Find unused
unused = registry.find_unused_toolchains(min_age_days=30)
```

## API

### ToolchainCacheRegistry

```python
class ToolchainCacheRegistry:
    def add_entry(self, toolchain_id: str, toolchain_dir: Path, metadata: Dict) -> None
    def get_entry(self, toolchain_id: str) -> RegistryEntry
    def remove_entry(self, toolchain_id: str) -> None
    def increment_reference(self, toolchain_id: str, project_root: Path) -> None
    def decrement_reference(self, toolchain_id: str, project_root: Path) -> None
    def find_unused_toolchains(self, min_age_days: int = 30) -> List[str]
    def get_cache_stats(self) -> Dict[str, Any]
```

### RegistryEntry

```python
@dataclass
class RegistryEntry:
    toolchain_id: str
    toolchain_dir: Path
    metadata: Dict
    reference_count: int
    referenced_by: List[Path]
    installed_at: datetime
    last_used: datetime
```

## Features

- **Reference Counting**: Tracks which projects use each toolchain
- **Thread-Safe**: File locking for concurrent access
- **JSON Storage**: Human-readable format at `~/.toolchainkit/registry.json`
- **Atomic Updates**: Crash-safe operations
- **Statistics**: Cache size, unused toolchains, free space

## Example

```python
# Toolchain lifecycle
registry = ToolchainCacheRegistry()

# 1. Install toolchain
registry.add_entry(
    "gcc-13.2.0-linux-x64",
    Path("/opt/gcc-13.2.0"),
    {"version": "13.2.0", "type": "gcc", "size_mb": 450}
)

# 2. Projects start using it
registry.increment_reference("gcc-13.2.0-linux-x64", Path("/proj1"))
registry.increment_reference("gcc-13.2.0-linux-x64", Path("/proj2"))

# 3. Check usage
entry = registry.get_entry("gcc-13.2.0-linux-x64")
print(f"References: {entry.reference_count}")  # 2
print(f"Projects: {entry.referenced_by}")      # [/proj1, /proj2]

# 4. Projects stop using it
registry.decrement_reference("gcc-13.2.0-linux-x64", Path("/proj1"))
registry.decrement_reference("gcc-13.2.0-linux-x64", Path("/proj2"))

# 5. Cleanup unused (if ref_count == 0 and age > 30 days)
if "gcc-13.2.0-linux-x64" in registry.find_unused_toolchains(30):
    registry.remove_entry("gcc-13.2.0-linux-x64")
```

## Integration

Used by:
- Toolchain downloader
- Cleanup operations
- Project initialization
- Upgrade command
