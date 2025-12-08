# Platform Detection

Automatic detection of OS, architecture, and ABI for cross-platform builds.

## Quick Start

```python
from toolchainkit.core.platform import detect_platform

platform = detect_platform()
print(f"Platform: {platform.platform_string()}")  # e.g., linux-x64-glibc
print(f"OS: {platform.os}, Arch: {platform.architecture}, ABI: {platform.abi}")
```

## API

### PlatformInfo

```python
@dataclass
class PlatformInfo:
    os: str              # linux, windows, macos, android, ios
    arch: str            # x64, arm64, x86, arm, riscv64
    os_version: str      # OS version string (e.g., '10.0.19041', '22.04')
    distribution: str    # Linux distribution ('ubuntu', 'centos', etc.) or empty
    abi: str             # glibc-2.31, musl, msvc, macos-11.0

    def platform_string(self) -> str:
        """Returns platform string (e.g., 'linux-x64')"""

    def toolchain_suffix(self) -> str:
        """Returns toolchain suffix (e.g., 'linux-x86_64')"""
```

### Functions

- `detect_platform() -> PlatformInfo` - Detect current platform (cached)
- `is_supported_platform(platform: PlatformInfo) -> bool` - Check if platform is supported

## Platform Strings

Format: `{os}-{arch}[-{abi}]`

Examples:
- `linux-x64-glibc`
- `windows-x64-msvc`
- `macos-arm64`
- `android-arm64-v8a`

## Supported Platforms

| OS | Architectures | ABI |
|----|--------------|-----|
| Linux | x64, arm64, x86, arm | glibc, musl |
| Windows | x64, x86, arm64 | msvc |
| macOS | x64, arm64 | deployment target |
| Android | arm64-v8a, armeabi-v7a, x86_64, x86 | API level |
| iOS | arm64, x86_64 (simulator) | deployment target |

## Example

```python
platform = detect_platform()

if platform.os == "linux" and platform.arch == "x64":
    print("Linux x64 detected")

# Validate platform
from toolchainkit.core.platform import is_supported_platform
if not is_supported_platform(platform):
    raise RuntimeError(f"Unsupported platform: {platform.platform_string()}")
```

## Integration

Used by:
- Toolchain selection (`ToolchainDownloader`)
- CMake toolchain generation
- Package manager configuration
- Cross-compilation setup
