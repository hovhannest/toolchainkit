"""
Unit tests for lock file generation and verification module.

Tests lock file generation, saving, loading, verification, and diff operations.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from toolchainkit.config.lockfile import (
    LockFileManager,
    LockFile,
    LockedComponent,
    LockFileError,
)


class TestLockedComponent:
    """Tests for LockedComponent dataclass."""

    def test_default_values(self):
        """Test LockedComponent with minimal fields."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        assert comp.url == "https://example.com/file.tar.gz"
        assert comp.sha256 == "abc123"
        assert comp.size_bytes == 1024
        assert comp.version is None
        assert comp.verified is False
        assert comp.verification_date is None

    def test_custom_values(self):
        """Test LockedComponent with all fields."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="1.2.3",
            verified=True,
            verification_date="2025-11-18T10:30:00",
        )

        assert comp.version == "1.2.3"
        assert comp.verified is True
        assert comp.verification_date == "2025-11-18T10:30:00"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="1.2.3",
            verified=True,
            verification_date="2025-11-18T10:30:00",
        )

        data = comp.to_dict()

        assert data["url"] == "https://example.com/file.tar.gz"
        assert data["sha256"] == "abc123"
        assert data["size_bytes"] == 1024
        assert data["version"] == "1.2.3"
        assert data["verified"] is True
        assert data["verification_date"] == "2025-11-18T10:30:00"

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        data = comp.to_dict()

        assert "url" in data
        assert "sha256" in data
        assert "size_bytes" in data
        assert "version" not in data
        assert "verified" not in data or data["verified"] is False
        assert "verification_date" not in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "url": "https://example.com/file.tar.gz",
            "sha256": "abc123",
            "size_bytes": 1024,
            "version": "1.2.3",
            "verified": True,
            "verification_date": "2025-11-18T10:30:00",
        }

        comp = LockedComponent.from_dict(data)

        assert comp.url == "https://example.com/file.tar.gz"
        assert comp.sha256 == "abc123"
        assert comp.size_bytes == 1024
        assert comp.version == "1.2.3"
        assert comp.verified is True
        assert comp.verification_date == "2025-11-18T10:30:00"

    def test_from_dict_minimal(self):
        """Test from_dict with minimal fields."""
        data = {
            "url": "https://example.com/file.tar.gz",
            "sha256": "abc123",
            "size_bytes": 1024,
        }

        comp = LockedComponent.from_dict(data)

        assert comp.version is None
        assert comp.verified is False
        assert comp.verification_date is None


class TestLockFile:
    """Tests for LockFile dataclass."""

    def test_default_values(self):
        """Test LockFile default values."""
        lock = LockFile()

        assert lock.version == 1
        assert lock.generated is None
        assert lock.platform is None
        assert lock.toolchains == {}
        assert lock.build_tools == {}
        assert lock.packages == {}
        assert lock.metadata == {}

    def test_custom_values(self):
        """Test LockFile with custom values."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock = LockFile(
            version=1,
            generated="2025-11-18T10:30:00",
            platform="linux-x64-glibc",
            toolchains={"llvm-18": comp},
            build_tools={"ninja": comp},
            packages={"boost": {"version": "1.83.0"}},
            metadata={"generator": "ToolchainKit"},
        )

        assert lock.platform == "linux-x64-glibc"
        assert "llvm-18" in lock.toolchains
        assert "ninja" in lock.build_tools
        assert "boost" in lock.packages
        assert lock.metadata["generator"] == "ToolchainKit"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        comp = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="1.2.3",
        )

        lock = LockFile(toolchains={"llvm-18": comp}, build_tools={"ninja": comp})

        data = lock.to_dict()

        assert "version" in data
        assert "toolchains" in data
        assert "build_tools" in data
        assert "llvm-18" in data["toolchains"]
        assert "ninja" in data["build_tools"]

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "version": 1,
            "generated": "2025-11-18T10:30:00",
            "platform": "linux-x64-glibc",
            "toolchains": {
                "llvm-18": {
                    "url": "https://example.com/file.tar.gz",
                    "sha256": "abc123",
                    "size_bytes": 1024,
                }
            },
            "build_tools": {},
            "packages": {},
            "metadata": {},
        }

        lock = LockFile.from_dict(data)

        assert lock.version == 1
        assert lock.platform == "linux-x64-glibc"
        assert "llvm-18" in lock.toolchains
        assert isinstance(lock.toolchains["llvm-18"], LockedComponent)


