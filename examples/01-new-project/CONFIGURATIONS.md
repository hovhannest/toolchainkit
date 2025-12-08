# Configuration Files Reference

This directory contains 28 different ToolchainKit configurations for testing various scenarios.

## Platform Compatibility

| Config | Toolchain | Build Tool | Special Features | Linux | macOS | Windows |
|--------|-----------|------------|------------------|:-----:|:-----:|:-------:|
| toolchainkit.yaml | LLVM 18 | Ninja | Default, Conan | ✅ | ✅ | ✅ |
| toolchainkit_1.yaml | LLVM 18 | Ninja | Basic LLVM | ✅ | ✅ | ✅ |
| toolchainkit_2.yaml | GCC 13 | Make | Basic GCC | ✅ | ✅ | ❌ |
| toolchainkit_3.yaml | MSVC | MSBuild | Basic MSVC | ❌ | ❌ | ✅ |
| toolchainkit_4.yaml | MSVC | MSBuild | MSVC Alt | ❌ | ❌ | ✅ |
| toolchainkit_5.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_6.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_7.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_8.yaml | LLVM 18 | Ninja | jemalloc | ✅ | ✅ | ⚠️ |
| toolchainkit_9.yaml | LLVM 18 | Ninja | mimalloc | ✅ | ✅ | ✅ |
| toolchainkit_10.yaml | LLVM 18 | Ninja | tbbmalloc | ✅ | ✅ | ✅ |
| toolchainkit_11.yaml | LLVM 18 | Ninja | tcmalloc | ✅ | ✅ | ❌ |
| toolchainkit_12.yaml | LLVM 18 | Ninja | snmalloc | ✅ | ✅ | ✅ |
| toolchainkit_13.yaml | LLVM 18 | Ninja | AddressSanitizer | ✅ | ✅ | ⚠️ |
| toolchainkit_14.yaml | LLVM 18 | Ninja | MemorySanitizer | ✅ | ❌ | ❌ |
| toolchainkit_15.yaml | LLVM 18 | Ninja | ThreadSanitizer | ✅ | ✅ | ❌ |
| toolchainkit_16.yaml | LLVM 18 | Ninja | UBSanitizer | ✅ | ✅ | ⚠️ |
| toolchainkit_17.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_18.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_19.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_20.yaml | LLVM 18 | Ninja | mimalloc | ✅ | ✅ | ✅ |
| toolchainkit_21.yaml | GCC 13 | Make | GCC + jemalloc | ✅ | ✅ | ❌ |
| toolchainkit_22.yaml | MSVC | MSBuild | MSVC + tbbmalloc | ❌ | ❌ | ✅ |
| toolchainkit_23.yaml | LLVM 18 | Ninja | LLVM + jemalloc | ✅ | ✅ | ⚠️ |
| toolchainkit_24.yaml | GCC 13 | Ninja | GCC + tcmalloc | ✅ | ✅ | ❌ |
| toolchainkit_25.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_26.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |
| toolchainkit_27.yaml | LLVM 18 | Ninja | LLVM Variant | ✅ | ✅ | ✅ |

Legend:
- ✅ Fully supported
- ⚠️ Partial support or platform-specific limitations
- ❌ Not supported on this platform

## Notes

### Windows
- **GCC**: Not supported (no MinGW support yet)
- **Make**: Not available (use Ninja or MSBuild)
- **tcmalloc**: Not supported (use mimalloc instead)
- **MemorySanitizer**: Not supported
- **ThreadSanitizer**: Not supported
- **jemalloc**: Link-time only
- **Sanitizers**: MSVC support is version-dependent

### macOS
- **MSVC**: Not available
- **MemorySanitizer**: Not supported on Apple Silicon

### Linux
- **MSVC**: Not available (except with Wine, not recommended)

## Testing on Windows

When testing on Windows, the following configurations will:

**Work fully**:
- toolchainkit.yaml (LLVM + Ninja)
- toolchainkit_1, 5, 6, 7, 17, 18, 19, 25, 26, 27 (LLVM + Ninja)
- toolchainkit_3, 4, 22 (MSVC + MSBuild)
- toolchainkit_9, 10, 12, 20 (LLVM + allocators compatible with Windows)

**Fail or fallback to system compiler**:
- toolchainkit_2, 21, 24 (GCC - not available on Windows)
- toolchainkit_11 (tcmalloc - not available on Windows)
- toolchainkit_14 (MemorySanitizer - not available on Windows)
- toolchainkit_15 (ThreadSanitizer - not available on Windows)

**May work with limitations**:
- toolchainkit_8, 23 (jemalloc - link-time only on Windows)
- toolchainkit_13, 16 (Sanitizers - depends on MSVC version)

## Recommended Testing Approach

1. **On Windows**: Test LLVM and MSVC configs
2. **On Linux**: Test all configs
3. **On macOS**: Test LLVM configs

This ensures comprehensive coverage across all supported platforms.
