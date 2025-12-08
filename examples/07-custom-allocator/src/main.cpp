#include <iostream>
#include <vector>
#include <string>

// Include allocator headers based on configuration
#ifdef USE_MIMALLOC
#include <mimalloc.h>
#endif

#ifdef USE_JEMALLOC
#include <jemalloc/jemalloc.h>
#endif

// Forward declaration of benchmark function
void run_benchmark();

void print_allocator_info() {
    std::cout << "========================================\n";
    std::cout << "Allocator Demo Application\n";
    std::cout << "========================================\n\n";

    #ifdef USE_MIMALLOC
    std::cout << "Active Allocator: mimalloc\n";
    std::cout << "Version: " << MI_MALLOC_VERSION << "\n";
    std::cout << "Features: High-performance allocator with security features\n";

    #elif defined(USE_JEMALLOC)
    std::cout << "Active Allocator: jemalloc\n";
    std::cout << "Version: " << JEMALLOC_VERSION << "\n";
    std::cout << "Features: Scalable concurrent allocator\n";

    #elif defined(USE_TCMALLOC)
    std::cout << "Active Allocator: tcmalloc (gperftools)\n";
    std::cout << "Features: Thread-caching malloc\n";

    #else
    std::cout << "Active Allocator: System default (libc malloc)\n";
    std::cout << "Features: Standard C library allocator\n";
    #endif

    std::cout << "\n========================================\n\n";
}

void demonstrate_basic_allocation() {
    std::cout << "Basic Allocation Test:\n";
    std::cout << "----------------------\n";

    // Allocate some memory using C++ standard containers
    // These will use the custom allocator if properly configured
    std::vector<int> vec;
    vec.reserve(1000);

    for (int i = 0; i < 1000; ++i) {
        vec.push_back(i);
    }

    std::cout << "✓ Allocated vector with " << vec.size() << " elements\n";

    // Allocate some strings
    std::vector<std::string> strings;
    strings.reserve(100);

    for (int i = 0; i < 100; ++i) {
        strings.push_back("String number " + std::to_string(i));
    }

    std::cout << "✓ Allocated " << strings.size() << " strings\n";
    std::cout << "\n";
}

void demonstrate_raw_allocation() {
    std::cout << "Raw Memory Allocation Test:\n";
    std::cout << "----------------------------\n";

    const size_t count = 100;
    const size_t size = 1024;

    std::vector<void*> ptrs;
    ptrs.reserve(count);

    // Allocate using malloc (will use custom allocator)
    for (size_t i = 0; i < count; ++i) {
        void* ptr = malloc(size);
        if (ptr) {
            ptrs.push_back(ptr);
        }
    }

    std::cout << "✓ Allocated " << ptrs.size() << " blocks of " << size << " bytes each\n";

    // Free all allocations
    for (auto ptr : ptrs) {
        free(ptr);
    }

    std::cout << "✓ Freed all allocations\n";
    std::cout << "\n";
}

#ifdef USE_MIMALLOC
void demonstrate_mimalloc_features() {
    std::cout << "mimalloc-Specific Features:\n";
    std::cout << "----------------------------\n";

    // Show stats
    std::cout << "Memory statistics:\n";
    mi_stats_print(nullptr);

    std::cout << "\n";
}
#endif

#ifdef USE_JEMALLOC
void demonstrate_jemalloc_features() {
    std::cout << "jemalloc-Specific Features:\n";
    std::cout << "----------------------------\n";

    // Get jemalloc statistics
    size_t allocated, active, metadata, resident, mapped;
    size_t sz = sizeof(size_t);

    if (mallctl("stats.allocated", &allocated, &sz, nullptr, 0) == 0) {
        std::cout << "Allocated: " << allocated << " bytes\n";
    }

    if (mallctl("stats.active", &active, &sz, nullptr, 0) == 0) {
        std::cout << "Active: " << active << " bytes\n";
    }

    if (mallctl("stats.metadata", &metadata, &sz, nullptr, 0) == 0) {
        std::cout << "Metadata: " << metadata << " bytes\n";
    }

    std::cout << "\n";
}
#endif

int main() {
    print_allocator_info();

    demonstrate_basic_allocation();
    demonstrate_raw_allocation();

    #ifdef USE_MIMALLOC
    demonstrate_mimalloc_features();
    #endif

    #ifdef USE_JEMALLOC
    demonstrate_jemalloc_features();
    #endif

    std::cout << "Running Performance Benchmarks:\n";
    std::cout << "================================\n\n";
    run_benchmark();

    std::cout << "\n========================================\n";
    std::cout << "Demo completed successfully!\n";
    std::cout << "========================================\n";

    return 0;
}
