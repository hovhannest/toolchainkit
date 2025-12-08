# Doctor Command

> **✅ Status: Implemented (v0.1.0)**
> The `doctor` command is fully implemented. This document describes the current implementation.

Diagnose development environment and configuration issues.

## Quick Start

```bash
tkgen doctor
```

Output:
```
✓ Python 3.13.0 (OK)
✓ CMake 3.28.1 (OK)
✓ Configuration valid (toolchainkit.yaml)
✓ Toolchain installed (llvm-18.1.8-linux-x64)
⚠ sccache not found (optional - install for build caching)
✓ Ninja found (OK)

All critical checks passed. 1 warning.
```

## Health Checks

1. **Python Version**: ≥3.8 required
2. **CMake**: Installed and in PATH
3. **Configuration**: Valid toolchainkit.yaml
4. **Toolchain**: Installed and accessible
5. **Build Cache**: sccache/ccache (optional)
6. **Build Tool**: Ninja (optional, recommended)

## Exit Codes

- `0`: All critical checks passed
- `1`: One or more critical checks failed

## Options

```bash
tkgen doctor --quiet      # CI-friendly output
tkgen doctor --verbose    # Detailed diagnostics
tkgen doctor --config PATH # Use custom configuration file
```

## API

```python
from toolchainkit.cli.commands.doctor import run_doctor_checks

results = run_doctor_checks(project_root=Path("."))

for result in results:
    if result.passed:
        print(f"✓ {result.check_name}")
    else:
        print(f"✗ {result.check_name}: {result.message}")
```

## Example Output (Failure)

```
✓ Python 3.13.0 (OK)
✗ CMake not found
  → Install CMake 3.20 or later: https://cmake.org/download/
✗ Configuration invalid (toolchainkit.yaml)
  → Missing required field: toolchains
⚠ Ninja not found (optional)

Critical checks failed. Fix errors above.
```

## Integration

Used by: CI/CD pipelines, pre-build validation
