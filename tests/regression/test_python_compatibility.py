"""
Regression tests for Python version compatibility.

Ensures ToolchainKit works across Python 3.8-3.12.
"""

import pytest
import sys


@pytest.mark.regression
class TestPythonVersionCompatibility:
    """Test ToolchainKit works across Python versions."""

    def test_minimum_python_version(self):
        """Verify we're running on supported Python version."""
        assert sys.version_info >= (3, 8), "ToolchainKit requires Python 3.8 or higher"

    def test_import_core_modules(self):
        """Verify core modules import successfully."""
        # These should work on all Python versions
        from toolchainkit.core import directory
        from toolchainkit.cli import parser
        from toolchainkit.cli.commands import doctor

        assert directory
        assert parser
        assert doctor

    def test_pathlib_operations(self, tmp_path):
        """Verify pathlib operations work across versions."""
        # Path operations changed slightly between versions
        test_file = tmp_path / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "content"

        # Test Path.unlink (missing_ok added in 3.8)
        test_file.unlink(missing_ok=True)
        test_file.unlink(missing_ok=True)  # Should not raise

    def test_subprocess_operations(self, tmp_path):
        """Verify subprocess operations work across versions."""
        import subprocess

        # capture_output added in 3.7, but check it works
        result = subprocess.run(
            [sys.executable, "-c", 'print("test")'],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0
        assert "test" in result.stdout


@pytest.mark.regression
class TestStandardLibraryCompatibility:
    """Test standard library usage across Python versions."""

    def test_json_operations(self, tmp_path):
        """Verify JSON operations work consistently."""
        import json

        data = {"version": "1.0.0", "items": [1, 2, 3], "nested": {"key": "value"}}

        file_path = tmp_path / "test.json"

        # Write
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Read
        loaded = json.loads(file_path.read_text(encoding="utf-8"))

        assert loaded == data

    def test_hashlib_operations(self):
        """Verify hashing operations work consistently."""
        import hashlib

        data = b"test data"

        # SHA-256
        sha256 = hashlib.sha256(data).hexdigest()
        assert len(sha256) == 64

    def test_datetime_operations(self):
        """Verify datetime operations work consistently."""
        from datetime import datetime, timezone

        # Create UTC timestamp
        now = datetime.now(timezone.utc)

        # ISO format
        iso_str = now.isoformat()
        assert "T" in iso_str


@pytest.mark.regression
class TestDataclassCompatibility:
    """Test dataclass usage across Python versions."""

    def test_basic_dataclass(self):
        """Verify dataclass decorator works."""
        from dataclasses import dataclass, field

        @dataclass
        class TestConfig:
            name: str
            version: str = "1.0.0"
            items: list = field(default_factory=list)

        config = TestConfig(name="test")
        assert config.name == "test"
        assert config.version == "1.0.0"
        assert config.items == []


@pytest.mark.regression
def test_imports_dont_fail_on_any_supported_version():
    """
    Critical test: Verify all public imports work.

    This test should pass on Python 3.8, 3.9, 3.10, 3.11, 3.12, and 3.13.
    """
    # Try importing all public modules
    modules = [
        "toolchainkit",
        "toolchainkit.core",
        "toolchainkit.core.directory",
        "toolchainkit.cli",
        "toolchainkit.cli.parser",
        "toolchainkit.cli.commands.doctor",
    ]

    for module_name in modules:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
