"""
Tests for VS Code configuration generation.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from toolchainkit.ide.vscode import VSCodeIntegrator


@pytest.fixture
def project_root(tmp_path):
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def integrator(project_root):
    return VSCodeIntegrator(project_root)


def test_generate_settings(integrator, project_root):
    toolchain_file = project_root / ".toolchainkit" / "cmake" / "toolchain.cmake"
    compiler_path = Path("/usr/bin/clang")

    settings_file = integrator.generate_settings(
        toolchain_file=toolchain_file,
        compiler_path=compiler_path,
        build_dir="build",
        generator="Ninja",
    )

    assert settings_file.exists()

    with open(settings_file) as f:
        settings = json.load(f)

    assert "cmake.configureSettings" in settings
    assert (
        settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
        == "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
    )
    assert settings["C_Cpp.default.compilerPath"] == str(compiler_path)
    assert settings["cmake.generator"] == "Ninja"


def test_generate_tasks(integrator):
    tasks_file = integrator.generate_tasks_config()

    assert tasks_file.exists()

    with open(tasks_file) as f:
        data = json.load(f)

    assert data["version"] == "2.0.0"
    assert len(data["tasks"]) >= 2
    assert any(t["label"] == "Build All" for t in data["tasks"])


def test_generate_launch_config(integrator):
    targets = [
        {
            "name": "app",
            "path": str(integrator.project_root / "build" / "app"),
            "config": "Debug",
        },
        {
            "name": "test",
            "path": str(integrator.project_root / "build" / "test"),
            "config": "Debug",
        },
    ]

    launch_file = integrator.generate_launch_config(targets)

    assert launch_file.exists()

    with open(launch_file) as f:
        data = json.load(f)

    assert len(data["configurations"]) == 2
    app_config = next(c for c in data["configurations"] if c["name"] == "Debug app")
    assert app_config["program"] == "${workspaceFolder}/build/app"
    assert app_config["type"] == "cppdbg"


@patch("toolchainkit.ide.vscode.CMakeFileAPI")
@patch("subprocess.run")
def test_configure_workspace(mock_run, MockAPI, integrator, project_root):
    # Mock API
    mock_api = MockAPI.return_value
    mock_api.get_executables.return_value = [
        {
            "name": "myapp",
            "path": str(project_root / "build" / "myapp"),
            "config": "Debug",
        }
    ]

    integrator.configure_workspace(
        toolchain_file=Path("toolchain.cmake"),
        compiler_path=Path("clang"),
        build_dir="build",
    )

    # Check all files generated
    vscode_dir = project_root / ".vscode"
    assert (vscode_dir / "settings.json").exists()
    assert (vscode_dir / "launch.json").exists()
    assert (vscode_dir / "tasks.json").exists()
    assert (vscode_dir / "extensions.json").exists()

    # Check launch.json content
    with open(vscode_dir / "launch.json") as f:
        data = json.load(f)

    assert data["configurations"][0]["name"] == "Debug myapp"
