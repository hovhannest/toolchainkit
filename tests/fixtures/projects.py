"""Reusable CMake project fixtures for testing.

This module provides pytest fixtures that create realistic CMake project
structures for testing CMake generation, configuration, and build functionality.
"""

import pytest
from pathlib import Path


@pytest.fixture
def minimal_cmake_project(tmp_path) -> Path:
    """
    Create minimal CMake project with single source file.

    Creates:
    - CMakeLists.txt (basic configuration)
    - src/main.cpp (simple Hello World)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_cmake_generation(minimal_cmake_project):
            cmake_file = minimal_cmake_project / "CMakeLists.txt"
            assert cmake_file.exists()
            assert "project(TestProject" in cmake_file.read_text()
    """
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create CMakeLists.txt
    cmake_content = """cmake_minimum_required(VERSION 3.20)
project(TestProject CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(main src/main.cpp)
"""
    (project_root / "CMakeLists.txt").write_text(cmake_content)

    # Create source directory and main.cpp
    src_dir = project_root / "src"
    src_dir.mkdir()
    main_cpp = """#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""
    (src_dir / "main.cpp").write_text(main_cpp)

    return project_root


@pytest.fixture
def cmake_project_with_library(tmp_path) -> Path:
    """
    Create CMake project with library and executable.

    Creates:
    - CMakeLists.txt (with library target)
    - src/main.cpp (uses library)
    - src/mylib.cpp, include/mylib.h (library implementation)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_library_project(cmake_project_with_library):
            assert (cmake_project_with_library / "src" / "mylib.cpp").exists()
            assert (cmake_project_with_library / "include" / "mylib.h").exists()
    """
    project_root = tmp_path / "library_project"
    project_root.mkdir()

    # Create CMakeLists.txt with library
    cmake_content = """cmake_minimum_required(VERSION 3.20)
project(LibraryProject CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Library
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)

# Executable
add_executable(main src/main.cpp)
target_link_libraries(main PRIVATE mylib)
"""
    (project_root / "CMakeLists.txt").write_text(cmake_content)

    # Create source files
    src_dir = project_root / "src"
    src_dir.mkdir()

    (src_dir / "main.cpp").write_text(
        """#include "mylib.h"
#include <iostream>

int main() {
    std::cout << "Result: " << add(5, 3) << std::endl;
    return 0;
}
"""
    )

    (src_dir / "mylib.cpp").write_text(
        """#include "mylib.h"

int add(int a, int b) {
    return a + b;
}
"""
    )

    # Create header file
    include_dir = project_root / "include"
    include_dir.mkdir()
    (include_dir / "mylib.h").write_text(
        """#pragma once

int add(int a, int b);
"""
    )

    return project_root


@pytest.fixture
def cmake_project_with_tests(tmp_path) -> Path:
    """
    Create CMake project with tests enabled.

    Creates:
    - CMakeLists.txt (with enable_testing)
    - src/main.cpp, src/mylib.cpp
    - tests/test_mylib.cpp (simple test)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_project_with_tests(cmake_project_with_tests):
            assert (cmake_project_with_tests / "tests" / "test_mylib.cpp").exists()
    """
    project_root = tmp_path / "project_with_tests"
    project_root.mkdir()

    # Create CMakeLists.txt with testing
    cmake_content = """cmake_minimum_required(VERSION 3.20)
project(ProjectWithTests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

# Library
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)

# Executable
add_executable(main src/main.cpp)
target_link_libraries(main PRIVATE mylib)

# Tests
add_executable(test_mylib tests/test_mylib.cpp)
target_link_libraries(test_mylib PRIVATE mylib)
add_test(NAME test_mylib COMMAND test_mylib)
"""
    (project_root / "CMakeLists.txt").write_text(cmake_content)

    # Create source files
    src_dir = project_root / "src"
    src_dir.mkdir()

    (src_dir / "main.cpp").write_text(
        """#include "mylib.h"
