# Profiling Layers

This directory contains YAML layer definitions for profiling and performance analysis.

## Available Profiling Layers

| Layer | Method | Overhead | Platform | Best For |
|-------|--------|----------|----------|----------|
| `gprof` | Function call graph | 10-30% | Linux, macOS, MinGW | Function-level profiling |
| `instrument-functions` | Custom hooks | 30-100% | All | Call tracing, custom profilers |
| `asan-profile` | Memory access tracking | 200-300% | All (with ASan) | Memory debugging |
| `perf` | CPU sampling | <5% | Linux only | Production profiling |

## Profiling Methods Explained

### gprof - GNU Profiler
Traditional function-level profiling with call graph analysis.
- **Output**: `gmon.out`
- **Analysis**: `gprof program gmon.out`
- **Features**: Call counts, timing, call graph
- **Limitations**: Single-threaded, requires normal exit

### instrument-functions - Custom Instrumentation
Explicit callbacks on every function entry/exit.
- **Hooks**: `__cyg_profile_func_enter/exit`
- **Use Cases**: Custom profilers, tracing, call graphs
- **Flexibility**: Complete control over data collection
- **Overhead**: High but configurable

### asan-profile - AddressSanitizer Profiling
Enhanced memory access profiling with use-after-scope detection.
- **Requires**: AddressSanitizer layer (-fsanitize=address)
- **Features**: Stack variable lifetime tracking
- **Use Cases**: Memory bug hunting, development/testing
- **Overhead**: Very high (3x total with ASan)

### perf - Linux Performance Counters
Low-overhead sampling-based CPU profiling.
- **Tool**: Linux `perf` command
- **Output**: `perf.data`
- **Features**: CPU profiling, hardware counters, flame graphs
- **Overhead**: Minimal (<5%)
- **Best For**: Production-like profiling

## Usage Examples

### Basic Function Profiling (gprof)
```yaml
layers:
  - type: base
    name: gcc-13
  - type: optimization
    name: o2  # Representative optimization
  - type: profiling
    name: gprof
```

Analysis:
```bash
./program  # Generates gmon.out
gprof program gmon.out > analysis.txt
```

### Custom Function Tracing
```yaml
layers:
  - type: base
    name: clang-18
  - type: profiling
    name: instrument-functions
```

Implement callbacks:
```c
void __cyg_profile_func_enter(void *this_fn, void *call_site) {
    fprintf(stderr, "Enter: %p\n", this_fn);
}

void __cyg_profile_func_exit(void *this_fn, void *call_site) {
    fprintf(stderr, "Exit: %p\n", this_fn);
}
```

### Memory Access Profiling
```yaml
layers:
  - type: base
    name: clang-18
  - type: sanitizer
    name: address  # Required
  - type: profiling
    name: asan-profile  # Adds use-after-scope detection
```

### Low-Overhead CPU Profiling (Linux)
```yaml
layers:
  - type: base
    name: gcc-13
  - type: optimization
    name: o2
  - type: profiling
    name: perf
```

Analysis:
```bash
perf record -g ./program
perf report
# Or generate flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

## Profiling Workflows

### Development Profiling
Goal: Find performance bottlenecks during development.

```yaml
layers:
  - type: base
    name: gcc-13
  - type: buildtype
    name: relwithdebinfo  # Release with debug info
  - type: profiling
    name: perf  # Low overhead
```

### Performance Analysis
Goal: Detailed function-level performance analysis.

```yaml
layers:
  - type: base
    name: gcc-13
  - type: optimization
    name: o2
  - type: profiling
    name: gprof
```

### Call Graph Generation
Goal: Understand program call structure.

```yaml
layers:
  - type: base
    name: clang-18
  - type: profiling
    name: instrument-functions
```

### Memory Profiling
Goal: Find memory access issues and leaks.

```yaml
layers:
  - type: base
    name: clang-18
  - type: sanitizer
    name: address
  - type: profiling
    name: asan-profile
