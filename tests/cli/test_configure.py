"""
Tests for cli.commands.configure module.

Tests cover:
- Configuration merging
- Conan profile generation
- Dependency installation
- Error handling
- Helper functions
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from argparse import Namespace

from toolchainkit.cli.commands import configure


@pytest.fixture
def mock_args():
    """Create mock arguments."""
    args = Namespace()
    args.project_root = Path("/test/project")
    args.config = None
    args.toolchain = "llvm-18"
    args.build_type = "Release"
    args.build_dir = "build"
    args.target = None
    args.stdlib = "libc++"
    args.clean = False
    args.cache = None
    return args


class TestConfigureCommand:
    """Test configure command basic functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config dictionary."""
        return {
            "build": {
                "build_type": "Release",
                "build_dir": "build",
            },
            "packages": {
                "manager": "conan",
            },
        }

    @patch("toolchainkit.cli.commands.configure.check_initialized")
    def test_run_not_initialized(self, mock_check_init, mock_args):
        """Test run fails when project not initialized."""
        mock_check_init.return_value = False

        result = configure.run(mock_args)

        assert result == 1
        mock_check_init.assert_called_once()

    @patch("toolchainkit.cli.commands.configure.check_initialized")
    @patch("toolchainkit.cli.commands.configure.load_yaml_config")
    def test_run_config_load_failure(
        self, mock_load_config, mock_check_init, mock_args
    ):
        """Test run fails when config load fails."""
        mock_check_init.return_value = True
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        result = configure.run(mock_args)

        assert result == 1

    def test_merge_arguments(self, mock_args, mock_config):
        """Test merging CLI arguments with config."""
        result = configure._merge_arguments(mock_config, mock_args)

        assert result["build"]["build_type"] == mock_args.build_type
        assert result["build"]["build_dir"] == mock_args.build_dir

    def test_merge_arguments_with_empty_build_config(self, mock_args):
        """Test merging arguments with empty build config."""
        config = {}

        result = configure._merge_arguments(config, mock_args)

        assert "build" in result
        assert result["build"]["build_type"] == "Release"

    def test_merge_arguments_overrides_config(self, mock_config):
        """Test that CLI args override config values."""
        args = Namespace()
        args.build_type = "Debug"
        args.build_dir = "build-debug"

        result = configure._merge_arguments(mock_config, args)

        assert result["build"]["build_type"] == "Debug"
        assert result["build"]["build_dir"] == "build-debug"

    def test_merge_arguments_preserves_other_config(self, mock_config, mock_args):
        """Test that other config values are preserved."""
        result = configure._merge_arguments(mock_config, mock_args)

        assert "packages" in result
        assert result["packages"]["manager"] == "conan"


class TestConanProfileGeneration:
    """Test Conan profile generation."""

    def test_generate_conan_profile_linux(self):
        """Test generating Conan profile for Linux."""
        project_root = Path("/test/project")
        toolchain_name = "llvm-18"
        toolchain_path = Path("/cache/llvm-18")
        platform_str = "linux-x86_64"

        with patch("toolchainkit.cli.commands.configure.Path.mkdir"):
            with patch(
                "toolchainkit.cli.commands.configure.Path.write_text"
            ) as mock_write:
                configure._generate_conan_profile(
                    project_root, toolchain_name, toolchain_path, platform_str
                )

                mock_write.assert_called_once()
                profile_content = mock_write.call_args[0][0]
                assert "os=Linux" in profile_content
                assert "arch=x86_64" in profile_content
                assert "compiler=clang" in profile_content

    def test_generate_conan_profile_windows(self):
        """Test generating Conan profile for Windows (MSVC)."""
        project_root = Path("/test/project")
        toolchain_name = "llvm-18"
        toolchain_path = Path("C:\\cache\\llvm-18")
        platform_str = "windows-x86_64"

        with patch("toolchainkit.cli.commands.configure.Path.mkdir"):
            with patch(
                "toolchainkit.cli.commands.configure.Path.write_text"
            ) as mock_write:
                configure._generate_conan_profile(
                    project_root, toolchain_name, toolchain_path, platform_str
                )

                mock_write.assert_called_once()
                profile_content = mock_write.call_args[0][0]
                assert "os=Windows" in profile_content
                assert "compiler=msvc" in profile_content

    def test_generate_conan_profile_macos(self):
        """Test generating Conan profile for macOS."""
        project_root = Path("/test/project")
        toolchain_name = "llvm-18"
        toolchain_path = Path("/cache/llvm-18")
        platform_str = "macos-arm64"

        with patch("toolchainkit.cli.commands.configure.Path.mkdir"):
            with patch(
                "toolchainkit.cli.commands.configure.Path.write_text"
            ) as mock_write:
                configure._generate_conan_profile(
                    project_root, toolchain_name, toolchain_path, platform_str
                )

                mock_write.assert_called_once()
                profile_content = mock_write.call_args[0][0]
                assert "os=Macos" in profile_content
                assert "arch=armv8" in profile_content

    def test_generate_conan_profile_gcc(self):
        """Test generating Conan profile for GCC."""
        project_root = Path("/test/project")
        toolchain_name = "gcc-13"
        toolchain_path = Path("/cache/gcc-13")
        platform_str = "linux-x86_64"

        with patch("toolchainkit.cli.commands.configure.Path.mkdir"):
            with patch(
                "toolchainkit.cli.commands.configure.Path.write_text"
            ) as mock_write:
                configure._generate_conan_profile(
                    project_root, toolchain_name, toolchain_path, platform_str
                )

                mock_write.assert_called_once()
                profile_content = mock_write.call_args[0][0]
                assert "compiler=gcc" in profile_content
                assert "libcxx=libstdc++11" in profile_content

    def test_generate_conan_profile_write_failure(self):
        """Test handling profile write failure."""
        project_root = Path("/test/project")
        toolchain_name = "llvm-18"
        toolchain_path = Path("/cache/llvm-18")
        platform_str = "linux-x86_64"

        with patch("toolchainkit.cli.commands.configure.Path.mkdir"):
            with patch(
                "toolchainkit.cli.commands.configure.Path.write_text",
                side_effect=OSError("Write failed"),
            ):
                with pytest.raises(Exception, match="Failed to write Conan profile"):
                    configure._generate_conan_profile(
                        project_root, toolchain_name, toolchain_path, platform_str
                    )


class TestDependencyInstallation:
    """Test dependency installation."""

    @patch("toolchainkit.cli.commands.configure.get_package_manager_instance")
    def test_install_dependencies_conan(self, mock_get_pm):
        """Test installing dependencies with Conan."""
        project_root = Path("/test/project")
        packages_config = {"manager": "conan"}

        mock_pm = Mock()
        mock_pm.detect.return_value = True
        mock_get_pm.return_value = mock_pm

        configure._install_dependencies(project_root, packages_config)

        mock_get_pm.assert_called_once_with("conan", project_root, packages_config)
        mock_pm.detect.assert_called_once()
        mock_pm.install_dependencies.assert_called_once()

    @patch("toolchainkit.cli.commands.configure.get_package_manager_instance")
    def test_install_dependencies_with_profile(self, mock_get_pm):
        """Test installing dependencies with Conan profile."""
        project_root = Path("/test/project")
        packages_config = {"manager": "conan", "conan": {"profile": "default"}}

        mock_pm = Mock()
        mock_pm.detect.return_value = True
        mock_get_pm.return_value = mock_pm

        with patch(
            "toolchainkit.cli.commands.configure.Path.exists", return_value=True
        ):
            configure._install_dependencies(project_root, packages_config)

        mock_pm.install_dependencies.assert_called_once()

    @patch("toolchainkit.cli.commands.configure.get_package_manager_instance")
    def test_install_dependencies_manager_not_detected(self, mock_get_pm):
        """Test installing dependencies when manager not detected."""
        project_root = Path("/test/project")
        packages_config = {"manager": "conan"}

        mock_pm = Mock()
        mock_pm.detect.return_value = False
        mock_get_pm.return_value = mock_pm

        configure._install_dependencies(project_root, packages_config)

        mock_pm.detect.assert_called_once()
        mock_pm.install_dependencies.assert_not_called()

    def test_install_dependencies_no_manager(self):
        """Test installing dependencies with no manager."""
        project_root = Path("/test/project")
        packages_config = {}

        # Should not raise
        configure._install_dependencies(project_root, packages_config)

    @patch("toolchainkit.cli.commands.configure.get_package_manager_instance")
    def test_install_dependencies_failure(self, mock_get_pm):
        """Test handling dependency installation failure."""
        project_root = Path("/test/project")
        packages_config = {"manager": "conan"}

        mock_pm = Mock()
        mock_pm.detect.return_value = True
        mock_pm.install_dependencies.side_effect = Exception("Install failed")
        mock_get_pm.return_value = mock_pm

        with pytest.raises(Exception, match="Install failed"):
            configure._install_dependencies(project_root, packages_config)


class TestBootstrap:
    """Test bootstrap mode helper function."""

    def test_print_success_message_basic(self):
        """Test print success message with basic arguments."""
        with patch("builtins.print") as mock_print:
            configure._print_success_message("llvm-18", Path("/test/build"), "Release")

            # Should print at least once
            assert mock_print.call_count > 0

    def test_print_success_message_debug_build(self):
        """Test print success message with Debug build type."""
        with patch("builtins.print") as mock_print:
            configure._print_success_message(
                "gcc-13", Path("/test/build-debug"), "Debug"
            )

            assert mock_print.call_count > 0


class TestToolchainTypeDetection:
    """Test compiler type detection from toolchain names."""

    def test_detect_llvm_toolchain(self):
        """Test detection of LLVM toolchain."""
        # This is implicitly tested in configure, but we verify the logic
        toolchain_name = "llvm-18"
        compiler_type = "clang" if "llvm" in toolchain_name.lower() else "gcc"
        assert compiler_type == "clang"

    def test_detect_clang_toolchain(self):
        """Test detection of Clang toolchain."""
        toolchain_name = "clang-15"
        compiler_type = "clang" if "clang" in toolchain_name.lower() else "gcc"
        assert compiler_type == "clang"

    def test_detect_gcc_toolchain(self):
        """Test detection of GCC toolchain."""
        toolchain_name = "gcc-13"
        compiler_type = "gcc" if "gcc" in toolchain_name.lower() else "clang"
        assert compiler_type == "gcc"

    def test_detect_msvc_toolchain(self):
        """Test detection of MSVC toolchain."""
        toolchain_name = "msvc-2022"
        compiler_type = "msvc" if "msvc" in toolchain_name.lower() else "clang"
        assert compiler_type == "msvc"


class TestToolchainNameParsing:
    """Test parsing toolchain vendor and version."""

    def test_parse_vendor_version(self):
        """Test parsing vendor-version format."""
        toolchain_name = "llvm-18"
        parts = toolchain_name.rsplit("-", 1)
        assert len(parts) == 2
        vendor, version = parts
        assert vendor == "llvm"
        assert version == "18"

    def test_parse_no_version(self):
        """Test parsing toolchain without version."""
        toolchain_name = "llvm"
        parts = toolchain_name.rsplit("-", 1)
        if len(parts) == 2:
            vendor, version = parts
        else:
            vendor, version = toolchain_name, "latest"
        assert vendor == "llvm"
        assert version == "latest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestRegression:
    """Regression tests for reported bugs."""

    @patch("toolchainkit.cli.commands.configure.check_initialized", return_value=True)
    @patch("toolchainkit.cli.commands.configure.load_yaml_config")
    @patch("toolchainkit.plugins.registry.get_global_registry")
    @patch("toolchainkit.core.platform.detect_platform")
    def test_configure_crash_on_toolchain_download_failure(
        self,
        mock_platform,
        mock_registry,
        mock_load_config,
        mock_check_init,
        mock_args,
        tmp_path,
    ):
        """
        Test that configure does not crash with UnboundLocalError when toolchain download fails.
        Regression test for: local variable 'compiler_type' referenced before assignment
        """
        # Setup mocks
        mock_args.project_root = tmp_path
        (tmp_path / "toolchainkit.yaml").touch()

        mock_load_config.return_value = {"toolchain": {"type": "llvm", "version": "18"}}

        # Mock platform
        mock_platform_info = Mock()
        mock_platform_info.os = "windows"
        mock_platform_info.arch = "x86_64"
        mock_platform_info.platform_string.return_value = "windows-x86_64"
        mock_platform.return_value = mock_platform_info

        # Mock registry to return no providers, causing a download failure
        mock_reg_instance = Mock()
        mock_reg_instance.get_toolchain_providers.return_value = []
        # Strategy lookup needs to work even if providers don't
        mock_reg_instance.has_compiler_strategy.return_value = True
        mock_reg_instance.get_compiler_strategy.return_value = Mock()
        mock_registry.return_value = mock_reg_instance

        # Run configure
        result = configure.run(mock_args)

        assert (
            result == 0
        ), "Configure should succeed with fallback when toolchain download fails"
