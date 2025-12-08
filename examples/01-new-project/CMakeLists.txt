cmake_minimum_required(VERSION 3.20)
project(MyNewProject VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find dependencies from Conan
find_package(fmt REQUIRED)
find_package(spdlog REQUIRED)

# Library
add_library(mylib
    src/mylib.cpp
)

target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(mylib PUBLIC
    fmt::fmt
    spdlog::spdlog
)

# Executable
add_executable(myapp
    src/main.cpp
)

target_link_libraries(myapp PRIVATE mylib)

# Tests
enable_testing()
add_executable(tests tests/test_main.cpp)
target_link_libraries(tests PRIVATE mylib)
add_test(NAME unit_tests COMMAND tests)
