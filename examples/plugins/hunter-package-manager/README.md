# Hunter Package Manager Plugin

Example plugin adding Hunter package manager support to ToolchainKit.

## Features

- Hunter package manager integration
- Dependency management via hunter.cmake
- Cross-platform package resolution
- CMake integration

## Installation

```bash
cp -r hunter-package-manager ~/.toolchainkit/plugins/
```

## Usage

```yaml
# toolchainkit.yaml
packages:
  hunter:
    enabled: true
    gate_url: https://github.com/cpp-pm/hunter/archive/v0.24.18.tar.gz
    gate_sha1: 2c0f491fd0b80f7b09c3d5623e9e19fe1bc17244
```

## Files

- `plugin.yaml` - Metadata
- `hunter_plugin.py` - Implementation
- `tests/test_hunter_plugin.py` - Tests

## Implementation

Integrates Hunter's CMake-based dependency management with ToolchainKit.

See [Plugin Guide](../../../docs/plugins.md) for details.
