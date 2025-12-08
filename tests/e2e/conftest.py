"""
Fixtures for end-to-end tests.

Provides reusable fixtures for E2E testing scenarios including
workspace setup, configuration, and build environments.
"""

import pytest


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create a temporary workspace directory.

    Returns:
        Path to temporary workspace
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_cmake_project(temp_workspace):
    """
    Create a sample CMake project for E2E testing.

    Returns:
        Path to project with CMakeLists.txt and source files
    """
    # Create simple CMakeLists.txt
    cmake_content = """cmake_minimum_required(VERSION 3.20)
project(TestApp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_app main.cpp)
"""
    (temp_workspace / "CMakeLists.txt").write_text(cmake_content)

    # Create main.cpp
    main_content = """#include <iostream>

int main() {
    std::cout << "Test App Running" << std::endl;
    return 0;
}
"""
    (temp_workspace / "main.cpp").write_text(main_content)

    return temp_workspace


@pytest.fixture
def sample_toolchainkit_config(temp_workspace):
    """
    Create a sample toolchainkit.yaml configuration file.

    Returns:
        Path to workspace with toolchainkit.yaml
    """
    config_content = """toolchains:
  - name: default
    type: system
    std: c++17

build:
  generator: Ninja
  build_type: Release
  parallel_jobs: 4
"""
    (temp_workspace / "toolchainkit.yaml").write_text(config_content)

    return temp_workspace


@pytest.fixture
def python_api_workspace(sample_cmake_project):
    """
    Workspace configured for Python API testing.

    This fixture provides a workspace ready for testing ToolchainKit
    Python API calls (as opposed to CLI commands).

    Returns:
        Path to configured workspace
    """
    from toolchainkit.core.directory import create_directory_structure

    # Initialize directory structure
    create_directory_structure(sample_cmake_project)

    # Workspace already has CMake project from sample_cmake_project
    return sample_cmake_project


# Note: Fixtures for CLI-based workflows (initialized_workspace, configured_workspace)
# will be added when CLI commands (Tasks 32-40) are implemented.
# For now, E2E tests focus on Python API workflows.


@pytest.fixture
def cmake_available():
    """
    Check if CMake is available for testing.

    Returns:
        True if CMake is available, otherwise skips test
    """
    import shutil

    if not shutil.which("cmake"):
        pytest.skip("CMake not available")
    return True


@pytest.fixture
def compiler_available():
    """
    Check if a C++ compiler is available for testing.

    Returns:
        True if compiler available, otherwise skips test
    """
    import shutil

    # Check for common compilers
    compilers = ["clang++", "g++", "cl"]
    for compiler in compilers:
        if shutil.which(compiler):
            return True

    pytest.skip("No C++ compiler available")


@pytest.fixture
def build_backend_available():
    """
    Check if a build backend (Ninja, Make, MSBuild) is available.

    Returns:
        Name of available backend
    """
    from toolchainkit.cmake.backends import detect_build_backend
    from toolchainkit.core.exceptions import BuildBackendError

    try:
        backend = detect_build_backend()
        return backend.name
    except BuildBackendError:
        pytest.skip("No build backend available")
