# Platform and Compiler Compatibility Guide

This guide explains which compilers are supported on each platform in toolchainkit and how to handle incompatible configurations.

## Quick Reference: Supported Combinations

| Platform | Supported Compilers | NOT Supported |
|----------|-------------------|---------------|
| **Linux (x64, ARM64)** | GCC, LLVM/Clang | MSVC |
| **Windows (x64)** | LLVM/Clang, MSVC | GCC* |
| **macOS (x64, ARM64)** | LLVM/Clang (Apple Clang) | GCC*, MSVC |

\* GCC support for Windows (MinGW) and macOS may be added in future releases.

## Validation Behavior

### When Bootstrap Scripts Are Generated

ToolchainKit validates compatibility when you run:
```bash
tkgen bootstrap
```

**Result:**
- ✅ Valid configuration → Scripts generated successfully
- ❌ Invalid configuration → Error with helpful suggestions, no scripts generated
- ⚠️  Warnings → Scripts generated, but with warnings about potential issues

### When Configuration Is Loaded

When you initialize or load a configuration:
```bash
tkgen init
```

**Result:**
- ❌ Invalid toolchains → Errors shown during validation
- ⚠️  Potentially problematic configurations → Warnings displayed

### When Bootstrap Scripts Are Run

Even if a script is generated, runtime checks ensure compatibility:
```bash
./bootstrap.sh    # Linux/macOS
bootstrap.bat     # Windows
bootstrap.ps1     # Windows PowerShell
```

**Result:**
- Platform is detected automatically
- Script exits immediately if toolchain is incompatible with detected platform
- Clear error message explains the problem

## Common Scenarios

### Scenario 1: Using GCC on Windows

**Configuration:**
```yaml
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
```

**On Windows:**
```bash
$ tkgen bootstrap
ERROR: Incompatible configuration (compiler)
       Cannot generate bootstrap scripts for gcc on windows-x64:
       GCC is not supported on Windows in toolchainkit.
       Use LLVM/Clang or MSVC instead.
       MinGW/MinGW-w64 support may be added in future releases.

       Suggestion: Use one of the supported compilers for windows-x64: llvm, msvc
```

**Solution:**
```yaml
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  # OR
  - name: msvc-2022
    type: msvc
    version: latest
defaults:
  toolchain: llvm-18  # or msvc-2022
```

### Scenario 2: Using GCC on macOS

**Configuration:**
```yaml
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
```

**On macOS:**
```bash
$ tkgen bootstrap
ERROR: Incompatible configuration (compiler)
       Cannot generate bootstrap scripts for gcc on macos-arm64:
       GCC is not officially supported on macOS in toolchainkit.
       macOS uses Apple Clang as the primary compiler.
       Use LLVM/Clang instead.

       Suggestion: Use one of the supported compilers for macos-arm64: llvm
```

**Solution:**
```yaml
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
defaults:
  toolchain: llvm-18
```

### Scenario 3: Using MSVC on Linux

**Configuration:**
```yaml
version: 1
toolchains:
  - name: msvc-2022
    type: msvc
    version: latest
defaults:
  toolchain: msvc-2022
```

**On Linux:**
```bash
$ tkgen bootstrap
ERROR: Incompatible configuration (compiler)
       Cannot generate bootstrap scripts for msvc on linux-x64:
       MSVC is only available on Windows.
       For linux-x64, use LLVM/Clang or GCC instead.

       Suggestion: Use one of the supported compilers for linux-x64: llvm, gcc
```

**Solution:**
```yaml
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  # OR
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: llvm-18  # or gcc-13
```

### Scenario 4: Cross-Platform Configuration

**Goal:** Configuration that works on multiple platforms

**Solution:** Use LLVM/Clang (supported everywhere)
```yaml
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
defaults:
  toolchain: llvm-18
```

