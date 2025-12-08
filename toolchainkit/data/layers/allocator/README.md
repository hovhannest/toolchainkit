# Memory Allocator Layers

This directory contains configuration layers for different memory allocators. Memory allocators can have a significant impact on application performance (10-30% improvement is common), especially for multi-threaded applications.

## Available Allocators

### Production-Ready Allocators

#### jemalloc
- **Best For**: Multi-threaded applications, low fragmentation
- **Performance**: 10-30% improvement over system malloc
- **Platforms**: Linux, macOS, Windows
- **Features**: Thread-local caching, profiling support
- **Installation**:
  - Ubuntu/Debian: `sudo apt install libjemalloc-dev`
  - macOS: `brew install jemalloc`
  - Fedora: `sudo dnf install jemalloc-devel`

#### tcmalloc (Google)
- **Best For**: Multi-threaded performance, profiling
- **Performance**: 10-25% improvement
- **Platforms**: Linux, macOS (limited Windows support)
- **Features**: Heap profiler, leak checker
- **Installation**:
  - Ubuntu/Debian: `sudo apt install libgoogle-perftools-dev`
  - macOS: `brew install gperftools`

#### mimalloc (Microsoft)
- **Best For**: Security, high performance
- **Performance**: 15-35% improvement
- **Platforms**: Linux, macOS, Windows
- **Features**: Free-list sharding (security), very low fragmentation
- **Installation**:
  - Ubuntu/Debian: `sudo apt install libmimalloc-dev`
  - macOS: `brew install mimalloc`

#### tbbmalloc (Intel TBB)
- **Best For**: Applications using Intel TBB, NUMA systems
- **Performance**: 10-30% improvement
- **Platforms**: Linux, macOS, Windows
- **Features**: NUMA-aware, excellent scalability
- **Installation**:
  - Ubuntu/Debian: `sudo apt install libtbb-dev`
  - macOS: `brew install tbb`

### Specialized Allocators

#### snmalloc (Microsoft Research)
- **Best For**: Concurrent workloads, cache efficiency
- **Performance**: 10-25% improvement
- **Platforms**: Linux, macOS, Windows
- **Features**: Message-passing design, header-only option
- **Notes**: Research allocator, excellent for high-core-count systems

#### Hoard
- **Best For**: Preventing false sharing
- **Performance**: 15-30% when false sharing is an issue
- **Platforms**: Linux, macOS, Windows
- **Notes**: Best used when false sharing is a known bottleneck

#### nedmalloc
- **Best For**: Windows performance
- **Performance**: 20-40% improvement on Windows
- **Platforms**: All (best on Windows)
- **Features**: Header-only library
- **Notes**: On Linux/macOS, prefer jemalloc or tcmalloc

#### default
- **Purpose**: System default malloc (baseline for comparison)
- **Platforms**: All
- **Notes**: No special configuration needed

## Usage

### Basic Configuration

```yaml
# toolchainkit.yaml
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: platform
      name: linux-x64
    - type: buildtype
      name: release
    - type: allocator
      name: jemalloc
```

### Python API

```python
from toolchainkit.config import LayerComposer

composer = LayerComposer()
config = composer.compose([
    {"type": "base", "name": "clang-18"},
    {"type": "platform", "name": "linux-x64"},
    {"type": "buildtype", "name": "release"},
    {"type": "allocator", "name": "jemalloc"},
])
```

### Integration Methods

Each allocator supports multiple integration methods:

1. **link** (Recommended): Compile-time linking
   - Most reliable and performant
   - Adds `-ljemalloc` to linker flags
   - Works on all platforms

2. **ld_preload** (Linux/macOS only): Runtime replacement
   - No recompilation needed
   - Set `LD_PRELOAD` environment variable
   - Useful for testing different allocators quickly

3. **proxy**: Proxy library (fallback)
   - Rarely used
   - Creates wrapper library

4. **auto**: Automatic selection (default)
   - Chooses best method for platform
   - Windows: always uses link (no LD_PRELOAD)

### Specifying Integration Method

```yaml
# Use specific integration method
toolchain:
  layers:
    - type: allocator
      name: jemalloc
      method: link  # or ld_preload, proxy, auto
```

## Performance Comparison

| Allocator | Single-Thread | Multi-Thread | Memory Overhead | Fragmentation |
|-----------|---------------|--------------|-----------------|---------------|
| default   | Baseline      | Baseline     | Minimal         | Medium        |
| jemalloc  | +5-10%        | +10-30%      | Low             | Low           |
| tcmalloc  | +5-10%        | +10-25%      | Low             | Low           |
| mimalloc  | +10-15%       | +15-35%      | Very Low        | Very Low      |
| snmalloc  | +5-10%        | +10-25%      | Low             | Low           |
| hoard     | +5-10%        | +15-30%*     | Medium          | Medium        |
| tbbmalloc | +5-10%        | +10-30%      | Low             | Low           |
| nedmalloc | +10-20%**     | +20-40%**    | Low             | Low           |

