# Cross-Compilation

Cross-compile for Android, iOS, and Raspberry Pi.

## Quick Start

```python
from toolchainkit.cross.targets import AndroidTarget, IOSTarget

# Android
android = AndroidTarget(
    abi="arm64-v8a",
    api_level=30,
    ndk_path=Path("~/Android/Sdk/ndk/26.1.10909125")
)

cmake_vars = android.get_cmake_variables()

# iOS
ios = IOSTarget(
    platform="iphoneos",  # or "iphonesimulator"
    deployment_target="14.0"
)

cmake_vars = ios.get_cmake_variables()
```

## Supported Targets

### Android
- ABIs: arm64-v8a, armeabi-v7a, x86_64, x86
- NDK: Automatic detection or custom path
- API levels: 21+

### iOS
- Platforms: iphoneos (device), iphonesimulator
- Architectures: arm64, x86_64
- Deployment target: Configurable

### Raspberry Pi
- 32-bit: armv7l
- 64-bit: aarch64
- Sysroot: Custom cross-compilation sysroot

## Configuration

```yaml
# toolchainkit.yaml
cross:
  enabled: true
  target: android
  android:
    abi: arm64-v8a
    api_level: 30
    ndk_path: ~/Android/Sdk/ndk/26.1.10909125
```

## CMake Integration

```cmake
set(CMAKE_SYSTEM_NAME Android)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_ANDROID_NDK /path/to/ndk)
set(CMAKE_ANDROID_ARCH_ABI arm64-v8a)
set(CMAKE_ANDROID_NDK_API 30)
```

## Example

```bash
# Configure for Android ARM64
tkgen configure --cross android --abi arm64-v8a

# Build
cmake --build build
```
