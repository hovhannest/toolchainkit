"""Reusable directory structure fixtures for testing.

This module provides pytest fixtures that create realistic directory structures
for testing directory management, cache operations, and project setup.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def mock_global_cache(tmp_path) -> Path:
    """
    Create mock global cache directory structure.

    Creates the ToolchainKit global cache directory with:
    - toolchains/ (empty)
    - downloads/ (empty)
    - lock/ (empty)
    - embedded-python/ (empty)
    - registry.json (empty registry)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to mock global cache directory (~/.toolchainkit)

    Example:
        def test_cache_structure(mock_global_cache):
            assert (mock_global_cache / "toolchains").is_dir()
            assert (mock_global_cache / "registry.json").exists()
    """
    cache_dir = tmp_path / ".toolchainkit"
    cache_dir.mkdir()

    # Create subdirectories
    (cache_dir / "toolchains").mkdir()
    (cache_dir / "downloads").mkdir()
    (cache_dir / "lock").mkdir()
    (cache_dir / "embedded-python").mkdir()

    # Create empty registry
    registry_data = {
        "version": "1.0",
        "toolchains": {},
        "total_size_bytes": 0,
        "created_at": "2025-11-22T00:00:00Z",
    }
    (cache_dir / "registry.json").write_text(json.dumps(registry_data, indent=2))

    return cache_dir


@pytest.fixture
def mock_global_cache_with_toolchains(tmp_path) -> Path:
    """
    Create mock global cache with example toolchains.

    Creates global cache with:
    - toolchains/llvm-18.1.8/ (mock toolchain)
    - toolchains/gcc-13.2.0/ (mock toolchain)
    - registry.json (with toolchain entries)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to mock global cache directory

    Example:
        def test_toolchain_listing(mock_global_cache_with_toolchains):
            toolchains_dir = mock_global_cache_with_toolchains / "toolchains"
            assert (toolchains_dir / "llvm-18.1.8").is_dir()
    """
    cache_dir = tmp_path / ".toolchainkit"
    cache_dir.mkdir()

    # Create subdirectories
    (cache_dir / "downloads").mkdir()
    (cache_dir / "lock").mkdir()
    (cache_dir / "embedded-python").mkdir()

    # Create toolchains directory with examples
    toolchains_dir = cache_dir / "toolchains"
    toolchains_dir.mkdir()

    # Mock LLVM toolchain
    llvm_dir = toolchains_dir / "llvm-18.1.8-linux-x64"
    llvm_dir.mkdir()
    (llvm_dir / "bin").mkdir()
    (llvm_dir / "lib").mkdir()
    (llvm_dir / "include").mkdir()

    # Mock GCC toolchain
    gcc_dir = toolchains_dir / "gcc-13.2.0-linux-x64"
    gcc_dir.mkdir()
    (gcc_dir / "bin").mkdir()
    (gcc_dir / "lib64").mkdir()
    (gcc_dir / "include").mkdir()

    # Create registry with toolchains
    registry_data = {
        "version": "1.0",
        "toolchains": {
            "llvm-18.1.8-linux-x64": {
                "path": str(llvm_dir),
                "size_bytes": 1024 * 1024 * 500,  # 500 MB
                "installed_at": "2025-11-20T10:00:00Z",
                "last_used": "2025-11-22T09:00:00Z",
                "projects": [],
            },
            "gcc-13.2.0-linux-x64": {
                "path": str(gcc_dir),
                "size_bytes": 1024 * 1024 * 300,  # 300 MB
                "installed_at": "2025-11-21T14:00:00Z",
                "last_used": "2025-11-22T08:00:00Z",
                "projects": [],
            },
        },
        "total_size_bytes": 1024 * 1024 * 800,  # 800 MB
        "created_at": "2025-11-20T00:00:00Z",
    }
    (cache_dir / "registry.json").write_text(json.dumps(registry_data, indent=2))

    return cache_dir


@pytest.fixture
def mock_project_local(tmp_path) -> Path:
    """
    Create mock project-local .toolchainkit directory.

    Creates the project-local ToolchainKit directory with:
    - cmake/ (generated CMake files)
    - packages/ (package manager caches)
    - state.json (project state)

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to mock project-local directory (<project>/.toolchainkit)

    Example:
        def test_project_structure(mock_project_local):
            assert (mock_project_local / "cmake").is_dir()
            assert (mock_project_local / "state.json").exists()
    """
    local_dir = tmp_path / "project" / ".toolchainkit"
    local_dir.mkdir(parents=True)

    # Create subdirectories
    (local_dir / "cmake").mkdir()
    (local_dir / "packages").mkdir()

    # Create empty state file
    state_data = {
        "version": "1.0",
        "active_toolchain": None,
        "config_hash": None,
        "bootstrap_complete": False,
        "cmake_configured": False,
        "build_directory": "build",
        "last_bootstrap": None,
        "last_configure": None,
    }
    (local_dir / "state.json").write_text(json.dumps(state_data, indent=2))

    return local_dir


@pytest.fixture
def mock_project_local_with_state(tmp_path) -> Path:
    """
    Create mock project-local directory with active state.

    Creates project-local directory with:
    - Configured state (toolchain, config hash set)
    - CMake toolchain file
    - Package manager cache directories

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to mock project-local directory

    Example:
        def test_configured_project(mock_project_local_with_state):
            state_file = mock_project_local_with_state / "state.json"
            state = json.loads(state_file.read_text())
            assert state['bootstrap_complete'] is True
    """
    local_dir = tmp_path / "project" / ".toolchainkit"
    local_dir.mkdir(parents=True)

    # Create subdirectories
    cmake_dir = local_dir / "cmake"
    cmake_dir.mkdir()
    (local_dir / "packages").mkdir()
    (local_dir / "packages" / "conan").mkdir()
    (local_dir / "packages" / "vcpkg").mkdir()

    # Create CMake toolchain file
    (cmake_dir / "toolchainkit-toolchain.cmake").write_text(
        """# Generated by ToolchainKit
