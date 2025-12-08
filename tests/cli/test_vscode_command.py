"""
Tests for 'vscode' CLI command.
"""

from unittest.mock import MagicMock, patch

import pytest

from toolchainkit.cli.commands import vscode


@pytest.fixture
def mock_args():
    args = MagicMock()
    args.project_root = "."
    args.config = None
    args.force = False
    args.build_dir = None
    args.build_type = None
    return args


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
@patch("toolchainkit.cli.commands.vscode.StateManager")
@patch("toolchainkit.cli.commands.vscode.VSCodeIntegrator")
def test_vscode_run_success(
    MockIntegrator,
    MockStateManager,
    mock_load_config,
    mock_check_init,
    mock_args,
    tmp_path,
):
    """Test successful run of vscode command."""
    mock_args.project_root = str(tmp_path)

    # Mocks
    mock_check_init.return_value = True
    mock_load_config.return_value = {}

    mock_state = MagicMock()
    mock_state.active_toolchain = "llvm-18"
    mock_state.build_directory = "build"
    MockStateManager.return_value.load.return_value = mock_state

    mock_integrator = MockIntegrator.return_value
    mock_integrator.vscode_dir = tmp_path / ".vscode"

    # Run
    ret = vscode.run(mock_args)
    assert ret == 0

    mock_integrator.configure_workspace.assert_called_once()


@patch("toolchainkit.cli.commands.vscode.check_initialized")
def test_vscode_not_initialized(mock_check_init, mock_args):
    """Test failure when not initialized."""
    mock_check_init.return_value = False
    ret = vscode.run(mock_args)
    assert ret == 1


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
def test_vscode_config_error(mock_load_config, mock_check_init, mock_args):
    """Test failure when config load fails."""
    mock_check_init.return_value = True
    mock_load_config.side_effect = Exception("Config error")
    ret = vscode.run(mock_args)
    assert ret == 1


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
@patch("toolchainkit.cli.commands.vscode.StateManager")
@patch("toolchainkit.cli.commands.vscode.VSCodeIntegrator")
def test_vscode_existing_config_no_force(
    MockIntegrator,
    MockStateManager,
    mock_load_config,
    mock_check_init,
    mock_args,
    tmp_path,
):
    """Test that existing config aborts without force flag."""
    mock_args.project_root = str(tmp_path)
    mock_check_init.return_value = True

    # Simulate existing settings.json
    mock_integrator = MockIntegrator.return_value
    mock_integrator.vscode_dir = tmp_path / ".vscode"
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "settings.json").touch()

    ret = vscode.run(mock_args)
    assert ret == 0
    mock_integrator.configure_workspace.assert_not_called()


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
@patch("toolchainkit.cli.commands.vscode.StateManager")
@patch("toolchainkit.cli.commands.vscode.VSCodeIntegrator")
def test_vscode_existing_config_with_force(
    MockIntegrator,
    MockStateManager,
    mock_load_config,
    mock_check_init,
    mock_args,
    tmp_path,
):
    """Test that force flag overwrites existing config."""
    mock_args.project_root = str(tmp_path)
    mock_args.force = True
    mock_check_init.return_value = True

    mock_integrator = MockIntegrator.return_value
    mock_integrator.vscode_dir = tmp_path / ".vscode"
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "settings.json").touch()

    ret = vscode.run(mock_args)
    assert ret == 0
    mock_integrator.configure_workspace.assert_called_once()


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
@patch("toolchainkit.cli.commands.vscode.StateManager")
@patch("toolchainkit.cli.commands.vscode.VSCodeIntegrator")
def test_vscode_exception_during_config(
    MockIntegrator,
    MockStateManager,
    mock_load_config,
    mock_check_init,
    mock_args,
    tmp_path,
):
    """Test handling of exception during workspace configuration."""
    mock_args.project_root = str(tmp_path)
    mock_check_init.return_value = True

    mock_integrator = MockIntegrator.return_value
    mock_integrator.vscode_dir = tmp_path / ".vscode"
    mock_integrator.configure_workspace.side_effect = Exception("Write failed")

    ret = vscode.run(mock_args)
    assert ret == 1


@patch("toolchainkit.cli.commands.vscode.check_initialized")
@patch("toolchainkit.cli.commands.vscode.load_yaml_config")
@patch("toolchainkit.cli.commands.vscode.StateManager")
@patch("toolchainkit.cli.commands.vscode.VSCodeIntegrator")
@patch("toolchainkit.core.cache_registry.ToolchainCacheRegistry")
@patch("toolchainkit.core.directory.get_global_cache_dir")
def test_vscode_detects_clang_tools(
    mock_get_cache_dir,
    MockRegistry,
    MockIntegrator,
    MockStateManager,
    mock_load_config,
    mock_check_init,
    mock_args,
    tmp_path,
):
    """Test that Clang tools are detected and passed to integrator."""
    mock_args.project_root = str(tmp_path)
    mock_check_init.return_value = True

    # Mock State
    mock_state = MagicMock()
    mock_state.active_toolchain = "llvm-18"
    MockStateManager.return_value.load.return_value = mock_state

    # Mock Registry identifying toolchain path
    toolchain_dir = tmp_path / "toolchain"
    toolchain_dir.mkdir()
    (toolchain_dir / "bin").mkdir()
    (toolchain_dir / "bin" / "clang").touch()  # Not used for logic but good to have
    # Add .exe for Windows compatibility
    (toolchain_dir / "bin" / "clang-tidy.exe").touch()
    (toolchain_dir / "bin" / "clang-format.exe").touch()
    (
        toolchain_dir / "bin" / "clang-tidy"
    ).touch()  # For non-windows fallback consistency
    (toolchain_dir / "bin" / "clang-format").touch()

    mock_registry = MockRegistry.return_value
    mock_registry.get_toolchain_info.return_value = {"path": str(toolchain_dir)}

    # Mock Config Files in Project Root
    (tmp_path / ".clang-tidy").touch()
    (tmp_path / ".clang-format").touch()

    # Mock Integrator
    mock_integrator = MockIntegrator.return_value
    mock_integrator.vscode_dir = tmp_path / ".vscode"

    # Run
    ret = vscode.run(mock_args)
    assert ret == 0

    # Verify calls
    mock_integrator.configure_workspace.assert_called_once()
    call_args = mock_integrator.configure_workspace.call_args[1]

    import sys

    is_win = sys.platform == "win32"
    tidy_name = "clang-tidy.exe" if is_win else "clang-tidy"
    format_name = "clang-format.exe" if is_win else "clang-format"

    assert "clang_tidy_path" in call_args
    assert "clang_format_path" in call_args
    assert str(call_args["clang_tidy_path"]) == str(toolchain_dir / "bin" / tidy_name)
    assert str(call_args["clang_format_path"]) == str(
        toolchain_dir / "bin" / format_name
    )
