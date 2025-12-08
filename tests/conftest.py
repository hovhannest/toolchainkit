"""
Pytest configuration and shared fixtures for ToolchainKit tests.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Generator

# Import test fixtures to make them available to all tests
# These imports register the fixtures with pytest's fixture discovery system
# ruff: noqa: F401
from tests.fixtures.toolchains import (
    mock_llvm_toolchain,
    mock_gcc_toolchain,
    mock_msvc_toolchain,
    mock_toolchain_metadata,
)
from tests.fixtures.projects import (
    minimal_cmake_project,
    cmake_project_with_library,
    cmake_project_with_tests,
    cmake_project_with_subdirectories,
    cmake_project_with_conan,
)
from tests.fixtures.directories import (
    mock_global_cache,
    mock_global_cache_with_toolchains,
    mock_project_local,
    mock_project_local_with_state,
    mock_complete_workspace,
)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests that require network access",
    )
    parser.addoption(
        "--link-validation",
        action="store_true",
        default=False,
        help="run link and hash validation tests (network intensive)",
    )
    parser.addoption(
        "--validation-level",
        action="store",
        default="head",
        choices=["head", "partial", "full"],
        help="validation level: head (HTTP HEAD only), partial (first 1MB), full (complete download)",
    )
    parser.addoption(
        "--validation-cache-dir",
        action="store",
        default=None,
        help="directory for validation cache (default: tempdir)",
    )
    parser.addoption(
        "--no-cache",
        action="store_true",
        default=False,
        help="disable validation caching (always perform fresh validation)",
    )
    parser.addoption(
        "--clear-cache",
        action="store_true",
        default=False,
        help="clear validation cache before running tests",
    )


def pytest_collection_modifyitems(config, items):
    """
    Skip integration tests unless --integration flag is provided.
    Skip link validation tests unless --link-validation flag is provided.
    """
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
    if not config.getoption("--link-validation"):
        skip_link_validation = pytest.mark.skip(
            reason="need --link-validation option to run"
        )
        for item in items:
            if "link_validation" in item.keywords:
                item.add_marker(skip_link_validation)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (requires --integration)",
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "link_validation: marks tests as link validation tests (requires --link-validation)",
    )
    config.addinivalue_line(
        "markers",
        "link_validation_slow: marks tests as slow link validation tests (full downloads)",
    )


# ============================================================================
# Shared Test Fixtures
# ============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_workspace(temp_dir: Path) -> Path:
    """Create temporary workspace with standard structure."""
    workspace = temp_dir / "workspace"
    workspace.mkdir()

    # Create standard directories
    (workspace / ".toolchainkit").mkdir()
    (workspace / "build").mkdir()
    (workspace / "src").mkdir()

    # Create minimal CMakeLists.txt
    cmake_content = """cmake_minimum_required(VERSION 3.20)
project(TestProject CXX)
add_executable(test_app src/main.cpp)
"""
    (workspace / "CMakeLists.txt").write_text(cmake_content)

    # Create minimal main.cpp
    cpp_content = """#include <iostream>
int main() {
    std::cout << "Hello, Test!" << std::endl;
    return 0;
}
"""
    (workspace / "src" / "main.cpp").write_text(cpp_content)

    return workspace


@pytest.fixture
def sample_config_yaml(temp_dir: Path) -> Path:
    """Create sample toolchainkit.yaml configuration."""
    config_content = """version: 1
project:
  name: test-project
  language: cpp

toolchains:
  - name: llvm-18
    type: llvm
    version: "18.1.8"

build:
  generator: Ninja
  configurations:
    - Debug
    - Release
"""
    config_file = temp_dir / "toolchainkit.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def isolated_home(temp_dir: Path, monkeypatch) -> Path:
    """Create isolated home directory for tests."""
    fake_home = temp_dir / "home"
    fake_home.mkdir()

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    return fake_home


@pytest.fixture
def no_network(monkeypatch):
    """Disable network access for tests."""
    import socket

    def guard(*args, **kwargs):
        raise RuntimeError("Network access not allowed in this test")

    monkeypatch.setattr(socket, "socket", guard)


@pytest.fixture(scope="session", autouse=True)
def initialize_core_components():
    """Initialize core compiler strategies and package managers for all tests."""
    try:
        from toolchainkit.core.initialization import initialize_core
        from toolchainkit.plugins.registry import get_global_registry

        registry = get_global_registry()
        initialize_core(registry)
    except ImportError:
        pass  # If modules not available, skip initialization

    yield


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset any module-level caches between tests."""
    # Import modules that use caching
    try:
        from toolchainkit.core import platform

        # Clear lru_cache decorated functions
        if hasattr(platform.detect_platform, "cache_clear"):
            platform.detect_platform.cache_clear()
    except (ImportError, AttributeError):
        pass

    yield

    # Cleanup after test (if needed in the future)