#include <iostream>

int main() {
    std::cout << "Result: " << add(5, 3) << std::endl;
    return 0;
}
"""
    )

    (src_dir / "mylib.cpp").write_text(
        """#include "mylib.h"

int add(int a, int b) {
    return a + b;
}
"""
    )

    # Create header file
    include_dir = project_root / "include"
    include_dir.mkdir()
    (include_dir / "mylib.h").write_text(
        """#pragma once

int add(int a, int b);
"""
    )

    # Create test directory
    tests_dir = project_root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mylib.cpp").write_text(
        """#include "mylib.h"
#include <cassert>

int main() {
    assert(add(2, 3) == 5);
    assert(add(0, 0) == 0);
    assert(add(-1, 1) == 0);
    return 0;
}
"""
    )

    return project_root


@pytest.fixture
def cmake_project_with_subdirectories(tmp_path) -> Path:
    """
    Create CMake project with multiple subdirectories.

    Creates:
    - CMakeLists.txt (top-level)
    - app/CMakeLists.txt, app/main.cpp
    - lib/CMakeLists.txt, lib/mylib.cpp, lib/mylib.h

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_subdirectory_project(cmake_project_with_subdirectories):
            assert (cmake_project_with_subdirectories / "app" / "CMakeLists.txt").exists()
            assert (cmake_project_with_subdirectories / "lib" / "CMakeLists.txt").exists()
    """
    project_root = tmp_path / "subdir_project"
    project_root.mkdir()

    # Top-level CMakeLists.txt
    (project_root / "CMakeLists.txt").write_text(
        """cmake_minimum_required(VERSION 3.20)
project(SubdirProject CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(lib)
add_subdirectory(app)
"""
    )

    # Library subdirectory
    lib_dir = project_root / "lib"
    lib_dir.mkdir()
    (lib_dir / "CMakeLists.txt").write_text(
        """add_library(mylib mylib.cpp)
target_include_directories(mylib PUBLIC .)
"""
    )
    (lib_dir / "mylib.cpp").write_text(
        """#include "mylib.h"

int multiply(int a, int b) {
    return a * b;
}
"""
    )
    (lib_dir / "mylib.h").write_text(
        """#pragma once

int multiply(int a, int b);
"""
    )

    # App subdirectory
    app_dir = project_root / "app"
    app_dir.mkdir()
    (app_dir / "CMakeLists.txt").write_text(
        """add_executable(app main.cpp)
target_link_libraries(app PRIVATE mylib)
"""
    )
    (app_dir / "main.cpp").write_text(
        """#include "mylib.h"
#include <iostream>

int main() {
    std::cout << "Result: " << multiply(4, 7) << std::endl;
    return 0;
}
"""
    )

    return project_root


@pytest.fixture
def cmake_project_with_conan(tmp_path) -> Path:
    """
    Create CMake project configured for Conan.

    Creates:
    - CMakeLists.txt (with Conan integration)
    - conanfile.txt (dependencies)
    - src/main.cpp

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_conan_project(cmake_project_with_conan):
            assert (cmake_project_with_conan / "conanfile.txt").exists()
    """
    project_root = tmp_path / "conan_project"
    project_root.mkdir()

    # CMakeLists.txt with Conan
    (project_root / "CMakeLists.txt").write_text(
        """cmake_minimum_required(VERSION 3.20)
project(ConanProject CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Conan integration
include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake OPTIONAL)

add_executable(main src/main.cpp)
"""
    )

    # conanfile.txt
    (project_root / "conanfile.txt").write_text(
        """[requires]
fmt/10.1.1

[generators]
CMakeDeps
CMakeToolchain
"""
    )

    # Source file
    src_dir = project_root / "src"
    src_dir.mkdir()
    (src_dir / "main.cpp").write_text(
        """#include <iostream>

int main() {
    std::cout << "Project with Conan dependencies" << std::endl;
    return 0;
}
"""
    )

    return project_root
