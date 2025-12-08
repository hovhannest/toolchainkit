import argparse
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from toolchainkit.cli.commands import init, configure, bootstrap, doctor
from toolchainkit.cli.utils import check_initialized


class TestCustomConfig:
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project root with CMakeLists.txt."""
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.15)\nproject(Test)"
        )
        return tmp_path

    def test_init_custom_config(self, project_root):
        """Test 'init' with custom config file."""
        custom_config = project_root / "custom.yaml"
        args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain="llvm-18",
            minimal=True,
            auto_detect=False,
            force=False,
        )

        assert init.run(args) == 0
        assert custom_config.exists()
        assert not (project_root / "toolchainkit.yaml").exists()

        # Verify content
        content = custom_config.read_text()
        assert "name: llvm-18" in content

    def test_configure_custom_config(self, project_root):
        """Test 'configure' with custom config file."""
        # First init
        custom_config = project_root / "custom.yaml"
        init_args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain="llvm-18",
            minimal=True,
            auto_detect=False,
            force=False,
        )
        init.run(init_args)

        # Then configure
        args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain="llvm-18",
            build_type="Release",
            build_dir="build",
            clean=False,
            target=None,
            stdlib=None,
            cache=None,
        )

        # Mock provider to avoid actual network calls
        mock_provider = MagicMock()
        mock_provider.can_provide.return_value = True
        mock_provider.provide_toolchain.return_value = Path("/tmp/fake/toolchain")
        mock_provider.get_toolchain_id.return_value = "llvm-18-linux-x64"

        # Mock registry to return our provider
        mock_registry = MagicMock()
        mock_registry.get_toolchain_providers.return_value = [mock_provider]
        mock_registry.has_compiler_strategy.return_value = True
        mock_registry.get_compiler_strategy.return_value = MagicMock()

        with patch(
            "toolchainkit.plugins.registry.get_global_registry",
            return_value=mock_registry,
        ):
            # Mock generator
            with patch(
                "toolchainkit.cmake.toolchain_generator.CMakeToolchainGenerator"
            ), patch("toolchainkit.core.platform.detect_platform") as mock_platform:
                mock_platform.return_value.os = "linux"
                mock_platform.return_value.arch = "x64"
                assert configure.run(args) == 0

    def test_bootstrap_custom_config(self, project_root):
        """Test 'bootstrap' with custom config file."""
        # First init
        custom_config = project_root / "custom.yaml"
        init_args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain="llvm-18",
            minimal=True,
            auto_detect=False,
            force=False,
        )
        init.run(init_args)

        # Then bootstrap
        args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain=None,
            build_type=None,
            force=True,
            dry_run=False,
            platform="all",
        )

        assert bootstrap.run(args) == 0
        assert (project_root / "bootstrap.sh").exists() or (
            project_root / "bootstrap.bat"
        ).exists()

    def test_doctor_custom_config(self, project_root):
        """Test 'doctor' with custom config file."""
        # First init
        custom_config = project_root / "custom.yaml"
        init_args = argparse.Namespace(
            project_root=project_root,
            config=custom_config,
            toolchain="llvm-18",
            minimal=True,
            auto_detect=False,
            force=False,
        )
        init.run(init_args)

        # Then doctor
        args = argparse.Namespace(
            project_root=project_root, config=custom_config, quiet=True, fix=False
        )

        # Doctor might fail on other checks (cmake, python etc), but we check if it finds the toolchain config
        # We can mock the runner to check if it receives the config file
        with patch("toolchainkit.cli.commands.doctor.DoctorRunner") as MockRunner:
            mock_instance = MockRunner.return_value
            mock_instance.run_all_checks.return_value = []

            doctor.run(args)

            MockRunner.assert_called_with(project_root, custom_config)

    def test_check_initialized_utils(self, project_root):
        """Test check_initialized utility."""
        custom_config = project_root / "custom.yaml"
        custom_config.touch()

        assert check_initialized(project_root, custom_config)
        assert not check_initialized(project_root)  # Default should fail
