"""
Integration tests for compiler launcher configuration.

These tests verify the CompilerLauncherConfig class works correctly
with real build cache tools when available.
"""

from pathlib import Path

import pytest

from toolchainkit.caching.detection import BuildCacheDetector, BuildCacheManager
from toolchainkit.caching.launcher import CompilerLauncherConfig


pytestmark = pytest.mark.integration


@pytest.fixture
def detector():
    """Create a build cache detector."""
    return BuildCacheDetector()


@pytest.fixture
def manager(tmp_path):
    """Create a build cache manager with temporary project root."""
    return BuildCacheManager(project_root=tmp_path)


# =============================================================================
# Real Tool Integration Tests
# =============================================================================


class TestCompilerLauncherIntegration:
    """Integration tests with real build cache tools."""

    @pytest.mark.slow
    def test_launcher_with_real_sccache(self, manager):
        """Test launcher with real sccache if available."""
        # Try to get or install sccache
        config = manager.get_or_install(prefer="sccache")

        if not config or config.tool != "sccache":
            pytest.skip("sccache not available")

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Test CMake variables
        cmake_vars = launcher.get_cmake_variables()
        assert "CMAKE_C_COMPILER_LAUNCHER" in cmake_vars
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in cmake_vars
        assert cmake_vars["CMAKE_C_COMPILER_LAUNCHER"] == str(
            config.executable_path
        ).replace("\\", "/")

        # Test environment configuration
        env_vars = launcher.configure_environment()
        assert "SCCACHE_DIR" in env_vars
        assert env_vars["SCCACHE_DIR"] == str(config.cache_dir)

        # Test CMake snippet generation
        snippet = launcher.generate_cmake_snippet()
        assert "CMAKE_C_COMPILER_LAUNCHER" in snippet
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in snippet
        assert str(config.executable_path).replace("\\", "/") in snippet

        print("\nTested sccache launcher:")
        print(f"  Executable: {config.executable_path}")
        print(f"  Version: {config.version}")
        print(f"  Cache dir: {config.cache_dir}")

    @pytest.mark.slow
    def test_launcher_with_real_ccache(self, detector):
        """Test launcher with real ccache if available."""
        # Detect ccache
        ccache_path = detector.detect_ccache()

        if not ccache_path:
            pytest.skip("ccache not available")

        # Get version
        version = detector.get_version(ccache_path)

        # Create config
        from toolchainkit.caching.detection import BuildCacheConfig

        config = BuildCacheConfig(
            tool="ccache",
            executable_path=ccache_path,
            cache_dir=Path.home() / ".cache" / "ccache",
            max_size="10G",
            version=version,
        )

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Test CMake variables
        cmake_vars = launcher.get_cmake_variables()
        assert "CMAKE_C_COMPILER_LAUNCHER" in cmake_vars
        assert cmake_vars["CMAKE_C_COMPILER_LAUNCHER"] == str(ccache_path).replace(
            "\\", "/"
        )

        # Test environment configuration
        env_vars = launcher.configure_environment()
        assert "CCACHE_DIR" in env_vars

        # Test CMake snippet generation
        snippet = launcher.generate_cmake_snippet()
        assert "CMAKE_C_COMPILER_LAUNCHER" in snippet
        assert "ccache" in snippet.lower()

        print("\nTested ccache launcher:")
        print(f"  Executable: {ccache_path}")
        print(f"  Version: {version}")

    @pytest.mark.slow
    def test_get_stats_with_real_tool(self, manager):
        """Test getting statistics from real cache tool."""
        # Try to get or install sccache
        config = manager.get_or_install(prefer="sccache")

        if not config:
            pytest.skip("No cache tool available")

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Get statistics (may be None if tool doesn't support stats)
        stats = launcher.get_stats()

        if stats:
            assert stats.hits >= 0
            assert stats.misses >= 0
            assert stats.errors >= 0
            assert 0.0 <= stats.hit_rate <= 100.0

            print(f"\nCache statistics ({config.tool}):")
            print(f"  Hits: {stats.hits}")
            print(f"  Misses: {stats.misses}")
            print(f"  Errors: {stats.errors}")
            print(f"  Hit rate: {stats.hit_rate:.1f}%")
            print(f"  Cache size: {stats.cache_size} bytes")
        else:
            print(f"\nNo statistics available for {config.tool}")

    @pytest.mark.slow
    def test_clear_cache_with_real_tool(self, manager):
        """Test clearing cache with real cache tool."""
        # Try to get or install sccache
        config = manager.get_or_install(prefer="sccache")

        if not config:
            pytest.skip("No cache tool available")

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Clear cache
        result = launcher.clear_cache()

        # sccache --zero-stats should succeed
        # ccache --clear should succeed
        assert result is True, f"Failed to clear cache for {config.tool}"

        print(f"\nCleared cache for {config.tool}")

    def test_cmake_snippet_is_valid(self, manager):
        """Test that generated CMake snippet is syntactically valid."""
        # Try to get or install a cache tool
        config = manager.get_or_install()

        if not config:
            pytest.skip("No cache tool available")

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Generate CMake snippet
        snippet = launcher.generate_cmake_snippet()

        # Verify snippet is not empty
        assert snippet.strip(), "Generated empty CMake snippet"

        # Verify it contains set() commands
        assert "set(" in snippet.lower(), "CMake snippet missing set() commands"

        # Verify it sets both C and C++ launcher
        assert "CMAKE_C_COMPILER_LAUNCHER" in snippet
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in snippet

        # Verify executable path is present
        executable_str = str(config.executable_path).replace("\\", "/")
        assert executable_str in snippet

        print("\nGenerated CMake snippet:")
        print("-" * 60)
        print(snippet)
        print("-" * 60)

    def test_environment_variables_are_valid(self, manager):
        """Test that environment variables are correctly formatted."""
        # Try to get or install a cache tool
        config = manager.get_or_install()

        if not config:
            pytest.skip("No cache tool available")

        # Create launcher
        launcher = CompilerLauncherConfig(config)

        # Get environment variables
        env_vars = launcher.configure_environment()

        # Verify env vars is a dictionary
        assert isinstance(env_vars, dict)

        # Verify at least one env var is set
        assert len(env_vars) > 0, "No environment variables configured"

        # Verify all values are strings
        for key, value in env_vars.items():
            assert isinstance(key, str), f"Key {key} is not a string"
            assert isinstance(value, str), f"Value for {key} is not a string"

        # Verify tool-specific variables
        if config.tool == "sccache":
            assert "SCCACHE_DIR" in env_vars
        elif config.tool == "ccache":
            assert "CCACHE_DIR" in env_vars

        print(f"\nEnvironment variables for {config.tool}:")
        for key, value in env_vars.items():
            print(f"  {key}={value}")


if __name__ == "__main__":
    # Run integration tests directly
    pytest.main([__file__, "-v", "--tb=short"])
