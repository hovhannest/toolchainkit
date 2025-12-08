cmake_minimum_required(VERSION 3.20)
project(allocator-demo VERSION 1.0.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Option to select allocator
set(USE_ALLOCATOR "mimalloc" CACHE STRING "Custom allocator to use (mimalloc, jemalloc, tcmalloc, system)")
set_property(CACHE USE_ALLOCATOR PROPERTY STRINGS mimalloc jemalloc tcmalloc system)

message(STATUS "Using allocator: ${USE_ALLOCATOR}")

# Main executable
add_executable(allocator_demo
    src/main.cpp
    src/benchmark.cpp
)

# Configure allocator based on selection
if(USE_ALLOCATOR STREQUAL "mimalloc")
    find_package(mimalloc REQUIRED)
    target_link_libraries(allocator_demo PRIVATE mimalloc-static)
    target_compile_definitions(allocator_demo PRIVATE USE_MIMALLOC=1)
    message(STATUS "Linking with mimalloc")

elseif(USE_ALLOCATOR STREQUAL "jemalloc")
    find_package(jemalloc REQUIRED)
    target_link_libraries(allocator_demo PRIVATE jemalloc::jemalloc)
    target_compile_definitions(allocator_demo PRIVATE USE_JEMALLOC=1)
    message(STATUS "Linking with jemalloc")

elseif(USE_ALLOCATOR STREQUAL "tcmalloc")
    find_package(gperftools REQUIRED)
    target_link_libraries(allocator_demo PRIVATE gperftools::tcmalloc)
    target_compile_definitions(allocator_demo PRIVATE USE_TCMALLOC=1)
    message(STATUS "Linking with tcmalloc")

else()
    message(STATUS "Using system allocator")
    target_compile_definitions(allocator_demo PRIVATE USE_SYSTEM_ALLOCATOR=1)
endif()

# Enable warnings
if(MSVC)
    target_compile_options(allocator_demo PRIVATE /W4)
else()
    target_compile_options(allocator_demo PRIVATE -Wall -Wextra -pedantic)
endif()

# Installation
install(TARGETS allocator_demo
    RUNTIME DESTINATION bin
)
