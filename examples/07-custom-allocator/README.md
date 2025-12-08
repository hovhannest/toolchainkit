# Example 07: Custom Allocator Integration

## Overview

This example demonstrates how to integrate a custom memory allocator (like jemalloc, tcmalloc, or mimalloc) into an existing CMake-based C++ project using ToolchainKit. Custom allocators can significantly improve performance for memory-intensive applications.

## Use Case

You have an existing C++ application that:
- Makes frequent memory allocations
- Could benefit from a more efficient allocator than the system default
- Needs to switch between different allocators for testing/benchmarking
- Requires consistent allocator configuration across development and production

## What This Example Shows

- Adding a custom allocator (mimalloc) to an existing project via package manager
- Modifying CMakeLists.txt to link against the custom allocator
- Configuring ToolchainKit to manage allocator dependencies
- Testing allocator integration with a simple benchmark
- Switching between different allocators using configuration

## Project Structure

```
07-custom-allocator/
├── README.md                    # This file
├── toolchainkit.yaml           # ToolchainKit configuration
├── conanfile.txt               # Conan dependencies (includes mimalloc)
├── CMakeLists.txt              # Modified to support custom allocators
└── src/
    ├── main.cpp                # Application with memory allocation patterns
    └── benchmark.cpp           # Simple allocator benchmark
```

## Getting Started

### 1. Initialize ToolchainKit

```bash
# Generate bootstrap script (assuming CLI support)
tkgen bootstrap --output setup.sh

# Run the bootstrap script
./setup.sh

# Or using Python API
python -c "from toolchainkit.bootstrap import BootstrapGenerator; BootstrapGenerator().generate('.')"
```

### 2. Configure and Build

```bash
# Configure with CMake presets (includes allocator setup)
cmake --preset default

# Build the project
cmake --build --preset default

# Run the application
./build/allocator_demo
```

### 3. Test Different Allocators

The project supports multiple allocators via configuration:

```bash
# Use mimalloc (default in this example)
cmake --preset default -DUSE_ALLOCATOR=mimalloc
cmake --build --preset default

# Use jemalloc
cmake --preset default -DUSE_ALLOCATOR=jemalloc
cmake --build --preset default

# Use system allocator
cmake --preset default -DUSE_ALLOCATOR=system
cmake --build --preset default
```

## What Changed in CMakeLists.txt

The existing `CMakeLists.txt` was modified with minimal changes:

```cmake
# Added option to select allocator
option(USE_ALLOCATOR "Custom allocator to use (mimalloc, jemalloc, tcmalloc, system)" "mimalloc")

# Added allocator detection and linking
if(USE_ALLOCATOR STREQUAL "mimalloc")
    find_package(mimalloc REQUIRED)
    target_link_libraries(${PROJECT_NAME} PRIVATE mimalloc-static)
    target_compile_definitions(${PROJECT_NAME} PRIVATE USE_MIMALLOC=1)
elseif(USE_ALLOCATOR STREQUAL "jemalloc")
    find_package(jemalloc REQUIRED)
    target_link_libraries(${PROJECT_NAME} PRIVATE jemalloc::jemalloc)
    target_compile_definitions(${PROJECT_NAME} PRIVATE USE_JEMALLOC=1)
elseif(USE_ALLOCATOR STREQUAL "tcmalloc")
    find_package(gperftools REQUIRED)
    target_link_libraries(${PROJECT_NAME} PRIVATE gperftools::tcmalloc)
    target_compile_definitions(${PROJECT_NAME} PRIVATE USE_TCMALLOC=1)
endif()
```

These changes are **non-invasive** and maintain backward compatibility with the original project.

## Configuration Files

### toolchainkit.yaml

Defines the project configuration, including compiler settings and allocator options:

```yaml
project:
  name: allocator-demo
  version: 1.0.0

toolchain:
  compiler: gcc
  version: "11"

package_manager:
  type: conan

allocator:
  default: mimalloc
  options:
    - mimalloc
    - jemalloc
    - tcmalloc
    - system
```

### conanfile.txt

Lists dependencies including the custom allocator:

```ini
[requires]
mimalloc/2.1.2

[generators]
CMakeDeps
CMakeToolchain
```

## Benefits

