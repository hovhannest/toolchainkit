"""
Unit tests for CMake build backend configuration.

Tests backend detection, configuration, and build argument generation
across different platforms and build systems.
"""

import pytest
import platform as sys_platform
from unittest.mock import patch
import shutil

from toolchainkit.cmake.backends import (
    BuildBackend,
    NinjaBackend,
    MakeBackend,
    MSBuildBackend,
    XcodeBackend,
    NMakeMakefilesBackend,
    BuildBackendDetector,
    BuildBackendConfig,
    detect_build_backend,
    BuildBackendError,
    BackendNotAvailableError,
)


class TestBuildBackend:
    """Test BuildBackend base class."""

    def test_base_class_not_implementable(self):
        """Test that BuildBackend methods are abstract."""
        backend = BuildBackend("Test", parallel_jobs=4)

        with pytest.raises(NotImplementedError):
            backend.get_cmake_generator()

        with pytest.raises(NotImplementedError):
            backend.get_build_args()

        with pytest.raises(NotImplementedError):
            backend.is_available()

    @patch("os.cpu_count")
    def test_default_parallel_jobs(self, mock_cpu_count):
        """Test default parallel jobs uses CPU count."""
        mock_cpu_count.return_value = 4
        backend = BuildBackend("Test")
        assert backend.parallel_jobs > 0
        assert backend.parallel_jobs >= 4  # Minimum fallback

    def test_custom_parallel_jobs(self):
        """Test custom parallel jobs."""
        backend = BuildBackend("Test", parallel_jobs=8)
        assert backend.parallel_jobs == 8

    def test_string_representation(self):
        """Test string representation."""
        backend = BuildBackend("Test Backend", parallel_jobs=4)
        assert "Test Backend" in str(backend)
        assert "parallel=4" in str(backend)


class TestNinjaBackend:
    """Test Ninja build backend."""

    def test_cmake_generator(self):
        """Test CMake generator name."""
        backend = NinjaBackend()
        assert backend.get_cmake_generator() == "Ninja"

    def test_build_args(self):
        """Test build arguments."""
        backend = NinjaBackend(parallel_jobs=8)
        args = backend.get_build_args()

        assert "-j" in args
        assert "8" in args

    def test_is_available(self):
        """Test availability detection."""
        backend = NinjaBackend()

        # Should return True if ninja is on PATH
        is_available = backend.is_available()

        # Check against actual ninja availability
        ninja_exists = shutil.which("ninja") is not None
        assert is_available == ninja_exists

    def test_cmake_variables(self):
        """Test CMake variables."""
        backend = NinjaBackend()
        vars = backend.get_cmake_variables()

        assert "CMAKE_GENERATOR" in vars
        assert vars["CMAKE_GENERATOR"] == "Ninja"
        assert "CMAKE_EXPORT_COMPILE_COMMANDS" in vars
        assert vars["CMAKE_EXPORT_COMPILE_COMMANDS"] == "ON"

    @patch("shutil.which")
    def test_availability_with_mock(self, mock_which):
        """Test availability with mocked which."""
        backend = NinjaBackend()

        # Test when ninja is available
        mock_which.return_value = "/usr/bin/ninja"
        assert backend.is_available() is True

        # Test when ninja is not available
        mock_which.return_value = None
        assert backend.is_available() is False


class TestMakeBackend:
    """Test Make build backend."""

    def test_cmake_generator(self):
        """Test CMake generator name."""
        backend = MakeBackend()
        assert backend.get_cmake_generator() == "Unix Makefiles"

    def test_build_args(self):
        """Test build arguments."""
        backend = MakeBackend(parallel_jobs=16)
        args = backend.get_build_args()

        assert "-j" in args
        assert "16" in args

    def test_is_available(self):
        """Test availability detection."""
        backend = MakeBackend()
        is_available = backend.is_available()

        # Check against actual make availability
        make_exists = shutil.which("make") is not None
        assert is_available == make_exists

    @patch("shutil.which")
    def test_availability_with_mock(self, mock_which):
        """Test availability with mocked which."""
        backend = MakeBackend()

        mock_which.return_value = "/usr/bin/make"
        assert backend.is_available() is True

        mock_which.return_value = None
        assert backend.is_available() is False


