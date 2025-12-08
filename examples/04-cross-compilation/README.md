# Example 4: Cross-Platform and Cross-Compilation

This example demonstrates how to use ToolchainKit for cross-platform development and cross-compilation to mobile and embedded targets.

## Scenario

You're building a C++ library that needs to run on:
- Desktop platforms (Windows, Linux, macOS)
- Mobile platforms (Android, iOS)
- Embedded platforms (Raspberry Pi, ARM boards)

## Project Structure

```
04-cross-compilation/
├── CMakeLists.txt
├── toolchainkit.yaml          # Main configuration
├── toolchainkit-android.yaml  # Android-specific
├── toolchainkit-ios.yaml      # iOS-specific
├── toolchainkit-rpi.yaml      # Raspberry Pi
├── bootstrap.sh
├── bootstrap-android.sh       # Android bootstrap
├── bootstrap-ios.sh           # iOS bootstrap
├── src/
│   ├── platform/
│   │   ├── linux.cpp
│   │   ├── windows.cpp
│   │   ├── macos.cpp
│   │   └── android.cpp
│   └── core.cpp
└── README.md
```

## Multi-Platform Configuration

### Main Configuration

`toolchainkit.yaml`:

```yaml
version: "1.0"

project:
  name: cross-platform-lib
  version: "1.0.0"

# Default: native platform
toolchain:
  name: llvm-18
  stdlib: libc++

build:
  type: Release
  dir: build

bootstrap:
  toolchain: llvm-18
  build_type: Release
```

### Android Configuration

`toolchainkit-android.yaml`:

```yaml
version: "1.0"

project:
  name: cross-platform-lib
  version: "1.0.0"

# Android cross-compilation
toolchain:
  name: android-ndk-26
  target: android-arm64

cross_compilation:
  target: android-arm64
  android:
    ndk_version: "26.1.10909125"
    api_level: 24
    abi: arm64-v8a
    stl: c++_shared

build:
  type: Release
  dir: build-android

bootstrap:
  toolchain: android-ndk-26
  build_type: Release
  build_dir: build-android
```

### iOS Configuration

`toolchainkit-ios.yaml`:

```yaml
version: "1.0"

project:
  name: cross-platform-lib
  version: "1.0.0"

# iOS cross-compilation
toolchain:
  name: apple-clang-15
  target: ios-arm64

cross_compilation:
  target: ios-arm64
  ios:
    sdk: iphoneos
    deployment_target: "14.0"
    arch: arm64

build:
  type: Release
  dir: build-ios

bootstrap:
  toolchain: apple-clang-15
  build_type: Release
  build_dir: build-ios
```

### Raspberry Pi Configuration

`toolchainkit-rpi.yaml`:

```yaml
version: "1.0"

project:
  name: cross-platform-lib
  version: "1.0.0"

# Raspberry Pi 4 cross-compilation
toolchain:
  name: gcc-arm-linux-gnueabihf-12
  target: linux-armv7l

cross_compilation:
  target: linux-armv7l
  sysroot:
    enabled: true
    path: ~/.toolchainkit/sysroots/raspberry-pi-4
    url: "https://downloads.raspberrypi.org/..."

build:
  type: Release
  dir: build-rpi

bootstrap:
  toolchain: gcc-arm-linux-gnueabihf-12
  build_type: Release
  build_dir: build-rpi
```

## Usage Examples

### 1. Build for Native Platform

```bash
# Desktop (Linux/Windows/macOS)
tkgen bootstrap
cmake --build build
```

### 2. Build for Android

```bash
# Use Android-specific config
tkgen bootstrap --config toolchainkit-android.yaml

# Or generate Android bootstrap script
tkgen bootstrap --config toolchainkit-android.yaml --platform unix \
    > bootstrap-android.sh
chmod +x bootstrap-android.sh

# Run Android bootstrap
./bootstrap-android.sh

# Build
cmake --build build-android
```

### 3. Build for iOS

```bash
# macOS only
tkgen bootstrap --config toolchainkit-ios.yaml

# Generate iOS bootstrap
tkgen bootstrap --config toolchainkit-ios.yaml --platform unix \
    > bootstrap-ios.sh
chmod +x bootstrap-ios.sh

./bootstrap-ios.sh
cmake --build build-ios
```

### 4. Build for Raspberry Pi

```bash
# From any platform
tkgen bootstrap --config toolchainkit-rpi.yaml

./bootstrap-rpi.sh
cmake --build build-rpi

# Deploy to Raspberry Pi
scp -r build-rpi/myapp pi@raspberrypi.local:~/
```

### 5. Build All Platforms

```bash
#!/bin/bash
# build-all.sh

# Native
tkgen bootstrap
cmake --build build

# Android ARM64
tkgen bootstrap --config toolchainkit-android.yaml
cmake --build build-android

# iOS ARM64 (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    tkgen bootstrap --config toolchainkit-ios.yaml
    cmake --build build-ios
fi

# Raspberry Pi
tkgen bootstrap --config toolchainkit-rpi.yaml
cmake --build build-rpi

echo "All platforms built successfully!"
```

## CMakeLists.txt for Cross-Platform

