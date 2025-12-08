"""
Test utilities for ToolchainKit testing.

This package provides custom assertions, test data builders, helper utilities,
and mocking utilities to simplify test writing and improve test readability.
"""

from .assertions import (
    assert_file_exists,
    assert_dir_exists,
    assert_files_equal,
    assert_cmake_variable,
    assert_command_output,
)
from .builders import (
    ToolchainBuilder,
    ConfigBuilder,
)
from .helpers import (
    has_command,
    has_cmake,
    has_ninja,
    has_gcc,
    has_clang,
    has_msvc,
    create_file_tree,
    run_command_safe,
    compare_files,
    get_command_version,
    find_executable,
    create_empty_file,
    copy_tree,
)
from .mocks import (
    mock_http_download,
    create_mock_registry,
    create_mock_toolchain_entry,
    create_mock_state,
    create_mock_metadata,
    write_mock_json,
    create_mock_download_info,
    create_mock_config_yaml,
)

__all__ = [
    # Assertions
    "assert_file_exists",
    "assert_dir_exists",
    "assert_files_equal",
    "assert_cmake_variable",
    "assert_command_output",
    # Builders
    "ToolchainBuilder",
    "ConfigBuilder",
    # Helpers
    "has_command",
    "has_cmake",
    "has_ninja",
    "has_gcc",
    "has_clang",
    "has_msvc",
    "create_file_tree",
    "run_command_safe",
    "compare_files",
    "get_command_version",
    "find_executable",
    "create_empty_file",
    "copy_tree",
    # Mocks
    "mock_http_download",
    "create_mock_registry",
    "create_mock_toolchain_entry",
    "create_mock_state",
    "create_mock_metadata",
    "write_mock_json",
    "create_mock_download_info",
    "create_mock_config_yaml",
]
