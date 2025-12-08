# State Management

Track project state and detect configuration changes.

## Quick Start

```python
from toolchainkit.core.state import StateManager
from pathlib import Path

state_mgr = StateManager(project_root=Path("/my/project"))

# Save state after configuration
state_mgr.update_state(
    active_toolchain="llvm-18.1.8",
    config_hash="abc123",
    build_dir=Path("build")
)

# Check if reconfiguration needed
if state_mgr.needs_reconfiguration(new_config_hash):
    print("Configuration changed - reconfigure required")
    run_configure()
```

## State File Location

`.toolchainkit/state.json` in project root

## State Contents

```json
{
  "version": "1.0",
  "active_toolchain": "llvm-18.1.8-linux-x64",
  "config_hash": "abc123...",
  "build_directory": "build",
  "bootstrapped_at": "2025-11-24T10:00:00Z",
  "configured_at": "2025-11-24T10:05:00Z",
  "cmake_configured": true,
  "package_manager": "conan",
  "cache_enabled": true
}
```

## API

```python
class StateManager:
    def load_state(self) -> State
    def update_state(self, **kwargs) -> None
    def needs_reconfiguration(self, config_hash: str) -> bool
    def mark_configured(self) -> None
    def get_active_toolchain(self) -> str
```

## Change Detection

```python
# Detect configuration changes
current_hash = compute_config_hash(config)

if state_mgr.needs_reconfiguration(current_hash):
    # Config changed - regenerate CMake files
    regenerate_cmake_toolchain()
    state_mgr.mark_configured()
```

## Features

- **Change Detection**: Automatic reconfiguration triggers
- **Atomic Updates**: Crash-safe state modifications
- **Validation**: Checks toolchain exists, build dir valid
- **Timestamps**: Track bootstrap and configuration times

## Integration

Used by:
- `tkgen configure` - Update state after configuration
- `tkgen reconfigure` - Check if reconfiguration needed
- IDE integrations - Query active toolchain
