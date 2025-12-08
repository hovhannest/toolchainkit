#include <iostream>
#include <vector>
#include <chrono>
#include <iomanip>
#include <cstdlib>
#include <cstring>

struct BenchmarkResult {
    std::string name;
    double duration_ms;
    size_t operations;

    double ops_per_second() const {
        return (operations / duration_ms) * 1000.0;
    }
};

class Timer {
public:
    Timer() : start_(std::chrono::high_resolution_clock::now()) {}

    double elapsed_ms() const {
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start_);
        return duration.count() / 1000.0;
    }

private:
    std::chrono::high_resolution_clock::time_point start_;
};

BenchmarkResult benchmark_small_allocations(size_t count) {
    Timer timer;
    std::vector<void*> ptrs;
    ptrs.reserve(count);

    // Allocate
    for (size_t i = 0; i < count; ++i) {
        ptrs.push_back(malloc(64));
    }

    // Deallocate
    for (auto ptr : ptrs) {
        free(ptr);
    }

    return {"Small allocations (64 bytes)", timer.elapsed_ms(), count * 2};
}

BenchmarkResult benchmark_medium_allocations(size_t count) {
    Timer timer;
    std::vector<void*> ptrs;
    ptrs.reserve(count);

    // Allocate
    for (size_t i = 0; i < count; ++i) {
        ptrs.push_back(malloc(1024));
    }

    // Deallocate
    for (auto ptr : ptrs) {
        free(ptr);
    }

    return {"Medium allocations (1KB)", timer.elapsed_ms(), count * 2};
}

BenchmarkResult benchmark_large_allocations(size_t count) {
    Timer timer;
    std::vector<void*> ptrs;
    ptrs.reserve(count);

    // Allocate
    for (size_t i = 0; i < count; ++i) {
        ptrs.push_back(malloc(1024 * 1024)); // 1MB
    }

    // Deallocate
    for (auto ptr : ptrs) {
        free(ptr);
    }

    return {"Large allocations (1MB)", timer.elapsed_ms(), count * 2};
}

BenchmarkResult benchmark_mixed_sizes(size_t count) {
    Timer timer;
    std::vector<void*> ptrs;
    ptrs.reserve(count);

    size_t sizes[] = {16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192};

    // Allocate mixed sizes
    for (size_t i = 0; i < count; ++i) {
        size_t size = sizes[i % 10];
        ptrs.push_back(malloc(size));
    }

    // Deallocate in reverse order (worst case for some allocators)
    for (auto it = ptrs.rbegin(); it != ptrs.rend(); ++it) {
        free(*it);
    }

    return {"Mixed size allocations", timer.elapsed_ms(), count * 2};
}

BenchmarkResult benchmark_reallocations(size_t count) {
    Timer timer;

    void* ptr = malloc(64);

    for (size_t i = 1; i < count; ++i) {
        ptr = realloc(ptr, 64 * (i + 1));
    }

    free(ptr);

    return {"Reallocations", timer.elapsed_ms(), count};
}

BenchmarkResult benchmark_string_operations(size_t count) {
    Timer timer;

    std::vector<std::string> strings;
    strings.reserve(count);

    // Allocate strings
    for (size_t i = 0; i < count; ++i) {
        strings.push_back("This is a test string number " + std::to_string(i));
    }

    // Perform operations
    for (auto& str : strings) {
        str += " - modified";
        str.reserve(str.size() + 100);
    }

    strings.clear();

    return {"String operations", timer.elapsed_ms(), count * 3};
}

BenchmarkResult benchmark_container_growth(size_t count) {
    Timer timer;

    std::vector<int> vec;

    // Let vector grow naturally (tests reallocation patterns)
    for (size_t i = 0; i < count; ++i) {
        vec.push_back(static_cast<int>(i));
    }

    return {"Vector growth", timer.elapsed_ms(), count};
}

void print_result(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(35) << result.name << " : "
              << std::right << std::setw(10) << std::fixed << std::setprecision(3)
              << result.duration_ms << " ms ("
              << std::setw(12) << std::fixed << std::setprecision(0)
              << result.ops_per_second() << " ops/sec)\n";
}

void run_benchmark() {
    const size_t iterations = 10000;

    std::vector<BenchmarkResult> results;

    std::cout << "Running benchmarks with " << iterations << " iterations each...\n\n";

    results.push_back(benchmark_small_allocations(iterations));
    results.push_back(benchmark_medium_allocations(iterations));
    results.push_back(benchmark_large_allocations(iterations / 10)); // Fewer for large allocs
    results.push_back(benchmark_mixed_sizes(iterations));
    results.push_back(benchmark_reallocations(iterations));
    results.push_back(benchmark_string_operations(iterations));
    results.push_back(benchmark_container_growth(iterations));

    std::cout << "Results:\n";
    std::cout << "--------\n";

    for (const auto& result : results) {
        print_result(result);
    }

    // Calculate total time
    double total_time = 0.0;
    size_t total_ops = 0;

    for (const auto& result : results) {
        total_time += result.duration_ms;
        total_ops += result.operations;
    }

    std::cout << "\nTotal:\n";
    std::cout << "  Time: " << total_time << " ms\n";
    std::cout << "  Operations: " << total_ops << "\n";
    std::cout << "  Average: " << std::fixed << std::setprecision(0)
              << (total_ops / total_time) * 1000.0 << " ops/sec\n";
}