class TestLockFileManagerInit:
    """Tests for LockFileManager initialization."""

    def test_init_with_valid_path(self, temp_dir):
        """Test initialization with valid project root."""
        manager = LockFileManager(temp_dir)

        assert manager.project_root == temp_dir.resolve()
        assert manager.lock_file_path == temp_dir.resolve() / "toolchainkit.lock"

    def test_init_with_string_path(self, temp_dir):
        """Test initialization with string path."""
        manager = LockFileManager(str(temp_dir))

        assert manager.project_root == temp_dir.resolve()
        assert isinstance(manager.project_root, Path)

    def test_init_with_nonexistent_path(self, temp_dir):
        """Test initialization with nonexistent path."""
        nonexistent = temp_dir / "nonexistent"

        with pytest.raises(LockFileError) as exc_info:
            LockFileManager(nonexistent)

        assert "does not exist" in str(exc_info.value)

    def test_init_with_file_path(self, temp_dir):
        """Test initialization with file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("test")

        with pytest.raises(LockFileError) as exc_info:
            LockFileManager(file_path)

        assert "not a directory" in str(exc_info.value)


class TestLockFileGeneration:
    """Tests for lock file generation."""

    def test_generate_minimal(self, temp_dir):
        """Test generating lock file with minimal info."""
        manager = LockFileManager(temp_dir)

        config = Mock()
        platform = Mock()
        platform.platform_string.return_value = "linux-x64-glibc"

        toolchain_info = {
            "llvm-18": {
                "url": "https://example.com/llvm-18.tar.gz",
                "sha256": "abc123",
                "size_bytes": 1024,
                "version": "18.0.0",
            }
        }

        lock = manager.generate(config, platform, toolchain_info)

        assert lock.version == 1
        assert lock.generated is not None
        assert lock.platform == "linux-x64-glibc"
        assert "llvm-18" in lock.toolchains
        assert lock.toolchains["llvm-18"].url == "https://example.com/llvm-18.tar.gz"

    def test_generate_with_build_tools(self, temp_dir):
        """Test generating lock file with build tools."""
        manager = LockFileManager(temp_dir)

        config = Mock()
        platform = Mock()
        platform.platform_string.return_value = "linux-x64-glibc"

        toolchain_info = {
            "llvm-18": {
                "url": "https://example.com/llvm.tar.gz",
                "sha256": "abc123",
                "size_bytes": 1024,
            }
        }

        build_tools_info = {
            "ninja": {
                "url": "https://example.com/ninja.zip",
                "sha256": "def456",
                "size_bytes": 512,
                "version": "1.11.1",
            }
        }

        lock = manager.generate(config, platform, toolchain_info, build_tools_info)

        assert "ninja" in lock.build_tools
        assert lock.build_tools["ninja"].version == "1.11.1"

    def test_generate_includes_metadata(self, temp_dir):
        """Test that generated lock file includes metadata."""
        manager = LockFileManager(temp_dir)

        config = Mock()
        platform = Mock()
        platform.platform_string.return_value = "linux-x64"

        toolchain_info = {
            "gcc-13": {
                "url": "https://example.com/gcc.tar.gz",
                "sha256": "abc123",
                "size_bytes": 1024,
            }
        }

        lock = manager.generate(config, platform, toolchain_info)

        assert "generator" in lock.metadata
        assert "ToolchainKit" in lock.metadata["generator"]


class TestLockFileSave:
    """Tests for lock file saving."""

    def test_save_creates_file(self, temp_dir):
        """Test that save creates lock file."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock = LockFile(platform="linux-x64", toolchains={"llvm-18": comp})

        manager.save(lock)

        assert manager.lock_file_path.exists()

    def test_save_writes_yaml(self, temp_dir):
        """Test that save writes valid YAML."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="1.2.3",
        )

        lock = LockFile(platform="linux-x64", toolchains={"llvm-18": comp})

        manager.save(lock)

        # Load and verify YAML
        with open(manager.lock_file_path, "r") as f:
            data = yaml.safe_load(f)

        assert data["platform"] == "linux-x64"
        assert "llvm-18" in data["toolchains"]
        assert data["toolchains"]["llvm-18"]["sha256"] == "abc123"

    def test_save_overwrites_existing(self, temp_dir):
        """Test that save overwrites existing lock file."""
        manager = LockFileManager(temp_dir)

        # Save first lock
        lock1 = LockFile(platform="linux-x64")
        manager.save(lock1)

        # Save second lock
        lock2 = LockFile(platform="windows-x64")
        manager.save(lock2)

        # Verify second lock
        with open(manager.lock_file_path, "r") as f:
            data = yaml.safe_load(f)

        assert data["platform"] == "windows-x64"


class TestLockFileLoad:
    """Tests for lock file loading."""

    def test_load_missing_file(self, temp_dir):
        """Test loading when lock file doesn't exist."""
        manager = LockFileManager(temp_dir)
        lock = manager.load()

        assert lock is None

    def test_load_existing_file(self, temp_dir):
        """Test loading existing lock file."""
        manager = LockFileManager(temp_dir)

        # Create lock file
        data = {
            "version": 1,
            "platform": "linux-x64",
            "toolchains": {
                "llvm-18": {
                    "url": "https://example.com/file.tar.gz",
                    "sha256": "abc123",
                    "size_bytes": 1024,
                }
            },
            "build_tools": {},
            "packages": {},
            "metadata": {},
        }

        with open(manager.lock_file_path, "w") as f:
            yaml.safe_dump(data, f)

        # Load
        lock = manager.load()

        assert lock is not None
        assert lock.platform == "linux-x64"
        assert "llvm-18" in lock.toolchains

    def test_load_corrupted_yaml(self, temp_dir):
        """Test loading corrupted YAML file."""
        manager = LockFileManager(temp_dir)

        # Write invalid YAML
        manager.lock_file_path.write_text("{ invalid yaml")

        with pytest.raises(LockFileError) as exc_info:
            manager.load()

        assert "Failed to load lock file" in str(exc_info.value)

    def test_load_roundtrip(self, temp_dir):
        """Test save and load roundtrip."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="1.2.3",
            verified=True,
        )

        lock = LockFile(
            platform="linux-x64",
            toolchains={"llvm-18": comp},
            build_tools={"ninja": comp},
        )

        manager.save(lock)
        loaded = manager.load()

        assert loaded.platform == lock.platform
        assert "llvm-18" in loaded.toolchains
        assert "ninja" in loaded.build_tools
        assert loaded.toolchains["llvm-18"].sha256 == "abc123"


class TestLockFileVerification:
    """Tests for lock file verification."""

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_verify_matching_installation(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test verification with matching installation."""
        # Setup mocks
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain_info.return_value = {
            "path": str(temp_dir / "llvm"),
            "hash": "abc123",
        }
        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock = LockFile(toolchains={"llvm-18": comp})

        verified, issues = manager.verify(lock)

        assert verified is True
        assert issues == []

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_verify_missing_toolchain(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test verification detects missing toolchain."""
        # Setup mocks
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain_info.return_value = None
        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock = LockFile(toolchains={"llvm-18": comp})

        verified, issues = manager.verify(lock)

        assert verified is False
        assert len(issues) == 1
        assert "not installed" in issues[0]

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_verify_hash_mismatch(self, mock_cache_dir, mock_registry_class, temp_dir):
        """Test verification detects hash mismatch."""
        # Setup mocks
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain.return_value = {
            "path": str(temp_dir / "llvm"),
            "hash": "wrong_hash",
        }
        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock = LockFile(toolchains={"llvm-18": comp})

        verified, issues = manager.verify(lock)

        assert verified is False
        assert len(issues) == 1
        assert "hash mismatch" in issues[0].lower()


class TestLockFileDiff:
    """Tests for lock file diff computation."""

    def test_diff_identical_files(self, temp_dir):
        """Test diff of identical lock files."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock1 = LockFile(toolchains={"llvm-18": comp})
        lock2 = LockFile(toolchains={"llvm-18": comp})

        changes = manager.diff(lock1, lock2)

        assert changes["toolchains"]["added"] == []
        assert changes["toolchains"]["removed"] == []
        assert changes["toolchains"]["modified"] == []

    def test_diff_added_toolchain(self, temp_dir):
        """Test diff detects added toolchain."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock1 = LockFile()
        lock2 = LockFile(toolchains={"llvm-18": comp})

        changes = manager.diff(lock1, lock2)

        assert "llvm-18" in changes["toolchains"]["added"]
        assert changes["toolchains"]["removed"] == []

    def test_diff_removed_toolchain(self, temp_dir):
        """Test diff detects removed toolchain."""
        manager = LockFileManager(temp_dir)

        comp = LockedComponent(
            url="https://example.com/file.tar.gz", sha256="abc123", size_bytes=1024
        )

        lock1 = LockFile(toolchains={"llvm-18": comp})
        lock2 = LockFile()

        changes = manager.diff(lock1, lock2)

        assert "llvm-18" in changes["toolchains"]["removed"]
        assert changes["toolchains"]["added"] == []

    def test_diff_modified_toolchain(self, temp_dir):
        """Test diff detects modified toolchain."""
        manager = LockFileManager(temp_dir)

        comp1 = LockedComponent(
            url="https://example.com/file.tar.gz",
            sha256="abc123",
            size_bytes=1024,
            version="18.0.0",
        )

        comp2 = LockedComponent(
            url="https://example.com/file2.tar.gz",
            sha256="def456",
            size_bytes=2048,
            version="18.1.0",
        )

        lock1 = LockFile(toolchains={"llvm-18": comp1})
        lock2 = LockFile(toolchains={"llvm-18": comp2})

        changes = manager.diff(lock1, lock2)

        assert len(changes["toolchains"]["modified"]) == 1
        mod = changes["toolchains"]["modified"][0]
        assert mod["name"] == "llvm-18"
        assert mod["old_version"] == "18.0.0"
        assert mod["new_version"] == "18.1.0"

    def test_diff_build_tools(self, temp_dir):
        """Test diff for build tools."""
        manager = LockFileManager(temp_dir)

        comp1 = LockedComponent(
            url="https://example.com/ninja.zip", sha256="abc123", size_bytes=1024
        )

        comp2 = LockedComponent(
            url="https://example.com/cmake.zip", sha256="def456", size_bytes=2048
        )

        lock1 = LockFile(build_tools={"ninja": comp1})
        lock2 = LockFile(build_tools={"cmake": comp2})

        changes = manager.diff(lock1, lock2)

        assert "cmake" in changes["build_tools"]["added"]
        assert "ninja" in changes["build_tools"]["removed"]


class TestLockFileHelpers:
    """Tests for helper methods."""

    def test_find_tool_path_project_local(self, temp_dir):
        """Test finding tool in project-local directory."""
        import os

        manager = LockFileManager(temp_dir)

        # Create tool in project
        tools_dir = temp_dir / ".toolchainkit" / "tools"
        tools_dir.mkdir(parents=True)
        tool_name = "ninja.exe" if os.name == "nt" else "ninja"
        tool_path = tools_dir / tool_name
        tool_path.write_text("ninja binary")

        found = manager._find_tool_path("ninja")

        assert found is not None
        assert found.exists()

    def test_find_tool_path_missing(self, temp_dir):
        """Test finding missing tool."""
        manager = LockFileManager(temp_dir)

        found = manager._find_tool_path("nonexistent")

        assert found is None

    def test_get_platform_string(self, temp_dir):
        """Test getting platform string."""
        manager = LockFileManager(temp_dir)

        platform = Mock()
        platform.platform_string.return_value = "linux-x64-glibc"

        result = manager._get_platform_string(platform)

        assert result == "linux-x64-glibc"

    def test_get_python_version(self, temp_dir):
        """Test getting Python version."""
        manager = LockFileManager(temp_dir)

        version = manager._get_python_version()

        assert "." in version
        parts = version.split(".")
        assert len(parts) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