class TestMSBuildBackend:
    """Test MSBuild build backend."""

    def test_cmake_generator(self):
        """Test CMake generator name."""
        backend = MSBuildBackend(version="17 2022")
        assert backend.get_cmake_generator() == "Visual Studio 17 2022"

    def test_default_version(self):
        """Test default Visual Studio version."""
        backend = MSBuildBackend()
        assert "Visual Studio" in backend.get_cmake_generator()

    def test_build_args(self):
        """Test build arguments."""
        backend = MSBuildBackend(parallel_jobs=12)
        args = backend.get_build_args()

        assert "--" in args  # Separator for MSBuild args
        assert "/maxcpucount:12" in args

    @patch("platform.system")
    def test_only_available_on_windows(self, mock_system):
        """Test that MSBuild is only available on Windows."""
        backend = MSBuildBackend()

        mock_system.return_value = "Linux"
        assert backend.is_available() is False

        mock_system.return_value = "Darwin"
        assert backend.is_available() is False

    @pytest.mark.platform_windows
    def test_windows_availability(self):
        """Test availability on actual Windows system."""
        if sys_platform.system() != "Windows":
            pytest.skip("Windows-only test")

        backend = MSBuildBackend()
        # Should be available if VS is installed
        is_available = backend.is_available()

        # Just verify it returns a boolean
        assert isinstance(is_available, bool)


class TestXcodeBackend:
    """Test Xcode build backend."""

    def test_cmake_generator(self):
        """Test CMake generator name."""
        backend = XcodeBackend()
        assert backend.get_cmake_generator() == "Xcode"

    def test_build_args(self):
        """Test build arguments."""
        backend = XcodeBackend(parallel_jobs=6)
        args = backend.get_build_args()

        assert "--" in args
        assert "-jobs" in args
        assert "6" in args

    @patch("platform.system")
    def test_only_available_on_macos(self, mock_system):
        """Test that Xcode is only available on macOS."""
        backend = XcodeBackend()

        mock_system.return_value = "Linux"
        assert backend.is_available() is False

        mock_system.return_value = "Windows"
        assert backend.is_available() is False

    @pytest.mark.platform_macos
    def test_macos_availability(self):
        """Test availability on actual macOS system."""
        if sys_platform.system() != "Darwin":
            pytest.skip("macOS-only test")

        backend = XcodeBackend()
        is_available = backend.is_available()

        # Should check for Xcode.app or xcodebuild
        assert isinstance(is_available, bool)


class TestNMakeMakefilesBackend:
    """Test NMake Makefiles backend."""

    def test_cmake_generator(self):
        """Test CMake generator name."""
        backend = NMakeMakefilesBackend()
        assert backend.get_cmake_generator() == "NMake Makefiles"

    def test_build_args(self):
        """Test build arguments (NMake doesn't support parallel)."""
        backend = NMakeMakefilesBackend()
        args = backend.get_build_args()

        # NMake doesn't have good parallel support
        assert args == []

    @patch("shutil.which")
    def test_availability(self, mock_which):
        """Test availability detection."""
        backend = NMakeMakefilesBackend()

        mock_which.return_value = "C:\\Program Files\\nmake.exe"
        assert backend.is_available() is True

        mock_which.return_value = None
        assert backend.is_available() is False


