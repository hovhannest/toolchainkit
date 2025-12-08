"""
Build cache detection and installation.

This module provides automated detection and installation of build cache tools
(sccache, ccache) to accelerate C++ compilation through result caching.

Features:
- Automatic detection of sccache/ccache on system PATH
- Installation of sccache from GitHub releases if not found
- Platform-specific binary selection (Windows, Linux, macOS)
- Version detection and validation
- Cache directory setup and configuration

Usage:
    from toolchainkit.caching.detection import BuildCacheManager
    from pathlib import Path

    # Initialize manager
    manager = BuildCacheManager(project_root=Path.cwd())

    # Get or install cache tool
    config = manager.get_or_install(prefer='sccache')

    if config:
        print(f"Cache tool: {config.tool} {config.version}")
        print(f"Executable: {config.executable_path}")
        print(f"Cache dir: {config.cache_dir}")
"""

import os
import shutil
import subprocess
import tarfile
import zipfile
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from ..core.download import download_file
from ..core.filesystem import safe_rmtree
from ..core.platform import detect_platform, PlatformInfo


logger = logging.getLogger(__name__)


@dataclass
class BuildCacheConfig:
    """
    Configuration for build cache tool.

    Attributes:
        tool: Cache tool name ('sccache' or 'ccache')
        executable_path: Path to cache tool executable
        cache_dir: Directory for cached compilation results
        max_size: Maximum cache size (e.g., '10G', '50G')
        enabled: Whether caching is enabled
        version: Detected version of the tool (if available)

    Example:
        >>> config = BuildCacheConfig(
        ...     tool='sccache',
        ...     executable_path=Path('/usr/bin/sccache'),
        ...     cache_dir=Path('/tmp/cache'),
        ...     max_size='10G',
        ...     enabled=True,
        ...     version='0.7.4'
        ... )
    """

    tool: str
    executable_path: Path
    cache_dir: Path
    max_size: str = "10G"
    enabled: bool = True
    version: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.tool not in ("sccache", "ccache"):
            raise ValueError(
                f"Invalid cache tool: {self.tool}. Must be 'sccache' or 'ccache'."
            )

        if not isinstance(self.executable_path, Path):
            self.executable_path = Path(self.executable_path)

        if not isinstance(self.cache_dir, Path):
            self.cache_dir = Path(self.cache_dir)


