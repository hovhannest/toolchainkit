"""
Integration tests for bootstrap compatibility validation.

Tests cover:
- Bootstrap command rejecting incompatible configurations
- Bootstrap scripts containing platform checks
- End-to-end validation flow
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolchainkit.cli.commands import bootstrap
from toolchainkit.core.platform import PlatformInfo


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create a minimal config file
    config_file = project_root / "toolchainkit.yaml"
    return project_root, config_file


@pytest.fixture
def mock_linux_platform():
    """Mock Linux platform."""
    return PlatformInfo(
        os="linux",
        arch="x64",
        os_version="5.15",
        distribution="ubuntu",
        abi="glibc-2.31",
    )


@pytest.fixture
def mock_windows_platform():
    """Mock Windows platform."""
    return PlatformInfo(
        os="windows",
        arch="x64",
        os_version="10.0.19041",
        distribution="",
        abi="msvc",
    )


@pytest.fixture
def mock_macos_platform():
    """Mock macOS platform."""
    return PlatformInfo(
        os="macos",
        arch="arm64",
        os_version="14.1",
        distribution="",
        abi="macos-11.0",
    )


class TestBootstrapCompatibilityIntegration:
    """Integration tests for bootstrap compatibility validation."""

    def test_gcc_on_linux_succeeds(self, temp_project, mock_linux_platform):
        """Test GCC configuration on Linux passes validation."""
        project_root, config_file = temp_project

        # Create config with GCC
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
"""
        )

        # Mock the args
        args = MagicMock()
        args.project_root = str(project_root)
        args.config = str(config_file)
        args.toolchain = None
        args.build_type = None
        args.force = False
        args.dry_run = True  # Use dry-run to avoid actual generation
        args.platform = "all"
        args.verbose = False
        args.quiet = False

        # Mock platform detection
        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_linux_platform,
        ):
            # Should not raise an error
            result = bootstrap.run(args)
            # Dry-run returns 0 on success
            assert result == 0

    def test_gcc_on_windows_fails(self, temp_project, mock_windows_platform):
        """Test GCC configuration on Windows fails validation."""
        project_root, config_file = temp_project

        # Create config with GCC
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
"""
        )

        # Mock the args
        args = MagicMock()
        args.project_root = str(project_root)
        args.config = str(config_file)
        args.toolchain = None
        args.build_type = None
        args.force = False
        args.dry_run = False
        args.platform = "all"
        args.verbose = False
        args.quiet = False

        # Mock platform detection
        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_windows_platform,
        ):
            # Should fail with error code 1
            result = bootstrap.run(args)
            assert result == 1

    def test_gcc_on_macos_fails(self, temp_project, mock_macos_platform):
        """Test GCC configuration on macOS fails validation."""
        project_root, config_file = temp_project

        # Create config with GCC
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
"""
        )

        # Mock the args
        args = MagicMock()
        args.project_root = str(project_root)
        args.config = str(config_file)
        args.toolchain = None
        args.build_type = None
        args.force = False
        args.dry_run = False
        args.platform = "all"
        args.verbose = False
        args.quiet = False

        # Mock platform detection
        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_macos_platform,
        ):
            # Should fail with error code 1
            result = bootstrap.run(args)
            assert result == 1

    def test_msvc_on_linux_fails(self, temp_project, mock_linux_platform):
        """Test MSVC configuration on Linux fails validation."""
        project_root, config_file = temp_project

        # Create config with MSVC
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: msvc-2022
    type: msvc
    version: latest
defaults:
  toolchain: msvc-2022
"""
        )

        # Mock the args
        args = MagicMock()
        args.project_root = str(project_root)
        args.config = str(config_file)
        args.toolchain = None
        args.build_type = None
        args.force = False
        args.dry_run = False
        args.platform = "all"
        args.verbose = False
        args.quiet = False

        # Mock platform detection
        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_linux_platform,
        ):
            # Should fail with error code 1
            result = bootstrap.run(args)
            assert result == 1

    def test_clang_on_all_platforms_succeeds(
        self,
        temp_project,
        mock_linux_platform,
        mock_windows_platform,
        mock_macos_platform,
    ):
        """Test Clang configuration succeeds on all platforms."""
        project_root, config_file = temp_project

        # Create config with Clang
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
defaults:
  toolchain: llvm-18
"""
        )

        for platform in [
            mock_linux_platform,
            mock_windows_platform,
            mock_macos_platform,
        ]:
            # Mock the args
            args = MagicMock()
            args.project_root = str(project_root)
            args.config = str(config_file)
            args.toolchain = None
            args.build_type = None
            args.force = True  # Allow overwrite
            args.dry_run = True
            args.platform = "all"
            args.verbose = False
            args.quiet = False

            # Mock platform detection
            with patch(
                "toolchainkit.core.compatibility.detect_platform", return_value=platform
            ):
                # Should succeed
                result = bootstrap.run(args)
                assert result == 0, f"Clang should work on {platform.platform_string()}"


class TestGeneratedScriptCompatibility:
    """Test that generated scripts contain platform checks."""

    def test_shell_script_contains_gcc_check(self, temp_project, mock_macos_platform):
        """Test shell script contains GCC compatibility check."""
        project_root, config_file = temp_project

        # Create config with GCC (will fail, but we're testing script generation in dry-run)
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: gcc-13
"""
        )

        # Generate script for Linux (where GCC is valid)

        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_macos_platform,
        ):
            # Can't actually generate because validation will fail, so test template directly
            pass

        # Read the template to verify it has checks
        template_path = (
            Path(__file__).parent.parent.parent
            / "toolchainkit"
            / "bootstrap"
            / "templates"
            / "bootstrap.sh.j2"
        )
        if template_path.exists():
            template_content = template_path.read_text()
            assert "gcc" in template_content.lower()
            assert "COMPATIBLE" in template_content or "ERROR" in template_content

    def test_batch_script_contains_gcc_check(self):
        """Test batch script contains GCC compatibility check."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "toolchainkit"
            / "bootstrap"
            / "templates"
            / "bootstrap.bat.j2"
        )
        if template_path.exists():
            template_content = template_path.read_text()
            assert "gcc" in template_content.lower()
            assert "ERROR" in template_content

    def test_powershell_script_contains_gcc_check(self):
        """Test PowerShell script contains GCC compatibility check."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "toolchainkit"
            / "bootstrap"
            / "templates"
            / "bootstrap.ps1.j2"
        )
        if template_path.exists():
            template_content = template_path.read_text()
            assert "gcc" in template_content.lower()
            assert "ERROR" in template_content or "Red" in template_content


class TestCommandLineOverrides:
    """Test command-line overrides with compatibility validation."""

    def test_override_to_incompatible_compiler_fails(
        self, temp_project, mock_windows_platform
    ):
        """Test overriding to incompatible compiler fails."""
        project_root, config_file = temp_project

        # Create config with valid compiler
        config_file.write_text(
            """
version: 1
project:
  name: test-project
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8
  - name: gcc-13
    type: gcc
    version: 13.2.0
defaults:
  toolchain: llvm-18
"""
        )

        # Mock the args - override to GCC on Windows
        args = MagicMock()
        args.project_root = str(project_root)
        args.config = str(config_file)
        args.toolchain = "gcc-13"  # Override to incompatible
        args.build_type = None
        args.force = False
        args.dry_run = False
        args.platform = "all"
        args.verbose = False
        args.quiet = False

        # Mock platform detection
        with patch(
            "toolchainkit.core.compatibility.detect_platform",
            return_value=mock_windows_platform,
        ):
            # Should fail because GCC is not supported on Windows
            result = bootstrap.run(args)
            assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
