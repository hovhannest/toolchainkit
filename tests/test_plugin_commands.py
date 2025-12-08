#!/usr/bin/env python3
"""
Quick test script for plugin management commands.
Run this to verify the plugin CLI commands work correctly.
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    print(f"\n{'='*60}")
    print(f"Running: {cmd}")
    print("=" * 60)

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print("STDOUT:")
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    print(f"Return code: {result.returncode}")

    return result.returncode, result.stdout, result.stderr


def main():
    """Test plugin management commands."""
    print("Testing ToolchainKit Plugin Management Commands")
    print("=" * 60)

    # Test 1: List plugins
    print("\n\nTest 1: List all plugins")
    returncode, stdout, stderr = run_command("toolchainkit plugin list")
    if returncode != 0:
        print("❌ FAILED: plugin list command failed")
        return False
    print("✅ PASSED: plugin list command succeeded")

    # Test 2: List search paths
    print("\n\nTest 2: List plugin search paths")
    returncode, stdout, stderr = run_command("toolchainkit plugin list-paths")
    if returncode != 0:
        print("❌ FAILED: plugin list-paths command failed")
        return False
    print("✅ PASSED: plugin list-paths command succeeded")

    # Test 3: Add a test path
    test_path = Path.cwd() / "test-plugins"
    print(f"\n\nTest 3: Add plugin search path: {test_path}")

    # Create the directory if it doesn't exist
    test_path.mkdir(exist_ok=True)

    # Use --force since this is just a test directory with no actual plugins
    returncode, stdout, stderr = run_command(
        f'toolchainkit plugin add "{test_path}" --force'
    )
    if returncode != 0:
        print("❌ FAILED: plugin add command failed")
        # Clean up
        if test_path.exists():
            test_path.rmdir()
        return False
    print("✅ PASSED: plugin add command succeeded")

    # Test 4: Verify path was added
    print("\n\nTest 4: Verify path appears in list-paths")
    returncode, stdout, stderr = run_command("toolchainkit plugin list-paths")
    if returncode != 0 or str(test_path) not in stdout:
        print("❌ FAILED: Added path not found in list-paths output")
        return False
    print("✅ PASSED: Added path appears in list-paths")

    # Test 5: Try adding same path again (should warn)
    print("\n\nTest 5: Try adding duplicate path")
    returncode, stdout, stderr = run_command(
        f'toolchainkit plugin add "{test_path}" --force'
    )
    if "already registered" not in stdout.lower():
        print("❌ FAILED: Expected duplicate path warning")
        return False
    print("✅ PASSED: Duplicate path detection works")

    # Test 6: Remove the test path
    print(f"\n\nTest 6: Remove plugin search path: {test_path}")
    returncode, stdout, stderr = run_command(
        f'toolchainkit plugin remove "{test_path}"'
    )
    if returncode != 0:
        print("❌ FAILED: plugin remove command failed")
        return False
    print("✅ PASSED: plugin remove command succeeded")

    # Test 7: Verify path was removed
    print("\n\nTest 7: Verify path no longer in list-paths")
    returncode, stdout, stderr = run_command("toolchainkit plugin list-paths")
    if returncode != 0:
        print("❌ FAILED: plugin list-paths command failed")
        # Clean up
        if test_path.exists():
            test_path.rmdir()
        return False
    if str(test_path) in stdout:
        print("❌ FAILED: Removed path still appears in list-paths output")
        # Clean up
        if test_path.exists():
            test_path.rmdir()
        return False
    print("✅ PASSED: Removed path no longer appears in list-paths")

    # Clean up the test directory
    if test_path.exists():
        test_path.rmdir()

    # Test 8: Try removing non-existent path
    print("\n\nTest 8: Try removing non-existent path")
    fake_path = Path.cwd() / "nonexistent-plugins"
    returncode, stdout, stderr = run_command(
        f'toolchainkit plugin remove "{fake_path}"'
    )
    # After removing the only configured path, config is empty, so we get "No plugin search paths"
    # This is acceptable behavior - silently handle removal of non-existent paths
    if returncode != 0:
        print("❌ FAILED: Command should succeed even for non-existent paths")
        return False
    print("✅ PASSED: Non-existent path removal handled correctly")

    # Final summary
    print("\n" + "=" * 60)
    print("🎉 All tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test execution failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
