# Filesystem Utilities

Cross-platform filesystem operations for safe file handling.

## Quick Start

```python
from toolchainkit.core.filesystem import (
    create_link, extract_archive, atomic_write,
    compute_file_hash, safe_delete
)
from pathlib import Path

# Create symlink/junction
create_link(Path("/source"), Path("/link"))

# Extract archive securely
extract_archive(Path("archive.tar.gz"), Path("/dest"))

# Atomic write (crash-safe)
atomic_write(Path("config.json"), '{"key": "value"}')

# Compute hash
hash_value = compute_file_hash(Path("file.txt"), algorithm="sha256")

# Safe delete with validation
safe_delete(Path("/path/to/delete"), required_parent=Path("/safe/root"))
```

## API

### Linking
- `create_link(source, link_path)` - Symlink (Unix) or junction (Windows)
- `is_link(path)` - Check if path is link
- `resolve_link(path)` - Get link target

### Archives
- `extract_archive(archive_path, dest_dir)` - Extract .zip, .tar.gz, .tar.xz, .7z
- Validates against directory traversal attacks

### Safe Operations
- `atomic_write(path, content)` - Write with temp file + rename
- `safe_delete(path, required_parent=None)` - Delete with validation
- `secure_temp_dir()` - Create temp dir with secure permissions

### Hashing
- `compute_file_hash(path, algorithm="sha256")` - Streaming hash computation
- Supports: sha256, sha512, md5, sha1

## Features

- **Security**: Path validation, directory traversal prevention
- **Atomicity**: Crash-safe writes
- **Cross-platform**: Handles Windows/Unix differences
- **Streaming**: Constant memory for large files

## Example

```python
# Download, verify, and extract toolchain
archive = Path("llvm-18.tar.gz")
dest = Path("/opt/llvm-18")

# Verify hash
expected_hash = "abc123..."
actual_hash = compute_file_hash(archive)
assert actual_hash == expected_hash, "Hash mismatch"

# Extract securely
extract_archive(archive, dest)

# Create link to current version
create_link(dest, Path("/opt/llvm"))
```

## Integration

Used by:
- Toolchain download and extraction
- CMake file generation (atomic writes)
- Project structure setup
- Cache management
