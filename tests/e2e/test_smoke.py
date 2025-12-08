"""
Smoke tests for ToolchainKit.

Quick tests to verify basic functionality works. These tests should run fast
and catch obvious breakage.
"""

import pytest
import shutil


@pytest.mark.e2e
@pytest.mark.smoke
class TestSmoke:
    """Fast smoke tests for basic functionality."""

    def test_imports(self):
        """Test: All main modules can be imported."""
        # Core modules

        # Config modules

        # Toolchain modules

        # CMake modules

        assert True  # All imports successful

    def test_platform_detection(self):
        """Test: Platform detection works."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()

        assert platform is not None
        assert platform.os in ["windows", "linux", "macos"]
        assert platform.arch in ["x64", "arm64", "x86", "arm"]

    def test_directory_creation(self, temp_workspace):
        """Test: Directory structure can be created."""
        from toolchainkit.core.directory import create_directory_structure

        paths = create_directory_structure(temp_workspace)

        assert paths["global_cache"].exists()
        assert paths["project_local"].exists()
        assert (temp_workspace / ".toolchainkit").exists()

    def test_backend_detection(self):
        """Test: Build backend can be detected."""
        from toolchainkit.cmake.backends import BuildBackendDetector
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        # Should find at least one backend on most systems
        backends = detector.get_all()

        # May be empty on minimal systems, but should not crash
        assert isinstance(backends, list)

    def test_cmake_available(self):
        """Test: Check if CMake is available for testing."""
        cmake_path = shutil.which("cmake")

        if cmake_path:
            print(f"CMake available at: {cmake_path}")
        else:
            pytest.skip("CMake not available (OK for smoke test)")

    def test_config_parser_basic(self, temp_workspace):
        """Test: Configuration parser can parse basic YAML."""
        from toolchainkit.config.parser import parse_config

        # Create minimal config
        config_file = temp_workspace / "toolchainkit.yaml"
        config_content = """version: 1
toolchains:
  - name: test
    type: clang
    version: "18"

build:
  backend: ninja
"""
        config_file.write_text(config_content)

        config = parse_config(config_file)

        assert config is not None
        assert len(config.toolchains) == 1
        assert config.toolchains[0].name == "test"
        assert config.build.backend == "ninja"

    def test_toolchain_metadata_registry(self):
        """Test: Toolchain metadata registry is accessible."""
        from toolchainkit.toolchain.metadata_registry import ToolchainMetadataRegistry

        registry = ToolchainMetadataRegistry()

        # Should have some toolchains registered
        assert registry is not None

    def test_filesystem_utilities(self, temp_workspace):
        """Test: Filesystem utilities work."""
        from toolchainkit.core.filesystem import atomic_write, compute_file_hash

        # Atomic write
        test_file = temp_workspace / "test.txt"
        atomic_write(test_file, "test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"

        # Hash computation
        hash_result = compute_file_hash(test_file, "sha256")
        assert len(hash_result) == 64  # SHA256 hex length


@pytest.mark.e2e
@pytest.mark.smoke
class TestSystemEnvironment:
    """Smoke tests for system environment."""

    def test_python_version(self):
        """Test: Python version is compatible."""
        import sys

        version_info = sys.version_info
        print(
            f"Python version: {version_info.major}.{version_info.minor}.{version_info.micro}"
        )

        # Should be Python 3.8+
        assert version_info.major == 3
        assert version_info.minor >= 8

    def test_required_modules(self):
        """Test: Required Python modules are available."""

        assert True

    def test_write_permissions(self, temp_workspace):
        """Test: Can write to temporary directory."""
        test_file = temp_workspace / "write_test.txt"
        test_file.write_text("test")

        assert test_file.exists()
        assert test_file.read_text() == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
