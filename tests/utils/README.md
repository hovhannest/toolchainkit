# Test Utilities

Helper functions and mocks for tests.

## Modules

### `utils/helpers.py`
- `has_command()`, `has_cmake()`, `has_ninja()`
- `create_file_tree()`, `compare_files()`
- `run_command_safe()`, `get_command_version()`

### `utils/mocks.py`
- `mock_http_download()` - Mock HTTP responses
- `create_mock_registry()` - Mock toolchain registry
- `create_mock_state()` - Mock project state

## Usage

```python
from tests.utils.helpers import has_cmake, create_file_tree
from tests.utils.mocks import mock_http_download

if not has_cmake():
    pytest.skip("CMake required")

create_file_tree(temp_dir, {"file.txt": "content"})
```

See individual modules for complete API.