**Alternative:** Platform-specific defaults
```yaml
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  - name: gcc-13
    type: gcc
    version: 13.2.0
  - name: msvc-2022
    type: msvc
    version: latest

# Platform-specific defaults
defaults:
  linux: gcc-13
  macos: llvm-18
  windows: msvc-2022
```

## Error Messages Reference

### GCC on Windows
```
GCC is not supported on Windows in toolchainkit.
Use LLVM/Clang or MSVC instead.
MinGW/MinGW-w64 support may be added in future releases.
```

**What to do:**
1. Change compiler to `clang` or `msvc`
2. Update your toolchainkit.yaml
3. Run `tkgen bootstrap` again

### GCC on macOS
```
GCC is not officially supported on macOS in toolchainkit.
macOS uses Apple Clang as the primary compiler.
Use LLVM/Clang instead.
```

**What to do:**
1. Change compiler to `clang` (type: clang)
2. macOS comes with Apple Clang pre-installed
3. Update configuration and bootstrap again

### MSVC on Linux/macOS
```
MSVC is only available on Windows.
For <platform>, use LLVM/Clang or GCC instead.
```

**What to do:**
1. On Linux: Use GCC or Clang
2. On macOS: Use Clang (Apple Clang)
3. MSVC can only be used on Windows

## Runtime Script Errors

If you run a bootstrap script on the wrong platform:

### bootstrap.sh on macOS with GCC
```bash
$ ./bootstrap.sh
Bootstrapping my-project...

Detected platform: macos-arm64
ERROR: GCC is not supported on macOS in toolchainkit
       macOS uses Apple Clang as the primary compiler
       Please use LLVM/Clang toolchain instead

Bootstrap aborted due to incompatible configuration
```

### bootstrap.bat on Windows with GCC
```cmd
> bootstrap.bat
Bootstrapping my-project...

Detected platform: Windows
ERROR: GCC is not supported on Windows in toolchainkit
       Use LLVM/Clang or MSVC toolchain instead
       MinGW/MinGW-w64 support may be added in future releases
```

## Best Practices

### 1. Use LLVM/Clang for Cross-Platform Projects

LLVM/Clang is supported on all platforms:
```yaml
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
```

### 2. Check Platform Before Configuring

Detect your current platform:
```bash
uname -s    # Linux, Darwin (macOS), etc.
uname -m    # x86_64, arm64, etc.
```

### 3. Use Platform-Specific Configurations

For single-platform projects:
```yaml
# Linux-only project
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

# Windows-only project
toolchains:
  - name: msvc-2022
    type: msvc
    version: latest
```

### 4. Test Configurations Before CI/CD

Validate locally before pushing to CI:
```bash
tkgen bootstrap --dry-run
```

This shows what would be generated without creating files.

## FAQ

**Q: Can I use MinGW on Windows?**
A: Not currently. MinGW/MinGW-w64 support may be added in future releases. Use LLVM/Clang or MSVC instead.

**Q: Can I use GCC on macOS if I install it via Homebrew?**
A: While you can install GCC via Homebrew, toolchainkit doesn't officially support it due to complexity with macOS system libraries. Use Apple Clang instead.

**Q: What if I need different compilers on different platforms?**
A: Use platform-specific defaults in your configuration (see Scenario 4 above).

**Q: Can I bypass these checks?**
A: No. The checks prevent configurations that won't work. However, if you have a legitimate use case, please file an issue on GitHub.

**Q: Why does the validation happen in multiple places?**
A: Defense in depth: validation happens at config load, bootstrap generation, and script runtime to catch errors as early as possible.

## Related Documentation

- [config.md](config.md) - Full configuration reference
- [platform.md](platform.md) - Platform detection and capabilities
- [toolchains.md](toolchains.md) - Toolchain configuration guide
- [bootstrap.md](bootstrap.md) - Bootstrap script generation

## Reporting Issues

If you encounter a compatibility issue not covered here:
1. Check that you're using the latest version
2. Verify your configuration matches the supported combinations
3. File an issue with your configuration and error message
