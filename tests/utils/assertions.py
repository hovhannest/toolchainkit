"""
Custom assertions for ToolchainKit testing.

This module provides domain-specific assertions that make tests
more readable and provide better error messages.
"""

from pathlib import Path
from typing import List, Union


def assert_file_exists(path: Union[Path, str], msg: str = ""):
    """
    Assert that file exists.

    Args:
        path: File path to check
        msg: Optional custom error message

    Raises:
        AssertionError: If file doesn't exist or path is not a file
    """
    path = Path(path)
    assert path.exists(), f"File does not exist: {path}. {msg}"
    assert path.is_file(), f"Path is not a file: {path}. {msg}"


def assert_dir_exists(path: Union[Path, str], msg: str = ""):
    """
    Assert that directory exists.

    Args:
        path: Directory path to check
        msg: Optional custom error message

    Raises:
        AssertionError: If directory doesn't exist or path is not a directory
    """
    path = Path(path)
    assert path.exists(), f"Directory does not exist: {path}. {msg}"
    assert path.is_dir(), f"Path is not a directory: {path}. {msg}"


def assert_files_equal(path1: Union[Path, str], path2: Union[Path, str]):
    """
    Assert that two files have identical content.

    Args:
        path1: First file path
        path2: Second file path

    Raises:
        AssertionError: If files don't exist or have different content
    """
    path1 = Path(path1)
    path2 = Path(path2)

    assert path1.exists(), f"First file does not exist: {path1}"
    assert path2.exists(), f"Second file does not exist: {path2}"

    content1 = path1.read_bytes()
    content2 = path2.read_bytes()

    assert content1 == content2, (
        f"Files differ:\n"
        f"  File 1: {path1} ({len(content1)} bytes)\n"
        f"  File 2: {path2} ({len(content2)} bytes)"
    )


def assert_cmake_variable(cmake_file: Union[Path, str], variable: str, value: str):
    """
    Assert CMake file contains specific variable setting.

    Args:
        cmake_file: Path to CMake file
        variable: Variable name (e.g., "CMAKE_C_COMPILER")
        value: Expected value

    Raises:
        AssertionError: If variable not found or has different value
    """
    cmake_file = Path(cmake_file)
    assert cmake_file.exists(), f"CMake file does not exist: {cmake_file}"

    content = cmake_file.read_text()
    expected = f'set({variable} "{value}")'

    assert expected in content, (
        f"CMake variable not found:\n"
        f"  Variable: {variable}\n"
        f"  Expected value: {value}\n"
        f"  Expected line: {expected}\n"
        f"  File: {cmake_file}"
    )


def assert_command_output(output: str, expected_phrases: List[str]):
    """
    Assert command output contains expected phrases.

    Args:
        output: Command output to check
        expected_phrases: List of phrases that should appear in output

    Raises:
        AssertionError: If any phrase is not found in output
    """
    for phrase in expected_phrases:
        assert phrase in output, (
            f"Expected phrase not in output:\n"
            f"  Phrase: '{phrase}'\n"
            f"  Output: {output[:200]}..."
        )


def assert_json_contains(json_data: dict, **expected_values):
    """
    Assert JSON/dict contains expected key-value pairs.

    Args:
        json_data: JSON data (dict) to check
        **expected_values: Key-value pairs to verify

    Raises:
        AssertionError: If any key is missing or has wrong value
    """
    for key, expected_value in expected_values.items():
        assert key in json_data, f"Key '{key}' not found in JSON data"
        actual_value = json_data[key]
        assert actual_value == expected_value, (
            f"Value mismatch for key '{key}':\n"
            f"  Expected: {expected_value}\n"
            f"  Actual: {actual_value}"
        )


def assert_lines_match(text: str, patterns: List[str]):
    """
    Assert text contains lines matching patterns (supports wildcards).

    Args:
        text: Text to search
        patterns: List of patterns to match (supports * wildcards)

    Raises:
        AssertionError: If any pattern doesn't match any line
    """
    lines = text.splitlines()

    for pattern in patterns:
        found = False
        if "*" in pattern:
            # Simple wildcard matching
            import re

            regex_pattern = pattern.replace("*", ".*")
            for line in lines:
                if re.search(regex_pattern, line):
                    found = True
                    break
        else:
            # Exact substring match
            found = any(pattern in line for line in lines)

        assert found, (
            f"Pattern not found in text:\n"
            f"  Pattern: '{pattern}'\n"
            f"  Text: {text[:500]}..."
        )
