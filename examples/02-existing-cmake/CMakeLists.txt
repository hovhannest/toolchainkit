cmake_minimum_required(VERSION 3.15)

# Optional: Use ToolchainKit toolchain file if available
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/.toolchainkit/cmake/toolchainkit/toolchain.cmake")
    set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/.toolchainkit/cmake/toolchainkit/toolchain.cmake")
endif()

project(LegacyProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Dependencies from Conan
find_package(Boost REQUIRED COMPONENTS filesystem system)
find_package(fmt REQUIRED)

# Executable
add_executable(myapp
    src/main.cpp
    src/utils.cpp
)

target_include_directories(myapp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(myapp PRIVATE
    Boost::filesystem
    Boost::system
    fmt::fmt
)
