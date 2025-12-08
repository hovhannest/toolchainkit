# Compiler Definitions Directory

This directory contains YAML-based compiler configuration files that define how different C++ compilers behave in ToolchainKit.

## Structure

```
compilers/
├── README.md           # This file
├── clang.yaml          # Clang/LLVM compiler definition (Task 10)
├── gcc.yaml            # GCC compiler definition (Task 11)
├── msvc.yaml           # MSVC compiler definition (Task 11)
├── clang-18.yaml       # Version-specific configurations (optional)
└── ...                 # Additional compiler configurations
```

## Purpose

YAML compiler definitions replace Python `CompilerConfig` classes, making it easier to:
- Add new compilers without writing Python code
- Customize compiler flags and behavior
- Maintain compiler configurations
- See all compiler settings at a glance

## YAML Schema

Each compiler YAML file defines:
- **Identification**: name, display_name, type
- **Version Detection**: version_command, version_regex
- **Executables**: c, cxx, ar, ranlib
- **Flags**: debug, release, relwithdebinfo, minsizerel
- **Warnings**: all, error, pedantic, extra
- **Standards**: C and C++ standards with flag templates
- **Standard Libraries**: libc++, libstdc++, MSVC (optional)
- **Linkers**: lld, gold, mold, ld (optional)
- **Sanitizers**: address, undefined, thread, memory, etc. (optional)
- **Coverage**: Code coverage flags (optional)
- **LTO**: Link-time optimization (optional)
- **Platform Overrides**: Platform-specific settings (optional)
- **CMake Integration**: CMake variables (optional)
- **Composition**: Extend base configurations (optional)

See `enhancement/compiler-schema.md` for complete schema documentation.

## How Compiler YAMLs are Loaded

1. **Loading**: `YAMLCompilerLoader` reads YAML files from this directory
2. **Composition**: If `extends` is present, base config is loaded and merged
3. **Platform Overrides**: Platform-specific settings are applied if match found
4. **Variable Interpolation**: Placeholders like `{toolchain_root}` are replaced
5. **CMake Generation**: Configuration used to generate toolchain files

## Usage

### From Python API

```python
from toolchainkit.cmake.yaml_compiler import YAMLCompilerLoader
from pathlib import Path

# Initialize loader
loader = YAMLCompilerLoader(Path(__file__).parent.parent / "data" / "compilers")

# Load compiler config
clang = loader.load("clang", platform="linux")

# Get flags
flags = clang.get_flags_for_build_type("release")
print(flags)  # ['-O3', '-DNDEBUG']

# Get standard library flags
stdlib_flags = clang.get_stdlib_flags("libc++")
print(stdlib_flags['compile_flags'])  # ['-stdlib=libc++']
```

### From CLI

```bash
# Configure project with YAML compiler
tkgen configure --compiler clang

# Compilers are automatically loaded from YAML if available
# Falls back to Python CompilerConfig if YAML not found
```

## Adding a New Compiler

1. Create a new YAML file (e.g., `intel.yaml`)
2. Define all required fields (see schema documentation)
3. Add optional fields as needed
4. Test with `tkgen validate-compiler intel.yaml`
5. Use with `tkgen configure --compiler intel`

Example minimal compiler definition:

```yaml
name: "mycompiler"
display_name: "My Compiler"
type: "gcc"  # or "clang" or "msvc"

version_command: ["--version"]
version_regex: "version (\\d+\\.\\d+\\.\\d+)"

executables:
  c: "mycc"
  cxx: "myc++"
  ar: "ar"
  ranlib: "ranlib"

flags:
  debug: ["-g", "-O0"]
  release: ["-O3", "-DNDEBUG"]
  relwithdebinfo: ["-g", "-O2", "-DNDEBUG"]
  minsizerel: ["-Os", "-DNDEBUG"]

standards:
  c:
    default: "c17"
    supported: ["c11", "c17"]
    flag_template: "-std={standard}"
  cxx:
    default: "c++20"
    supported: ["c++17", "c++20"]
    flag_template: "-std={standard}"
```

## Available Compilers

- ✅ `clang.yaml` - Clang/LLVM configuration
- ✅ `gcc.yaml` - GCC configuration
- ✅ `msvc.yaml` - MSVC configuration

## References

- [YAML Compiler Schema Specification](../../enhancement/compiler-schema.md)
- [Example Clang YAML](../../enhancement/examples/clang-example.yaml)
- [Example GCC YAML](../../enhancement/examples/gcc-example.yaml)
- [Example MSVC YAML](../../enhancement/examples/msvc-example.yaml)
