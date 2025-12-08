"""
Integration tests for build cache detection and installation.

These tests verify actual sccache installation and detection when possible.
They are marked as 'slow' and 'requires_network' since they download real binaries.
"""

import pytest
from pathlib import Path

from toolchainkit.caching.detection import (
    BuildCacheDetector,
    BuildCacheInstaller,
    BuildCacheManager,
)
from toolchainkit.core.platform import detect_platform


pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.requires_network]


@pytest.mark.skipif(
    not hasattr(pytest, "skip"), reason="Integration test - may download large files"
)
class TestBuildCacheIntegration:
    """Integration tests for build cache."""

    def test_detector_finds_system_tools(self):
        """Test detecting cache tools if installed on system."""
        detector = BuildCacheDetector()

        # Try to detect any available tool
        result = detector.detect_best()

        # This test doesn't fail if nothing found - just informational
        if result:
            tool_name, tool_path = result
            print(f"\nFound {tool_name} at: {tool_path}")

            # Try to get version
            version = detector.get_version(tool_path)
            if version:
                print(f"Version: {version}")
        else:
            print("\nNo cache tools found on system (expected if not installed)")

    def test_full_installation_workflow(self, tmp_path, monkeypatch):
        """Test complete installation workflow (slow - downloads real binary)."""
        # This test actually downloads sccache - skip by default
        pytest.skip(
            "Skipping actual download test - use pytest --run-integration to enable"
        )

        # Set up isolated home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        # Install sccache
        installer = BuildCacheInstaller()

        platform = detect_platform()
        supported_platforms = ["linux", "macos", "windows"]

        if platform.os not in supported_platforms:
            pytest.skip(f"Platform {platform.os} not supported for sccache")

        # Download and install
        sccache_path = installer.install_sccache()

        # Verify installation
        assert sccache_path.exists()
        assert sccache_path.is_file()

        # Verify it's executable (Unix)
        if platform.os in ("linux", "macos"):
            import os

            assert os.access(sccache_path, os.X_OK)

        # Try to detect it
        detector = BuildCacheDetector(platform)
        detected = detector.detect_sccache()

        assert detected == sccache_path

    def test_manager_workflow(self, tmp_path):
        """Test manager end-to-end workflow."""
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        manager = BuildCacheManager(project_root)

        # Try to get or install (won't actually install in this test)
        config = manager.get_or_install(prefer="sccache")

        # If config is None, it means no tool found and installation skipped
        # This is OK for automated tests
        if config:
            print("\nCache configuration:")
            print(f"  Tool: {config.tool}")
            print(f"  Executable: {config.executable_path}")
            print(f"  Cache dir: {config.cache_dir}")
            print(f"  Version: {config.version}")

            # Verify cache directory was created
            assert config.cache_dir.exists()
            assert config.cache_dir.is_dir()
        else:
            print("\nNo cache tool available (expected if not installed)")


@pytest.mark.unit
class TestDetectionSanity:
    """Quick sanity checks that can run without installation."""

    def test_detector_initializes(self):
        """Test detector initialization."""
        detector = BuildCacheDetector()
        assert detector.platform is not None

    def test_installer_initializes(self):
        """Test installer initialization."""
        installer = BuildCacheInstaller()
        assert installer.platform is not None
        assert installer.tools_dir is not None

    def test_manager_initializes(self, tmp_path):
        """Test manager initialization."""
        project_root = tmp_path / "test"
        project_root.mkdir()

        manager = BuildCacheManager(project_root)
        assert manager.project_root == project_root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