class BuildCacheDetector:
    """
    Detect installed build cache tools.

    This class searches for sccache and ccache in standard locations:
    1. System PATH
    2. Local tools directory (~/.toolchainkit/tools/)
    3. Standard installation directories

    Example:
        >>> from toolchainkit.core.platform import detect_platform
        >>> detector = BuildCacheDetector(detect_platform())
        >>> sccache = detector.detect_sccache()
        >>> if sccache:
        ...     print(f"Found sccache at: {sccache}")
    """

    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        """
        Initialize detector.

        Args:
            platform_info: Platform information. If None, auto-detect.
        """
        self.platform = platform_info or detect_platform()

    def detect_sccache(self) -> Optional[Path]:
        """
        Detect sccache installation.

        Search order:
        1. sccache on PATH (using shutil.which)
        2. ~/.toolchainkit/tools/sccache[.exe]
        3. Standard system locations

        Returns:
            Path to sccache executable, or None if not found

        Example:
            >>> detector = BuildCacheDetector()
            >>> path = detector.detect_sccache()
            >>> if path:
            ...     print(f"sccache found: {path}")
        """
        # Check PATH
        exe_name = "sccache.exe" if self.platform.os == "windows" else "sccache"
        sccache_path = shutil.which("sccache")
        if sccache_path:
            logger.info(f"Found sccache on PATH: {sccache_path}")
            return Path(sccache_path)

        # Check local tools directory
        tools_dir = Path.home() / ".toolchainkit" / "tools"
        local_sccache = tools_dir / exe_name

        if local_sccache.exists() and os.access(local_sccache, os.X_OK):
            logger.info(f"Found sccache in local tools: {local_sccache}")
            return local_sccache

        # Check standard locations (Unix-like systems)
        if self.platform.os in ("linux", "macos"):
            standard_locations = [
                Path("/usr/local/bin") / "sccache",
                Path("/usr/bin") / "sccache",
                Path("/opt/local/bin") / "sccache",  # MacPorts
                Path("/opt/homebrew/bin") / "sccache",  # Homebrew (ARM Mac)
            ]

            for location in standard_locations:
                if location.exists() and os.access(location, os.X_OK):
                    logger.info(f"Found sccache in standard location: {location}")
                    return location

        logger.debug("sccache not found")
        return None

    def detect_ccache(self) -> Optional[Path]:
        """
        Detect ccache installation.

        Search order:
        1. ccache on PATH (using shutil.which)
        2. ~/.toolchainkit/tools/ccache[.exe]
        3. Standard system locations

        Returns:
            Path to ccache executable, or None if not found

        Example:
            >>> detector = BuildCacheDetector()
            >>> path = detector.detect_ccache()
            >>> if path:
            ...     print(f"ccache found: {path}")
        """
        # Check PATH
        exe_name = "ccache.exe" if self.platform.os == "windows" else "ccache"
        ccache_path = shutil.which("ccache")
        if ccache_path:
            logger.info(f"Found ccache on PATH: {ccache_path}")
            return Path(ccache_path)

        # Check local tools directory
        tools_dir = Path.home() / ".toolchainkit" / "tools"
        local_ccache = tools_dir / exe_name

        if local_ccache.exists() and os.access(local_ccache, os.X_OK):
            logger.info(f"Found ccache in local tools: {local_ccache}")
            return local_ccache

        # Check standard locations (Unix-like systems)
        if self.platform.os in ("linux", "macos"):
            standard_locations = [
                Path("/usr/local/bin") / "ccache",
                Path("/usr/bin") / "ccache",
                Path("/opt/local/bin") / "ccache",  # MacPorts
                Path("/opt/homebrew/bin") / "ccache",  # Homebrew (ARM Mac)
            ]

            for location in standard_locations:
                if location.exists() and os.access(location, os.X_OK):
                    logger.info(f"Found ccache in standard location: {location}")
                    return location

        logger.debug("ccache not found")
        return None

    def detect_best(self) -> Optional[Tuple[str, Path]]:
        """
        Detect best available cache tool.

        Preference order: sccache > ccache
        (sccache has better cross-platform support, especially on Windows)

        Returns:
            Tuple of (tool_name, path) or None if no cache tool found

        Example:
            >>> detector = BuildCacheDetector()
            >>> result = detector.detect_best()
            >>> if result:
            ...     tool, path = result
            ...     print(f"Best tool: {tool} at {path}")
        """
        # Try sccache first (preferred)
        sccache = self.detect_sccache()
        if sccache:
            logger.info(f"Best cache tool: sccache at {sccache}")
            return ("sccache", sccache)

        # Fall back to ccache
        ccache = self.detect_ccache()
        if ccache:
            logger.info(f"Best cache tool: ccache at {ccache}")
            return ("ccache", ccache)

        logger.debug("No cache tool found")
        return None

    def get_version(self, tool_path: Path) -> Optional[str]:
        """
        Get version of cache tool.

        Args:
            tool_path: Path to cache tool executable

        Returns:
            Version string (e.g., '0.7.4') or None if detection fails

        Example:
            >>> detector = BuildCacheDetector()
            >>> path = detector.detect_sccache()
            >>> if path:
            ...     version = detector.get_version(path)
            ...     print(f"Version: {version}")
        """
        try:
            result = subprocess.run(
                [str(tool_path), "--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                # Parse version from output
                # sccache output: "sccache 0.7.4"
                # ccache output: "ccache version 4.8.3"
                first_line = result.stdout.split("\n")[0]

                # Extract version number using regex
                import re

                match = re.search(r"(\d+\.\d+\.\d+)", first_line)
                if match:
                    version = match.group(1)
                    logger.debug(f"Detected version: {version}")
                    return version

            logger.debug(f"Failed to parse version from: {result.stdout}")
            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"Version check timed out for {tool_path}")
            return None
        except Exception as e:
            logger.debug(f"Failed to get version: {e}")
            return None


class BuildCacheInstaller:
    """
    Download and install build cache tools.

    Currently supports:
    - sccache: Download from GitHub releases
    - ccache: Must be installed via system package manager

    Example:
        >>> from toolchainkit.core.platform import detect_platform
        >>> installer = BuildCacheInstaller(detect_platform())
        >>> sccache_path = installer.install_sccache(version='0.7.4')
        >>> print(f"Installed sccache to: {sccache_path}")
    """

    # sccache release URLs from GitHub
    # https://github.com/mozilla/sccache/releases
    SCCACHE_RELEASES = {
        "linux-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-unknown-linux-musl.tar.gz",
        "macos-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-apple-darwin.tar.gz",
        "macos-arm64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-aarch64-apple-darwin.tar.gz",
        "windows-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-pc-windows-msvc.zip",
    }

    # Latest stable version as of November 2025
    SCCACHE_DEFAULT_VERSION = "0.7.4"

    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        """
        Initialize installer.

        Args:
            platform_info: Platform information. If None, auto-detect.
        """
        self.platform = platform_info or detect_platform()
        self.tools_dir = Path.home() / ".toolchainkit" / "tools"
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    def install_sccache(self, version: str = "latest") -> Path:
        """
        Download and install sccache.

        Args:
            version: Version to install ('latest' or specific version like '0.7.4')

        Returns:
            Path to installed sccache executable

        Raises:
            RuntimeError: If platform not supported or installation fails

        Example:
            >>> installer = BuildCacheInstaller()
            >>> path = installer.install_sccache(version='0.7.4')
            >>> print(f"Installed to: {path}")
        """
        if version == "latest":
            version = self.SCCACHE_DEFAULT_VERSION

        # Get download URL for platform
        url = self._get_sccache_url(version)
        if not url:
            raise RuntimeError(
                f"No sccache binary available for {self.platform.platform_string()}. "
                f"Supported platforms: {', '.join(self.SCCACHE_RELEASES.keys())}"
            )

        logger.info(
            f"Installing sccache {version} for {self.platform.platform_string()}"
        )
        logger.info(f"Download URL: {url}")

        # Determine archive path based on URL extension
        if url.endswith(".tar.gz"):
            archive_path = self.tools_dir / f"sccache-{version}.tar.gz"
        elif url.endswith(".zip"):
            archive_path = self.tools_dir / f"sccache-{version}.zip"
        else:
            raise RuntimeError(f"Unsupported archive format in URL: {url}")

        # Download archive
        try:
            logger.info(f"Downloading to: {archive_path}")
            download_file(url, archive_path)
            logger.info("Download complete")
        except Exception as e:
            raise RuntimeError(f"Failed to download sccache: {e}") from e

        # Extract archive
        extract_dir = self.tools_dir / f"sccache-{version}-temp"
        extract_dir.mkdir(exist_ok=True)

        try:
            logger.info(f"Extracting to: {extract_dir}")
            if url.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
            elif url.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_file:
                    zip_file.extractall(extract_dir)

            logger.info("Extraction complete")
        except Exception as e:
            safe_rmtree(extract_dir, require_prefix=self.tools_dir)
            raise RuntimeError(f"Failed to extract sccache archive: {e}") from e

        # Find sccache executable in extracted files
        exe_name = "sccache.exe" if self.platform.os == "windows" else "sccache"
        sccache_exe = None

        for item in extract_dir.rglob("sccache*"):
            if item.is_file() and item.name == exe_name:
                sccache_exe = item
                break

        if not sccache_exe:
            # Try without exact name match (in case of different naming)
            for item in extract_dir.rglob("*"):
                if item.is_file() and "sccache" in item.name.lower():
                    if self.platform.os == "windows" and item.name.endswith(".exe"):
                        sccache_exe = item
                        break
                    elif self.platform.os != "windows" and not item.name.endswith(
                        ".exe"
                    ):
                        # Check if executable on Unix
                        if os.access(item, os.X_OK):
                            sccache_exe = item
                            break

        if not sccache_exe:
            safe_rmtree(extract_dir, require_prefix=self.tools_dir)
            raise RuntimeError(
                f"sccache executable not found in archive. "
                f"Expected to find '{exe_name}' in extracted files."
            )

        # Move to tools directory
        target_path = self.tools_dir / exe_name

        # Remove existing if present
        if target_path.exists():
            logger.info(f"Removing existing installation: {target_path}")
            target_path.unlink()

        logger.info(f"Installing to: {target_path}")
        shutil.move(str(sccache_exe), str(target_path))

        # Set executable permissions (Unix-like systems)
        if self.platform.os in ("linux", "macos"):
            os.chmod(target_path, 0o755)
            logger.debug(f"Set executable permissions: {target_path}")

        # Cleanup
        logger.info("Cleaning up temporary files")
        safe_rmtree(extract_dir, require_prefix=self.tools_dir)
        archive_path.unlink()

        logger.info(f"Successfully installed sccache to: {target_path}")
        return target_path

    def install_ccache(self, version: str = "latest") -> Path:
        """
        Install ccache.

        Note: ccache is typically installed via system package manager.
        Direct binary installation is not currently supported.

        Args:
            version: Version to install (ignored)

        Raises:
            NotImplementedError: Always raised - use package manager

        Example:
            On Ubuntu/Debian: sudo apt-get install ccache
            On Fedora/RHEL: sudo dnf install ccache
            On macOS: brew install ccache
        """
        logger.error("ccache installation not implemented - use system package manager")

        # Provide platform-specific instructions
        if self.platform.os == "linux":
            if (
                "ubuntu" in self.platform.distribution.lower()
                or "debian" in self.platform.distribution.lower()
            ):
                instruction = "sudo apt-get install ccache"
            elif (
                "fedora" in self.platform.distribution.lower()
                or "centos" in self.platform.distribution.lower()
            ):
                instruction = "sudo dnf install ccache"
            elif "arch" in self.platform.distribution.lower():
                instruction = "sudo pacman -S ccache"
            else:
                instruction = (
                    "Use your distribution's package manager to install ccache"
                )
        elif self.platform.os == "macos":
            instruction = "brew install ccache"
        elif self.platform.os == "windows":
            instruction = "Install ccache via Chocolatey: choco install ccache"
        else:
            instruction = "Use your system's package manager to install ccache"

        raise NotImplementedError(
            f"ccache must be installed via package manager. "
            f"Recommendation for {self.platform.platform_string()}: {instruction}"
        )

    def _get_sccache_url(self, version: str) -> Optional[str]:
        """
        Get download URL for sccache binary.

        Args:
            version: sccache version to download

        Returns:
            Download URL or None if platform not supported
        """
        try:
            platform_key = self._get_platform_key()
        except RuntimeError:
            # Platform not supported
            return None

        url_template = self.SCCACHE_RELEASES.get(platform_key)
        if not url_template:
            logger.warning(f"No sccache binary available for platform: {platform_key}")
            return None

        return url_template.format(version=version)

    def _get_platform_key(self) -> str:
        """
        Get platform key for download URL lookup.

        Returns:
            Platform key (e.g., 'linux-x64', 'macos-arm64')

        Raises:
            RuntimeError: If platform not supported
        """
        os_name = self.platform.os
        arch = self.platform.arch

        if os_name == "linux" and arch == "x64":
            return "linux-x64"
        elif os_name == "macos" and arch == "x64":
            return "macos-x64"
        elif os_name == "macos" and arch == "arm64":
            return "macos-arm64"
        elif os_name == "windows" and arch == "x64":
            return "windows-x64"
        else:
            raise RuntimeError(
                f"Unsupported platform: {os_name}-{arch}. "
                f"Supported: {', '.join(self.SCCACHE_RELEASES.keys())}"
            )


class BuildCacheManager:
    """
    High-level build cache management.

    Orchestrates detection and installation to provide a simple interface
    for getting build cache configuration.

    Example:
        >>> from pathlib import Path
        >>> manager = BuildCacheManager(project_root=Path.cwd())
        >>> config = manager.get_or_install(prefer='sccache')
        >>> if config:
        ...     print(f"Cache configured: {config.tool} at {config.executable_path}")
        ...     print(f"Cache directory: {config.cache_dir}")
    """

    def __init__(
        self,
        project_root: Path,
        platform_info: Optional[PlatformInfo] = None,
        tools_dir: Optional[Path] = None,
    ):
        """
        Initialize cache manager.

        Args:
            project_root: Project root directory
            platform_info: Platform information. If None, auto-detect.
            tools_dir: Tools directory for downloaded tools. If None, use default.
        """
        self.project_root = Path(project_root)
        self.platform = platform_info or detect_platform()
        self.tools_dir = tools_dir or (Path.home() / ".toolchainkit" / "tools")
        self.detector = BuildCacheDetector(self.platform)
        # Keep old installer for backward compatibility
        self.installer = BuildCacheInstaller(self.platform)

    def get_or_install(self, prefer: str = "sccache") -> Optional[BuildCacheConfig]:
        """
        Get existing cache tool or install if needed.

        Args:
            prefer: Preferred tool ('sccache' or 'ccache')

        Returns:
            BuildCacheConfig with tool configuration, or None if unavailable

        Example:
            >>> manager = BuildCacheManager(Path.cwd())
            >>> config = manager.get_or_install(prefer='sccache')
            >>> if config:
            ...     print(f"Using {config.tool} {config.version}")
        """
        if prefer not in ("sccache", "ccache"):
            logger.warning(f"Invalid preference '{prefer}', defaulting to 'sccache'")
            prefer = "sccache"

        # Try to detect existing tools
        logger.info(f"Searching for build cache tools (prefer: {prefer})")
        tool_info = self.detector.detect_best()

        if tool_info:
            tool_name, tool_path = tool_info
            logger.info(f"Found existing cache tool: {tool_name} at {tool_path}")
            return self._create_config(tool_name, tool_path)

        # No existing tool found, try to install preferred tool
        logger.info(f"No cache tool found, attempting to install {prefer}")

        if prefer == "sccache":
            try:
                # Use unified SccacheDownloader from tool_downloader.py
                from ..packages.tool_downloader import SccacheDownloader

                downloader = SccacheDownloader(self.tools_dir, platform=self.platform)

                if not downloader.is_installed():
                    logger.info("Downloading sccache...")
                    downloader.download()

                tool_path = downloader.get_executable_path()
                if tool_path:
                    logger.info(f"Successfully installed sccache to: {tool_path}")
                    return self._create_config("sccache", tool_path)
                else:
                    raise RuntimeError("sccache installation verification failed")

            except Exception as e:
                logger.error(f"Failed to install sccache: {e}")
                logger.info("Build caching will not be available")
                return None
        elif prefer == "ccache":
            logger.warning(
                "ccache must be installed via system package manager. "
                "Build caching will not be available."
            )
            return None

        return None

    def _create_config(self, tool_name: str, tool_path: Path) -> BuildCacheConfig:
        """
        Create cache configuration.

        Args:
            tool_name: Name of cache tool ('sccache' or 'ccache')
            tool_path: Path to cache tool executable

        Returns:
            BuildCacheConfig with tool configuration
        """
        # Cache directory in project-local .toolchainkit
        cache_dir = self.project_root / ".toolchainkit" / "cache" / tool_name
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Detect version
        version = self.detector.get_version(tool_path)

        config = BuildCacheConfig(
            tool=tool_name,
            executable_path=tool_path,
            cache_dir=cache_dir,
            max_size="10G",
            enabled=True,
            version=version,
        )

        logger.info(f"Created cache configuration: {tool_name} {version or 'unknown'}")
        logger.info(f"  Executable: {tool_path}")
        logger.info(f"  Cache dir: {cache_dir}")
        logger.info(f"  Max size: {config.max_size}")

        return config
