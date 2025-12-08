"""
Integration tests for toolchainkit.core.python_env module.

These tests actually download and set up Python distributions to verify
the complete workflow works correctly. They are marked as slow and can
be skipped during normal development.

Run with: pytest tests/test_python_env_integration.py -v -m "not slow"
Or include slow tests: pytest tests/test_python_env_integration.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

from toolchainkit.core.python_env import (
    setup_python_environment,
    verify_python,
    get_python_version,
    get_python_environment,
    detect_platform,
)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.timeout(600)  # 10 minute timeout for slow download tests
class TestPythonEnvironmentIntegration:
    """Integration tests that actually download and set up Python."""

    @pytest.mark.timeout(300)  # 5 minute timeout for this test
    def test_setup_python_full_workflow(self):
        """Test the complete workflow of setting up Python environment."""
        # Use a temporary directory as global cache for this test
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache = Path(tmpdir).resolve() / ".toolchainkit"
            test_cache.mkdir()

            # Mock get_python_dir to use our test cache
            from unittest.mock import patch

            with patch(
                "toolchainkit.core.python_env.get_global_cache_dir",
                return_value=test_cache,
            ):
                # This will actually download Python (with 5 min timeout)
                python_exe = setup_python_environment(timeout=300)

                # Verify the executable was created
                assert python_exe.exists()
                assert os.access(python_exe, os.X_OK) or os.name == "nt"

                # Verify it's in the expected location
                python_dir = test_cache / "python"
                assert python_dir.exists()
                assert python_exe.is_relative_to(python_dir)

                # Verify Python works
                assert verify_python(python_exe) is True

                # Get and check version
                version = get_python_version(python_exe)
                assert version[0] == 3
                assert version[1] >= 8

                print(
                    f"✓ Python {version[0]}.{version[1]}.{version[2]} downloaded and verified"
                )

    @pytest.mark.timeout(360)  # 6 minute timeout (download + verification)
    def test_setup_python_idempotency(self):
        """Test that re-running setup doesn't re-download Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache = Path(tmpdir).resolve() / ".toolchainkit"
            test_cache.mkdir()

            from unittest.mock import patch

            with patch(
                "toolchainkit.core.python_env.get_global_cache_dir",
                return_value=test_cache,
            ):
                # First setup - downloads Python (with timeout)
                print("First setup: downloading Python...")
                python_exe1 = setup_python_environment(timeout=300)
                assert python_exe1.exists()

                # Get modification time
                python_dir = test_cache / "python"
                mtime1 = python_dir.stat().st_mtime

                # Second setup - should reuse existing (fast)
                print("Second setup: should reuse existing...")
                python_exe2 = setup_python_environment(timeout=60)
                assert python_exe2.exists()
                assert python_exe1 == python_exe2

                # Directory should not have been recreated
                mtime2 = python_dir.stat().st_mtime
                assert mtime1 == mtime2

                print("✓ Python environment reused successfully")

    @pytest.mark.timeout(330)  # 5.5 minute timeout (download + subprocess)
    def test_python_environment_isolation(self):
        """Test that Python environment is isolated from system Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache = Path(tmpdir).resolve() / ".toolchainkit"
            test_cache.mkdir()

            from unittest.mock import patch
            import subprocess

            with patch(
                "toolchainkit.core.python_env.get_global_cache_dir",
                return_value=test_cache,
            ):
                print("Setting up Python for isolation test...")
                python_exe = setup_python_environment(timeout=300)
                env = get_python_environment(python_exe)

                # Verify isolation environment variables
                assert env.get("PYTHONNOUSERSITE") == "1"
                assert env.get("PYTHONDONTWRITEBYTECODE") == "1"
                assert "PYTHONHOME" in env
                assert "PYTHONPATH" in env

                # Run a simple command to verify isolation
                print("Testing Python isolation...")
                result = subprocess.run(
                    [str(python_exe), "-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=str(tmpdir),  # Ensure valid CWD
                    timeout=30,  # 30 second timeout to prevent hanging
                )

                assert result.returncode == 0, f"Python command failed: {result.stderr}"
                output_exe = Path(result.stdout.strip())
                assert output_exe.is_relative_to(test_cache / "python")

                print("✓ Python environment is properly isolated")

    def test_python_stdlib_modules(self):
        """Test that required stdlib modules are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache = Path(tmpdir).resolve() / ".toolchainkit"
            test_cache.mkdir()

            from unittest.mock import patch
            import subprocess

            with patch(
                "toolchainkit.core.python_env.get_global_cache_dir",
                return_value=test_cache,
            ):
                python_exe = setup_python_environment()
                env = get_python_environment(python_exe)

                # Test importing critical modules
                modules_to_test = [
                    "pathlib",
                    "hashlib",
                    "json",
                    "zipfile",
                    "tarfile",
                    "subprocess",
                    "os",
                    "sys",
                    "urllib.request",
                ]

                for module in modules_to_test:
                    result = subprocess.run(
                        [str(python_exe), "-c", f'import {module}; print("OK")'],
                        capture_output=True,
                        text=True,
                        env=env,
                        cwd=str(tmpdir),  # Ensure valid CWD
                        timeout=10,
                    )

                    assert (
                        result.returncode == 0
                    ), f"Failed to import {module}: {result.stderr}"
                    assert (
                        "OK" in result.stdout
                    ), f"Module {module} import didn't produce expected output"

                print(f"✓ All {len(modules_to_test)} required stdlib modules available")

    def test_force_reinstall(self):
        """Test that force_reinstall actually reinstalls Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache = Path(tmpdir).resolve() / ".toolchainkit"
            test_cache.mkdir()

            from unittest.mock import patch

            with patch(
                "toolchainkit.core.python_env.get_global_cache_dir",
                return_value=test_cache,
            ):
                # Initial setup
                python_exe1 = setup_python_environment()
                assert python_exe1.exists()

                python_dir = test_cache / "python"

                # Add a marker file
                marker = python_dir / "marker.txt"
                marker.write_text("original")

                # Force reinstall
                python_exe2 = setup_python_environment(force_reinstall=True)
                assert python_exe2.exists()

                # Marker file should be gone (directory was recreated)
                assert not marker.exists()

                # Python should still work
                assert verify_python(python_exe2) is True

                print("✓ Force reinstall works correctly")


@pytest.mark.integration
class TestPythonEnvironmentQuick:
    """Quick integration tests that don't download Python."""

    def test_detect_current_platform(self):
        """Test that current platform can be detected."""
        platform_key = detect_platform()

        assert isinstance(platform_key, str)
        assert "-" in platform_key

        parts = platform_key.split("-")
        assert len(parts) == 2

        os_name, arch = parts
        assert os_name in ["windows", "linux", "macos"]
        assert arch in ["x64", "arm64"]

        print(f"✓ Detected platform: {platform_key}")

    def test_python_executable_works(self):
        """Test that current Python executable can be verified."""
        current_python = Path(sys.executable)
        result = verify_python(current_python)

        assert result is True

        version = get_python_version(current_python)
        assert version[0] >= 3
        assert version[1] >= 8

        print(f"✓ Current Python {version[0]}.{version[1]}.{version[2]} verified")

    def test_environment_generation(self):
        """Test that environment variables can be generated."""
        current_python = Path(sys.executable)
        env = get_python_environment(current_python)

        assert isinstance(env, dict)
        assert "PYTHONNOUSERSITE" in env
        assert "PYTHONDONTWRITEBYTECODE" in env
        assert "PYTHONHOME" in env
        assert "PYTHONPATH" in env

        print("✓ Environment variables generated correctly")


if __name__ == "__main__":
    # Run quick tests by default
    pytest.main([__file__, "-v", "-m", "not slow"])
