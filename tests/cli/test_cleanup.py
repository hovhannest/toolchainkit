"""
Tests for cleanup command.
"""

import logging
from unittest.mock import Mock


from toolchainkit.cli.commands import cleanup


class TestCleanupCommand:
    """Test cleanup command functionality."""

    def test_cleanup_basic_run(self):
        """Test basic cleanup command execution."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_with_dry_run(self):
        """Test cleanup with --dry-run flag."""
        args = Mock(
            dry_run=True,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_with_unused_flag(self):
        """Test cleanup with --unused flag."""
        args = Mock(
            dry_run=False,
            unused=True,
            older_than=None,
            toolchain=None,
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_with_older_than(self):
        """Test cleanup with --older-than parameter."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than="30d",
            toolchain=None,
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_with_specific_toolchain(self):
        """Test cleanup with specific toolchain."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain="gcc-11.2.0",
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_with_all_options(self):
        """Test cleanup with all options combined."""
        args = Mock(
            dry_run=True,
            unused=True,
            older_than="7d",
            toolchain="clang-14.0.0",
        )

        result = cleanup.run(args)

        assert result == 0

    def test_cleanup_logs_info_message(self, caplog):
        """Test that cleanup logs an info message."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        with caplog.at_level(logging.INFO):
            cleanup.run(args)

        assert "Cleanup command" in caplog.text

    def test_cleanup_logs_debug_arguments(self, caplog):
        """Test that cleanup logs debug information."""
        args = Mock(
            dry_run=True,
            unused=True,
            older_than="14d",
            toolchain="gcc",
        )

        with caplog.at_level(logging.DEBUG):
            cleanup.run(args)

        assert "Arguments:" in caplog.text

    def test_cleanup_output_dry_run_true(self, capsys):
        """Test cleanup output shows dry_run True."""
        args = Mock(
            dry_run=True,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        cleanup.run(args)
        captured = capsys.readouterr()

        assert "--dry-run: True" in captured.out

    def test_cleanup_output_dry_run_false(self, capsys):
        """Test cleanup output shows dry_run False."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        cleanup.run(args)
        captured = capsys.readouterr()

        assert "--dry-run: False" in captured.out

    def test_cleanup_output_unused_flag(self, capsys):
        """Test cleanup output shows unused flag."""
        args = Mock(
            dry_run=False,
            unused=True,
            older_than=None,
            toolchain=None,
        )

        cleanup.run(args)
        captured = capsys.readouterr()

        assert "--unused: True" in captured.out

    def test_cleanup_output_older_than(self, capsys):
        """Test cleanup output shows older-than value."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than="30d",
            toolchain=None,
        )

        cleanup.run(args)
        captured = capsys.readouterr()

        assert "--older-than: 30d" in captured.out

    def test_cleanup_output_toolchain(self, capsys):
        """Test cleanup output shows toolchain value."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain="gcc-11.2.0",
        )

        cleanup.run(args)
        captured = capsys.readouterr()

        assert "--toolchain: gcc-11.2.0" in captured.out

    def test_cleanup_returns_zero_exit_code(self):
        """Test cleanup always returns 0 (success)."""
        args = Mock(
            dry_run=False,
            unused=False,
            older_than=None,
            toolchain=None,
        )

        result = cleanup.run(args)

        assert result == 0
        assert isinstance(result, int)

    def test_cleanup_handles_none_values(self):
        """Test cleanup handles None values in arguments."""
        args = Mock(
            dry_run=None,
            unused=None,
            older_than=None,
            toolchain=None,
        )

        # Should not raise an exception
        result = cleanup.run(args)

        assert result == 0
