"""
Unit tests for Build Backend plugin system.
"""

import pytest
from unittest.mock import Mock, patch
from toolchainkit.backends.base import BuildBackend
from toolchainkit.backends.cmake import CMakeBackend
from toolchainkit.plugins.registry import get_global_registry


class TestBuildBackendRegistry:
    """Test build backend registration in plugin registry."""

    def test_cmake_backend_registered(self):
        """Test that CMake backend is automatically registered."""
        registry = get_global_registry()

        # Check if cmake is registered
        assert registry.has_backend("cmake")
        backend = registry.get_backend("cmake")
        assert isinstance(backend, CMakeBackend)
        assert isinstance(backend, BuildBackend)

    def test_get_unknown_backend(self):
        """Test getting an unknown backend."""
        registry = get_global_registry()
        with pytest.raises(KeyError, match="Build backend 'unknown' not found"):
            registry.get_backend("unknown")

    def test_list_backends(self):
        """Test listing registered backends."""
        registry = get_global_registry()
        backends = registry.list_backends()
        assert "cmake" in backends


class TestCMakeBackend:
    """Test CMake backend implementation."""

    @patch("toolchainkit.backends.cmake.subprocess.run")
    @patch("toolchainkit.backends.cmake.CMakeToolchainGenerator")
    def test_configure_basic(self, mock_generator_cls, mock_run, tmp_path):
        """Test basic CMake configuration."""
        # Setup mocks
        mock_generator = Mock()
        mock_generator_cls.return_value = mock_generator
        mock_generator.generate.return_value = tmp_path / "toolchain.cmake"
        mock_run.return_value = Mock(returncode=0)

        # Create backend
        backend = CMakeBackend()

        # Configure
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        toolchain_data = {
            "id": "llvm-18.1.8",
            "path": str(tmp_path / "toolchain"),
            "name": "llvm-18.1.8-linux-x64",
        }

        config = {
            "build_type": "Release",
            "stdlib": "libc++",
        }

        backend.configure(project_root, build_dir, toolchain_data, config)

        # Verify generator was called
        assert mock_generator_cls.called
        assert mock_generator.generate.called

        # Verify CMake was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "cmake"
        assert "-B" in call_args
        assert str(build_dir) in call_args
        assert "-S" in call_args
        assert str(project_root) in call_args
        assert "-DCMAKE_BUILD_TYPE=Release" in call_args

    @patch("toolchainkit.backends.cmake.subprocess.run")
    @patch("toolchainkit.backends.cmake.CMakeToolchainGenerator")
    def test_configure_with_cmake_args(self, mock_generator_cls, mock_run, tmp_path):
        """Test CMake configuration with additional arguments."""
        mock_generator = Mock()
        mock_generator_cls.return_value = mock_generator
        mock_generator.generate.return_value = tmp_path / "toolchain.cmake"
        mock_run.return_value = Mock(returncode=0)

        backend = CMakeBackend()
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        toolchain_data = {
            "id": "gcc-13",
            "path": str(tmp_path / "toolchain"),
            "name": "gcc-13.2.0",
        }

        config = {
            "build_type": "Debug",
            "cmake_args": ["-DENABLE_TESTING=ON", "-DCMAKE_VERBOSE_MAKEFILE=ON"],
        }

        backend.configure(project_root, build_dir, toolchain_data, config)

        # Verify additional args were passed
        call_args = mock_run.call_args[0][0]
        assert "-DENABLE_TESTING=ON" in call_args
        assert "-DCMAKE_VERBOSE_MAKEFILE=ON" in call_args

    @patch("toolchainkit.backends.cmake.subprocess.run")
    @patch("toolchainkit.backends.cmake.CMakeToolchainGenerator")
    def test_configure_cmake_not_found(self, mock_generator_cls, mock_run, tmp_path):
        """Test error handling when CMake is not found."""
        mock_generator = Mock()
        mock_generator_cls.return_value = mock_generator
        mock_generator.generate.return_value = tmp_path / "toolchain.cmake"
        mock_run.side_effect = FileNotFoundError("cmake not found")

        backend = CMakeBackend()
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        toolchain_data = {
            "id": "test",
            "path": str(tmp_path / "toolchain"),
            "name": "test",
        }

        config = {"build_type": "Release"}

        with pytest.raises(RuntimeError, match="CMake not found"):
            backend.configure(project_root, build_dir, toolchain_data, config)

    @patch("toolchainkit.backends.cmake.subprocess.run")
    @patch("toolchainkit.backends.cmake.CMakeToolchainGenerator")
    def test_configure_cmake_failure(self, mock_generator_cls, mock_run, tmp_path):
        """Test error handling when CMake configuration fails."""
        mock_generator = Mock()
        mock_generator_cls.return_value = mock_generator
        mock_generator.generate.return_value = tmp_path / "toolchain.cmake"
        mock_run.return_value = Mock(returncode=1)

        backend = CMakeBackend()
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        toolchain_data = {
            "id": "test",
            "path": str(tmp_path / "toolchain"),
            "name": "test",
        }

        config = {"build_type": "Release"}

        with pytest.raises(RuntimeError, match="CMake configuration failed"):
            backend.configure(project_root, build_dir, toolchain_data, config)

    @patch("toolchainkit.backends.cmake.subprocess.run")
    @patch("toolchainkit.backends.cmake.CMakeToolchainGenerator")
    def test_compiler_type_inference(self, mock_generator_cls, mock_run, tmp_path):
        """Test compiler type inference from toolchain name."""
        mock_generator = Mock()
        mock_generator_cls.return_value = mock_generator
        mock_generator.generate.return_value = tmp_path / "toolchain.cmake"
        mock_run.return_value = Mock(returncode=0)

        backend = CMakeBackend()
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Test LLVM inference
        toolchain_data = {
            "id": "llvm-18",
            "path": str(tmp_path / "toolchain"),
            "name": "llvm-18.1.8-linux-x64",
        }
        config = {"build_type": "Release"}

        backend.configure(project_root, tmp_path / "build1", toolchain_data, config)

        # Check that generate was called with correct config
        generate_call = mock_generator.generate.call_args[0][0]
        assert generate_call.compiler_type == "clang"

        # Test GCC inference
        toolchain_data["name"] = "gcc-13.2.0"
        backend.configure(project_root, tmp_path / "build2", toolchain_data, config)
        generate_call = mock_generator.generate.call_args[0][0]
        assert generate_call.compiler_type == "gcc"

        # Test MSVC inference
        toolchain_data["name"] = "msvc-19.38"
        backend.configure(project_root, tmp_path / "build3", toolchain_data, config)
        generate_call = mock_generator.generate.call_args[0][0]
        assert generate_call.compiler_type == "msvc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
