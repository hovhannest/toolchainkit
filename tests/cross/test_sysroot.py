"""
Unit tests for sysroot management.
"""

import pytest
from unittest.mock import patch
from toolchainkit.cross.sysroot import (
    SysrootSpec,
    SysrootManager,
    SysrootDownloadError,
    SysrootExtractionError,
)


class TestSysrootSpec:
    """Tests for SysrootSpec dataclass."""

    def test_minimal_spec(self):
        """Test creation with minimal required fields."""
        spec = SysrootSpec(
            target="android-arm64",
            version="21",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        assert spec.target == "android-arm64"
        assert spec.version == "21"
        assert spec.url == "https://example.com/sysroot.tar.gz"
        assert spec.hash == "abc123"
        assert spec.extract_path is None

    def test_complete_spec(self):
        """Test creation with all fields."""
        spec = SysrootSpec(
            target="raspberry-pi-armv7",
            version="11",
            url="https://example.com/rpi-sysroot.tar.xz",
            hash="def456",
            extract_path="sysroot",
        )

        assert spec.target == "raspberry-pi-armv7"
        assert spec.version == "11"
        assert spec.url == "https://example.com/rpi-sysroot.tar.xz"
        assert spec.hash == "def456"
        assert spec.extract_path == "sysroot"

    def test_dataclass_fields(self):
        """Test that dataclass has expected fields."""
        spec = SysrootSpec("target", "1.0", "url", "hash")

        assert hasattr(spec, "target")
        assert hasattr(spec, "version")
        assert hasattr(spec, "url")
        assert hasattr(spec, "hash")
        assert hasattr(spec, "extract_path")


class TestSysrootManagerInit:
    """Tests for SysrootManager initialization."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates cache directories."""
        _manager = SysrootManager(temp_dir)

        assert (temp_dir / "sysroots").exists()
        assert (temp_dir / "sysroots" / "downloads").exists()

    def test_init_with_existing_directories(self, temp_dir):
        """Test initialization with existing directories."""
        cache_dir = temp_dir / "sysroots"
        cache_dir.mkdir(parents=True)
        downloads_dir = cache_dir / "downloads"
        downloads_dir.mkdir()

        manager = SysrootManager(temp_dir)

        assert manager.cache_dir == cache_dir
        assert manager.downloads_dir == downloads_dir

    def test_cache_dir_property(self, temp_dir):
        """Test cache_dir property."""
        manager = SysrootManager(temp_dir)

        assert manager.cache_dir == temp_dir / "sysroots"
        assert manager.cache_dir.exists()


class TestSysrootDownload:
    """Tests for sysroot download functionality."""

    @patch("toolchainkit.cross.sysroot.download_file")
    @patch("toolchainkit.cross.sysroot.extract_archive")
    def test_download_success(self, mock_extract, mock_download, temp_dir):
        """Test successful sysroot download."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        # Mock extract to create a dummy directory
        def mock_extract_side_effect(archive_path, destination, **kwargs):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "usr").mkdir()
            (destination / "usr" / "include").mkdir()

        mock_extract.side_effect = mock_extract_side_effect

        result = manager.download_sysroot(spec)

        assert result == temp_dir / "sysroots" / "test-target-1.0"
        assert result.exists()
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_download_existing_skips(self, temp_dir):
        """Test that existing sysroot is not re-downloaded."""
        manager = SysrootManager(temp_dir)

        # Create existing sysroot
        existing = temp_dir / "sysroots" / "test-target-1.0"
        existing.mkdir(parents=True)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        with patch("toolchainkit.cross.sysroot.download_file") as mock_download:
            result = manager.download_sysroot(spec)

            assert result == existing
            mock_download.assert_not_called()

    @patch("toolchainkit.cross.sysroot.download_file")
    def test_download_force_redownload(self, mock_download, temp_dir):
        """Test force re-download of existing sysroot."""
        manager = SysrootManager(temp_dir)

        # Create existing sysroot
        existing = temp_dir / "sysroots" / "test-target-1.0"
        existing.mkdir(parents=True)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        # Mock download failure to verify it was called
        mock_download.side_effect = Exception("Download called")

        with pytest.raises(SysrootDownloadError):
            manager.download_sysroot(spec, force=True)

        mock_download.assert_called_once()

    @patch("toolchainkit.cross.sysroot.download_file")
    def test_download_error_handling(self, mock_download, temp_dir):
        """Test download error handling."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        mock_download.side_effect = RuntimeError("Network error")

        with pytest.raises(SysrootDownloadError, match="Failed to download sysroot"):
            manager.download_sysroot(spec)

    @patch("toolchainkit.cross.sysroot.download_file")
    @patch("toolchainkit.cross.sysroot.extract_archive")
    def test_extraction_error_handling(self, mock_extract, mock_download, temp_dir):
        """Test extraction error handling."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        mock_extract.side_effect = RuntimeError("Extraction failed")

        with pytest.raises(SysrootExtractionError, match="Failed to extract"):
            manager.download_sysroot(spec)

    @patch("toolchainkit.cross.sysroot.download_file")
    @patch("toolchainkit.cross.sysroot.extract_archive")
    def test_download_with_progress_callback(
        self, mock_extract, mock_download, temp_dir
    ):
        """Test download with progress callback."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        def mock_extract_side_effect(archive_path, destination, **kwargs):
            destination.mkdir(parents=True, exist_ok=True)

        mock_extract.side_effect = mock_extract_side_effect

        manager.download_sysroot(spec, progress_callback=progress_callback)

        # Progress callback should be wrapped and passed to download_file
        assert mock_download.called


class TestSysrootCacheManagement:
    """Tests for sysroot cache management."""

    def test_get_sysroot_path_exists(self, temp_dir):
        """Test getting path to existing sysroot."""
        manager = SysrootManager(temp_dir)

        # Create sysroot
        sysroot = temp_dir / "sysroots" / "test-target-1.0"
        sysroot.mkdir(parents=True)

        result = manager.get_sysroot_path("test-target", "1.0")

        assert result == sysroot

    def test_get_sysroot_path_not_exists(self, temp_dir):
        """Test getting path to non-existent sysroot."""
        manager = SysrootManager(temp_dir)

        result = manager.get_sysroot_path("test-target", "1.0")

        assert result is None

    def test_list_sysroots_empty(self, temp_dir):
        """Test listing sysroots when cache is empty."""
        manager = SysrootManager(temp_dir)

        result = manager.list_sysroots()

        assert result == []

    def test_list_sysroots_multiple(self, temp_dir):
        """Test listing multiple sysroots."""
        manager = SysrootManager(temp_dir)

        # Create multiple sysroots
        (temp_dir / "sysroots" / "android-arm64-21").mkdir(parents=True)
        (temp_dir / "sysroots" / "raspberry-pi-armv7-11").mkdir(parents=True)
        (temp_dir / "sysroots" / "ios-arm64-14").mkdir(parents=True)

        result = manager.list_sysroots()

        assert len(result) == 3
        assert "android-arm64-21" in result
        assert "raspberry-pi-armv7-11" in result
        assert "ios-arm64-14" in result

    def test_list_sysroots_sorted(self, temp_dir):
        """Test that sysroots are listed in sorted order."""
        manager = SysrootManager(temp_dir)

        # Create sysroots in non-alphabetical order
        (temp_dir / "sysroots" / "zzz").mkdir(parents=True)
        (temp_dir / "sysroots" / "aaa").mkdir(parents=True)
        (temp_dir / "sysroots" / "mmm").mkdir(parents=True)

        result = manager.list_sysroots()

        assert result == ["aaa", "mmm", "zzz"]

    def test_list_sysroots_excludes_downloads(self, temp_dir):
        """Test that downloads directory is excluded from listing."""
        manager = SysrootManager(temp_dir)

        (temp_dir / "sysroots" / "test-sysroot").mkdir(parents=True)

        result = manager.list_sysroots()

        assert "downloads" not in result
        assert "test-sysroot" in result

    def test_remove_sysroot_exists(self, temp_dir):
        """Test removing existing sysroot."""
        manager = SysrootManager(temp_dir)

        sysroot = temp_dir / "sysroots" / "test-target-1.0"
        sysroot.mkdir(parents=True)

        result = manager.remove_sysroot("test-target", "1.0")

        assert result is True
        assert not sysroot.exists()

    def test_remove_sysroot_not_exists(self, temp_dir):
        """Test removing non-existent sysroot."""
        manager = SysrootManager(temp_dir)

        result = manager.remove_sysroot("test-target", "1.0")

        assert result is False

    def test_get_cache_size_empty(self, temp_dir):
        """Test getting cache size when empty."""
        manager = SysrootManager(temp_dir)

        size = manager.get_cache_size()

        assert size == 0

    def test_get_cache_size_with_files(self, temp_dir):
        """Test getting cache size with files."""
        manager = SysrootManager(temp_dir)

        # Create sysroot with files
        sysroot = temp_dir / "sysroots" / "test-target-1.0"
        sysroot.mkdir(parents=True)
        (sysroot / "file1.txt").write_text("a" * 100)
        (sysroot / "file2.txt").write_text("b" * 200)

        size = manager.get_cache_size()

        assert size == 300

    def test_clear_cache_empty(self, temp_dir):
        """Test clearing empty cache."""
        manager = SysrootManager(temp_dir)

        count = manager.clear_cache()

        assert count == 0

    def test_clear_cache_with_sysroots(self, temp_dir):
        """Test clearing cache with sysroots."""
        manager = SysrootManager(temp_dir)

        # Create multiple sysroots
        (temp_dir / "sysroots" / "sysroot1").mkdir(parents=True)
        (temp_dir / "sysroots" / "sysroot2").mkdir(parents=True)
        (temp_dir / "sysroots" / "sysroot3").mkdir(parents=True)

        count = manager.clear_cache()

        assert count == 3
        assert manager.list_sysroots() == []


class TestSysrootExtractPath:
    """Tests for extract_path functionality."""

    @patch("toolchainkit.cross.sysroot.download_file")
    @patch("toolchainkit.cross.sysroot.extract_archive")
    def test_extract_specific_path(self, mock_extract, mock_download, temp_dir):
        """Test extracting specific path from archive."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
            extract_path="nested/sysroot",
        )

        def mock_extract_side_effect(archive_path, destination, **kwargs):
            # Create nested directory structure
            destination.mkdir(parents=True, exist_ok=True)
            nested = destination / "nested" / "sysroot"
            nested.mkdir(parents=True)
            (nested / "usr").mkdir()

        mock_extract.side_effect = mock_extract_side_effect

        result = manager.download_sysroot(spec)

        assert result.exists()
        assert (result / "usr").exists()

    @patch("toolchainkit.cross.sysroot.download_file")
    @patch("toolchainkit.cross.sysroot.extract_archive")
    def test_extract_path_not_found(self, mock_extract, mock_download, temp_dir):
        """Test error when extract_path doesn't exist."""
        manager = SysrootManager(temp_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
            extract_path="nonexistent",
        )

        def mock_extract_side_effect(archive_path, destination, **kwargs):
            destination.mkdir(parents=True, exist_ok=True)

        mock_extract.side_effect = mock_extract_side_effect

        with pytest.raises(SysrootExtractionError, match="Extract path not found"):
            manager.download_sysroot(spec)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_target_name(self, temp_dir):
        """Test with empty target name."""
        _spec = SysrootSpec(
            target="",
            version="1.0",
            url="https://example.com/sysroot.tar.gz",
            hash="abc123",
        )

        manager = SysrootManager(temp_dir)

        # Should still work (directory name is just version)
        path = manager.get_sysroot_path("", "1.0")
        # Path format: "-1.0"
        expected = temp_dir / "sysroots" / "-1.0"
        assert path is None or path == expected

    def test_special_characters_in_names(self, temp_dir):
        """Test with special characters in target/version."""
        manager = SysrootManager(temp_dir)

        # Create sysroot with special characters
        sysroot = temp_dir / "sysroots" / "target_v1.0-beta"
        sysroot.mkdir(parents=True)

        result = manager.list_sysroots()

        assert "target_v1.0-beta" in result

    def test_concurrent_operations_safety(self, temp_dir):
        """Test that operations are safe (basic check)."""
        manager1 = SysrootManager(temp_dir)
        manager2 = SysrootManager(temp_dir)

        # Both managers should see the same cache
        sysroot = temp_dir / "sysroots" / "test-sysroot"
        sysroot.mkdir(parents=True)

        assert manager1.list_sysroots() == manager2.list_sysroots()

    def test_manager_reuse(self, temp_dir):
        """Test that manager can be reused for multiple operations."""
        manager = SysrootManager(temp_dir)

        # Create multiple sysroots
        (temp_dir / "sysroots" / "sysroot1").mkdir(parents=True)
        (temp_dir / "sysroots" / "sysroot2").mkdir(parents=True)

        # Multiple list operations
        result1 = manager.list_sysroots()
        result2 = manager.list_sysroots()

        assert result1 == result2
        assert len(result1) == 2

    def test_unicode_in_paths(self, temp_dir):
        """Test handling of unicode characters."""
        manager = SysrootManager(temp_dir)

        # Create sysroot with unicode name (if filesystem supports it)
        try:
            sysroot = temp_dir / "sysroots" / "test-unicode-→"
            sysroot.mkdir(parents=True)

            result = manager.list_sysroots()
            assert any("→" in s for s in result)
        except OSError:
            # Skip if filesystem doesn't support unicode
            pytest.skip("Filesystem doesn't support unicode characters")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
