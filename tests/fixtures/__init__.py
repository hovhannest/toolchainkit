"""Test fixtures for ToolchainKit tests.

This package provides reusable pytest fixtures for testing ToolchainKit components.
Fixtures are organized by type:

- toolchains: Mock toolchain directories (LLVM, GCC, MSVC)
- projects: CMake project templates (minimal, with tests, with dependencies)
- directories: Directory structures (global cache, project-local)

Import fixtures in your tests using:
    from tests.fixtures.toolchains import mock_llvm_toolchain
    from tests.fixtures.projects import minimal_cmake_project
    from tests.fixtures.directories import mock_global_cache

See README.md for detailed usage examples.
"""

__all__ = [
    "toolchains",
    "projects",
    "directories",
]
