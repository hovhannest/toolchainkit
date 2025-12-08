# Test Fixtures

Reusable pytest fixtures for tests.

## Available Fixtures

### Toolchains (`fixtures/toolchains.py`)
- `mock_llvm_toolchain` - Mock LLVM toolchain
- `mock_gcc_toolchain` - Mock GCC toolchain
- `mock_msvc_toolchain` - Mock MSVC toolchain

### Projects (`fixtures/projects.py`)
- `minimal_project` - Basic CMake project
- `library_project` - Library with tests
- `conan_project` - Project with Conan dependencies

### Directories (`fixtures/directories.py`)
- `global_cache` - Mock global cache
- `project_local` - Mock project .toolchainkit/
- `complete_workspace` - Full workspace fixture

## Usage

```python
def test_something(mock_llvm_toolchain, minimal_project):
    # Use fixtures
    pass
```

See `tests/fixtures/README.md` (this file) for complete list.
