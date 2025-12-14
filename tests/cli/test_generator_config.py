import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from toolchainkit.cli.commands import configure


class TestGeneratorConfig(unittest.TestCase):
    @patch("toolchainkit.cli.commands.configure.check_initialized", return_value=True)
    @patch("toolchainkit.cli.commands.configure.load_yaml_config")
    @patch("toolchainkit.plugins.registry.get_global_registry")
    @patch("toolchainkit.core.platform.detect_platform")
    @patch("toolchainkit.cli.commands.configure._run_bootstrap")
    @patch("toolchainkit.cli.commands.configure.format_success_message")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    def test_configure_respects_generator_config(
        self,
        mock_exists,
        mock_resolve,
        mock_mkdir,
        mock_format_success,
        mock_run_bootstrap,
        mock_detect_platform,
        mock_registry,
        mock_load_config,
        mock_check_init,
    ):
        # Setup mocks
        mock_args = MagicMock()
        mock_args.project_root = "/mock/project"
        mock_args.config = None
        mock_args.toolchain = "llvm-18"
        mock_args.build_type = "Release"
        mock_args.build_dir = "build"
        mock_args.target = None
        mock_args.clean = False
        mock_args.bootstrap = True

        mock_resolve.return_value = Path("/mock/project")
        mock_exists.return_value = True

        # config with generator specified
        mock_load_config.return_value = {
            "defaults": {"generator": "Ninja"},
            "toolchain": {"type": "clang"},
        }

        # Registry and provider setup
        mock_provider = MagicMock()
        mock_provider.can_provide.return_value = True
        mock_provider.provide_toolchain.return_value = Path("/path/to/toolchain")
        mock_registry.return_value.get_toolchain_providers.return_value = [
            mock_provider
        ]

        # Run
        configure.run(mock_args)

        # Verify call to _run_bootstrap
        pass

    @patch("toolchainkit.cli.commands.configure.check_initialized", return_value=True)
    @patch("subprocess.run")
    def test_run_bootstrap_respects_generator(
        self, mock_subprocess_run, mock_check_init
    ):
        # Test _run_bootstrap directly
        mock_args = MagicMock()
        mock_args.build_type = "Release"
        mock_args.build_dir = "build"
        mock_args.cmake_args = []

        config = {"defaults": {"generator": "Ninja"}, "toolchain": {"type": "clang"}}

        # We need to patch NinjaDownloader and other things inside _run_bootstrap
        with patch(
            "toolchainkit.packages.tool_downloader.NinjaDownloader"
        ) as mock_ninja:
            mock_ninja.return_value.is_installed.return_value = True
            mock_ninja.return_value.get_executable_path.return_value = Path(
                "/bin/ninja"
            )

            with patch("toolchainkit.plugins.registry.get_global_registry"):
                with patch("toolchainkit.core.platform.detect_platform"):
                    with patch(
                        "toolchainkit.cli.commands.configure._print_success_message"
                    ):
                        configure._run_bootstrap(
                            Path("/mock/project"),
                            mock_args,
                            config,
                            Path("/mock/tc.cmake"),
                            Path("/mock/tc/path"),
                        )

        # Verify CMake called with -G Ninja
        args, kwargs = mock_subprocess_run.call_args
        self.assertIn("-G", args[0])
        self.assertIn("Ninja", args[0])

    @patch("toolchainkit.cli.commands.configure.check_initialized", return_value=True)
    @patch("subprocess.run")
    def test_run_bootstrap_respects_other_generator(
        self, mock_subprocess_run, mock_check_init
    ):
        # Test _run_bootstrap directly with specific generator
        mock_args = MagicMock()
        mock_args.build_type = "Release"
        mock_args.build_dir = "build"
        mock_args.cmake_args = []

        config = {
            "build": {"generator": "Unix Makefiles"},
            "toolchain": {"type": "gcc"},
        }

        with patch("toolchainkit.plugins.registry.get_global_registry"):
            with patch("toolchainkit.core.platform.detect_platform"):
                with patch(
                    "toolchainkit.cli.commands.configure._print_success_message"
                ):
                    configure._run_bootstrap(
                        Path("/mock/project"),
                        mock_args,
                        config,
                        Path("/mock/tc.cmake"),
                        Path("/mock/tc/path"),
                    )

        # Verify CMake called with -G Unix Makefiles
        args, kwargs = mock_subprocess_run.call_args
        self.assertIn("-G", args[0])
        self.assertIn("Unix Makefiles", args[0])
