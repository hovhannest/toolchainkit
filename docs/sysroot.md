# Sysroot Management

Manage system root filesystems for cross-compilation targets.

## Overview

A sysroot is a directory tree containing the target system's headers, libraries, and other files needed for cross-compilation. ToolchainKit provides automated sysroot download, verification, and caching.

## Quick Start

```python
from toolchainkit.cross.sysroot import SysrootManager, SysrootSpec
from toolchainkit.core.directory import get_global_cache_dir

# Initialize manager
cache_dir = get_global_cache_dir()
manager = SysrootManager(cache_dir)

# Define sysroot
spec = SysrootSpec(
    target='android-arm64',
    version='r25c',
    url='https://dl.google.com/android/repository/android-ndk-r25c-linux.zip',
    hash='sha256:abcd1234...',
    extract_path='toolchains/llvm/prebuilt/linux-x86_64/sysroot'
)

# Download and extract
sysroot_path = manager.download_sysroot(spec)
print(f"Sysroot installed at: {sysroot_path}")
```

## SysrootManager API

```python
class SysrootManager:
    """Manage sysroots for cross-compilation."""

    def __init__(self, cache_dir: Path, downloader=None):
        """
        Initialize sysroot manager.

        Args:
            cache_dir: Root cache directory (typically ~/.toolchainkit)
            downloader: Optional downloader instance
        """

    def download_sysroot(
        self,
        spec: SysrootSpec,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        force: bool = False,
    ) -> Path:
        """
        Download and extract sysroot.

        Args:
            spec: Sysroot specification
            progress_callback: Optional progress callback (bytes_downloaded, total_bytes)
            force: Force re-download even if cached

        Returns:
            Path to extracted sysroot directory

        Raises:
            SysrootDownloadError: Download failed
            SysrootVerificationError: Hash verification failed
            SysrootExtractionError: Extraction failed
        """

    def get_sysroot_path(self, target: str, version: str) -> Path:
        """
        Get path to cached sysroot.

        Args:
            target: Target platform identifier
            version: Sysroot version

        Returns:
            Path to sysroot directory (may not exist)
        """

    def is_cached(self, spec: SysrootSpec) -> bool:
        """
        Check if sysroot is already cached.

        Args:
            spec: Sysroot specification

        Returns:
            True if sysroot exists in cache
        """

    def list_sysroots(self) -> List[Tuple[str, str]]:
        """
        List all cached sysroots.

        Returns:
            List of (target, version) tuples
        """

    def remove_sysroot(self, target: str, version: str) -> bool:
        """
        Remove cached sysroot.

        Args:
            target: Target platform identifier
            version: Sysroot version

        Returns:
            True if removed, False if not found
        """

    def get_cache_size(self) -> int:
        """
        Get total size of sysroot cache in bytes.

        Returns:
            Cache size in bytes
        """

    def clear_cache(self) -> int:
        """
        Clear all cached sysroots.

        Returns:
            Number of sysroots removed
        """
```

## SysrootSpec

```python
@dataclass
class SysrootSpec:
    """Sysroot specification."""

    target: str              # Target platform (e.g., 'android-arm64')
    version: str             # Version string (e.g., 'r25c')
    url: str                 # Download URL
    hash: str                # SHA-256 hash for verification
    extract_path: Optional[str] = None  # Path within archive to extract
```

## Common Sysroot Targets

### Android NDK

```python
# Android ARM64
spec = SysrootSpec(
    target='android-arm64',
    version='r25c',
    url='https://dl.google.com/android/repository/android-ndk-r25c-linux.zip',
    hash='sha256:...',
    extract_path='toolchains/llvm/prebuilt/linux-x86_64/sysroot'
)

# Android ARMv7
spec = SysrootSpec(
    target='android-armv7',
    version='r25c',
    url='https://dl.google.com/android/repository/android-ndk-r25c-linux.zip',
    hash='sha256:...',
    extract_path='toolchains/llvm/prebuilt/linux-x86_64/sysroot'
)
```

### Raspberry Pi

```python
# Raspberry Pi 4 (ARM64)
spec = SysrootSpec(
    target='raspberry-pi-aarch64',
    version='bullseye',
    url='https://downloads.raspberrypi.org/raspios_arm64/root.tar.xz',
    hash='sha256:...',
)

# Raspberry Pi 3 (ARMv7)
spec = SysrootSpec(
    target='raspberry-pi-armv7',
    version='bullseye',
    url='https://downloads.raspberrypi.org/raspios_armhf/root.tar.xz',
    hash='sha256:...',
)
```

### Custom Embedded Linux

```python
spec = SysrootSpec(
    target='custom-arm-linux',
    version='1.0.0',
    url='https://internal.example.com/sysroots/custom-arm-linux-1.0.0.tar.gz',
    hash='sha256:...',
)
```

## Progress Tracking

