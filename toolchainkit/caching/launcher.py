"""
Compiler launcher configuration for build cache integration (sccache/ccache).

This module provides the CompilerLauncherConfig class that configures CMAKE_*_COMPILER_LAUNCHER
variables, environment variables, and provides utilities for cache statistics and management.

Usage:
    from toolchainkit.caching.detection import BuildCacheManager
    from toolchainkit.caching.launcher import CompilerLauncherConfig

    # Get cache configuration
    manager = BuildCacheManager()
    cache_config = manager.get_or_install()

    # Create launcher config
    launcher = CompilerLauncherConfig(cache_config)

    # Get CMake variables
    cmake_vars = launcher.get_cmake_variables()
    # {'CMAKE_C_COMPILER_LAUNCHER': '/path/to/sccache', ...}

    # Get environment variables
    env_vars = launcher.configure_environment()
    # {'SCCACHE_DIR': '/path/to/cache', ...}

    # Get cache statistics
    stats = launcher.get_stats()
    if stats:
        print(f"Hit rate: {stats.hit_rate:.1f}%")
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional

from .detection import BuildCacheConfig

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics for build cache tools."""

    hits: int
    """Number of cache hits."""

    misses: int
    """Number of cache misses."""

    errors: int
    """Number of cache errors."""

    cache_size: int
    """Current cache size in bytes."""

    hit_rate: float
    """Hit rate as percentage (0-100)."""

    def __str__(self) -> str:
        """String representation of cache stats."""
        return (
            f"CacheStats(hits={self.hits}, misses={self.misses}, "
            f"errors={self.errors}, hit_rate={self.hit_rate:.1f}%)"
        )


