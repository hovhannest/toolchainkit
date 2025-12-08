"""
Unit tests for test utility helpers.

Tests the utility functions to ensure they work correctly.
"""

import pytest

from tests.utils.helpers import (
    has_command,
    create_file_tree,
    compare_files,
    create_empty_file,
)
from tests.utils.mocks import (
    create_mock_registry,
    create_mock_toolchain_entry,
    create_mock_state,
    write_mock_json,
)


class TestHelpers:
    """Test helper utilities."""

    def test_has_command_python(self):
        """Test has_command with Python (always available in tests)."""
        assert has_command("python") or has_command("python3")

    def test_has_command_nonexistent(self):
        """Test has_command returns False for nonexistent command."""
        assert not has_command("this_command_does_not_exist_xyz123")

    def test_create_file_tree_simple(self, tmp_path):
        """Test creating simple file tree."""
        create_file_tree(
            tmp_path,
            {
                "file1.txt": "content 1",
                "file2.txt": "content 2",
            },
        )

        assert (tmp_path / "file1.txt").read_text() == "content 1"
        assert (tmp_path / "file2.txt").read_text() == "content 2"

    def test_create_file_tree_with_dirs(self, tmp_path):
        """Test creating file tree with directories."""
        create_file_tree(
            tmp_path,
            {
                "src/main.cpp": "#include <iostream>",
                "include/": None,  # Directory
                "include/header.h": "#pragma once",
            },
        )

        assert (tmp_path / "src" / "main.cpp").exists()
        assert (tmp_path / "include").is_dir()
        assert (tmp_path / "include" / "header.h").exists()

    def test_create_file_tree_binary(self, tmp_path):
        """Test creating files with binary content."""
        binary_data = b"\x00\x01\x02\x03\x04"

        create_file_tree(
            tmp_path,
            {
                "data.bin": binary_data,
            },
        )

        assert (tmp_path / "data.bin").read_bytes() == binary_data

    def test_compare_files_identical(self, tmp_path):
        """Test comparing identical files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("same content")
        file2.write_text("same content")

        assert compare_files(file1, file2)

    def test_compare_files_different(self, tmp_path):
        """Test comparing different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("content 1")
        file2.write_text("content 2")

        assert not compare_files(file1, file2)

    def test_compare_files_whitespace(self, tmp_path):
        """Test comparing files with whitespace differences."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("word1 word2 word3")
        file2.write_text("word1  word2   word3")  # Extra spaces

        assert not compare_files(file1, file2, ignore_whitespace=False)
        assert compare_files(file1, file2, ignore_whitespace=True)

    def test_create_empty_file(self, tmp_path):
        """Test creating empty file."""
        file_path = tmp_path / "empty.txt"
        create_empty_file(file_path)

        assert file_path.exists()
        assert file_path.stat().st_size == 0

    def test_create_empty_file_with_size(self, tmp_path):
        """Test creating file with specific size."""
        file_path = tmp_path / "sized.dat"
        size = 1024  # 1KB

        create_empty_file(file_path, size=size)

        assert file_path.exists()
        assert file_path.stat().st_size == size


class TestMocks:
    """Test mock utilities."""

    def test_create_mock_registry_empty(self):
        """Test creating empty registry."""
        registry = create_mock_registry()

        assert registry["version"] == "1.0"
        assert registry["toolchains"] == {}
        assert "metadata" in registry

    def test_create_mock_registry_with_toolchains(self):
        """Test creating registry with toolchains."""
        toolchains = {
            "llvm-18": {"name": "llvm", "version": "18.1.8"},
            "gcc-13": {"name": "gcc", "version": "13.2.0"},
        }

        registry = create_mock_registry(toolchains)

        assert len(registry["toolchains"]) == 2
        assert "llvm-18" in registry["toolchains"]
        assert "gcc-13" in registry["toolchains"]

    def test_create_mock_toolchain_entry(self):
        """Test creating toolchain entry."""
        entry = create_mock_toolchain_entry(
            name="llvm", version="18.1.8", platform="linux-x64", reference_count=3
        )

        assert entry["name"] == "llvm"
        assert entry["version"] == "18.1.8"
        assert entry["platform"] == "linux-x64"
        assert entry["id"] == "llvm-18.1.8-linux-x64"
        assert entry["reference_count"] == 3
        assert entry["type"] == "llvm"
        assert "path" in entry
        assert "install_time" in entry

    def test_create_mock_toolchain_entry_with_extras(self):
        """Test creating toolchain entry with extra fields."""
        entry = create_mock_toolchain_entry(
            name="gcc",
            version="13.2.0",
            platform="linux-x64",
            sha256="abc123def456",
            size=123456789,
        )

        assert entry["sha256"] == "abc123def456"
        assert entry["size"] == 123456789

    def test_create_mock_state(self):
        """Test creating mock state."""
        state = create_mock_state(
            bootstrap_complete=True,
            active_toolchain="llvm-18.1.8-linux-x64",
            config_hash="abc123",
        )

        assert state["bootstrap_complete"] is True
        assert state["active_toolchain"] == "llvm-18.1.8-linux-x64"
        assert state["config_hash"] == "abc123"
        assert state["version"] == "1.0"

    def test_write_mock_json(self, tmp_path):
        """Test writing mock JSON to file."""
        data = create_mock_registry({"llvm-18": {"name": "llvm"}})
        json_file = tmp_path / "registry.json"

        write_mock_json(json_file, data)

        assert json_file.exists()

        # Verify can be loaded
        import json

        loaded = json.loads(json_file.read_text())
        assert loaded == data


class TestIntegration:
    """Integration tests combining multiple utilities."""

    def test_create_workspace_with_state(self, tmp_path):
        """Test creating complete workspace with state files."""
        # Create project structure
        create_file_tree(
            tmp_path,
            {
                "src/main.cpp": "#include <iostream>\nint main() { return 0; }",
                "CMakeLists.txt": "cmake_minimum_required(VERSION 3.20)",
                ".toolchainkit/": None,
            },
        )

        # Create mock state
        state = create_mock_state(
            bootstrap_complete=True, active_toolchain="llvm-18.1.8-linux-x64"
        )

        # Write state file
        state_file = tmp_path / ".toolchainkit" / "state.json"
        write_mock_json(state_file, state)

        # Verify structure
        assert (tmp_path / "src" / "main.cpp").exists()
        assert (tmp_path / "CMakeLists.txt").exists()
        assert (tmp_path / ".toolchainkit").is_dir()
        assert state_file.exists()

        # Verify state content
        import json

        loaded_state = json.loads(state_file.read_text())
        assert loaded_state["bootstrap_complete"] is True

    def test_create_registry_with_entries(self, tmp_path):
        """Test creating registry with multiple toolchain entries."""
        # Create mock registry
        registry = create_mock_registry(
            {
                "llvm-18.1.8-linux-x64": create_mock_toolchain_entry(
                    name="llvm",
                    version="18.1.8",
                    platform="linux-x64",
                    reference_count=2,
                ),
                "gcc-13.2.0-linux-x64": create_mock_toolchain_entry(
                    name="gcc",
                    version="13.2.0",
                    platform="linux-x64",
                    reference_count=1,
                ),
            }
        )

        # Write registry
        registry_file = tmp_path / "registry.json"
        write_mock_json(registry_file, registry)

        # Verify
        assert registry_file.exists()

        import json

        loaded = json.loads(registry_file.read_text())
        assert len(loaded["toolchains"]) == 2
        assert loaded["toolchains"]["llvm-18.1.8-linux-x64"]["reference_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
