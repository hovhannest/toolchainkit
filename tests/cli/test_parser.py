"""
Tests for CLI argument parser.
"""

import pytest
from unittest.mock import patch
from pathlib import Path

from toolchainkit.cli.parser import CLI


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_creation(self):
        """Test CLI can be created."""
        cli = CLI()
        assert cli is not None
        assert cli.parser is not None

    def test_no_command_shows_help(self, capsys):
        """Test that running without command shows help."""
        cli = CLI()
        result = cli.run([])

        assert result == 1
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()

    def test_version_flag(self, capsys):
        """Test --version flag."""
        cli = CLI()

        with pytest.raises(SystemExit) as exc_info:
            cli.run(["--version"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "ToolchainKit" in captured.out


class TestInitCommand:
    """Test init command parsing."""

    def test_init_basic(self):
        """Test basic init command."""
        cli = CLI()
        args = cli.parse_args(["init"])

        assert args.command == "init"
        assert args.auto_detect is False
        assert args.toolchain is None
        assert args.minimal is False

    def test_init_with_auto_detect(self):
        """Test init with --auto-detect."""
        cli = CLI()
        args = cli.parse_args(["init", "--auto-detect"])

        assert args.command == "init"
        assert args.auto_detect is True

    def test_init_with_toolchain(self):
        """Test init with --toolchain."""
        cli = CLI()
        args = cli.parse_args(["init", "--toolchain", "llvm-18"])

        assert args.command == "init"
        assert args.toolchain == "llvm-18"

    def test_init_with_minimal(self):
        """Test init with --minimal."""
        cli = CLI()
        args = cli.parse_args(["init", "--minimal"])

        assert args.command == "init"
        assert args.minimal is True

    def test_init_all_options(self):
        """Test init with all options."""
        cli = CLI()
        args = cli.parse_args(
            ["init", "--auto-detect", "--toolchain", "gcc-13", "--minimal"]
        )

        assert args.command == "init"
        assert args.auto_detect is True
        assert args.toolchain == "gcc-13"
        assert args.minimal is True


class TestConfigureCommand:
    """Test configure command parsing."""

    def test_configure_basic(self):
        """Test basic configure command."""
        cli = CLI()
        args = cli.parse_args(["configure", "--toolchain", "llvm-18"])

        assert args.command == "configure"
        assert args.toolchain == "llvm-18"
        assert args.build_type == "Release"
        assert args.build_dir == "build"

    def test_configure_without_toolchain_fails(self):
        """Test configure without required --toolchain fails."""
        cli = CLI()

        with pytest.raises(SystemExit):
            cli.parse_args(["configure"])

    def test_configure_with_stdlib(self):
        """Test configure with --stdlib."""
        cli = CLI()
        args = cli.parse_args(
            ["configure", "--toolchain", "llvm-18", "--stdlib", "libc++"]
        )

        assert args.stdlib == "libc++"

    def test_configure_with_build_type(self):
        """Test configure with --build-type."""
        cli = CLI()
        args = cli.parse_args(
            ["configure", "--toolchain", "gcc-13", "--build-type", "Debug"]
        )

        assert args.build_type == "Debug"

    def test_configure_with_build_dir(self):
        """Test configure with --build-dir."""
        cli = CLI()
        args = cli.parse_args(
            ["configure", "--toolchain", "llvm-18", "--build-dir", "build-release"]
        )

        assert args.build_dir == "build-release"

    def test_configure_with_cache(self):
        """Test configure with --cache."""
        cli = CLI()
        args = cli.parse_args(
            ["configure", "--toolchain", "llvm-18", "--cache", "sccache"]
        )

        assert args.cache == "sccache"

    def test_configure_with_target(self):
        """Test configure with --target."""
        cli = CLI()
        args = cli.parse_args(
            ["configure", "--toolchain", "llvm-18", "--target", "android-arm64"]
        )

        assert args.target == "android-arm64"

    def test_configure_with_clean(self):
        """Test configure with --clean."""
        cli = CLI()
        args = cli.parse_args(["configure", "--toolchain", "llvm-18", "--clean"])

        assert args.clean is True

    def test_configure_all_options(self):
        """Test configure with all options."""
        cli = CLI()
        args = cli.parse_args(
            [
                "configure",
                "--toolchain",
                "llvm-18",
                "--stdlib",
                "libc++",
                "--build-type",
                "RelWithDebInfo",
                "--build-dir",
                "build-custom",
                "--cache",
                "ccache",
                "--target",
                "ios-arm64",
                "--clean",
            ]
        )

        assert args.command == "configure"
        assert args.toolchain == "llvm-18"
        assert args.stdlib == "libc++"
        assert args.build_type == "RelWithDebInfo"
        assert args.build_dir == "build-custom"
        assert args.cache == "ccache"
        assert args.target == "ios-arm64"
        assert args.clean is True


class TestCleanupCommand:
    """Test cleanup command parsing."""

    def test_cleanup_basic(self):
        """Test basic cleanup command."""
        cli = CLI()
        args = cli.parse_args(["cleanup"])

        assert args.command == "cleanup"
        assert args.dry_run is False
        assert args.unused is False
        assert args.older_than is None
        assert args.toolchain is None

    def test_cleanup_with_dry_run(self):
        """Test cleanup with --dry-run."""
        cli = CLI()
        args = cli.parse_args(["cleanup", "--dry-run"])

        assert args.dry_run is True

    def test_cleanup_with_unused(self):
        """Test cleanup with --unused."""
        cli = CLI()
        args = cli.parse_args(["cleanup", "--unused"])

        assert args.unused is True

    def test_cleanup_with_older_than(self):
        """Test cleanup with --older-than."""
        cli = CLI()
        args = cli.parse_args(["cleanup", "--older-than", "90"])

        assert args.older_than == 90

    def test_cleanup_with_toolchain(self):
        """Test cleanup with --toolchain."""
        cli = CLI()
        args = cli.parse_args(["cleanup", "--toolchain", "llvm-17"])

        assert args.toolchain == "llvm-17"

    def test_cleanup_all_options(self):
        """Test cleanup with all options."""
        cli = CLI()
        args = cli.parse_args(
            [
                "cleanup",
                "--dry-run",
                "--unused",
                "--older-than",
                "60",
                "--toolchain",
                "gcc-12",
            ]
        )

        assert args.dry_run is True
        assert args.unused is True
        assert args.older_than == 60
        assert args.toolchain == "gcc-12"


class TestUpgradeCommand:
    """Test upgrade command parsing."""

    def test_upgrade_basic(self):
        """Test basic upgrade command."""
        cli = CLI()
        args = cli.parse_args(["upgrade"])

        assert args.command == "upgrade"
        assert args.toolchain is None
        assert args.all is False

    def test_upgrade_with_toolchain(self):
        """Test upgrade with --toolchain."""
        cli = CLI()
        args = cli.parse_args(["upgrade", "--toolchain", "llvm-18"])

        assert args.toolchain == "llvm-18"

    def test_upgrade_with_all(self):
        """Test upgrade with --all."""
        cli = CLI()
        args = cli.parse_args(["upgrade", "--all"])

        assert args.all is True


class TestVerifyCommand:
    """Test verify command parsing."""

    def test_verify_basic(self):
        """Test basic verify command."""
        cli = CLI()
        args = cli.parse_args(["verify"])

        assert args.command == "verify"
        assert args.full is False

    def test_verify_with_full(self):
        """Test verify with --full."""
        cli = CLI()
        args = cli.parse_args(["verify", "--full"])

        assert args.full is True


class TestGlobalOptions:
    """Test global options."""

    def test_verbose_flag(self):
        """Test --verbose flag."""
        cli = CLI()
        args = cli.parse_args(["--verbose", "init"])

        assert args.verbose is True
        assert args.command == "init"

    def test_quiet_flag(self):
        """Test --quiet flag."""
        cli = CLI()
        args = cli.parse_args(["--quiet", "configure", "--toolchain", "llvm-18"])

        assert args.quiet is True
        assert args.command == "configure"

    def test_config_option(self):
        """Test --config option."""
        cli = CLI()
        args = cli.parse_args(["--config", "custom.yaml", "init"])

        assert args.config == Path("custom.yaml")

    def test_project_root_option(self):
        """Test --project-root option."""
        cli = CLI()
        args = cli.parse_args(["--project-root", "/path/to/project", "init"])

        assert args.project_root == Path("/path/to/project")


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_default_logging(self):
        """Test default logging level."""
        cli = CLI()
        args = cli.parse_args(["init"])
        cli._configure_logging(args)

        import logging

        logger = logging.getLogger()
        assert logger.level == logging.INFO

    def test_verbose_logging(self):
        """Test verbose logging level."""
        cli = CLI()
        args = cli.parse_args(["--verbose", "init"])
        cli._configure_logging(args)

        import logging

        logger = logging.getLogger()
        assert logger.level == logging.DEBUG

    def test_quiet_logging(self):
        """Test quiet logging level."""
        cli = CLI()
        args = cli.parse_args(["--quiet", "init"])
        cli._configure_logging(args)

        import logging

        logger = logging.getLogger()
        assert logger.level == logging.ERROR


class TestCommandDispatch:
    """Test command dispatch system."""

    @patch("toolchainkit.cli.commands.init.run")
    def test_dispatch_init(self, mock_run):
        """Test dispatching to init command."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(["init"])

        assert result == 0
        assert mock_run.called

    @patch("toolchainkit.cli.commands.configure.run")
    def test_dispatch_configure(self, mock_run):
        """Test dispatching to configure command."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(["configure", "--toolchain", "llvm-18"])

        assert result == 0
        assert mock_run.called

    @patch("toolchainkit.cli.commands.cleanup.run")
    def test_dispatch_cleanup(self, mock_run):
        """Test dispatching to cleanup command."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(["cleanup"])

        assert result == 0
        assert mock_run.called

    @patch("toolchainkit.cli.commands.upgrade.run")
    def test_dispatch_upgrade(self, mock_run):
        """Test dispatching to upgrade command."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(["upgrade"])

        assert result == 0
        assert mock_run.called

    @patch("toolchainkit.cli.commands.verify.run")
    def test_dispatch_verify(self, mock_run):
        """Test dispatching to verify command."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(["verify"])

        assert result == 0
        assert mock_run.called


class TestErrorHandling:
    """Test error handling."""

    def test_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt."""
        cli = CLI()

        with patch("toolchainkit.cli.parser.CLI._dispatch_command") as mock_dispatch:
            mock_dispatch.side_effect = KeyboardInterrupt()

            result = cli.run(["init"])
            assert result == 130  # SIGINT exit code

    def test_exception_handling(self, capsys):
        """Test generic exception handling."""
        cli = CLI()

        with patch("toolchainkit.cli.parser.CLI._dispatch_command") as mock_dispatch:
            mock_dispatch.side_effect = RuntimeError("Test error")

            result = cli.run(["init"])
            assert result == 1

            captured = capsys.readouterr()
            assert "Error:" in captured.err or "Test error" in captured.err

    def test_exception_with_verbose(self, capsys):
        """Test exception handling with verbose mode."""
        cli = CLI()

        with patch("toolchainkit.cli.parser.CLI._dispatch_command") as mock_dispatch:
            mock_dispatch.side_effect = RuntimeError("Test error")

            result = cli.run(["--verbose", "init"])
            assert result == 1

            # Verbose mode should show traceback
            # In verbose mode we print traceback to stderr


class TestHelpText:
    """Test help text generation."""

    def test_main_help(self, capsys):
        """Test main help text."""
        cli = CLI()

        with pytest.raises(SystemExit):
            cli.parse_args(["--help"])

        captured = capsys.readouterr()
        assert "tkgen" in captured.out
        assert "init" in captured.out
        assert "configure" in captured.out

    def test_init_help(self, capsys):
        """Test init command help."""
        cli = CLI()

        with pytest.raises(SystemExit):
            cli.parse_args(["init", "--help"])

        captured = capsys.readouterr()
        assert "init" in captured.out.lower()
        assert "auto-detect" in captured.out.lower()

    def test_configure_help(self, capsys):
        """Test configure command help."""
        cli = CLI()

        with pytest.raises(SystemExit):
            cli.parse_args(["configure", "--help"])

        captured = capsys.readouterr()
        assert "configure" in captured.out.lower()
        assert "toolchain" in captured.out.lower()


class TestIntegration:
    """Integration tests for CLI."""

    def test_full_init_workflow(self, tmp_path):
        """Test full init workflow."""
        # Create a minimal CMakeLists.txt
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        cli = CLI()
        result = cli.run(
            [
                "--verbose",
                "--project-root",
                str(tmp_path),
                "init",
                "--auto-detect",
                "--toolchain",
                "llvm-18",
                "--minimal",
            ]
        )

        assert result == 0
        # Verify config file was created with specified toolchain
        config_file = tmp_path / "toolchainkit.yaml"
        assert config_file.exists()
        config_content = config_file.read_text()
        assert "llvm-18" in config_content

    @patch("toolchainkit.cli.commands.configure.run")
    def test_full_configure_workflow(self, mock_run):
        """Test full configure workflow."""
        mock_run.return_value = 0
        cli = CLI()
        result = cli.run(
            [
                "configure",
                "--toolchain",
                "gcc-13",
                "--stdlib",
                "libstdc++",
                "--build-type",
                "Debug",
                "--cache",
                "sccache",
            ]
        )

        assert result == 0
        assert mock_run.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
