"""
Integration tests for lock file generation and verification.

Tests real-world scenarios with actual file system and toolchains.
"""

import pytest
import yaml
from unittest.mock import Mock, patch

from toolchainkit.config.lockfile import LockFileManager, LockFile, LockedComponent


pytestmark = pytest.mark.integration


class TestLockFileIntegration:
    """Integration tests for lock file operations."""

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_generate_save_load_cycle(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test complete generate -> save -> load cycle."""
        # Setup
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        config = Mock()
        platform = Mock()
        platform.platform_string.return_value = "linux-x64-glibc"

        toolchain_info = {
            "llvm-18": {
                "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-18.0.0/llvm-18.tar.gz",
                "sha256": "abc123def456",
                "size_bytes": 1024000,
                "version": "18.0.0",
            },
            "gcc-13": {
                "url": "https://ftp.gnu.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.gz",
                "sha256": "def456abc789",
                "size_bytes": 2048000,
                "version": "13.2.0",
            },
        }

        build_tools_info = {
            "ninja": {
                "url": "https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-linux.zip",
                "sha256": "ninja123",
                "size_bytes": 512000,
                "version": "1.11.1",
            }
        }

        # Generate
        lock = manager.generate(config, platform, toolchain_info, build_tools_info)

        assert lock.platform == "linux-x64-glibc"
        assert len(lock.toolchains) == 2
        assert len(lock.build_tools) == 1

        # Save
        manager.save(lock)
        assert manager.lock_file_path.exists()

        # Load
        loaded = manager.load()
        assert loaded is not None
        assert loaded.platform == lock.platform
        assert len(loaded.toolchains) == 2
        assert len(loaded.build_tools) == 1
        assert loaded.toolchains["llvm-18"].version == "18.0.0"
        assert loaded.toolchains["gcc-13"].version == "13.2.0"
        assert loaded.build_tools["ninja"].version == "1.11.1"

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_verification_workflow(self, mock_cache_dir, mock_registry_class, temp_dir):
        """Test lock file verification workflow."""
        # Setup
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()

        # Simulate installed toolchains
        mock_registry.get_toolchain_info.side_effect = lambda name: {
            "llvm-18": {"path": str(temp_dir / "llvm"), "hash": "abc123"},
            "gcc-13": {"path": str(temp_dir / "gcc"), "hash": "def456"},
        }.get(name)

        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        # Create lock file
        lock = LockFile(
            platform="linux-x64-glibc",
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm.tar.gz",
                    sha256="abc123",
                    size_bytes=1024000,
                    version="18.0.0",
                ),
                "gcc-13": LockedComponent(
                    url="https://example.com/gcc.tar.gz",
                    sha256="def456",
                    size_bytes=2048000,
                    version="13.2.0",
                ),
            },
        )

        # Verify
        verified, issues = manager.verify(lock)

        assert verified is True
        assert issues == []

    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.core.directory.get_global_cache_dir")
    def test_verification_detects_missing(
        self, mock_cache_dir, mock_registry_class, temp_dir
    ):
        """Test verification detects missing toolchains."""
        # Setup
        mock_cache_dir.return_value = temp_dir / ".toolchainkit"
        mock_registry = Mock()
        mock_registry.get_toolchain_info.return_value = None  # Simulate missing
        mock_registry_class.return_value = mock_registry

        manager = LockFileManager(temp_dir)

        # Create lock file
        lock = LockFile(
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm.tar.gz",
                    sha256="abc123",
                    size_bytes=1024000,
                )
            }
        )

        # Verify
        verified, issues = manager.verify(lock)

        assert verified is False
        assert len(issues) == 1
        assert "not installed" in issues[0]

    def test_diff_workflow(self, temp_dir):
        """Test lock file diff workflow."""
        manager = LockFileManager(temp_dir)

        # Create two lock files with differences
        lock_v1 = LockFile(
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm-18.0.0.tar.gz",
                    sha256="abc123",
                    size_bytes=1024000,
                    version="18.0.0",
                ),
                "gcc-13": LockedComponent(
                    url="https://example.com/gcc-13.2.0.tar.gz",
                    sha256="def456",
                    size_bytes=2048000,
                    version="13.2.0",
                ),
            },
            build_tools={
                "ninja": LockedComponent(
                    url="https://example.com/ninja-1.11.0.zip",
                    sha256="ninja111",
                    size_bytes=512000,
                    version="1.11.0",
                )
            },
        )

        lock_v2 = LockFile(
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm-18.1.0.tar.gz",
                    sha256="abc789",  # Different hash
                    size_bytes=1048000,
                    version="18.1.0",  # New version
                ),
                # gcc-13 removed
                "clang-18": LockedComponent(  # New toolchain
                    url="https://example.com/clang-18.tar.gz",
                    sha256="clang123",
                    size_bytes=512000,
                    version="18.0.0",
                ),
            },
            build_tools={
                "ninja": LockedComponent(
                    url="https://example.com/ninja-1.11.1.zip",
                    sha256="ninja123",  # Different hash
                    size_bytes=512000,
                    version="1.11.1",  # New version
                ),
                "cmake": LockedComponent(  # New build tool
                    url="https://example.com/cmake.zip",
                    sha256="cmake123",
                    size_bytes=1024000,
                    version="3.27.0",
                ),
            },
        )

        # Compute diff
        changes = manager.diff(lock_v1, lock_v2)

        # Verify toolchain changes
        assert "clang-18" in changes["toolchains"]["added"]
        assert "gcc-13" in changes["toolchains"]["removed"]
        assert len(changes["toolchains"]["modified"]) == 1
        assert changes["toolchains"]["modified"][0]["name"] == "llvm-18"
        assert changes["toolchains"]["modified"][0]["old_version"] == "18.0.0"
        assert changes["toolchains"]["modified"][0]["new_version"] == "18.1.0"

        # Verify build tool changes
        assert "cmake" in changes["build_tools"]["added"]
        assert len(changes["build_tools"]["modified"]) == 1
        assert changes["build_tools"]["modified"][0]["name"] == "ninja"

    def test_yaml_format_compatibility(self, temp_dir):
        """Test that lock files use standard YAML format."""
        manager = LockFileManager(temp_dir)

        # Create lock file
        lock = LockFile(
            version=1,
            platform="linux-x64-glibc",
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm.tar.gz",
                    sha256="abc123",
                    size_bytes=1024000,
                    version="18.0.0",
                )
            },
        )

        # Save
        manager.save(lock)

        # Load with standard YAML parser
        with open(manager.lock_file_path, "r") as f:
            data = yaml.safe_load(f)

        # Verify structure
        assert data["version"] == 1
        assert data["platform"] == "linux-x64-glibc"
        assert "llvm-18" in data["toolchains"]
        assert data["toolchains"]["llvm-18"]["sha256"] == "abc123"
        assert data["toolchains"]["llvm-18"]["version"] == "18.0.0"

    def test_multiple_projects(self, temp_dir):
        """Test lock files in multiple project directories."""
        # Create two project directories
        project1 = temp_dir / "project1"
        project2 = temp_dir / "project2"
        project1.mkdir()
        project2.mkdir()

        manager1 = LockFileManager(project1)
        manager2 = LockFileManager(project2)

        # Create different lock files
        lock1 = LockFile(
            platform="linux-x64",
            toolchains={
                "llvm-18": LockedComponent(
                    url="https://example.com/llvm.tar.gz",
                    sha256="abc123",
                    size_bytes=1024,
                )
            },
        )

        lock2 = LockFile(
            platform="windows-x64",
            toolchains={
                "gcc-13": LockedComponent(
                    url="https://example.com/gcc.tar.gz",
                    sha256="def456",
                    size_bytes=2048,
                )
            },
        )

        # Save to different projects
        manager1.save(lock1)
        manager2.save(lock2)

        # Verify isolation
        loaded1 = manager1.load()
        loaded2 = manager2.load()

        assert loaded1.platform == "linux-x64"
        assert loaded2.platform == "windows-x64"
        assert "llvm-18" in loaded1.toolchains
        assert "gcc-13" in loaded2.toolchains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
