# Zig Compiler Plugin for ToolchainKit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A complete example plugin that adds [Zig compiler](https://ziglang.org/) support to ToolchainKit with **automatic toolchain download**.

## Overview

This plugin enables using Zig as a C/C++ compiler in your ToolchainKit projects. Zig provides excellent cross-compilation capabilities, bundled libc implementations, and LLVM-based optimizations.

### Features

- **Automatic Download**: Zig toolchain downloaded automatically (no manual install!)
- **C/C++ Compilation**: Compile C and C++ projects using `zig cc` and `zig c++`
- **Cross-Compilation**: Easy cross-compilation to many target platforms
- **Bundled libc**: No need for separate libc installations for most targets
- **LLVM Optimizations**: Modern optimization pipeline via LLVM
- **CMake Integration**: Seamless integration with CMake-based projects
- **Self-Contained**: Plugin includes its own toolchain registry (no core modifications)

## Requirements

- ToolchainKit >= 1.0.0
- **NO manual Zig installation required!** (plugin downloads automatically)

## Installation

### Option 1: Manual Installation

1. Copy this entire directory to your ToolchainKit plugins location:

```bash
# Linux/macOS
mkdir -p ~/.toolchainkit/plugins
cp -r zig-compiler ~/.toolchainkit/plugins/

# Windows
mkdir %USERPROFILE%\.toolchainkit\plugins
xcopy /E /I zig-compiler %USERPROFILE%\.toolchainkit\plugins\zig-compiler\
```

2. The plugin will be automatically discovered by ToolchainKit.

### Option 2: Project-Local Installation

Place the plugin in your project's plugins directory:

```
my-project/
├── toolchainkit.yaml
├── plugins/
│   └── zig-compiler/
│       ├── plugin.yaml
│       ├── zig_plugin.py
│       └── ...
└── ...
```

## Usage

### 1. Install Zig

Download and install Zig from [ziglang.org](https://ziglang.org/download/):

```bash
# Linux/macOS
wget https://ziglang.org/download/0.11.0/zig-linux-x86_64-0.11.0.tar.xz
tar -xf zig-linux-x86_64-0.11.0.tar.xz
sudo mv zig-linux-x86_64-0.11.0 /usr/local/zig

# Or use package manager
# macOS: brew install zig
# Ubuntu: snap install zig --classic --beta
```

### 2. Configure in toolchainkit.yaml

Add a Zig toolchain to your configuration:

```yaml
toolchains:
  - name: zig-toolchain
    type: zig                    # Uses zig-compiler plugin
    version: "0.11.0"
    root: /usr/local/zig         # Path to Zig installation
    build_types:
      - Debug
      - Release
```

### 3. Use with ToolchainKit

```python
from toolchainkit.plugins import PluginManager
from toolchainkit.cmake.compilers import CompilerConfigFactory

# Load plugins
manager = PluginManager()
manager.discover_and_load_all()

# Create compiler configuration
from toolchainkit.cmake.toolchain import ToolchainSpec

zig_toolchain = ToolchainSpec(
    name="zig-toolchain",
    type="zig",
    version="0.11.0",
    root="/usr/local/zig"
)

config = CompilerConfigFactory.create(zig_toolchain, "Release")
```

### 4. Cross-Compilation Example

Zig makes cross-compilation trivial:

```yaml
toolchains:
  - name: zig-cross-windows
    type: zig
    version: "0.11.0"
    root: /usr/local/zig
    target: x86_64-windows-gnu   # Cross-compile to Windows
    build_types:
      - Release

  - name: zig-cross-arm
    type: zig
    version: "0.11.0"
    root: /usr/local/zig
    target: aarch64-linux-gnu    # Cross-compile to ARM Linux
    build_types:
      - Release
```

## Configuration

The plugin uses a YAML configuration file (`compilers/zig.yaml`) that defines:

### Compiler Executables

```yaml
executables:
  c: "zig cc"
  cxx: "zig c++"
  ar: "zig ar"
  ranlib: "zig ranlib"
```

### Build Types

```yaml
flags:
  debug:
    - "-g"
    - "-O0"
  release:
    - "-O3"
    - "-DNDEBUG"
```

### Cross-Compilation Targets

```yaml
cross_compilation:
  targets:
    linux-x64: "-target x86_64-linux-gnu"
    windows-x64: "-target x86_64-windows-gnu"
    macos-arm64: "-target aarch64-macos"
```

## Development

### Running Tests

```bash
# Run plugin tests
pytest examples/plugins/zig-compiler/tests/

# Run with coverage
pytest examples/plugins/zig-compiler/tests/ \
    --cov=zig_plugin \
    --cov-report=term-missing
```

### Project Structure

```
zig-compiler/
├── plugin.yaml              # Plugin metadata
├── zig_plugin.py            # Plugin implementation
├── compilers/
│   └── zig.yaml             # Compiler configuration
├── tests/
│   └── test_zig_plugin.py   # Plugin tests
├── README.md                # This file
└── LICENSE                  # MIT license
```

## Troubleshooting

### Plugin Not Found

**Problem**: ToolchainKit doesn't find the plugin.

**Solution**:
- Ensure `plugin.yaml` exists in the plugin directory
- Check that the plugin is in a recognized location (~/.toolchainkit/plugins or project plugins/)
- Verify YAML syntax is valid

### Zig Not Detected

**Problem**: Plugin can't find Zig installation.

**Solution**:
- Ensure Zig is in your PATH: `which zig` (Linux/macOS) or `where zig` (Windows)
- Specify `root` explicitly in toolchainkit.yaml
- Check that the Zig executable is named `zig` (or `zig.exe` on Windows)

### Compiler Configuration Error

**Problem**: Error loading zig.yaml configuration.

**Solution**:
- Verify `compilers/zig.yaml` exists
- Check YAML syntax for errors
- Ensure all required fields are present

### Cross-Compilation Fails

**Problem**: Cross-compilation to target platform doesn't work.

**Solution**:
- Verify target string is correct (e.g., `x86_64-linux-gnu`)
- Check that Zig supports the target: `zig targets`
- Some targets may require additional libc installations

## Advanced Usage

### Custom Compiler Flags

Override flags in your toolchainkit.yaml:

```yaml
toolchains:
  - name: zig-custom
    type: zig
    version: "0.11.0"
    root: /usr/local/zig
    flags:
      release:
        - "-O3"
        - "-march=native"      # CPU-specific optimizations
        - "-DNDEBUG"
```

### Using with CMake

The plugin generates appropriate CMake toolchain files:

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(MyProject)

# ToolchainKit sets CMAKE_C_COMPILER to "zig cc"
# and CMAKE_CXX_COMPILER to "zig c++"

add_executable(myapp main.c)
```

### Sanitizer Support

Enable sanitizers for debugging:

```yaml
toolchains:
  - name: zig-asan
    type: zig
    version: "0.11.0"
    root: /usr/local/zig
    features:
      sanitizers:
        - address           # AddressSanitizer
        - undefined         # UndefinedBehaviorSanitizer
```

## Contributing

This is an example plugin demonstrating ToolchainKit's plugin API. Feel free to:

- Use as a template for your own compiler plugins
- Submit improvements via pull requests
- Report issues or suggestions

## Resources

- [Zig Website](https://ziglang.org/)
- [Zig Documentation](https://ziglang.org/documentation/master/)
- [ToolchainKit Documentation](https://github.com/toolchainkit/toolchainkit)
- [Plugin Development Guide](https://github.com/toolchainkit/toolchainkit/docs/plugins.md)

## License

MIT License - see LICENSE file for details.

This plugin is provided as an example and is not officially maintained by the Zig project.