```python
def progress_callback(downloaded: int, total: int):
    """Track download progress."""
    percent = (downloaded / total) * 100 if total > 0 else 0
    print(f"\rDownloading: {percent:.1f}% ({downloaded}/{total} bytes)", end='')

sysroot_path = manager.download_sysroot(
    spec=spec,
    progress_callback=progress_callback
)
```

## Cache Management

```python
# List all cached sysroots
sysroots = manager.list_sysroots()
for target, version in sysroots:
    print(f"{target} {version}")

# Check cache size
size_mb = manager.get_cache_size() / (1024 * 1024)
print(f"Cache size: {size_mb:.1f} MB")

# Remove specific sysroot
removed = manager.remove_sysroot('android-arm64', 'r25c')
if removed:
    print("Sysroot removed")

# Clear entire cache
count = manager.clear_cache()
print(f"Removed {count} sysroots")
```

## Integration with Cross-Compilation

```python
from toolchainkit.cross.targets import CrossCompileConfigurator
from toolchainkit.cross.sysroot import SysrootManager, SysrootSpec

# Setup sysroot
manager = SysrootManager(cache_dir)
spec = SysrootSpec(
    target='android-arm64',
    version='r25c',
    url='https://...',
    hash='sha256:...'
)
sysroot_path = manager.download_sysroot(spec)

# Configure cross-compilation
target = CrossCompileTarget(
    target_os='android',
    target_arch='arm64',
    abi='arm64-v8a',
    sysroot=sysroot_path,
    toolchain_prefix='aarch64-linux-android-',
)

configurator = CrossCompileConfigurator()
cmake_vars = configurator.configure(target)
```

## Error Handling

```python
from toolchainkit.cross.sysroot import (
    SysrootDownloadError,
    SysrootVerificationError,
    SysrootExtractionError
)

try:
    sysroot_path = manager.download_sysroot(spec)
except SysrootDownloadError as e:
    print(f"Download failed: {e}")
except SysrootVerificationError as e:
    print(f"Verification failed: {e}")
except SysrootExtractionError as e:
    print(f"Extraction failed: {e}")
```

## Verification

Sysroots are verified using SHA-256 hashes:

```python
# Hash is verified automatically during download
spec = SysrootSpec(
    target='android-arm64',
    version='r25c',
    url='https://...',
    hash='sha256:abcd1234...'  # Verified against downloaded file
)

# Download will fail if hash doesn't match
sysroot_path = manager.download_sysroot(spec)
```

## Complete Example

```python
from pathlib import Path
from toolchainkit.cross.sysroot import SysrootManager, SysrootSpec
from toolchainkit.cross.targets import CrossCompileTarget, CrossCompileConfigurator
from toolchainkit.core.directory import get_global_cache_dir

def setup_android_cross_compilation():
    """Setup Android cross-compilation with sysroot."""

    # Initialize sysroot manager
    cache_dir = get_global_cache_dir()
    manager = SysrootManager(cache_dir)

    # Android ARM64 sysroot
    spec = SysrootSpec(
        target='android-arm64',
        version='r25c',
        url='https://dl.google.com/android/repository/android-ndk-r25c-linux.zip',
        hash='sha256:...',
        extract_path='toolchains/llvm/prebuilt/linux-x86_64/sysroot'
    )

    # Download and extract (cached if already present)
    print("Setting up Android sysroot...")
    sysroot_path = manager.download_sysroot(
        spec=spec,
        progress_callback=lambda d, t: print(f"\rProgress: {d}/{t} bytes", end='')
    )
    print(f"\nSysroot ready: {sysroot_path}")

    # Configure cross-compilation
    target = CrossCompileTarget(
        target_os='android',
        target_arch='arm64',
        abi='arm64-v8a',
        api_level=29,
        sysroot=sysroot_path,
        toolchain_prefix='aarch64-linux-android29-',
    )

    configurator = CrossCompileConfigurator()
    cmake_vars = configurator.configure(target)

    print("CMake variables for cross-compilation:")
    for key, value in cmake_vars.items():
        print(f"  {key} = {value}")

    return cmake_vars

if __name__ == "__main__":
    setup_android_cross_compilation()
```

## Cache Location

Sysroots are cached at:
- Linux/macOS: `~/.toolchainkit/sysroots/`
- Windows: `%USERPROFILE%\.toolchainkit\sysroots\`

Directory structure:
```
~/.toolchainkit/sysroots/
├── downloads/               # Downloaded archives
│   └── android-ndk-r25c-linux.zip
├── android-arm64-r25c/      # Extracted sysroots
├── android-armv7-r25c/
└── raspberry-pi-aarch64-bullseye/
```

## See Also

- [Cross-Compilation](cross_compilation.md) - Cross-compilation guide
- [Configuration](config.md) - Configuration file format
- [Download Manager](download.md) - Download infrastructure
- [Verification](verification.md) - Hash verification
