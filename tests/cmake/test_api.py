"""
Tests for CMake File API helper.
"""

import json

import pytest

from toolchainkit.cmake.api import CMakeFileAPI


@pytest.fixture
def build_dir(tmp_path):
    path = tmp_path / "build"
    path.mkdir()
    return path


@pytest.fixture
def api(build_dir):
    return CMakeFileAPI(build_dir)


def test_prepare_query(api, build_dir):
    """Test query file creation."""
    api.prepare_query()

    query_file = build_dir / ".cmake" / "api" / "v1" / "query" / "codemodel-v2"
    assert query_file.exists()


def test_read_reply_no_dir(api):
    """Test reading reply when directory doesn't exist."""
    assert api.read_reply() is None


def test_read_reply_no_files(api, build_dir):
    """Test reading reply when no reply files exist."""
    (build_dir / ".cmake" / "api" / "v1" / "reply").mkdir(parents=True)
    assert api.read_reply() is None


def test_read_reply_success(api, build_dir):
    """Test reading latest reply."""
    reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
    reply_dir.mkdir(parents=True)

    # Old file
    (reply_dir / "codemodel-v2-old.json").write_text('{"version": 1}', encoding="utf-8")

    # New file (ensure mtime is newer)
    import time

    time.sleep(0.01)
    target_file = reply_dir / "codemodel-v2-new.json"
    target_file.write_text('{"version": 2}', encoding="utf-8")

    data = api.read_reply()
    assert data is not None
    assert data["version"] == 2


def test_get_executables_partial_data(api, build_dir):
    """Test getting executables with partial/missing data."""
    # Setup mock reply
    reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
    reply_dir.mkdir(parents=True)

    reply_data = {
        "configurations": [
            {
                "name": "Debug",
                "targets": [
                    {"jsonFile": "target-missing.json"},
                    {"jsonFile": "target-app.json"},
                ],
            }
        ]
    }

    (reply_dir / "codemodel-v2-mock.json").write_text(
        json.dumps(reply_data), encoding="utf-8"
    )

    # Create one target file but not the other
    target_data = {
        "name": "app",
        "type": "EXECUTABLE",
        "artifacts": [{"path": "app.exe"}],
    }
    (reply_dir / "target-app.json").write_text(
        json.dumps(target_data), encoding="utf-8"
    )

    executables = api.get_executables()
    assert len(executables) == 1
    assert executables[0]["name"] == "app"
    assert executables[0]["path"].endswith("app.exe")


def test_get_executables_no_artifacts(api, build_dir):
    """Test target with no artifacts."""
    reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
    reply_dir.mkdir(parents=True)

    reply_data = {
        "configurations": [
            {"name": "Debug", "targets": [{"jsonFile": "target-lib.json"}]}
        ]
    }
    (reply_dir / "codemodel-v2-mock.json").write_text(
        json.dumps(reply_data), encoding="utf-8"
    )

    target_data = {"name": "lib", "type": "STATIC_LIBRARY", "artifacts": []}
    (reply_dir / "target-lib.json").write_text(
        json.dumps(target_data), encoding="utf-8"
    )

    executables = api.get_executables()
    assert len(executables) == 0


def test_json_decode_error(api, build_dir):
    """Test handling of corrupt JSON."""
    reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
    reply_dir.mkdir(parents=True)
    (reply_dir / "codemodel-v2-bad.json").write_text("{invalid json", encoding="utf-8")

    assert api.read_reply() is None