```

## Performance Impact Comparison

| Configuration | Compile Time | Runtime | Memory | Binary Size |
|---------------|--------------|---------|--------|-------------|
| No profiling | baseline | baseline | baseline | baseline |
| perf | - | +3-5% | - | +10% (debug info) |
| gprof | +5% | +10-30% | +5% | +5% |
| instrument-functions | +10% | +30-100% | +10% | +10% |
| asan-profile | +20% | +200-300% | +200% | +50% |

## Platform Support

| Feature | Linux | Windows | macOS |
|---------|-------|---------|-------|
| gprof | ✓ | ✓ (MinGW) | ✓ |
| instrument-functions | ✓ | ✓ | ✓ |
| asan-profile | ✓ | ✓ | ✓ |
| perf | ✓ | ✗ | ✗ |

### Platform-Specific Alternatives
- **Windows**: Use Visual Studio Profiler or Intel VTune
- **macOS**: Use Instruments (part of Xcode)
- **Cross-platform**: Use Valgrind (callgrind), gperftools

## Conflicts

Profiling layers may conflict with:
- **Multiple profiling modes**: Only one profiling layer at a time (except asan-profile with sanitizers)
- **Aggressive optimization**: -O3/-Ofast may distort profiling results (especially gprof)
- **Frame pointer omission**: Conflicts with perf (frame pointers needed for stack traces)
- **Custom allocators**: May conflict with asan-profile

## Best Practices

### General Guidelines
1. **Profile with representative workload** - Use realistic data and scenarios
2. **Match production optimization** - Use -O2 for realistic results
3. **Avoid -O3/-Ofast with gprof** - Inlining distorts call graph
4. **Profile release-like builds** - Debug builds have different performance
5. **Run multiple times** - Ensure consistent results

### Tool Selection
- **Development**: Use `perf` for low-overhead continuous profiling
- **Detailed analysis**: Use `gprof` for function-level insights
- **Custom needs**: Use `instrument-functions` for flexibility
- **Memory issues**: Use `asan-profile` with AddressSanitizer
- **Production**: Only `perf` is suitable for production (low overhead)

### Analysis Tips
1. **Focus on hot paths** - Optimize the critical 20% that takes 80% of time
2. **Verify results** - Profile before and after optimizations
3. **Consider I/O and blocking** - Not all tools capture this
4. **Profile multi-threaded** - Use perf or custom instrumentation
5. **Visualize results** - Use flame graphs for intuitive understanding

## Tools and Visualization

### gprof Analysis
```bash
# Basic report
gprof program gmon.out

# Flat profile only
gprof -p program gmon.out

# Call graph only
gprof -q program gmon.out

# Generate call graph visualization
gprof program gmon.out | gprof2dot | dot -Tpng -o callgraph.png
```

### perf Analysis
```bash
# Interactive report
perf report

# Top functions
perf top

# Flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Source annotations
perf annotate

# Hardware events
perf stat ./program
```

### instrument-functions Integration
```c
// Simple timing profiler
#include <time.h>
#include <stdio.h>

struct call_info {
    void *fn;
    struct timespec start;
};

__thread struct call_info calls[1000];
__thread int call_depth = 0;

void __cyg_profile_func_enter(void *this_fn, void *call_site) {
    if (call_depth < 1000) {
        calls[call_depth].fn = this_fn;
        clock_gettime(CLOCK_MONOTONIC, &calls[call_depth].start);
        call_depth++;
    }
}

void __cyg_profile_func_exit(void *this_fn, void *call_site) {
    if (call_depth > 0) {
        call_depth--;
        struct timespec end;
        clock_gettime(CLOCK_MONOTONIC, &end);
        long ns = (end.tv_sec - calls[call_depth].start.tv_sec) * 1000000000L +
                  (end.tv_nsec - calls[call_depth].start.tv_nsec);
        fprintf(stderr, "Function %p took %ld ns\n", this_fn, ns);
    }
}
```

## Resources

- [GNU gprof Documentation](https://sourceware.org/binutils/docs/gprof/)
- [Linux perf Wiki](https://perf.wiki.kernel.org/)
- [Brendan Gregg's Flame Graphs](http://www.brendangregg.com/flamegraphs.html)
- [GCC Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)
- [AddressSanitizer Documentation](https://github.com/google/sanitizers/wiki/AddressSanitizer)