set(CMAKE_C_COMPILER /path/to/clang)
set(CMAKE_CXX_COMPILER /path/to/clang++)
"""
    )

    # Create state with active configuration
    state_data = {
        "version": "1.0",
        "active_toolchain": "llvm-18.1.8-linux-x64",
        "config_hash": "abc123def456",
        "bootstrap_complete": True,
        "cmake_configured": True,
        "build_directory": "build",
        "package_manager": "conan",
        "last_bootstrap": "2025-11-22T10:00:00Z",
        "last_configure": "2025-11-22T10:05:00Z",
    }
    (local_dir / "state.json").write_text(json.dumps(state_data, indent=2))

    return local_dir


@pytest.fixture
def mock_complete_workspace(tmp_path) -> Path:
    """
    Create complete mock workspace with both global cache and project-local.

    Creates a full workspace structure with:
    - Global cache (~/.toolchainkit) with toolchains
    - Project directory with .toolchainkit local state
    - CMakeLists.txt and source files
    - toolchainkit.yaml configuration

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to project root directory

    Example:
        def test_complete_setup(mock_complete_workspace):
            assert (mock_complete_workspace / "toolchainkit.yaml").exists()
            assert (mock_complete_workspace / ".toolchainkit" / "state.json").exists()
    """
    # Create global cache
    global_cache = tmp_path / "home" / ".toolchainkit"
    global_cache.mkdir(parents=True)
    (global_cache / "toolchains").mkdir()
    (global_cache / "downloads").mkdir()
    (global_cache / "lock").mkdir()
    (global_cache / "registry.json").write_text(
        json.dumps(
            {"version": "1.0", "toolchains": {}, "total_size_bytes": 0}, indent=2
        )
    )

    # Create project directory
    project_root = tmp_path / "projects" / "myapp"
    project_root.mkdir(parents=True)

    # Create toolchainkit.yaml
    (project_root / "toolchainkit.yaml").write_text(
        """toolchains:
  - name: llvm-18
    type: llvm
    version: 18.1.8
    std: c++17

build:
  generator: Ninja
  build_type: Release
"""
    )

    # Create minimal CMakeLists.txt
    (project_root / "CMakeLists.txt").write_text(
        """cmake_minimum_required(VERSION 3.20)
project(MyApp CXX)
add_executable(myapp src/main.cpp)
"""
    )

    # Create source directory
    src_dir = project_root / "src"
    src_dir.mkdir()
    (src_dir / "main.cpp").write_text(
        """#include <iostream>

int main() {
    std::cout << "Hello from MyApp!" << std::endl;
    return 0;
}
"""
    )

    # Create project-local .toolchainkit
    local_dir = project_root / ".toolchainkit"
    local_dir.mkdir()
    (local_dir / "cmake").mkdir()
    (local_dir / "packages").mkdir()
    (local_dir / "state.json").write_text(
        json.dumps(
            {"version": "1.0", "active_toolchain": None, "bootstrap_complete": False},
            indent=2,
        )
    )

    return project_root
