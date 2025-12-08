"""
Tests for doctor command.

This module tests the environment diagnostic functionality.
"""

import pytest
from unittest.mock import Mock, patch
import subprocess

from toolchainkit.cli.commands.doctor import EnvironmentChecker, CheckResult, run


class TestCheckResult:
    """Test CheckResult dataclass."""

    def test_check_result_passed(self):
        """Test CheckResult with passed check."""
        result = CheckResult(
            name="Test", passed=True, message="Test passed", fixable=False
        )

        assert result.name == "Test"
        assert result.passed is True
        assert result.message == "Test passed"
        assert result.fix_command is None
        assert result.fixable is False

    def test_check_result_failed(self):
        """Test CheckResult with failed check."""
        result = CheckResult(
            name="Test",
            passed=False,
            message="Test failed",
            fix_command="Run: fix command",
            fixable=True,
        )

        assert result.name == "Test"
        assert result.passed is False
        assert result.message == "Test failed"
        assert result.fix_command == "Run: fix command"
        assert result.fixable is True


class TestEnvironmentChecker:
    """Test EnvironmentChecker class."""

    def test_check_python_success(self):
        """Test Python version check when version is sufficient."""
        checker = EnvironmentChecker()
        result = checker.check_python()

        assert result.name == "Python"
        # Should pass since we're running with Python 3.8+
        assert result.passed is True
        assert "Python" in result.message
        assert result.fix_command is None

    def test_check_python_old_version(self):
        """Test Python version check with old Python version."""
        # Create a namedtuple similar to sys.version_info
        from collections import namedtuple

        VersionInfo = namedtuple(
            "VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"]
        )
        old_version = VersionInfo(3, 7, 0, "final", 0)

        with patch("toolchainkit.cli.commands.doctor.sys.version_info", old_version):
            checker = EnvironmentChecker()
            result = checker.check_python()

            assert result.name == "Python"
            assert result.passed is False
            assert "too old" in result.message
            assert "3.8+" in result.message
            assert result.fix_command is not None
            assert "python.org" in result.fix_command.lower()

    @patch("subprocess.run")
    def test_check_cmake_success(self, mock_run):
        """Test CMake check when CMake is installed."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="cmake version 3.27.0\n\nCMake suite maintained by Kitware",
        )

        checker = EnvironmentChecker()
        result = checker.check_cmake()

        assert result.name == "CMake"
        assert result.passed is True
        assert "cmake version" in result.message
        assert result.fix_command is None

    @patch("subprocess.run", side_effect=FileNotFoundError())
    def test_check_cmake_not_found(self, mock_run):
        """Test CMake check when CMake is not installed."""
        checker = EnvironmentChecker()
        result = checker.check_cmake()

        assert result.name == "CMake"
        assert result.passed is False
        assert "not found" in result.message
        assert result.fix_command is not None
        assert "cmake.org" in result.fix_command

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmake", 5))
    def test_check_cmake_timeout(self, mock_run):
        """Test CMake check when command times out."""
        checker = EnvironmentChecker()
        result = checker.check_cmake()

        assert result.name == "CMake"
        assert result.passed is False
        assert "timed out" in result.message.lower()

    def test_check_toolchain_no_config(self, tmp_path):
        """Test toolchain check when config file doesn't exist."""
        checker = EnvironmentChecker()
        result = checker.check_toolchain(tmp_path)

        assert result.name == "Toolchain Config"
        assert result.passed is False
        assert "toolchainkit.yaml" in result.message
        assert result.fix_command is not None
        assert "init" in result.fix_command

    def test_check_toolchain_no_directory(self, tmp_path):
        """Test toolchain check when .toolchainkit directory doesn't exist."""
        # Create config file
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        checker = EnvironmentChecker()
        result = checker.check_toolchain(tmp_path)

        assert result.name == "Toolchain"
        assert result.passed is False
        assert ".toolchainkit" in result.message
        assert result.fix_command is not None
        assert "configure" in result.fix_command

    def test_check_toolchain_no_toolchains(self, tmp_path):
        """Test toolchain check when no toolchains are installed."""
        # Create config file and directory
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        toolchain_dir = tmp_path / ".toolchainkit" / "toolchains"
        toolchain_dir.mkdir(parents=True)

        checker = EnvironmentChecker()
        result = checker.check_toolchain(tmp_path)

        assert result.name == "Toolchain"
        assert result.passed is False
        assert "No toolchains installed" in result.message
        assert result.fix_command is not None

    def test_check_toolchain_success(self, tmp_path):
        """Test toolchain check when toolchain is properly configured."""
        # Create config file, directory, and a toolchain
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        toolchain_dir = tmp_path / ".toolchainkit" / "toolchains"
        toolchain_dir.mkdir(parents=True)

        # Create a dummy toolchain directory
        (toolchain_dir / "llvm-18").mkdir()
        (toolchain_dir / "llvm-18" / "bin").mkdir()

        checker = EnvironmentChecker()
        result = checker.check_toolchain(tmp_path)

        assert result.name == "Toolchain"
        assert result.passed is True
        assert "found" in result.message.lower()

    @patch("shutil.which", return_value="/usr/bin/sccache")
    def test_check_build_cache_sccache(self, mock_which):
        """Test build cache check when sccache is available."""
        checker = EnvironmentChecker()
        result = checker.check_build_cache()

        assert result.name == "Build Cache"
        assert result.passed is True
        assert "sccache" in result.message
        assert result.fix_command is None

    @patch("shutil.which")
    def test_check_build_cache_ccache(self, mock_which):
        """Test build cache check when ccache is available."""

        def which_side_effect(name):
            if name == "sccache":
                return None
            elif name == "ccache":
                return "/usr/bin/ccache"
            return None

        mock_which.side_effect = which_side_effect

        checker = EnvironmentChecker()
        result = checker.check_build_cache()

        assert result.name == "Build Cache"
        assert result.passed is True
        assert "ccache" in result.message

    @patch("shutil.which", return_value=None)
    def test_check_build_cache_not_found(self, mock_which):
        """Test build cache check when no cache tool is available."""
        checker = EnvironmentChecker()
        result = checker.check_build_cache()

        assert result.name == "Build Cache"
        assert result.passed is False
        assert "no build cache" in result.message.lower()
        assert result.fix_command is not None
        assert "sccache" in result.fix_command

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/ninja")
    def test_check_ninja_success(self, mock_which, mock_run):
        """Test Ninja check when Ninja is installed."""
        mock_run.return_value = Mock(returncode=0, stdout="1.11.1")

        checker = EnvironmentChecker()
        result = checker.check_ninja()

        assert result.name == "Ninja"
        assert result.passed is True
        assert "Ninja" in result.message
        assert "found" in result.message.lower()

    @patch("shutil.which", return_value=None)
    def test_check_ninja_not_found(self, mock_which):
        """Test Ninja check when Ninja is not installed."""
        checker = EnvironmentChecker()
        result = checker.check_ninja()

        assert result.name == "Ninja"
        assert result.passed is False
        assert "not found" in result.message.lower()
        assert result.fix_command is not None
        assert "ninja" in result.fix_command.lower()


