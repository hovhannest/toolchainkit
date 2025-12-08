"""
Integration tests for sysroot management.

These tests verify sysroot management functionality in realistic scenarios,
including integration with cross-compilation configuration and real file operations.
"""

import pytest
from pathlib import Path
import tempfile
import tarfile
from unittest.mock import patch

from toolchainkit.cross.sysroot import (
    SysrootManager,
    SysrootSpec,
    SysrootExtractionError,
)
from toolchainkit.cross.targets import CrossCompilationConfigurator


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_sysroot_archive(temp_dir):
    """Create a sample sysroot archive with typical structure."""
    sysroot_dir = temp_dir / "sample-sysroot"
    sysroot_dir.mkdir()

    # Create typical sysroot structure
    (sysroot_dir / "usr" / "include").mkdir(parents=True)
    (sysroot_dir / "usr" / "lib").mkdir(parents=True)
    (sysroot_dir / "usr" / "bin").mkdir(parents=True)

    # Add some typical files
    (sysroot_dir / "usr" / "include" / "stdio.h").write_text("#include <stddef.h>")
    (sysroot_dir / "usr" / "include" / "stdlib.h").write_text("#include <stddef.h>")
    (sysroot_dir / "usr" / "lib" / "libc.so").write_text("mock library")
    (sysroot_dir / "usr" / "bin" / "gcc").write_text("#!/bin/bash\necho gcc")

    # Create tar.gz archive
    archive_path = temp_dir / "sysroot.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(sysroot_dir, arcname="sample-sysroot")

    return archive_path


@pytest.fixture
def nested_sysroot_archive(temp_dir):
    """Create a nested sysroot archive (common in SDK downloads)."""
    sdk_dir = temp_dir / "sdk"
    sdk_dir.mkdir()

    # Create nested structure: sdk/sysroot/usr/...
    sysroot_dir = sdk_dir / "sysroot"
    sysroot_dir.mkdir()
    (sysroot_dir / "usr" / "include").mkdir(parents=True)
    (sysroot_dir / "usr" / "lib").mkdir(parents=True)
    (sysroot_dir / "usr" / "include" / "stdio.h").write_text("#include <stddef.h>")
    (sysroot_dir / "usr" / "lib" / "libc.so").write_text("mock library")

    # Create tar.gz archive
    archive_path = temp_dir / "sdk.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(sdk_dir, arcname="sdk")

    return archive_path, "sdk/sysroot"


@pytest.mark.integration
class TestSysrootIntegration:
    """Integration tests for sysroot management with real file operations."""

    def test_download_and_extract_workflow(self, temp_dir, sample_sysroot_archive):
        """Test complete download and extract workflow with real archive."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="test-target",
            version="1.0",
            url=f"file://{sample_sysroot_archive}",
            hash="dummy-hash",
        )

        # Mock download_file to just copy the local archive
        def mock_download(url, destination, **kwargs):
            import shutil

            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            sysroot_path = manager.download_sysroot(spec)

        # Verify sysroot was extracted correctly
        assert sysroot_path.exists()
        assert (
            sysroot_path / "sample-sysroot" / "usr" / "include" / "stdio.h"
        ).exists()
        assert (sysroot_path / "sample-sysroot" / "usr" / "lib" / "libc.so").exists()

    def test_nested_archive_extraction(self, temp_dir, nested_sysroot_archive):
        """Test extraction of nested sysroot from SDK archive."""
        archive_path, extract_path = nested_sysroot_archive
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="sdk-target",
            version="2.0",
            url=f"file://{archive_path}",
            hash="dummy-hash",
            extract_path=extract_path,
        )

        def mock_download(url, destination, **kwargs):
            import shutil

            shutil.copy2(archive_path, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            sysroot_path = manager.download_sysroot(spec)

        # Verify only the nested sysroot was extracted
        assert sysroot_path.exists()
        assert (sysroot_path / "usr" / "include" / "stdio.h").exists()
        assert (sysroot_path / "usr" / "lib" / "libc.so").exists()

    def test_cache_management_workflow(self, temp_dir, sample_sysroot_archive):
        """Test complete cache management workflow."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        # Download multiple sysroots
        specs = [
            SysrootSpec("target-a", "1.0", f"file://{sample_sysroot_archive}", "hash1"),
            SysrootSpec("target-b", "2.0", f"file://{sample_sysroot_archive}", "hash2"),
            SysrootSpec("target-c", "1.5", f"file://{sample_sysroot_archive}", "hash3"),
        ]

        def mock_download(url, destination, **kwargs):
            import shutil

            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            for spec in specs:
                manager.download_sysroot(spec)

        # Verify all are listed
        sysroots = manager.list_sysroots()
        assert len(sysroots) == 3
        assert "target-a-1.0" in sysroots
        assert "target-b-2.0" in sysroots
        assert "target-c-1.5" in sysroots

        # Check cache size
        cache_size = manager.get_cache_size()
        assert cache_size > 0

        # Remove one sysroot
        manager.remove_sysroot("target-b", "2.0")
        sysroots = manager.list_sysroots()
        assert len(sysroots) == 2
        assert "target-b-2.0" not in sysroots

        # Clear cache
        manager.clear_cache()
        assert manager.list_sysroots() == []
        assert manager.get_cache_size() == 0

    def test_sysroot_reuse(self, temp_dir, sample_sysroot_archive):
        """Test that existing sysroots are reused without re-download."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="reuse-target",
            version="1.0",
            url=f"file://{sample_sysroot_archive}",
            hash="dummy-hash",
        )

        download_count = 0

        def mock_download(url, destination, **kwargs):
            nonlocal download_count
            download_count += 1
            import shutil

            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            # First download
            path1 = manager.download_sysroot(spec)
            assert download_count == 1

            # Second download should skip
            path2 = manager.download_sysroot(spec)
            assert download_count == 1  # No additional download
            assert path1 == path2

            # Force download
            path3 = manager.download_sysroot(spec, force=True)
            assert download_count == 2  # Forced re-download
            assert path1 == path3


@pytest.mark.integration
class TestCrossCompilationIntegration:
    """Integration tests for sysroot with cross-compilation configuration."""

    def test_android_with_sysroot(self, temp_dir, sample_sysroot_archive):
        """Test Android cross-compilation configuration with sysroot."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="android-arm64",
            version="29",
            url=f"file://{sample_sysroot_archive}",
            hash="dummy-hash",
        )

        def mock_download(url, destination, **kwargs):
            import shutil

            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            sysroot_path = manager.download_sysroot(spec)

        # Configure Android cross-compilation with sysroot
        ndk_path = temp_dir / "ndk"
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_android(ndk_path, "arm64-v8a", api_level=29)

        # Update sysroot in target
        target.sysroot = sysroot_path / "sample-sysroot"

        # Generate CMake variables
        cmake_vars = configurator.generate_cmake_variables(target)

        assert cmake_vars["CMAKE_SYSTEM_NAME"] == "Android"
        assert cmake_vars["CMAKE_SYSTEM_PROCESSOR"] == "aarch64"
        assert "CMAKE_SYSROOT" in cmake_vars
        assert Path(cmake_vars["CMAKE_SYSROOT"]) == target.sysroot


