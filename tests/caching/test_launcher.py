"""
Unit tests for compiler launcher configuration.

Tests the CompilerLauncherConfig class and CacheStats dataclass
for build cache integration with CMake.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from toolchainkit.caching.detection import BuildCacheConfig
from toolchainkit.caching.launcher import CacheStats, CompilerLauncherConfig


# =============================================================================
# CacheStats Tests
# =============================================================================


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_cache_stats_creation(self):
        """Test creating CacheStats object."""
        stats = CacheStats(
            hits=100,
            misses=25,
            errors=2,
            cache_size=1024 * 1024 * 500,  # 500 MB
            hit_rate=80.0,
        )

        assert stats.hits == 100
        assert stats.misses == 25
        assert stats.errors == 2
        assert stats.cache_size == 1024 * 1024 * 500
        assert stats.hit_rate == 80.0

    def test_cache_stats_str(self):
        """Test string representation."""
        stats = CacheStats(
            hits=100, misses=25, errors=2, cache_size=1024 * 1024 * 500, hit_rate=80.0
        )

        str_repr = str(stats)
        assert "hits=100" in str_repr
        assert "misses=25" in str_repr
        assert "errors=2" in str_repr
        assert "hit_rate=80.0%" in str_repr

    def test_hit_rate_calculation(self):
        """Test hit rate is correctly calculated."""
        # 75% hit rate
        stats = CacheStats(hits=75, misses=25, errors=0, cache_size=0, hit_rate=75.0)

        assert stats.hit_rate == 75.0

        # 100% hit rate
        stats = CacheStats(hits=100, misses=0, errors=0, cache_size=0, hit_rate=100.0)

        assert stats.hit_rate == 100.0


# =============================================================================
# CompilerLauncherConfig Tests
# =============================================================================


class TestCompilerLauncherConfig:
    """Tests for CompilerLauncherConfig class."""

    @pytest.fixture
    def sccache_config(self, tmp_path):
        """Create a mock sccache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()

        cache_dir = tmp_path / "cache" / "sccache"
        cache_dir.mkdir(parents=True)

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=cache_dir,
            max_size="10G",
        )

    @pytest.fixture
    def ccache_config(self, tmp_path):
        """Create a mock ccache configuration."""
        executable = tmp_path / "ccache.exe"
        executable.touch()

        cache_dir = tmp_path / "cache" / "ccache"
        cache_dir.mkdir(parents=True)

        return BuildCacheConfig(
            tool="ccache",
            version="4.8.3",
            executable_path=executable,
            cache_dir=cache_dir,
            max_size="5G",
        )

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_with_sccache_config(self, sccache_config):
        """Test initialization with sccache configuration."""
        launcher = CompilerLauncherConfig(sccache_config)

        assert launcher.cache_config == sccache_config
        assert launcher.cache_config.tool == "sccache"

    def test_init_with_ccache_config(self, ccache_config):
        """Test initialization with ccache configuration."""
        launcher = CompilerLauncherConfig(ccache_config)

        assert launcher.cache_config == ccache_config
        assert launcher.cache_config.tool == "ccache"

    def test_init_with_none_raises_error(self):
        """Test initialization with None raises ValueError."""
        with pytest.raises(ValueError, match="cache_config cannot be None"):
            CompilerLauncherConfig(None)

    def test_init_with_missing_executable_raises_error(self, tmp_path):
        """Test initialization with non-existent executable raises error."""
        config = BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=tmp_path / "nonexistent.exe",
            cache_dir=tmp_path / "cache",
            max_size="10G",
        )

        with pytest.raises(ValueError, match="Cache executable not found"):
            CompilerLauncherConfig(config)

    # -------------------------------------------------------------------------
    # CMake Variables Tests
    # -------------------------------------------------------------------------

    def test_get_cmake_variables_sccache(self, sccache_config):
        """Test CMake variables for sccache."""
        launcher = CompilerLauncherConfig(sccache_config)
        cmake_vars = launcher.get_cmake_variables()

        assert "CMAKE_C_COMPILER_LAUNCHER" in cmake_vars
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in cmake_vars

        # Both should point to same executable
        assert (
            cmake_vars["CMAKE_C_COMPILER_LAUNCHER"]
            == cmake_vars["CMAKE_CXX_COMPILER_LAUNCHER"]
        )

        # Should contain executable path (normalized with forward slashes)
        executable_str = str(sccache_config.executable_path).replace("\\", "/")
        assert cmake_vars["CMAKE_C_COMPILER_LAUNCHER"] == executable_str

    def test_get_cmake_variables_ccache(self, ccache_config):
        """Test CMake variables for ccache."""
        launcher = CompilerLauncherConfig(ccache_config)
        cmake_vars = launcher.get_cmake_variables()

        assert "CMAKE_C_COMPILER_LAUNCHER" in cmake_vars
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in cmake_vars

        executable_str = str(ccache_config.executable_path).replace("\\", "/")
        assert cmake_vars["CMAKE_C_COMPILER_LAUNCHER"] == executable_str

    def test_cmake_variables_use_forward_slashes(self, sccache_config):
        """Test CMake variables use forward slashes (Windows compatibility)."""
        launcher = CompilerLauncherConfig(sccache_config)
        cmake_vars = launcher.get_cmake_variables()

        # Should not contain backslashes
        for value in cmake_vars.values():
            assert "\\" not in value

    # -------------------------------------------------------------------------
    # Environment Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_environment_sccache(self, sccache_config):
        """Test environment configuration for sccache."""
        launcher = CompilerLauncherConfig(sccache_config)
        env_vars = launcher.configure_environment()

        assert "SCCACHE_DIR" in env_vars
        assert env_vars["SCCACHE_DIR"] == str(sccache_config.cache_dir)

        assert "SCCACHE_CACHE_SIZE" in env_vars
        assert env_vars["SCCACHE_CACHE_SIZE"] == "10G"

    def test_configure_environment_sccache_no_max_size(self, sccache_config):
        """Test environment configuration for sccache without max_size."""
        sccache_config.max_size = None
        launcher = CompilerLauncherConfig(sccache_config)
        env_vars = launcher.configure_environment()

        assert "SCCACHE_DIR" in env_vars
        assert "SCCACHE_CACHE_SIZE" not in env_vars

    def test_configure_environment_ccache(self, ccache_config):
        """Test environment configuration for ccache."""
        launcher = CompilerLauncherConfig(ccache_config)
        env_vars = launcher.configure_environment()

        assert "CCACHE_DIR" in env_vars
        assert env_vars["CCACHE_DIR"] == str(ccache_config.cache_dir)

        assert "CCACHE_MAXSIZE" in env_vars
        assert env_vars["CCACHE_MAXSIZE"] == "5G"

    def test_configure_environment_ccache_no_max_size(self, ccache_config):
        """Test environment configuration for ccache without max_size."""
        ccache_config.max_size = None
        launcher = CompilerLauncherConfig(ccache_config)
        env_vars = launcher.configure_environment()

        assert "CCACHE_DIR" in env_vars
        assert "CCACHE_MAXSIZE" not in env_vars

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    def test_get_stats_sccache(self, sccache_config):
        """Test getting statistics from sccache."""
        launcher = CompilerLauncherConfig(sccache_config)

        # Mock sccache --show-stats output
        mock_output = """Compile requests                      524
Compile requests executed             120
Cache hits                            404
Cache misses                          120
Cache timeouts                          0
Cache read errors                       0
Forced recaches                         0
Cache write errors                      0
Compilation failures                    0
Cache errors                            5
Non-cacheable compilations              0
Non-cacheable calls                     0
Non-compilation calls                   0
Unsupported compiler calls              0"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=mock_output, returncode=0)

            stats = launcher.get_stats()

        assert stats is not None
        assert stats.hits == 404
        assert stats.misses == 120
        assert stats.errors == 5
        assert stats.hit_rate == pytest.approx(77.1, abs=0.1)

    def test_get_stats_ccache(self, ccache_config):
        """Test getting statistics from ccache."""
        launcher = CompilerLauncherConfig(ccache_config)

        # Mock ccache --show-stats output
        mock_output = """Cacheable calls:    256 / 320 (80.00%)
  Hits:             200 / 256 (78.12%)
    Direct:         180 / 200 (90.00%)
    Preprocessed:    20 / 200 (10.00%)
  Misses:            56 / 256 (21.88%)
