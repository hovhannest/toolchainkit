"""
Unit tests for upgrade command and toolchain upgrader.

Tests cover:
- Version parsing and comparison
- Update checking logic
- Toolchain upgrade orchestration
- CLI command functionality
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from toolchainkit.toolchain.upgrader import (
    Version,
    VersionComparisonError,
    UpdateInfo,
    UpgradeResult,
    ToolchainUpgrader,
    UpdateCheckError,
    check_toolchainkit_updates,
    upgrade_toolchainkit,
)
from toolchainkit.cli.commands import upgrade as upgrade_command


# ============================================================================
# Version Class Tests
# ============================================================================


class TestVersion:
    """Test Version class for semantic version parsing and comparison."""

    def test_version_parsing_three_parts(self):
        """Test parsing version with major.minor.patch."""
        v = Version("18.1.8")
        assert v.major == 18
        assert v.minor == 1
        assert v.patch == 8
        assert str(v) == "18.1.8"

    def test_version_parsing_two_parts(self):
        """Test parsing version with major.minor (patch defaults to 0)."""
        v = Version("13.2")
        assert v.major == 13
        assert v.minor == 2
        assert v.patch == 0
        assert str(v) == "13.2.0"

    def test_version_parsing_with_leading_v(self):
        """Test parsing version with leading 'v'."""
        v = Version("v18.1.8")
        assert v.major == 18
        assert v.minor == 1
        assert v.patch == 8

    def test_version_comparison_less_than(self):
        """Test version less than comparison."""
        v1 = Version("18.1.7")
        v2 = Version("18.1.8")
        assert v1 < v2
        assert not v2 < v1

    def test_version_comparison_greater_than(self):
        """Test version greater than comparison."""
        v1 = Version("18.1.9")
        v2 = Version("18.1.8")
        assert v1 > v2
        assert not v2 > v1

    def test_version_comparison_equal(self):
        """Test version equality."""
        v1 = Version("18.1.8")
        v2 = Version("18.1.8")
        assert v1 == v2
        assert not v1 != v2

    def test_version_comparison_major_difference(self):
        """Test comparison with different major versions."""
        v1 = Version("17.0.0")
        v2 = Version("18.0.0")
        assert v1 < v2
        assert v2 > v1

    def test_version_comparison_minor_difference(self):
        """Test comparison with different minor versions."""
        v1 = Version("18.0.0")
        v2 = Version("18.1.0")
        assert v1 < v2
        assert v2 > v1

    def test_version_invalid_format_one_part(self):
        """Test invalid version with single part."""
        with pytest.raises(VersionComparisonError, match="Invalid version format"):
            Version("18")

    def test_version_invalid_format_too_many_parts(self):
        """Test invalid version with too many parts."""
        with pytest.raises(VersionComparisonError, match="Invalid version format"):
            Version("18.1.8.2")

    def test_version_invalid_format_non_numeric(self):
        """Test invalid version with non-numeric parts."""
        with pytest.raises(VersionComparisonError, match="must be integers"):
            Version("18.abc.8")

    def test_version_repr(self):
        """Test version representation."""
        v = Version("18.1.8")
        assert repr(v) == "Version('18.1.8')"


# ============================================================================
# Update Checking Tests
# ============================================================================


class TestUpdateChecking:
    """Test update checking functionality."""

    @patch("toolchainkit.toolchain.upgrader.requests.get")
    @patch("importlib.metadata.version")
    def test_check_toolchainkit_updates_available(self, mock_version, mock_get):
        """Test checking for ToolchainKit updates when update available."""
        # Mock current version
        mock_version.return_value = "0.1.0"

        # Mock PyPI response
        pypi_data = {"info": {"version": "0.2.0"}}
        mock_response = MagicMock()
        mock_response.json.return_value = pypi_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = check_toolchainkit_updates()

        assert result is not None
        assert result == ("0.1.0", "0.2.0")

    @patch("toolchainkit.toolchain.upgrader.requests.get")
    @patch("importlib.metadata.version")
    def test_check_toolchainkit_updates_up_to_date(self, mock_version, mock_get):
        """Test checking for updates when already up to date."""
        mock_version.return_value = "0.2.0"

        pypi_data = {"info": {"version": "0.2.0"}}
        mock_response = MagicMock()
        mock_response.json.return_value = pypi_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = check_toolchainkit_updates()

        assert result is None

    @patch("toolchainkit.toolchain.upgrader.requests.get")
    @patch("importlib.metadata.version")
    def test_check_toolchainkit_updates_network_error(self, mock_version, mock_get):
        """Test handling network errors when checking for updates."""
        import requests

        mock_version.return_value = "0.1.0"
        mock_get.side_effect = requests.RequestException("Network error")

        result = check_toolchainkit_updates()

        assert result is None  # Should return None on error

    @patch("subprocess.run")
    @patch("sys.executable", "/usr/bin/python3")
    def test_upgrade_toolchainkit_success(self, mock_run):
        """Test successful ToolchainKit upgrade."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = upgrade_toolchainkit()

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "pip" in args
        assert "install" in args
        assert "--upgrade" in args
        assert "toolchainkit" in args

    @patch("subprocess.run")
    def test_upgrade_toolchainkit_failure(self, mock_run):
        """Test failed ToolchainKit upgrade."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error message"
        mock_run.return_value = mock_result

        result = upgrade_toolchainkit()

        assert result is False


# ============================================================================
# ToolchainUpgrader Tests
# ============================================================================


class TestToolchainUpgrader:
    """Test ToolchainUpgrader class."""

    @pytest.fixture
    def mock_upgrader(self):
        """Create upgrader with mocked dependencies."""
        with patch("toolchainkit.toolchain.upgrader.ToolchainMetadataRegistry"), patch(
            "toolchainkit.toolchain.upgrader.ToolchainCacheRegistry"
        ), patch("toolchainkit.toolchain.upgrader.ToolchainDownloader"), patch(
            "toolchainkit.toolchain.upgrader.ToolchainVerifier"
        ), patch("toolchainkit.toolchain.upgrader.LockManager"):
            upgrader = ToolchainUpgrader()
            yield upgrader

    def test_check_for_updates_update_available(self, mock_upgrader):
        """Test checking for updates when update is available."""
        toolchain_id = "llvm-18.1.7-linux-x64"

        # Mock cache registry
        mock_upgrader.cache_registry.get_toolchain_info = Mock(
            return_value={
                "id": toolchain_id,
                "path": "/cache/toolchains/llvm-18.1.7-linux-x64",
            }
        )
        mock_upgrader.cache_registry.lock = MagicMock()

        # Mock metadata registry
        mock_upgrader.metadata_registry.list_versions = Mock(
            return_value=["18.1.7", "18.1.8", "18.1.9"]
        )
        mock_upgrader.metadata_registry.is_compatible = Mock(return_value=True)
        mock_upgrader.metadata_registry.lookup = Mock(
            return_value=Mock(
                url="https://example.com/llvm-18.1.9.tar.xz",
                sha256="abc123",
                size_mb=500,
            )
        )

        result = mock_upgrader.check_for_updates(toolchain_id)

        assert result is not None
        assert isinstance(result, UpdateInfo)
        assert result.current_version == "18.1.7"
        assert result.latest_version == "18.1.9"
        assert result.download_url == "https://example.com/llvm-18.1.9.tar.xz"

    def test_check_for_updates_already_latest(self, mock_upgrader):
        """Test checking for updates when already at latest."""
        toolchain_id = "llvm-18.1.9-linux-x64"

        mock_upgrader.cache_registry.get_toolchain_info = Mock(
            return_value={
                "id": toolchain_id,
                "path": "/cache/toolchains/llvm-18.1.9-linux-x64",
            }
        )
        mock_upgrader.cache_registry.lock = MagicMock()

        mock_upgrader.metadata_registry.list_versions = Mock(
            return_value=["18.1.7", "18.1.8", "18.1.9"]
        )
        mock_upgrader.metadata_registry.is_compatible = Mock(return_value=True)

        result = mock_upgrader.check_for_updates(toolchain_id)

        assert result is None

    def test_check_for_updates_toolchain_not_found(self, mock_upgrader):
        """Test checking for updates with invalid toolchain ID."""
        toolchain_id = "invalid-toolchain"

        mock_upgrader.cache_registry.get_toolchain_info = Mock(return_value=None)
        mock_upgrader.cache_registry.lock = MagicMock()

        with pytest.raises(UpdateCheckError, match="Toolchain not found"):
            mock_upgrader.check_for_updates(toolchain_id)

    def test_check_for_updates_no_compatible_versions(self, mock_upgrader):
        """Test checking for updates when no compatible versions available."""
        toolchain_id = "llvm-18.1.8-linux-x64"

        mock_upgrader.cache_registry.get_toolchain_info = Mock(
            return_value={
                "id": toolchain_id,
                "path": "/cache/toolchains/llvm-18.1.8-linux-x64",
            }
        )
        mock_upgrader.cache_registry.lock = MagicMock()

        mock_upgrader.metadata_registry.list_versions = Mock(return_value=["18.1.8"])
        mock_upgrader.metadata_registry.is_compatible = Mock(return_value=False)

        result = mock_upgrader.check_for_updates(toolchain_id)

        assert result is None

    def test_upgrade_toolchain_success(self, mock_upgrader):
        """Test successful toolchain upgrade."""
        toolchain_id = "llvm-18.1.7-linux-x64"

        # Mock update check
        mock_upgrader.check_for_updates = Mock(
            return_value=UpdateInfo(
                current_version="18.1.7",
                latest_version="18.1.9",
                download_url="https://example.com/llvm-18.1.9.tar.xz",
                sha256="abc123",
                size_mb=500,
            )
        )

        # Mock download
        mock_upgrader.downloader.download_and_install = Mock(
            return_value=Path("/cache/toolchains/llvm-18.1.9-linux-x64")
        )

        # Mock verification
        mock_upgrader.verifier.verify = Mock(return_value=Mock(success=True))

        # Mock registry operations
        mock_upgrader.cache_registry.lock = MagicMock()
        mock_upgrader.cache_registry.get_toolchain_info = Mock(
            side_effect=[
                {
                    "id": toolchain_id,
                    "path": "/cache/toolchains/llvm-18.1.7-linux-x64",
                    "projects": [],
                },  # Old toolchain
                {
                    "id": "llvm-18.1.9-linux-x64",
                    "path": "/cache/toolchains/llvm-18.1.9-linux-x64",
                },  # New toolchain
            ]
        )

        result = mock_upgrader.upgrade_toolchain(toolchain_id)

        assert result.success is True
        assert result.old_version == "18.1.7"
        assert result.new_version == "18.1.9"

    def test_upgrade_toolchain_already_latest(self, mock_upgrader):
        """Test upgrade when already at latest version."""
        toolchain_id = "llvm-18.1.9-linux-x64"

        mock_upgrader.check_for_updates = Mock(return_value=None)

        result = mock_upgrader.upgrade_toolchain(toolchain_id)

        assert result.success is True
        assert result.old_version == "18.1.9"
        assert result.new_version == "18.1.9"

    def test_upgrade_toolchain_verification_failure(self, mock_upgrader):
        """Test upgrade with verification failure."""
        toolchain_id = "llvm-18.1.7-linux-x64"

        mock_upgrader.check_for_updates = Mock(
            return_value=UpdateInfo(
                current_version="18.1.7",
                latest_version="18.1.9",
                download_url="https://example.com/llvm-18.1.9.tar.xz",
                sha256="abc123",
                size_mb=500,
            )
        )

        mock_upgrader.downloader.download_and_install = Mock(
            return_value=Path("/cache/toolchains/llvm-18.1.9-linux-x64")
        )

        # Mock verification failure
        mock_upgrader.verifier.verify = Mock(
            return_value=Mock(
                success=False, error="Compiler not found", issues=["clang not found"]
            )
        )

        result = mock_upgrader.upgrade_toolchain(toolchain_id)

        assert result.success is False
        assert "Verification failed" in result.error

    def test_upgrade_all_toolchains_success(self, mock_upgrader):
        """Test upgrading all toolchains."""
        # Mock installed toolchains
        mock_upgrader.cache_registry.list_toolchains = Mock(
            return_value=["llvm-18.1.7-linux-x64", "gcc-13.1.0-linux-x64"]
        )
        mock_upgrader.cache_registry.lock = MagicMock()

        # Mock successful upgrades
        mock_upgrader.check_for_updates = Mock(
            side_effect=[
                UpdateInfo("18.1.7", "18.1.9", "url1", "sha1", 500),
                UpdateInfo("13.1.0", "13.2.0", "url2", "sha2", 400),
            ]
        )
        mock_upgrader.upgrade_toolchain = Mock(
            side_effect=[
                UpgradeResult("llvm-18.1.7-linux-x64", "18.1.7", "18.1.9", True),
                UpgradeResult("gcc-13.1.0-linux-x64", "13.1.0", "13.2.0", True),
            ]
        )

        results = mock_upgrader.upgrade_all_toolchains()

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_upgrade_all_toolchains_no_toolchains(self, mock_upgrader):
        """Test upgrading all when no toolchains installed."""
        mock_upgrader.cache_registry.list_toolchains = Mock(return_value=[])
        mock_upgrader.cache_registry.lock = MagicMock()

        results = mock_upgrader.upgrade_all_toolchains()

        assert len(results) == 0


# ============================================================================
# CLI Command Tests
# ============================================================================


class TestUpgradeCommand:
    """Test upgrade CLI command."""

    @patch("toolchainkit.cli.commands.upgrade._upgrade_toolchainkit")
    def test_upgrade_self_command(self, mock_upgrade_tk):
        """Test upgrade --self command."""
        mock_upgrade_tk.return_value = 0

        args = Mock(spec=["toolchain", "all"])
        args.toolchain = None
        args.all = False
        setattr(args, "self", True)

        result = upgrade_command.run(args)

        assert result == 0
        mock_upgrade_tk.assert_called_once()

    @patch("toolchainkit.cli.commands.upgrade._upgrade_all_toolchains")
    def test_upgrade_all_command(self, mock_upgrade_all):
        """Test upgrade --all command."""
        mock_upgrade_all.return_value = 0

        args = Mock(spec=["toolchain", "all"])
        args.toolchain = None
        args.all = True

        result = upgrade_command.run(args)

        assert result == 0
        mock_upgrade_all.assert_called_once()

    @patch("toolchainkit.cli.commands.upgrade._upgrade_toolchain")
    def test_upgrade_toolchain_command(self, mock_upgrade_tc):
        """Test upgrade --toolchain command."""
        mock_upgrade_tc.return_value = 0

        args = Mock(spec=["toolchain", "all"])
        args.toolchain = "llvm-18"
        args.all = False

        result = upgrade_command.run(args)

        assert result == 0
        mock_upgrade_tc.assert_called_once_with("llvm-18")

    def test_upgrade_no_flags(self):
        """Test upgrade with no flags (error)."""
        args = Mock(spec=["toolchain", "all"])
        args.toolchain = None
        args.all = False

        result = upgrade_command.run(args)

        assert result == 1

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", return_value="y")
    def test_upgrade_toolchainkit_with_update(
        self, mock_input, mock_upgrade, mock_check
    ):
        """Test _upgrade_toolchainkit with update available."""
        mock_check.return_value = ("0.1.0", "0.2.0")
        mock_upgrade.return_value = True

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 0
        mock_upgrade.assert_called_once()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    def test_upgrade_toolchainkit_no_update(self, mock_check, capsys):
        """Test _upgrade_toolchainkit when already up to date."""
        mock_check.return_value = None

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 0
        captured = capsys.readouterr()
        assert "up to date" in captured.out.lower()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("builtins.input", return_value="n")
    def test_upgrade_toolchainkit_cancelled(self, mock_input, mock_check, capsys):
        """Test _upgrade_toolchainkit cancelled by user."""
        mock_check.return_value = ("0.1.0", "0.2.0")

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 0
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()


class TestUpgradeCommandExtended:
    """Extended tests for upgrade CLI command to improve coverage."""

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", side_effect=EOFError())
    def test_upgrade_toolchainkit_eof_error(self, mock_input, mock_upgrade, mock_check):
        """Test _upgrade_toolchainkit with EOFError on input."""
        mock_check.return_value = ("0.1.0", "0.2.0")

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 130
        mock_upgrade.assert_not_called()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", side_effect=KeyboardInterrupt())
    def test_upgrade_toolchainkit_keyboard_interrupt(
        self, mock_input, mock_upgrade, mock_check
    ):
        """Test _upgrade_toolchainkit with KeyboardInterrupt."""
        mock_check.return_value = ("0.1.0", "0.2.0")

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 130
        mock_upgrade.assert_not_called()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", return_value="yes")
    def test_upgrade_toolchainkit_yes_response(
        self, mock_input, mock_upgrade, mock_check
    ):
        """Test _upgrade_toolchainkit with 'yes' response."""
        mock_check.return_value = ("0.1.0", "0.2.0")
        mock_upgrade.return_value = True

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 0
        mock_upgrade.assert_called_once()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", return_value="Y")
    def test_upgrade_toolchainkit_capital_y_response(
        self, mock_input, mock_upgrade, mock_check
    ):
        """Test _upgrade_toolchainkit with capital 'Y' response."""
        mock_check.return_value = ("0.1.0", "0.2.0")
        mock_upgrade.return_value = True

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 0
        mock_upgrade.assert_called_once()

    @patch("toolchainkit.cli.commands.upgrade.check_toolchainkit_updates")
    @patch("toolchainkit.cli.commands.upgrade.upgrade_toolchainkit")
    @patch("builtins.input", return_value="y")
    def test_upgrade_toolchainkit_upgrade_failure(
        self, mock_input, mock_upgrade, mock_check, capsys
    ):
        """Test _upgrade_toolchainkit when upgrade fails."""
        mock_check.return_value = ("0.1.0", "0.2.0")
        mock_upgrade.return_value = False

        result = upgrade_command._upgrade_toolchainkit()

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed to upgrade" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_toolchain_not_found(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain with non-existent toolchain."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0", "clang-18.1.8"]
        mock_registry_cls.return_value = mock_registry

        result = upgrade_command._upgrade_toolchain("nonexistent")

        assert result == 1
        captured = capsys.readouterr()
        assert "Toolchain not found" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_toolchain_multiple_matches(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain with ambiguous toolchain name."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = [
            "gcc-13.1.0",
            "gcc-13.2.0",
            "gcc-14.0.0",
        ]
        mock_registry_cls.return_value = mock_registry

        result = upgrade_command._upgrade_toolchain("gcc")

        assert result == 1
        captured = capsys.readouterr()
        assert "Multiple toolchains match" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_toolchain_already_latest(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain when toolchain is already latest."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.2.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = None
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.2.0")

        assert result == 0
        captured = capsys.readouterr()
        assert "up to date" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", side_effect=EOFError())
    def test_upgrade_toolchain_user_cancels_eof(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain when user cancels with EOFError."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 130
        captured = capsys.readouterr()
        assert "cancelled" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", side_effect=KeyboardInterrupt())
    def test_upgrade_toolchain_user_cancels_keyboard_interrupt(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain when user cancels with KeyboardInterrupt."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 130

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="n")
    def test_upgrade_toolchain_user_declines(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain when user declines upgrade."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 0
        captured = capsys.readouterr()
        assert "cancelled" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="y")
    def test_upgrade_toolchain_upgrade_success(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test successful _upgrade_toolchain."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader.upgrade_toolchain.return_value = Mock(
            success=True, new_version="13.2.0"
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 0
        captured = capsys.readouterr()
        assert "Upgraded to 13.2.0" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="y")
    def test_upgrade_toolchain_upgrade_failure(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test failed _upgrade_toolchain."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader.upgrade_toolchain.return_value = Mock(
            success=False, error="Download failed"
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 1
        captured = capsys.readouterr()
        assert "Upgrade failed" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_toolchain_update_check_error(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain with UpdateCheckError."""
        from toolchainkit.toolchain.upgrader import UpdateCheckError

        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.side_effect = UpdateCheckError("Network error")
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed to check for updates" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="y")
    def test_upgrade_toolchain_upgrade_error(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain with UpgradeError."""
        from toolchainkit.toolchain.upgrader import UpgradeError

        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader.upgrade_toolchain.side_effect = UpgradeError(
            "Installation failed"
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 1
        captured = capsys.readouterr()
        assert "Upgrade failed" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_toolchain_unexpected_exception(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_toolchain with unexpected exception."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.side_effect = RuntimeError("Unexpected error")
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_toolchain("gcc-13.1.0")

        assert result == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_all_toolchains_no_toolchains(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains with no toolchains installed."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = []
        mock_registry_cls.return_value = mock_registry

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 0
        captured = capsys.readouterr()
        assert "No toolchains installed" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_all_toolchains_all_up_to_date(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains when all are up to date."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.2.0", "clang-18.1.8"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = None
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 0
        captured = capsys.readouterr()
        assert "All toolchains are up to date" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", side_effect=EOFError())
    def test_upgrade_all_toolchains_user_cancels_eof(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains when user cancels with EOFError."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0", "clang-18.1.7"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.side_effect = [
            Mock(latest_version="13.2.0", current_version="13.1.0", size_mb=400),
            Mock(latest_version="18.1.8", current_version="18.1.7", size_mb=500),
        ]
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 130

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="n")
    def test_upgrade_all_toolchains_user_declines(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains when user declines."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.return_value = Mock(
            latest_version="13.2.0", current_version="13.1.0", size_mb=400
        )
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 0
        captured = capsys.readouterr()
        assert "cancelled" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="y")
    def test_upgrade_all_toolchains_success(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test successful _upgrade_all_toolchains."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0", "clang-18.1.7"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.side_effect = [
            Mock(latest_version="13.2.0", current_version="13.1.0", size_mb=400),
            Mock(latest_version="18.1.8", current_version="18.1.7", size_mb=500),
        ]
        mock_upgrader.upgrade_toolchain.side_effect = [
            Mock(success=True, new_version="13.2.0"),
            Mock(success=True, new_version="18.1.8"),
        ]
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 0
        captured = capsys.readouterr()
        assert "2 upgraded, 0 failed" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    @patch("builtins.input", return_value="y")
    def test_upgrade_all_toolchains_partial_failure(
        self, mock_input, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains with partial failures."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.return_value = ["gcc-13.1.0", "clang-18.1.7"]
        mock_registry_cls.return_value = mock_registry

        mock_upgrader = Mock()
        mock_upgrader.check_for_updates.side_effect = [
            Mock(latest_version="13.2.0", current_version="13.1.0", size_mb=400),
            Mock(latest_version="18.1.8", current_version="18.1.7", size_mb=500),
        ]
        mock_upgrader.upgrade_toolchain.side_effect = [
            Mock(success=True, new_version="13.2.0"),
            Mock(success=False, error="Download failed"),
        ]
        mock_upgrader_cls.return_value = mock_upgrader

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 1
        captured = capsys.readouterr()
        assert "1 upgraded, 1 failed" in captured.out

    @patch("toolchainkit.cli.commands.upgrade.ToolchainUpgrader")
    @patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
    @patch("toolchainkit.cli.commands.upgrade.get_global_cache_dir")
    def test_upgrade_all_toolchains_unexpected_exception(
        self, mock_cache_dir, mock_registry_cls, mock_upgrader_cls, capsys
    ):
        """Test _upgrade_all_toolchains with unexpected exception."""
        mock_cache_dir.return_value = Path("/cache")
        mock_registry = Mock()
        mock_registry._lock = MagicMock()
        mock_registry.list_toolchains.side_effect = RuntimeError("Unexpected error")
        mock_registry_cls.return_value = mock_registry

        result = upgrade_command._upgrade_all_toolchains()

        assert result == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
