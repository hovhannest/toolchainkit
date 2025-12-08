# Concurrent Access Control

File-based locking for safe multi-process access to shared resources.

## Quick Start

```python
from toolchainkit.core.locking import LockManager, DownloadCoordinator
from pathlib import Path

lock_manager = LockManager()

# Lock registry for modifications
with lock_manager.registry_lock(timeout=30):
    # Modify shared registry
    registry.add_toolchain(...)

# Coordinate downloads across processes
coordinator = DownloadCoordinator(lock_manager)
toolchain_id = "llvm-18.1.8-linux-x64"
dest = Path("/opt/llvm-18.1.8")

with coordinator.coordinate_download(toolchain_id, dest) as should_download:
    if should_download:
        download_toolchain(...)  # This process downloads
    else:
        wait_for_download(...)   # Another process is downloading
```

## API

### LockManager

```python
class LockManager:
    def registry_lock(self, timeout: int = 30) -> LockContext:
        """Lock global registry for modifications"""

    def toolchain_lock(self, toolchain_id: str, timeout: int = 60) -> LockContext:
        """Lock specific toolchain installation"""

    def project_lock(self, project_root: Path, timeout: int = 10) -> LockContext:
        """Lock project-local state"""
```

### DownloadCoordinator

```python
class DownloadCoordinator:
    def coordinate_download(
        self,
        toolchain_id: str,
        dest_dir: Path
    ) -> ContextManager[bool]:
        """Returns True if this process should download"""
```

## Lock Types

| Lock | Purpose | Typical Timeout |
|------|---------|----------------|
| Registry | Global registry modifications | 30s |
| Toolchain | Toolchain installation | 60s |
| Project | Project state updates | 10s |

## Features

- **Cross-process**: Works across multiple ToolchainKit instances
- **Cross-platform**: Windows and Unix implementation
- **Timeout**: Prevents hanging on stale locks
- **Auto-cleanup**: Removes locks on process death
- **Wait-notify**: Efficient coordination pattern

## Example

```python
# Safe concurrent toolchain installation
lock_manager = LockManager()
coordinator = DownloadCoordinator(lock_manager)

def install_toolchain(name, version):
    toolchain_id = f"{name}-{version}"
    dest = Path(f"~/.toolchainkit/toolchains/{toolchain_id}").expanduser()

    # Coordinate with other processes
    with coordinator.coordinate_download(toolchain_id, dest) as should_download:
        if should_download:
            print(f"Installing {toolchain_id}...")
            download_and_extract(...)

            # Update registry (locked)
            with lock_manager.registry_lock():
                registry.add_entry(toolchain_id, dest)
        else:
            print(f"{toolchain_id} already being installed by another process")
```

## Integration

Used by:
- Toolchain download coordination
- Registry updates
- State file modifications
- Cache cleanup operations
