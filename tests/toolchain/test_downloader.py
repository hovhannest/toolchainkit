"""
Unit tests for toolchain downloader module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from toolchainkit.toolchain.downloader import (
    ToolchainDownloader,
    ToolchainDownloadError,
    DownloadResult,
    ProgressInfo,
    download_toolchain,
)
from toolchainkit.toolchain.metadata_registry import ToolchainMetadata


@pytest.fixture
def mock_metadata():
    """Create mock toolchain metadata."""
    return ToolchainMetadata(
        url="https://example.com/llvm-18.1.8-linux.tar.xz",
        sha256="abc123def456",
        size_mb=500,
        stdlib=["libc++", "libstdc++"],
    )


@pytest.fixture
def downloader(tmp_path):
    """Create downloader instance with temporary cache."""
    return ToolchainDownloader(cache_dir=tmp_path)


class TestToolchainDownloader:
    """Tests for ToolchainDownloader class."""

    def test_initialization(self, tmp_path):
        """Test downloader initialization."""
        downloader = ToolchainDownloader(cache_dir=tmp_path)

        assert downloader.cache_dir == tmp_path
        assert downloader.toolchains_dir == tmp_path / "toolchains"
        assert downloader.downloads_dir == tmp_path / "downloads"
        assert downloader.toolchains_dir.exists()
        assert downloader.downloads_dir.exists()

    def test_initialization_default_cache(self):
        """Test initialization with default global cache."""
        downloader = ToolchainDownloader()
        assert downloader.cache_dir is not None
        assert "toolchainkit" in str(downloader.cache_dir).lower()

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_download_toolchain_success(
        self, mock_extract, mock_download, downloader, mock_metadata
    ):
        """Test successful toolchain download."""
        # Mock registry lookup
        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                # Mock extract to create some files
                def create_files(archive_path, destination, progress_callback=None):
                    destination.mkdir(parents=True, exist_ok=True)
                    (destination / "bin").mkdir()
                    (destination / "bin" / "clang").write_text("fake binary")
                    if progress_callback:
                        progress_callback(1, 1)

                mock_extract.side_effect = create_files

                # Download
                result = downloader.download_toolchain("llvm", "18", "linux-x64")

                # Verify
                assert isinstance(result, DownloadResult)
                assert result.toolchain_id == "llvm-18.1.8-linux-x64"
                assert result.toolchain_path.exists()
                assert not result.was_cached
                assert result.download_time >= 0
                assert result.extraction_time >= 0
                assert result.total_size_bytes > 0

                # Verify download was called
                mock_download.assert_called_once()
                mock_extract.assert_called_once()

    def test_download_toolchain_not_found(self, downloader):
        """Test error when toolchain not found."""
        with patch.object(downloader.metadata_registry, "lookup", return_value=None):
            with pytest.raises(ToolchainDownloadError, match="Toolchain not found"):
                downloader.download_toolchain("nonexistent", "1.0", "linux-x64")

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_download_toolchain_cached(
        self, mock_extract, mock_download, downloader, mock_metadata
    ):
        """Test using cached toolchain."""
        # Create fake cached toolchain
        toolchain_dir = downloader.toolchains_dir / "llvm-18.1.8-linux-x64"
        toolchain_dir.mkdir(parents=True)
        (toolchain_dir / "bin").mkdir()
        (toolchain_dir / "bin" / "clang").write_text("cached binary")

        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                result = downloader.download_toolchain("llvm", "18", "linux-x64")

                # Should use cached version
                assert result.was_cached
                assert result.download_time == 0
                assert result.extraction_time == 0

                # Should not download or extract
                mock_download.assert_not_called()
                mock_extract.assert_not_called()

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_download_toolchain_force(
        self, mock_extract, mock_download, downloader, mock_metadata
    ):
        """Test force re-download of cached toolchain."""
        # Create fake cached toolchain
        toolchain_dir = downloader.toolchains_dir / "llvm-18.1.8-linux-x64"
        toolchain_dir.mkdir(parents=True)

        def create_files(archive_path, destination, progress_callback=None):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "bin").mkdir()
            (destination / "bin" / "clang").write_text("new binary")

        mock_extract.side_effect = create_files

        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                result = downloader.download_toolchain(
                    "llvm", "18", "linux-x64", force=True
                )

                # Should re-download
                assert not result.was_cached
                mock_download.assert_called_once()
                mock_extract.assert_called_once()

    @patch("toolchainkit.toolchain.downloader.download_file")
    def test_download_toolchain_download_failure(
        self, mock_download, downloader, mock_metadata
    ):
        """Test handling of download failure."""
        mock_download.side_effect = Exception("Network error")

        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                with pytest.raises(ToolchainDownloadError, match="Failed to download"):
                    downloader.download_toolchain("llvm", "18", "linux-x64")

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_download_toolchain_extraction_failure(
        self, mock_extract, mock_download, downloader, mock_metadata
    ):
        """Test handling of extraction failure."""
        mock_extract.side_effect = Exception("Extraction error")

        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                with pytest.raises(ToolchainDownloadError, match="Failed to download"):
                    downloader.download_toolchain("llvm", "18", "linux-x64")

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_progress_reporting(
        self, mock_extract, mock_download, downloader, mock_metadata
    ):
        """Test progress reporting during download and extraction."""
        progress_updates = []

        def progress_callback(progress: ProgressInfo):
            progress_updates.append(progress)

        def create_files(archive_path, destination, progress_callback=None):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "file").write_text("content")
            if progress_callback:
                progress_callback(1, 1)

        mock_extract.side_effect = create_files

        with patch.object(
            downloader.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                downloader.download_toolchain(
                    "llvm", "18", "linux-x64", progress_callback=progress_callback
                )

                # Should have progress updates
                assert len(progress_updates) > 0

                # Check phases
                phases = [p.phase for p in progress_updates]
                assert "complete" in phases

                # Check final progress is 100%
                assert progress_updates[-1].percentage == 100.0
                assert progress_updates[-1].phase == "complete"

    def test_is_cached(self, downloader):
        """Test checking if toolchain is cached."""
        # Not cached initially
        with patch.object(
            downloader.metadata_registry, "resolve_version", return_value="18.1.8"
        ):
            assert not downloader.is_cached("llvm", "18", "linux-x64")

        # Create cached toolchain
        toolchain_dir = downloader.toolchains_dir / "llvm-18.1.8-linux-x64"
        toolchain_dir.mkdir(parents=True)

        # Now cached
        with patch.object(
            downloader.metadata_registry, "resolve_version", return_value="18.1.8"
        ):
            assert downloader.is_cached("llvm", "18", "linux-x64")

    def test_get_toolchain_path(self, downloader):
        """Test getting path to cached toolchain."""
        # Not cached initially
        with patch.object(
            downloader.metadata_registry, "resolve_version", return_value="18.1.8"
        ):
            assert downloader.get_toolchain_path("llvm", "18", "linux-x64") is None

        # Create cached toolchain
        toolchain_dir = downloader.toolchains_dir / "llvm-18.1.8-linux-x64"
        toolchain_dir.mkdir(parents=True)

        # Now returns path
        with patch.object(
            downloader.metadata_registry, "resolve_version", return_value="18.1.8"
        ):
            path = downloader.get_toolchain_path("llvm", "18", "linux-x64")
            assert path == toolchain_dir
            assert path.exists()

    def test_normalize_root_directory_single_folder(self, downloader, tmp_path):
        """Test normalizing root directory with single folder."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        root_folder = extract_dir / "llvm-18.1.8"
        root_folder.mkdir()
        (root_folder / "bin").mkdir()

        normalized = downloader._normalize_root_directory(extract_dir)
        assert normalized == root_folder

    def test_normalize_root_directory_no_root(self, downloader, tmp_path):
        """Test normalizing root directory without root folder."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        (extract_dir / "bin").mkdir()
        (extract_dir / "lib").mkdir()

        normalized = downloader._normalize_root_directory(extract_dir)
        assert normalized == extract_dir

    def test_cleanup_on_error(self, downloader):
        """Test cleanup of temporary files on error."""
        archive = downloader.downloads_dir / "test.tar.xz"
        temp_dir = downloader.downloads_dir / "test_extract"
        install_dir = downloader.toolchains_dir / "test"

        # Create files
        archive.write_text("archive content")
        temp_dir.mkdir()
        (temp_dir / "file").write_text("temp file")
        install_dir.mkdir()
        (install_dir / "file").write_text("install file")

        # Cleanup
        downloader._cleanup_on_error(archive, temp_dir, install_dir)

        # Files should be removed
        assert not archive.exists()
        assert not temp_dir.exists()
        assert not install_dir.exists()


class TestProgressInfo:
    """Tests for ProgressInfo dataclass."""

    def test_create_progress_info(self):
        """Test creating ProgressInfo."""
        progress = ProgressInfo(
            phase="downloading",
            percentage=50.0,
            current_bytes=1024,
            total_bytes=2048,
            speed_bps=1000.0,
            eta_seconds=1.0,
        )

        assert progress.phase == "downloading"
        assert progress.percentage == 50.0
        assert progress.current_bytes == 1024
        assert progress.total_bytes == 2048
        assert progress.speed_bps == 1000.0
        assert progress.eta_seconds == 1.0


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_create_download_result(self, tmp_path):
        """Test creating DownloadResult."""
        result = DownloadResult(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=tmp_path / "toolchain",
            download_time=10.5,
            extraction_time=5.2,
            total_size_bytes=1024 * 1024 * 500,  # 500 MB
            was_cached=False,
        )

        assert result.toolchain_id == "llvm-18.1.8-linux-x64"
        assert result.download_time == 10.5
        assert result.extraction_time == 5.2
        assert result.total_size_bytes == 1024 * 1024 * 500
        assert not result.was_cached


class TestConvenienceFunction:
    """Tests for convenience function."""

    @patch("toolchainkit.toolchain.downloader.ToolchainDownloader")
    def test_download_toolchain_function(self, mock_downloader_class):
        """Test convenience function."""
        mock_instance = Mock()
        mock_downloader_class.return_value = mock_instance
        mock_instance.download_toolchain.return_value = DownloadResult(
            toolchain_id="test-1.0-linux",
            toolchain_path=Path("/tmp/test"),
            download_time=1.0,
            extraction_time=1.0,
            total_size_bytes=1000,
            was_cached=False,
        )

        result = download_toolchain("test", "1.0", "linux-x64")

        # Should create downloader and call download_toolchain
        mock_downloader_class.assert_called_once()
        mock_instance.download_toolchain.assert_called_once_with(
            "test", "1.0", "linux-x64", False, None
        )
        assert result.toolchain_id == "test-1.0-linux"


class TestConcurrency:
    """Tests for concurrent download coordination."""

    @patch("toolchainkit.toolchain.downloader.download_file")
    @patch("toolchainkit.toolchain.downloader.extract_archive")
    def test_concurrent_download_coordination(
        self, mock_extract, mock_download, tmp_path, mock_metadata
    ):
        """Test that concurrent downloads are coordinated."""
        # Create two downloaders (simulating two processes)
        downloader1 = ToolchainDownloader(cache_dir=tmp_path)
        downloader2 = ToolchainDownloader(cache_dir=tmp_path)

        def create_files(archive_path, destination, progress_callback=None):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "bin").mkdir()
            (destination / "bin" / "tool").write_text("binary")

        mock_extract.side_effect = create_files

        with patch.object(
            downloader1.metadata_registry, "lookup", return_value=mock_metadata
        ):
            with patch.object(
                downloader1.metadata_registry, "resolve_version", return_value="18.1.8"
            ):
                with patch.object(
                    downloader2.metadata_registry, "lookup", return_value=mock_metadata
                ):
                    with patch.object(
                        downloader2.metadata_registry,
                        "resolve_version",
                        return_value="18.1.8",
                    ):
                        # First download
                        result1 = downloader1.download_toolchain(
                            "llvm", "18", "linux-x64"
                        )
                        assert not result1.was_cached

                        # Second download should use cached version
                        result2 = downloader2.download_toolchain(
                            "llvm", "18", "linux-x64"
                        )
                        assert result2.was_cached
                        assert result2.toolchain_path == result1.toolchain_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