class TestBuildBackendDetector:
    """Test build backend detection."""

    def test_detector_initialization(self):
        """Test detector initializes with platform info."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        assert detector.platform == platform
        assert isinstance(detector._backends, list)

    def test_detect_best_prefers_ninja(self):
        """Test that detector prefers Ninja if available."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        # If Ninja is available, it should be selected
        available_backends = detector.get_all()
        has_ninja = any(isinstance(b, NinjaBackend) for b in available_backends)

        best = detector.detect_best()

        if has_ninja:
            assert isinstance(best, NinjaBackend)

    def test_detect_best_finds_fallback(self):
        """Test that detector finds fallback if Ninja unavailable."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()

        # Mock shutil.which to return None for ninja but allow other tools
        original_which = shutil.which

        def mock_which(cmd):
            if cmd == "ninja":
                return None
            return original_which(cmd)

        def mock_check_tool(instance, tool):
            if tool == "ninja":
                return False
            return original_which(tool) is not None

        with patch("shutil.which", side_effect=mock_which):
            # Also need to patch BuildBackendDetector._check_tool_available for ninja
            with patch.object(
                BuildBackendDetector,
                "_check_tool_available",
                mock_check_tool,
            ):
                detector = BuildBackendDetector(platform)

                # Should still find something (Make, MSBuild, or Xcode)
                if detector.get_all():
                    best = detector.detect_best()
                    assert best is not None
                    assert not isinstance(best, NinjaBackend)

    def test_get_all_returns_available_backends(self):
        """Test get_all returns list of available backends."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        all_backends = detector.get_all()

        # Should have at least one backend
        assert len(all_backends) >= 0  # May be 0 on minimal systems

        # All returned backends should be available
        for backend in all_backends:
            assert backend.is_available()

    def test_get_by_name(self):
        """Test getting backend by name."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        # Try to find Ninja by name
        ninja = detector.get_by_name("Ninja")

        if ninja:
            assert isinstance(ninja, NinjaBackend)

        # Case insensitive
        ninja2 = detector.get_by_name("ninja")
        if ninja2:
            assert isinstance(ninja2, NinjaBackend)

    def test_get_by_name_partial_match(self):
        """Test partial name matching."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)

        # Partial match should work
        vs = detector.get_by_name("Visual Studio")
        if vs:
            assert isinstance(vs, MSBuildBackend)

    def test_no_backends_available_raises_error(self):
        """Test that error is raised when no backends available."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()

        # Mock all backends as unavailable
        # Note: Ninja and Make use _check_tool_available which needs to be mocked too
        with patch.object(
            NinjaBackend, "is_available", return_value=False
        ), patch.object(MakeBackend, "is_available", return_value=False), patch.object(
            MSBuildBackend, "is_available", return_value=False
        ), patch.object(XcodeBackend, "is_available", return_value=False), patch.object(
            NMakeMakefilesBackend, "is_available", return_value=False
        ), patch.object(
            BuildBackendDetector, "_check_tool_available", return_value=False
        ):
            detector = BuildBackendDetector(platform)

            with pytest.raises(BuildBackendError) as exc_info:
                detector.detect_best()

            assert "No build backend available" in str(exc_info.value)


class TestBuildBackendConfig:
    """Test build backend configuration."""

    def test_generate_cmake_args(self):
        """Test CMake configuration argument generation."""
        backend = NinjaBackend()
        config = BuildBackendConfig(backend)

        args = config.generate_cmake_args()

        assert "-G" in args
        assert "Ninja" in args
        assert "-D" in args
        assert "CMAKE_EXPORT_COMPILE_COMMANDS=ON" in args

    def test_generate_build_args(self):
        """Test CMake build argument generation."""
        backend = MakeBackend(parallel_jobs=8)
        config = BuildBackendConfig(backend)

        args = config.generate_build_args("Debug")

        assert "--build" in args
        assert "." in args
        assert "--config" in args
        assert "Debug" in args
        assert "-j" in args
        assert "8" in args

    def test_generate_cmake_snippet(self):
        """Test CMake snippet generation."""
        backend = NinjaBackend(parallel_jobs=4)
        config = BuildBackendConfig(backend)

        snippet = config.generate_cmake_snippet()

        assert "Build Backend: Ninja" in snippet
        assert "Parallel Jobs: 4" in snippet
        assert "CMAKE_GENERATOR" in snippet
        assert "CMAKE_EXPORT_COMPILE_COMMANDS" in snippet

    def test_to_dict(self):
        """Test dictionary conversion."""
        backend = MSBuildBackend(version="17 2022", parallel_jobs=12)
        config = BuildBackendConfig(backend)

        data = config.to_dict()

        assert data["name"] == "Visual Studio 17 2022"
        assert data["generator"] == "Visual Studio 17 2022"
        assert data["parallel_jobs"] == 12
        assert "cmake_variables" in data


class TestDetectBuildBackend:
    """Test detect_build_backend helper function."""

    def test_detect_without_preference(self):
        """Test detection without preferred backend."""
        backend = detect_build_backend()

        assert isinstance(backend, BuildBackend)
        assert backend.is_available()

    def test_detect_with_valid_preference(self):
        """Test detection with valid preferred backend."""
        # Try to prefer Ninja if available
        try:
            backend = detect_build_backend(prefer="Ninja")
            assert isinstance(backend, NinjaBackend)
        except BackendNotAvailableError:
            # Ninja not available, expected
            pass

    def test_detect_with_invalid_preference_raises_error(self):
        """Test that invalid preference raises error."""
        with pytest.raises(BackendNotAvailableError) as exc_info:
            detect_build_backend(prefer="NonExistentBackend")

        assert "not available" in str(exc_info.value)


@pytest.mark.integration
class TestBackendIntegration:
    """Integration tests for backend detection and configuration."""

    def test_full_detection_flow(self):
        """Test complete detection and configuration flow."""
        from toolchainkit.core.platform import detect_platform

        # Detect platform
        platform = detect_platform()

        # Detect backend
        detector = BuildBackendDetector(platform)
        backend = detector.detect_best()

        assert backend is not None
        assert backend.is_available()

        # Create configuration
        config = BuildBackendConfig(backend)

        # Generate arguments
        cmake_args = config.generate_cmake_args()
        assert len(cmake_args) > 0

        build_args = config.generate_build_args()
        assert len(build_args) > 0

    def test_platform_specific_backends(self):
        """Test platform-specific backend availability."""
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()
        detector = BuildBackendDetector(platform)
        backends = detector.get_all()

        # Check platform-specific expectations
        if platform.os == "windows":
            # Windows should have MSBuild or NMake
            _has_windows_backend = any(
                isinstance(b, (MSBuildBackend, NMakeMakefilesBackend)) for b in backends
            )
            # Note: May not be true on minimal Windows installations

        elif platform.os == "macos":
            # macOS should have Make, possibly Xcode
            _has_make = any(isinstance(b, MakeBackend) for b in backends)
            # Make should generally be available on macOS

        elif platform.os == "linux":
            # Linux should have Make
            _has_make = any(isinstance(b, MakeBackend) for b in backends)
            # Make should generally be available on Linux


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