### Performance Improvements
- **mimalloc**: 10-30% faster allocation performance in many workloads
- **jemalloc**: Excellent for multi-threaded applications
- **tcmalloc**: Good for high-concurrency scenarios

### Development Workflow
- **Easy switching**: Change allocators via configuration, not code modifications
- **Reproducible**: Same allocator across all environments via lockfile
- **Testable**: Benchmark different allocators to find the best fit

### CI/CD Integration
- **Automated testing**: Test with multiple allocators in CI pipeline
- **Performance regression detection**: Track allocator performance over time
- **Platform-specific optimization**: Use different allocators per platform

## Code Example

The application demonstrates allocator usage:

```cpp
#include <iostream>
#include <vector>
#include <chrono>

#ifdef USE_MIMALLOC
#include <mimalloc.h>
#endif

void benchmark_allocations(size_t count, size_t size) {
    auto start = std::chrono::high_resolution_clock::now();

    std::vector<void*> ptrs;
    ptrs.reserve(count);

    // Allocate
    for (size_t i = 0; i < count; ++i) {
        ptrs.push_back(malloc(size));
    }

    // Deallocate
    for (auto ptr : ptrs) {
        free(ptr);
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    std::cout << "Allocated and freed " << count << " blocks of " << size
              << " bytes in " << duration.count() << " μs\n";
}

int main() {
    #ifdef USE_MIMALLOC
    std::cout << "Using mimalloc allocator\n";
    #elif defined(USE_JEMALLOC)
    std::cout << "Using jemalloc allocator\n";
    #elif defined(USE_TCMALLOC)
    std::cout << "Using tcmalloc allocator\n";
    #else
    std::cout << "Using system allocator\n";
    #endif

    benchmark_allocations(10000, 64);
    benchmark_allocations(10000, 1024);
    benchmark_allocations(10000, 4096);

    return 0;
}
```

## Advanced Usage

### Per-Target Allocator Configuration

You can configure different allocators for different targets:

```cmake
# Use mimalloc for the main application
target_link_libraries(app PRIVATE mimalloc-static)

# Use jemalloc for tests (better debugging)
target_link_libraries(tests PRIVATE jemalloc::jemalloc)
```

### Runtime Allocator Selection

Some allocators support runtime configuration:

```cpp
#ifdef USE_MIMALLOC
#include <mimalloc.h>

// Configure mimalloc options
mi_option_set(mi_option_show_stats, 1);
mi_option_set(mi_option_verbose, 1);
#endif
```

### CI/CD Pipeline Integration

Test with multiple allocators in your CI:

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    allocator: [mimalloc, jemalloc, system]

steps:
  - name: Build with ${{ matrix.allocator }}
    run: |
      ./setup.sh
      cmake --preset default -DUSE_ALLOCATOR=${{ matrix.allocator }}
      cmake --build --preset default

  - name: Run benchmarks
    run: ./build/allocator_demo
```

## Troubleshooting

### Allocator Not Found

If CMake can't find the allocator package:
```bash
# Ensure Conan installed the package
conan install . --build=missing

# Check that find_package can locate it
cmake --preset default --debug-find-pkg=mimalloc
```

### Linking Errors

If you get undefined references:
```bash
# Verify the allocator library is linked
cmake --build --preset default --verbose

# Check that the allocator is in the link command
```

### Performance Issues

If allocator performance is worse than expected:
- Check for debug builds (use Release mode)
- Verify allocator-specific optimizations are enabled
- Profile to ensure allocator is actually being used

## Key Takeaways

1. **Minimal Changes**: Adding a custom allocator requires only a few lines in CMakeLists.txt
2. **Package Manager Integration**: ToolchainKit handles allocator dependency installation
3. **Flexible Configuration**: Switch allocators via CMake options or ToolchainKit config
4. **Performance Gains**: Custom allocators can significantly improve application performance
5. **Reproducible**: Lockfile ensures consistent allocator versions across environments

## Next Steps

- Benchmark your application with different allocators to find the best fit
- Add allocator configuration to your CI/CD pipeline
- Explore allocator-specific tuning options for your workload
- Consider per-module allocator strategies for complex applications

## Related Examples

- **02-existing-cmake**: Migrating existing CMake projects
- **03-cicd-integration**: CI/CD pipeline setup with ToolchainKit
- **06-reproducible-builds**: Ensuring consistent builds with lockfiles