@pytest.mark.integration
class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    def test_invalid_archive_handling(self, temp_dir):
        """Test handling of corrupted/invalid archives."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="invalid-target",
            version="1.0",
            url="https://example.com/invalid.tar.gz",
            hash="dummy-hash",
        )

        def mock_download(url, destination, **kwargs):
            # Create invalid archive
            destination.write_text("not a valid tar.gz file")

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            with pytest.raises(SysrootExtractionError):
                manager.download_sysroot(spec)

        # Verify cleanup
        assert not (cache_dir / f"{spec.target}-{spec.version}").exists()

    def test_progress_callback_invocation(self, temp_dir, sample_sysroot_archive):
        """Test that progress callback is invoked during download."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        spec = SysrootSpec(
            target="progress-target",
            version="1.0",
            url=f"file://{sample_sysroot_archive}",
            hash="dummy-hash",
        )

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        def mock_download(url, destination, progress_callback=None, **kwargs):
            import shutil

            # Simulate progress callbacks
            if progress_callback:
                file_size = sample_sysroot_archive.stat().st_size
                from types import SimpleNamespace

                progress_callback(
                    SimpleNamespace(bytes_downloaded=0, total_bytes=file_size)
                )
                progress_callback(
                    SimpleNamespace(
                        bytes_downloaded=file_size // 2, total_bytes=file_size
                    )
                )
                progress_callback(
                    SimpleNamespace(bytes_downloaded=file_size, total_bytes=file_size)
                )
            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            manager.download_sysroot(spec, progress_callback=progress_callback)

        # Verify progress was tracked
        assert len(progress_calls) >= 3
        assert progress_calls[0][0] == 0  # Started at 0
        assert progress_calls[-1][0] == progress_calls[-1][1]  # Ended at 100%


@pytest.mark.integration
class TestMultipleSysroots:
    """Integration tests for managing multiple sysroots."""

    def test_different_versions_same_target(self, temp_dir, sample_sysroot_archive):
        """Test managing multiple versions of the same target."""
        cache_dir = temp_dir / "cache"
        manager = SysrootManager(cache_dir=cache_dir)

        specs = [
            SysrootSpec("target", "1.0", f"file://{sample_sysroot_archive}", "hash1"),
            SysrootSpec("target", "2.0", f"file://{sample_sysroot_archive}", "hash2"),
            SysrootSpec("target", "3.0", f"file://{sample_sysroot_archive}", "hash3"),
        ]

        def mock_download(url, destination, **kwargs):
            import shutil

            shutil.copy2(sample_sysroot_archive, destination)

        with patch(
            "toolchainkit.cross.sysroot.download_file", side_effect=mock_download
        ):
            paths = [manager.download_sysroot(spec) for spec in specs]

        # Verify all versions exist
        assert all(p.exists() for p in paths)
        assert len(set(paths)) == 3  # All unique paths

        # Verify listing
        sysroots = manager.list_sysroots()
        assert len(sysroots) == 3
        assert "target-1.0" in sysroots
        assert "target-2.0" in sysroots
        assert "target-3.0" in sysroots

        # Get specific version
        v2_path = manager.get_sysroot_path("target", "2.0")
        assert v2_path == paths[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
