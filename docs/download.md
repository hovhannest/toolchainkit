# Download Manager

HTTP/HTTPS downloads with resumption, progress tracking, and verification.

## Quick Start

```python
from toolchainkit.core.download import download_file, DownloadProgress

def show_progress(progress: DownloadProgress):
    print(f"{progress.percentage:.1f}% - {progress.speed_bps/1024/1024:.1f} MB/s")

# Download with verification
download_file(
    url="https://example.com/file.tar.gz",
    dest=Path("file.tar.gz"),
    expected_sha256="abc123...",
    progress_callback=show_progress
)
```

## API

### Main Function

```python
def download_file(
    url: str,
    dest: Path,
    expected_sha256: Optional[str] = None,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    timeout: int = 30,
    max_retries: int = 3
) -> None:
    """Download file with verification and progress tracking."""
```

### DownloadProgress

```python
@dataclass
class DownloadProgress:
    bytes_downloaded: int
    total_bytes: int
    percentage: float
    speed_bps: float        # Bytes per second
    eta_seconds: float      # Estimated time remaining
```

## Features

- **Resumable**: Uses HTTP Range headers for interrupted downloads
- **Verification**: Streaming SHA-256/SHA-512/MD5 during download
- **Progress**: Real-time callbacks with speed and ETA
- **Retry**: Automatic retry with exponential backoff
- **Caching**: Skips download if file exists with correct hash
- **Streaming**: Constant memory usage for any file size

## Example

```python
# Download large toolchain with progress bar
from pathlib import Path

url = "https://github.com/llvm/llvm-project/releases/download/..."
dest = Path("~/.toolchainkit/downloads/llvm-18.1.8.tar.gz").expanduser()

def progress(p: DownloadProgress):
    bar = "=" * int(p.percentage / 2)
    print(f"\r[{bar:50s}] {p.percentage:.1f}%", end="")

try:
    download_file(url, dest, expected_sha256="...", progress_callback=progress)
    print("\n✓ Download complete")
except Exception as e:
    print(f"\n✗ Download failed: {e}")
```

## Integration

Used by:
- Toolchain downloader
- Python environment setup
- Build cache tool installation