\* When false sharing is a bottleneck
\** Primarily on Windows

## Platform Support Matrix

| Allocator | Linux | macOS | Windows | Notes                              |
|-----------|-------|-------|---------|-----------------------------------|
| jemalloc  | ✅     | ✅     | ✅       | Excellent cross-platform support  |
| tcmalloc  | ✅     | ✅     | ⚠️      | Limited Windows support           |
| mimalloc  | ✅     | ✅     | ✅       | Microsoft's recommended allocator |
| snmalloc  | ✅     | ✅     | ✅       | Research project, stable          |
| hoard     | ✅     | ✅     | ✅       | Specialized use case              |
| nedmalloc | ✅     | ✅     | ✅       | Best on Windows                   |
| tbbmalloc | ✅     | ✅     | ✅       | Requires Intel TBB                |
| default   | ✅     | ✅     | ✅       | Always available                  |

## Conflicts and Limitations

### Sanitizer Conflicts

Memory allocators **cannot** be used with the following sanitizers:
- **AddressSanitizer (ASan)**: Has its own allocator
- **ThreadSanitizer (TSan)**: Requires special allocator integration
- **MemorySanitizer (MSan)**: Requires custom allocator support

If you need to use a sanitizer, use the `default` allocator.

### Example: Detecting Conflicts

```yaml
# This will FAIL - ASan conflicts with custom allocators
toolchain:
  layers:
    - type: base
      name: clang-18
    - type: sanitizer
      name: address
    - type: allocator
      name: jemalloc  # ERROR: Conflict detected
```

## Recommendations

### Development
- Use `default` or `jemalloc` with profiling enabled
- Avoid custom allocators when using sanitizers
- Use `tcmalloc` if you need heap profiling

### Testing
- Use `default` to avoid non-determinism
- Test with both default and production allocator

### Production
- **Multi-threaded server**: `jemalloc` or `tcmalloc`
- **Windows application**: `mimalloc` or `nedmalloc`
- **High-core-count system**: `snmalloc` or `tbbmalloc`
- **Security-critical**: `mimalloc` (free-list sharding)

### Benchmarking
- Always compare against `default` baseline
- Test with realistic workload, not synthetic benchmarks
- Measure both performance and memory usage
- Profile before and after to understand impact

## Troubleshooting

### Allocator Not Found

```
Error: Allocator 'jemalloc' not found on system.
```

**Solution**: Install the allocator using your package manager:
```bash
# Ubuntu/Debian
sudo apt install libjemalloc-dev

# macOS
brew install jemalloc

# Fedora/RHEL
sudo dnf install jemalloc-devel
```

### Link Errors

```
/usr/bin/ld: cannot find -ljemalloc
```

**Solution**: Verify the library is installed and in the linker search path.

### Performance Not Improving

Possible causes:
1. **Not multi-threaded**: Custom allocators help most with threading
2. **I/O bound**: If your app is I/O bound, allocator won't help
3. **Wrong allocator**: Try different allocators (jemalloc vs mimalloc)
4. **Already optimized**: System malloc may already be sufficient

### Windows LD_PRELOAD Not Working

**Solution**: Windows doesn't support LD_PRELOAD. Use `link` method:

```yaml
toolchain:
  layers:
    - type: allocator
      name: jemalloc
      method: link  # Required on Windows
```

## Benchmarking

To benchmark different allocators:

```bash
# Build with different allocators
toolkit configure --layers base/clang-18,platform/linux-x64,buildtype/release,allocator/default
toolkit build
./benchmark > results_default.txt

toolkit configure --layers base/clang-18,platform/linux-x64,buildtype/release,allocator/jemalloc
toolkit build
./benchmark > results_jemalloc.txt

toolkit configure --layers base/clang-18,platform/linux-x64,buildtype/release,allocator/tcmalloc
toolkit build
./benchmark > results_tcmalloc.txt
```

Then compare the results to find the best allocator for your workload.

## Further Reading

- [jemalloc Documentation](https://jemalloc.net/)
- [TCMalloc Documentation](https://github.com/google/tcmalloc)
- [mimalloc Documentation](https://github.com/microsoft/mimalloc)
- [snmalloc Paper](https://github.com/microsoft/snmalloc)
- [Hoard Allocator](https://github.com/emeryberger/Hoard)
- [Intel TBB Documentation](https://spec.oneapi.io/versions/latest/elements/oneTBB/source/nested-index.html)
