# Upgrade Command

Upgrade toolchains and ToolchainKit itself.

## Quick Start

```bash
# Check for updates
tkgen upgrade --check

# Upgrade specific toolchain
tkgen upgrade --toolchain llvm-18

# Upgrade all toolchains
tkgen upgrade --all

# Self-upgrade ToolchainKit
tkgen upgrade --self
```

## API

```python
from toolchainkit.toolchain.upgrader import ToolchainUpgrader

upgrader = ToolchainUpgrader()

# Check for toolchain updates
available = upgrader.check_updates("llvm")
if available:
    print(f"Update available: {available['current']} → {available['latest']}")

# Upgrade toolchain
upgrader.upgrade_toolchain(
    toolchain_id="llvm-18.1.8",
    target_version="latest"
)
```

## Upgrade Strategy

1. Check metadata registry for newer versions
2. Download new version
3. Verify integrity
4. Update registry entry
5. Preserve project references
6. Optionally remove old version (if unreferenced)

## Options

```bash
tkgen upgrade --toolchain NAME [--version VER]  # Specific toolchain
tkgen upgrade --all                              # All installed toolchains
tkgen upgrade --self                             # ToolchainKit itself
tkgen upgrade --check                            # Check only, don't upgrade
tkgen upgrade --cleanup                          # Remove old versions after upgrade
```

## Example

```bash
$ tkgen upgrade --toolchain llvm
Checking for updates...
Current: llvm-18.1.8
Latest:  llvm-18.1.9

Downloading llvm-18.1.9-linux-x64... [========] 100%
Verifying... ✓
Installing...✓
Updating registry... ✓

✓ Upgraded llvm-18.1.8 → llvm-18.1.9

Projects using this toolchain will automatically use the new version.
```

## Safety

- **Reference Counting**: Never removes toolchains in use by projects
- **Atomic Operations**: Upgrade succeeds or fails completely (no partial state)
- **Rollback**: Old version kept until new version verified

## Integration

Used by: CI/CD pipelines, maintenance scripts