class CompilerLauncherConfig:
    """
    Configuration for compiler launcher (build cache) integration with CMake.

    This class provides:
    - CMake variable configuration (CMAKE_*_COMPILER_LAUNCHER)
    - Environment variable configuration (SCCACHE_DIR, CCACHE_DIR, etc.)
    - Cache statistics retrieval and parsing
    - Cache management (clear, stats)
    - CMake snippet generation for toolchain files

    Attributes:
        cache_config: BuildCacheConfig instance with cache tool information
    """

    def __init__(self, cache_config: BuildCacheConfig):
        """
        Initialize compiler launcher configuration.

        Args:
            cache_config: BuildCacheConfig with cache tool information

        Raises:
            ValueError: If cache_config is None or invalid
        """
        if cache_config is None:
            raise ValueError("cache_config cannot be None")
        if (
            not cache_config.executable_path
            or not cache_config.executable_path.exists()
        ):
            raise ValueError(
                f"Cache executable not found: {cache_config.executable_path}"
            )

        self.cache_config = cache_config
        logger.info(
            f"Initialized CompilerLauncherConfig with {cache_config.tool} "
            f"at {cache_config.executable_path}"
        )

    def get_cmake_variables(self) -> Dict[str, str]:
        """
        Get CMake variables for compiler launcher configuration.

        Returns CMAKE_C_COMPILER_LAUNCHER and CMAKE_CXX_COMPILER_LAUNCHER
        pointing to the cache tool executable.

        Returns:
            Dictionary of CMake variable names to values

        Example:
            >>> launcher = CompilerLauncherConfig(cache_config)
            >>> vars = launcher.get_cmake_variables()
            >>> print(vars['CMAKE_C_COMPILER_LAUNCHER'])
            /path/to/sccache
        """
        executable_str = str(self.cache_config.executable_path).replace("\\", "/")

        cmake_vars = {
            "CMAKE_C_COMPILER_LAUNCHER": executable_str,
            "CMAKE_CXX_COMPILER_LAUNCHER": executable_str,
        }

        logger.debug(f"Generated CMake variables: {cmake_vars}")
        return cmake_vars

    def configure_environment(self) -> Dict[str, str]:
        """
        Configure environment variables for the cache tool.

        Returns tool-specific environment variables for:
        - sccache: SCCACHE_DIR, SCCACHE_CACHE_SIZE
        - ccache: CCACHE_DIR, CCACHE_MAXSIZE

        Returns:
            Dictionary of environment variable names to values

        Example:
            >>> launcher = CompilerLauncherConfig(cache_config)
            >>> env = launcher.configure_environment()
            >>> print(env['SCCACHE_DIR'])
            /path/to/cache/sccache
        """
        env_vars = {}

        if self.cache_config.tool == "sccache":
            env_vars["SCCACHE_DIR"] = str(self.cache_config.cache_dir)
            if self.cache_config.max_size:
                env_vars["SCCACHE_CACHE_SIZE"] = self.cache_config.max_size

            logger.debug(f"Configured sccache environment: {env_vars}")

        elif self.cache_config.tool == "ccache":
            env_vars["CCACHE_DIR"] = str(self.cache_config.cache_dir)
            if self.cache_config.max_size:
                env_vars["CCACHE_MAXSIZE"] = self.cache_config.max_size

            logger.debug(f"Configured ccache environment: {env_vars}")

        return env_vars

    def get_stats(self) -> Optional[CacheStats]:
        """
        Get cache statistics from the cache tool.

        Executes the cache tool's statistics command and parses the output:
        - sccache: `sccache --show-stats`
        - ccache: `ccache --show-stats`

        Returns:
            CacheStats object with statistics, or None if unavailable

        Example:
            >>> launcher = CompilerLauncherConfig(cache_config)
            >>> stats = launcher.get_stats()
            >>> if stats:
            ...     print(f"Hit rate: {stats.hit_rate:.1f}%")
        """
        try:
            if self.cache_config.tool == "sccache":
                return self._get_sccache_stats()
            elif self.cache_config.tool == "ccache":
                return self._get_ccache_stats()
            else:
                logger.warning(f"Unknown cache tool: {self.cache_config.tool}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting stats from {self.cache_config.tool}")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get stats: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting stats: {e}", exc_info=True)
            return None

    def _get_sccache_stats(self) -> CacheStats:
        """
        Parse sccache --show-stats output.

        Example output:
            Compile requests                      524
            Compile requests executed             120
            Cache hits                            404
            Cache misses                          120
            Cache errors                            0

        Returns:
            CacheStats object with parsed statistics
        """
        result = subprocess.run(
            [str(self.cache_config.executable_path), "--show-stats"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse key-value pairs
        stats_dict = {}
        for line in result.stdout.split("\n"):
            # Match "Key    value" format
            match = re.match(r"^(.+?)\s{2,}(\d+)", line)
            if match:
                key = match.group(1).strip()
                value = int(match.group(2))
                stats_dict[key] = value

        # Extract statistics
        hits = stats_dict.get("Cache hits", 0)
        misses = stats_dict.get("Cache misses", 0)
        errors = stats_dict.get("Cache errors", 0)

        # Calculate hit rate
        total = hits + misses
        hit_rate = (hits / total * 100.0) if total > 0 else 0.0

        cache_stats = CacheStats(
            hits=hits,
            misses=misses,
            errors=errors,
            cache_size=0,  # sccache doesn't report cache size in stats
            hit_rate=hit_rate,
        )

        logger.debug(f"Parsed sccache stats: {cache_stats}")
        return cache_stats

    def _get_ccache_stats(self) -> CacheStats:
        """
        Parse ccache --show-stats output.

        Example output:
            Cacheable calls:    256 / 320 (80.00%)
              Hits:             200 / 256 (78.12%)
                Direct:         180 / 200 (90.00%)
                Preprocessed:    20 / 200 (10.00%)
              Misses:            56 / 256 (21.88%)
            Uncacheable calls:   64 / 320 (20.00%)

        Returns:
            CacheStats object with parsed statistics
        """
        result = subprocess.run(
            [str(self.cache_config.executable_path), "--show-stats"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        hits = 0
        misses = 0
        cache_size = 0

        # Parse ccache output
        for line in result.stdout.split("\n"):
            line = line.strip()

            # Match "Hits:  200 / 256 (78.12%)"
            if line.startswith("Hits:"):
                match = re.search(r"(\d+)\s*/\s*\d+", line)
                if match:
                    hits = int(match.group(1))

            # Match "Misses:  56 / 256 (21.88%)"
            elif line.startswith("Misses:"):
                match = re.search(r"(\d+)\s*/\s*\d+", line)
                if match:
                    misses = int(match.group(1))

            # Match "Cache size (GB): 1.2 / 10.0"
            elif "Cache size" in line:
                match = re.search(r"([\d.]+)\s*/\s*[\d.]+", line)
                if match:
                    # Convert GB to bytes (approximate)
                    cache_size = int(float(match.group(1)) * 1024 * 1024 * 1024)

        # Calculate hit rate
        total = hits + misses
        hit_rate = (hits / total * 100.0) if total > 0 else 0.0

        cache_stats = CacheStats(
            hits=hits,
            misses=misses,
            errors=0,  # ccache doesn't report errors in stats
            cache_size=cache_size,
            hit_rate=hit_rate,
        )

        logger.debug(f"Parsed ccache stats: {cache_stats}")
        return cache_stats

    def clear_cache(self) -> bool:
        """
        Clear the cache data.

        Executes the cache tool's clear command:
        - sccache: `sccache --zero-stats` (clears statistics only)
        - ccache: `ccache --clear` (clears cache data)

        Returns:
            True if cache cleared successfully, False otherwise

        Example:
            >>> launcher = CompilerLauncherConfig(cache_config)
            >>> if launcher.clear_cache():
            ...     print("Cache cleared")
        """
        try:
            if self.cache_config.tool == "sccache":
                # sccache only clears stats, not cache data
                subprocess.run(
                    [str(self.cache_config.executable_path), "--zero-stats"],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
                logger.info("Cleared sccache statistics")
                return True

            elif self.cache_config.tool == "ccache":
                subprocess.run(
                    [str(self.cache_config.executable_path), "--clear"],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
                logger.info("Cleared ccache data")
                return True

            else:
                logger.warning(f"Unknown cache tool: {self.cache_config.tool}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout clearing cache for {self.cache_config.tool}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing cache: {e}", exc_info=True)
            return False

    def generate_cmake_snippet(self) -> str:
        """
        Generate CMake configuration snippet for toolchain files.

        Generates commented CMake code that sets CMAKE_*_COMPILER_LAUNCHER
        variables and includes configuration information.

        Returns:
            Multi-line string with CMake code

        Example:
            >>> launcher = CompilerLauncherConfig(cache_config)
            >>> print(launcher.generate_cmake_snippet())
            # Compiler Launcher: sccache 0.7.4
            set(CMAKE_C_COMPILER_LAUNCHER "/path/to/sccache")
            set(CMAKE_CXX_COMPILER_LAUNCHER "/path/to/sccache")
            ...
        """
        # Format paths for CMake (use forward slashes)
        executable_path = str(self.cache_config.executable_path).replace("\\", "/")
        cache_dir = str(self.cache_config.cache_dir).replace("\\", "/")

        # Build version string
        version_str = (
            self.cache_config.version if self.cache_config.version else "unknown"
        )

        # Generate CMake snippet
        lines = [
            f"# Compiler Launcher: {self.cache_config.tool} {version_str}",
            f'set(CMAKE_C_COMPILER_LAUNCHER "{executable_path}")',
            f'set(CMAKE_CXX_COMPILER_LAUNCHER "{executable_path}")',
            "",
            "# Cache configuration",
            f"# Cache directory: {cache_dir}",
        ]

        if self.cache_config.max_size:
            lines.append(f"# Max size: {self.cache_config.max_size}")

        lines.extend(
            [
                "",
                "# To view statistics:",
                f"#   {executable_path} --show-stats",
            ]
        )

        snippet = "\n".join(lines)
        logger.debug(f"Generated CMake snippet:\n{snippet}")
        return snippet