Uncacheable calls:   64 / 320 (20.00%)
Local storage:
  Cache size (GB): 1.2 / 10.0 (12.00%)
  Hits:            200 / 256 (78.12%)
  Misses:           56 / 256 (21.88%)"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=mock_output, returncode=0)

            stats = launcher.get_stats()

        assert stats is not None
        assert stats.hits == 200
        assert stats.misses == 56
        assert stats.cache_size == pytest.approx(1.2 * 1024**3, rel=0.01)
        assert stats.hit_rate == pytest.approx(78.12, abs=0.1)

    def test_get_stats_timeout(self, sccache_config):
        """Test statistics timeout handling."""
        launcher = CompilerLauncherConfig(sccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["sccache", "--show-stats"], timeout=10
            )

            stats = launcher.get_stats()

        assert stats is None

    def test_get_stats_error(self, sccache_config):
        """Test statistics error handling."""
        launcher = CompilerLauncherConfig(sccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd=["sccache", "--show-stats"]
            )

            stats = launcher.get_stats()

        assert stats is None

    def test_get_stats_unknown_tool(self, sccache_config):
        """Test statistics with unknown tool."""
        sccache_config.tool = "unknown"
        launcher = CompilerLauncherConfig(sccache_config)

        stats = launcher.get_stats()
        assert stats is None

    def test_get_stats_sccache_zero_total(self, sccache_config):
        """Test sccache statistics with zero hits and misses."""
        launcher = CompilerLauncherConfig(sccache_config)

        mock_output = """Compile requests                      0
Cache hits                            0
Cache misses                          0
Cache errors                          0"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=mock_output, returncode=0)

            stats = launcher.get_stats()

        assert stats is not None
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    # -------------------------------------------------------------------------
    # Clear Cache Tests
    # -------------------------------------------------------------------------

    def test_clear_cache_sccache(self, sccache_config):
        """Test clearing sccache statistics."""
        launcher = CompilerLauncherConfig(sccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = launcher.clear_cache()

        assert result is True
        mock_run.assert_called_once()

        # Verify correct command
        args = mock_run.call_args[0][0]
        assert str(sccache_config.executable_path) in str(args[0])
        assert "--zero-stats" in args

    def test_clear_cache_ccache(self, ccache_config):
        """Test clearing ccache data."""
        launcher = CompilerLauncherConfig(ccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = launcher.clear_cache()

        assert result is True
        mock_run.assert_called_once()

        # Verify correct command
        args = mock_run.call_args[0][0]
        assert str(ccache_config.executable_path) in str(args[0])
        assert "--clear" in args

    def test_clear_cache_timeout(self, sccache_config):
        """Test clear cache timeout handling."""
        launcher = CompilerLauncherConfig(sccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["sccache", "--zero-stats"], timeout=10
            )

            result = launcher.clear_cache()

        assert result is False

    def test_clear_cache_error(self, sccache_config):
        """Test clear cache error handling."""
        launcher = CompilerLauncherConfig(sccache_config)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd=["sccache", "--zero-stats"]
            )

            result = launcher.clear_cache()

        assert result is False

    def test_clear_cache_unknown_tool(self, sccache_config):
        """Test clear cache with unknown tool."""
        sccache_config.tool = "unknown"
        launcher = CompilerLauncherConfig(sccache_config)

        result = launcher.clear_cache()
        assert result is False

    # -------------------------------------------------------------------------
    # CMake Snippet Tests
    # -------------------------------------------------------------------------

    def test_generate_cmake_snippet_sccache(self, sccache_config):
        """Test CMake snippet generation for sccache."""
        launcher = CompilerLauncherConfig(sccache_config)
        snippet = launcher.generate_cmake_snippet()

        # Check header comment
        assert "Compiler Launcher: sccache 0.7.4" in snippet

        # Check CMake variables
        assert "CMAKE_C_COMPILER_LAUNCHER" in snippet
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in snippet

        # Check paths (should use forward slashes)
        executable_str = str(sccache_config.executable_path).replace("\\", "/")
        assert executable_str in snippet

        # Check cache config comments
        cache_dir_str = str(sccache_config.cache_dir).replace("\\", "/")
        assert cache_dir_str in snippet
        assert "Max size: 10G" in snippet

        # Check usage help
        assert "--show-stats" in snippet

    def test_generate_cmake_snippet_ccache(self, ccache_config):
        """Test CMake snippet generation for ccache."""
        launcher = CompilerLauncherConfig(ccache_config)
        snippet = launcher.generate_cmake_snippet()

        assert "Compiler Launcher: ccache 4.8.3" in snippet
        assert "CMAKE_C_COMPILER_LAUNCHER" in snippet
        assert "CMAKE_CXX_COMPILER_LAUNCHER" in snippet

        executable_str = str(ccache_config.executable_path).replace("\\", "/")
        assert executable_str in snippet

    def test_generate_cmake_snippet_no_version(self, sccache_config):
        """Test CMake snippet generation without version."""
        sccache_config.version = None
        launcher = CompilerLauncherConfig(sccache_config)
        snippet = launcher.generate_cmake_snippet()

        assert "Compiler Launcher: sccache unknown" in snippet

    def test_generate_cmake_snippet_no_max_size(self, sccache_config):
        """Test CMake snippet generation without max_size."""
        sccache_config.max_size = None
        launcher = CompilerLauncherConfig(sccache_config)
        snippet = launcher.generate_cmake_snippet()

        assert "Max size:" not in snippet

    def test_generate_cmake_snippet_forward_slashes(self, sccache_config):
        """Test CMake snippet uses forward slashes on Windows."""
        launcher = CompilerLauncherConfig(sccache_config)
        snippet = launcher.generate_cmake_snippet()

        # CMake snippet should not contain backslashes
        lines = [line for line in snippet.split("\n") if "set(" in line]
        for line in lines:
            # Extract quoted paths
            if '"' in line:
                path = line.split('"')[1]
                assert "\\" not in path, f"Found backslash in path: {path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