```cmake
cmake_minimum_required(VERSION 3.20)
project(CrossPlatformLib VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Platform detection
if(ANDROID)
    set(PLATFORM_NAME "Android")
    set(PLATFORM_SRC src/platform/android.cpp)
elseif(IOS)
    set(PLATFORM_NAME "iOS")
    set(PLATFORM_SRC src/platform/ios.cpp)
elseif(WIN32)
    set(PLATFORM_NAME "Windows")
    set(PLATFORM_SRC src/platform/windows.cpp)
elseif(APPLE)
    set(PLATFORM_NAME "macOS")
    set(PLATFORM_SRC src/platform/macos.cpp)
else()
    set(PLATFORM_NAME "Linux")
    set(PLATFORM_SRC src/platform/linux.cpp)
endif()

message(STATUS "Building for platform: ${PLATFORM_NAME}")

# Library
add_library(mylib
    src/core.cpp
    ${PLATFORM_SRC}
)

target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Platform-specific link libraries
if(ANDROID)
    target_link_libraries(mylib PUBLIC log android)
elseif(IOS)
    target_link_libraries(mylib PUBLIC "-framework Foundation")
elseif(WIN32)
    target_link_libraries(mylib PUBLIC ws2_32)
else()
    target_link_libraries(mylib PUBLIC pthread dl)
endif()

# Executable (not for mobile)
if(NOT ANDROID AND NOT IOS)
    add_executable(myapp src/main.cpp)
    target_link_libraries(myapp PRIVATE mylib)
endif()

# Installation
install(TARGETS mylib
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
)
```

## CI/CD for Multiple Platforms

`.github/workflows/cross-compile.yml`:

```yaml
name: Cross-Platform Build

on: [push, pull_request]

jobs:
  native:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap and build
        run: |
          tkgen bootstrap
          cmake --build build

  android:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Cache toolchains
        uses: actions/cache@v4
        with:
          path: ~/.toolchainkit
          key: android-toolchainkit-${{ hashFiles('toolchainkit-android.yaml') }}

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap Android build
        run: tkgen bootstrap --config toolchainkit-android.yaml

      - name: Build for Android
        run: cmake --build build-android

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: android-build
          path: build-android/

  ios:
    runs-on: macos-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap iOS build
        run: tkgen bootstrap --config toolchainkit-ios.yaml

      - name: Build for iOS
        run: cmake --build build-ios

      - name: Upload iOS build
        uses: actions/upload-artifact@v4
        with:
          name: ios-build
          path: build-ios/

  raspberry-pi:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap Raspberry Pi build
        run: tkgen bootstrap --config toolchainkit-rpi.yaml

      - name: Build for Raspberry Pi
        run: cmake --build build-rpi

      - name: Upload Raspberry Pi binary
        uses: actions/upload-artifact@v4
        with:
          name: raspberry-pi-build
          path: build-rpi/myapp
```

## Platform-Specific Code Example

`src/platform/linux.cpp`:

```cpp
#include "platform.h"
#include <unistd.h>
#include <sys/utsname.h>

namespace platform {

std::string get_platform_name() {
    return "Linux";
}

std::string get_platform_version() {
    struct utsname info;
    if (uname(&info) == 0) {
        return info.release;
    }
    return "unknown";
}

int get_cpu_count() {
    return sysconf(_SC_NPROCESSORS_ONLN);
}

} // namespace platform
```

`src/platform/android.cpp`:

```cpp
#include "platform.h"
#include <android/log.h>
#include <sys/system_properties.h>

namespace platform {

std::string get_platform_name() {
    return "Android";
}

std::string get_platform_version() {
    char version[PROP_VALUE_MAX];
    __system_property_get("ro.build.version.release", version);
    return version;
}

void log(const std::string& message) {
    __android_log_print(ANDROID_LOG_INFO, "MyApp", "%s", message.c_str());
}

} // namespace platform
```

## Benefits of ToolchainKit for Cross-Compilation

✅ **Unified Workflow**: Same commands for all platforms
✅ **Automatic Toolchain Management**: Downloads correct cross-compilers
✅ **Sysroot Management**: Handles target system headers/libraries
✅ **Reproducible**: Lock files pin exact toolchain versions
✅ **CI-Friendly**: Easy to set up multi-platform CI
✅ **Developer-Friendly**: No manual cross-compiler setup

## Testing on Target Devices

### Android
```bash
# Build
tkgen bootstrap --config toolchainkit-android.yaml
cmake --build build-android

# Deploy to device
adb push build-android/libmylib.so /data/local/tmp/
adb shell /data/local/tmp/myapp
```

### iOS
```bash
# Build
tkgen bootstrap --config toolchainkit-ios.yaml
cmake --build build-ios

# Deploy (requires code signing)
ios-deploy --bundle build-ios/MyApp.app
```

### Raspberry Pi
```bash
# Build
tkgen bootstrap --config toolchainkit-rpi.yaml
cmake --build build-rpi

# Deploy via SSH
scp build-rpi/myapp pi@raspberrypi.local:~/
ssh pi@raspberrypi.local './myapp'
```

## Common Cross-Compilation Issues

### Issue: Missing target headers

**Solution**: Configure sysroot in toolchainkit.yaml:
```yaml
cross_compilation:
  sysroot:
    enabled: true
    path: ~/.toolchainkit/sysroots/target
```

### Issue: Wrong architecture

**Solution**: Specify exact target triple:
```yaml
toolchain:
  target: aarch64-linux-gnu
```

### Issue: Linking errors

**Solution**: Add target-specific libraries:
```cmake
if(TARGET_PLATFORM STREQUAL "android")
    target_link_libraries(mylib PUBLIC log android)
endif()
```

## See Also

- [Cross-Compilation Documentation](../../docs/cross_compilation.md)
- [Sysroot Management](../../docs/sysroot.md)
- [Android NDK Integration](../../docs/toolchains.md#android-ndk)
- [iOS Development](../../docs/toolchains.md#apple-toolchains)