class TestDoctorCommand:
    """Test doctor command integration."""

    def test_run_all_checks_pass(self, tmp_path, capsys):
        """Test doctor command when all checks pass."""
        # Setup environment
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        toolchain_dir = tmp_path / ".toolchainkit" / "toolchains"
        toolchain_dir.mkdir(parents=True)
        (toolchain_dir / "llvm-18").mkdir()

        # Create mock args
        args = Mock()
        args.quiet = True
        args.project_root = tmp_path
        args.fix = False

        # Patch external checks
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="cmake version 3.27.0")

            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/ninja"

                exit_code = run(args)

        assert exit_code == 0

    def test_run_with_failures(self, tmp_path, capsys):
        """Test doctor command with failures."""
        # No config file, no cmake, etc.
        args = Mock()
        args.quiet = False
        args.project_root = tmp_path
        args.fix = False

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with patch("shutil.which", return_value=None):
                exit_code = run(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "critical issue" in captured.out.lower()

    def test_run_with_warnings_only(self, tmp_path, capsys):
        """Test doctor command with only warnings (optional tools missing)."""
        # Setup basic environment (config + toolchains)
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        toolchain_dir = tmp_path / ".toolchainkit" / "toolchains"
        toolchain_dir.mkdir(parents=True)
        (toolchain_dir / "llvm-18").mkdir()

        args = Mock()
        args.quiet = False
        args.project_root = tmp_path
        args.fix = False

        # CMake exists, but ninja and build cache don't
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="cmake version 3.27.0")

            with patch("shutil.which", return_value=None):
                exit_code = run(args)

        assert exit_code == 0  # Warnings don't fail
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "warning" in captured.out.lower()

    def test_run_quiet_mode(self, tmp_path, capsys):
        """Test doctor command in quiet mode."""
        config = tmp_path / "toolchainkit.yaml"
        config.write_text("version: 1\nproject:\n  name: test\n")

        toolchain_dir = tmp_path / ".toolchainkit" / "toolchains"
        toolchain_dir.mkdir(parents=True)
        (toolchain_dir / "llvm-18").mkdir()

        args = Mock()
        args.quiet = True
        args.project_root = tmp_path
        args.fix = False

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="cmake version 3.27.0")

            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/ninja"

                exit_code = run(args)

        captured = capsys.readouterr()
        # In quiet mode, minimal output
        assert "🏥" not in captured.out
        assert exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
