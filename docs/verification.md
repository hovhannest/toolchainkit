# Hash Verification

File integrity verification with multiple hash algorithms.

## Quick Start

```python
from toolchainkit.core.verification import verify_file_hash, compute_hash

# Verify single file
verify_file_hash(
    file_path=Path("llvm-18.1.8.tar.gz"),
    expected_hash="abc123...",
    algorithm="sha256"
)

# Compute hash
actual_hash = compute_hash(Path("file.tar.gz"), algorithm="sha256")
print(f"SHA-256: {actual_hash}")

# Verify from hash file (SHA256SUMS format)
from toolchainkit.core.verification import verify_from_hashfile

verify_from_hashfile(
    hashfile_path=Path("SHA256SUMS"),
    files_dir=Path("downloads/")
)
```

## API

```python
def verify_file_hash(
    file_path: Path,
    expected_hash: str,
    algorithm: str = "sha256"
) -> bool:
    """Verify file hash. Raises on mismatch."""

def compute_hash(
    file_path: Path,
    algorithm: str = "sha256"
) -> str:
    """Compute file hash (streaming)."""

def verify_from_hashfile(
    hashfile_path: Path,
    files_dir: Path
) -> Dict[Path, bool]:
    """Verify multiple files from hash file."""
```

## Supported Algorithms

- `sha256` (recommended)
- `sha512`
- `sha1`
- `md5`

## Features

- **Streaming**: Constant memory for any file size
- **Timing-safe**: Constant-time comparison prevents timing attacks
- **Batch verification**: Multiple files from hash file
- **Progress tracking**: For large files
- **GNU format**: Compatible with `sha256sum` output

## Example

```python
# Download and verify toolchain
url = "https://github.com/llvm/.../llvm-18.1.8.tar.gz"
dest = Path("llvm-18.1.8.tar.gz")
expected_sha256 = "e2e96558..."

# Download
download_file(url, dest)

# Verify integrity
try:
    verify_file_hash(dest, expected_sha256, algorithm="sha256")
    print("✓ Verification passed")
except ValueError as e:
    print(f"✗ Verification failed: {e}")
    dest.unlink()  # Delete corrupted file
```

## Hash File Format

```text
# SHA256SUMS
e2e96558... llvm-18.1.8-linux-x64.tar.gz
f3a45678... gcc-13.2.0-linux-x64.tar.xz
```

## Integration

Used by:
- Download manager (streaming verification)
- Toolchain downloader
- Lock file verification
