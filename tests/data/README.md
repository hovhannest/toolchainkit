# Test Data Directory

This directory contains test data files used across the ToolchainKit test suite.

## Directory Structure

```
tests/data/
├── README.md                   # This file
└── sample_configs/             # Sample configuration files
    ├── basic.yaml             # Basic single-toolchain config
    ├── multi_toolchain.yaml   # Multiple toolchains config
    └── full_featured.yaml     # Config with all features enabled
```

## Usage

### Sample Configurations

Sample configuration files can be used in tests to verify configuration parsing and validation:

```python
from pathlib import Path

def test_config_parsing():
    config_file = Path(__file__).parent / 'data' / 'sample_configs' / 'basic.yaml'
    # Use config_file in test...
```

## Adding New Test Data

When adding new test data files:

1. Place them in the appropriate subdirectory
2. Keep files small (prefer minimal test data)
3. Document the purpose in this README
4. Update relevant tests to use the new data

## Best Practices

- **Keep files small**: Test data should be minimal and focused
- **Use fixtures**: Prefer dynamically generated test data via fixtures when possible
- **Version control**: Commit test data files to git (use LFS for large files)
- **Platform independence**: Ensure test data works on Windows, Linux, and macOS
- **Documentation**: Document the purpose and structure of each test data file
