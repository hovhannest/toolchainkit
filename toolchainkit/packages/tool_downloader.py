"""
Package manager tool downloader.

Downloads and manages package manager tools (Conan, vcpkg) as part of the toolchain.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from toolchainkit.core.filesystem import safe_rmtree
from toolchainkit.core.platform import PlatformInfo, detect_platform

logger = logging.getLogger(__name__)


class ToolDownloadError(Exception):
    """Error downloading or installing a tool."""

    pass


@dataclass
class ToolMetadata:
    """Metadata for a downloadable tool."""

    name: str
    version: str
    url: str
    sha256: Optional[str] = None
    install_script: Optional[str] = None  # Post-install script


class ConanDownloader:
    """
    Download and install Conan package manager.

    Conan is a Python package, so this downloads Python packages or
    uses pip to install Conan in an isolated environment.
    """

    def __init__(self, tools_dir: Path, platform: Optional[PlatformInfo] = None):
        """
        Initialize Conan downloader.

        Args:
            tools_dir: Directory to install tools into
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = Path(tools_dir)
        self.platform = platform or detect_platform()
        self.conan_dir = self.tools_dir / "conan"

    def download(
        self,
        version: str = "2.0",
        force: bool = False,
        use_hermetic_python: bool = False,
    ) -> Path:
        """
        Download and install Conan.

        Since Conan is a Python package, this uses pip to install it
        in an isolated virtual environment within the tools directory.

        Args:
            version: Conan version to install (e.g., "2.0", "2.0.13")
            force: Force re-download even if already installed
            use_hermetic_python: Use downloaded Python instead of system Python

        Returns:
            Path to Conan installation directory

        Raises:
            ToolDownloadError: If download/installation fails
        """
        if self.conan_dir.exists() and not force:
            logger.info(f"Conan already installed at {self.conan_dir}")
            return self.conan_dir

        logger.info(f"Installing Conan {version} to {self.conan_dir}")

        try:
            # Create tools directory
            self.tools_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing installation if forcing
            if force and self.conan_dir.exists():
                safe_rmtree(self.conan_dir, require_prefix=self.tools_dir)

            # Determine Python executable
            python_exe: str
            if use_hermetic_python:
                logger.info("Using hermetic Python for Conan")
                python_downloader = PythonDownloader(
                    self.tools_dir, platform=self.platform
                )
                if not python_downloader.is_installed():
                    logger.info("Downloading hermetic Python first")
                    python_downloader.download()
                hermetic_python = python_downloader.get_executable_path()
                if not hermetic_python:
                    raise ToolDownloadError("Failed to get hermetic Python executable")
                python_exe = str(hermetic_python)
            else:
                python_exe = "python"

            # Create virtual environment for Conan
            venv_path = self.conan_dir / "venv"
            logger.debug(f"Creating virtual environment at {venv_path}")

            result = subprocess.run(
                [str(python_exe), "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise ToolDownloadError(
                    f"Failed to create virtual environment: {result.stderr}"
                )

            # Determine pip executable path
            if self.platform.os == "windows":
                pip_exe = venv_path / "Scripts" / "pip.exe"
                conan_exe = venv_path / "Scripts" / "conan.exe"
            else:
                pip_exe = venv_path / "bin" / "pip"
                conan_exe = venv_path / "bin" / "conan"

            # Install Conan in the virtual environment
            logger.debug(f"Installing Conan {version} via pip")

            # Determine version specifier
            if version == "2.0" or version == "2":
                version_spec = "conan>=2.0,<3.0"
            else:
                version_spec = f"conan=={version}"

            result = subprocess.run(
                [str(pip_exe), "install", version_spec],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise ToolDownloadError(f"Failed to install Conan: {result.stderr}")

            # Verify installation
            if not conan_exe.exists():
                raise ToolDownloadError(
                    f"Conan executable not found after installation: {conan_exe}"
                )

            logger.info(f"Successfully installed Conan at {self.conan_dir}")
            return self.conan_dir

        except subprocess.TimeoutExpired as e:
            raise ToolDownloadError(f"Installation timed out: {e}") from e
        except Exception as e:
            # Cleanup on error
            if self.conan_dir.exists():
                try:
                    safe_rmtree(self.conan_dir, require_prefix=self.tools_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup after error: {cleanup_error}")
            raise ToolDownloadError(f"Failed to install Conan: {e}") from e

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to Conan executable.

        Returns:
            Path to conan executable, or None if not installed
        """
        if not self.conan_dir.exists():
            return None

        if self.platform.os == "windows":
            conan_exe = self.conan_dir / "venv" / "Scripts" / "conan.exe"
        else:
            conan_exe = self.conan_dir / "venv" / "bin" / "conan"

        return conan_exe if conan_exe.exists() else None

    def is_installed(self) -> bool:
        """
        Check if Conan is installed.

        Returns:
            True if Conan is installed in tools directory
        """
        exe = self.get_executable_path()
        return exe is not None and exe.exists()


class VcpkgDownloader:
    """
    Download and install vcpkg package manager.

    vcpkg is distributed as a Git repository with a bootstrap script.
    """

    def __init__(self, tools_dir: Path, platform: Optional[PlatformInfo] = None):
        """
        Initialize vcpkg downloader.

        Args:
            tools_dir: Directory to install tools into
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = Path(tools_dir)
        self.platform = platform or detect_platform()
        self.vcpkg_dir = self.tools_dir / "vcpkg"

    def download(self, version: str = "latest", force: bool = False) -> Path:
        """
        Download and bootstrap vcpkg.

        Args:
            version: vcpkg version/tag to install (e.g., "2024.10.21", "latest")
            force: Force re-download even if already installed

        Returns:
            Path to vcpkg installation directory

        Raises:
            ToolDownloadError: If download/installation fails
        """
        if self.vcpkg_dir.exists() and not force:
            logger.info(f"vcpkg already installed at {self.vcpkg_dir}")
            return self.vcpkg_dir

        logger.info(f"Installing vcpkg to {self.vcpkg_dir}")

        try:
            # Create tools directory
            self.tools_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing installation if forcing
            if force and self.vcpkg_dir.exists():
                safe_rmtree(self.vcpkg_dir, require_prefix=self.tools_dir)

            # Clone vcpkg repository
            logger.debug("Cloning vcpkg repository")

            git_cmd = ["git", "clone", "https://github.com/microsoft/vcpkg.git"]

            if version != "latest":
                git_cmd.extend(["--branch", version])

            git_cmd.append(str(self.vcpkg_dir))

            result = subprocess.run(
                git_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.tools_dir,
            )

            if result.returncode != 0:
                raise ToolDownloadError(f"Failed to clone vcpkg: {result.stderr}")

            # Bootstrap vcpkg
            logger.debug("Bootstrapping vcpkg")

            if self.platform.os == "windows":
                bootstrap_script = self.vcpkg_dir / "bootstrap-vcpkg.bat"
            else:
                bootstrap_script = self.vcpkg_dir / "bootstrap-vcpkg.sh"

            if not bootstrap_script.exists():
                raise ToolDownloadError(
                    f"Bootstrap script not found: {bootstrap_script}"
                )

            # Make executable on Unix
            if self.platform.os != "windows":
                bootstrap_script.chmod(0o755)

            result = subprocess.run(
                [str(bootstrap_script)],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=self.vcpkg_dir,
            )

            if result.returncode != 0:
                raise ToolDownloadError(f"Failed to bootstrap vcpkg: {result.stderr}")

            logger.info(f"Successfully installed vcpkg at {self.vcpkg_dir}")
            return self.vcpkg_dir

        except subprocess.TimeoutExpired as e:
            raise ToolDownloadError(f"Installation timed out: {e}") from e
        except Exception as e:
            # Cleanup on error
            if self.vcpkg_dir.exists():
                try:
                    safe_rmtree(self.vcpkg_dir, require_prefix=self.tools_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup after error: {cleanup_error}")
            raise ToolDownloadError(f"Failed to install vcpkg: {e}") from e

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to vcpkg executable.

        Returns:
            Path to vcpkg executable, or None if not installed
        """
        if not self.vcpkg_dir.exists():
            return None

        if self.platform.os == "windows":
            vcpkg_exe = self.vcpkg_dir / "vcpkg.exe"
        else:
            vcpkg_exe = self.vcpkg_dir / "vcpkg"

        return vcpkg_exe if vcpkg_exe.exists() else None

    def is_installed(self) -> bool:
        """
        Check if vcpkg is installed.

        Returns:
            True if vcpkg is installed in tools directory
        """
        exe = self.get_executable_path()
        return exe is not None and exe.exists()


def get_system_conan_path() -> Optional[Path]:
    """
    Get path to system-installed Conan.

    Returns:
        Path to system conan executable, or None if not found
    """
    conan_path = shutil.which("conan")
    return Path(conan_path) if conan_path else None


def get_system_vcpkg_path() -> Optional[Path]:
    """
    Get path to system-installed vcpkg.

    Returns:
        Path to system vcpkg executable, or None if not found
    """
    vcpkg_path = shutil.which("vcpkg")
    return Path(vcpkg_path) if vcpkg_path else None


class CMakeDownloader:
    """
    Download and install CMake build system generator.

    Downloads pre-built CMake binaries from GitHub releases.
    """

    def __init__(
        self,
        tools_dir: Path,
        version: str = "3.28.1",
        platform: Optional[PlatformInfo] = None,
    ):
        """
        Initialize CMake downloader.

        Args:
            tools_dir: Directory to install tools into
            version: CMake version to download
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = tools_dir
        self.version = version
        self.platform = platform or detect_platform()
        self.install_dir = tools_dir / "cmake" / version

    def is_installed(self) -> bool:
        """
        Check if CMake is already installed.

        Returns:
            True if CMake executable exists, False otherwise
        """
        cmake_exe = self.get_executable_path()
        return cmake_exe.exists() if cmake_exe else False

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to CMake executable.

        Returns:
            Path to cmake executable if installed, None otherwise
        """
        if not self.install_dir.exists():
            return None

        # CMake structure varies by platform
        if self.platform.os == "windows":
            # cmake-3.28.1-windows-x86_64/bin/cmake.exe
            cmake_exe = self.install_dir / "bin" / "cmake.exe"
        else:
            # cmake-3.28.1-linux-x86_64/bin/cmake or cmake-3.28.1-macos-universal/CMake.app/Contents/bin/cmake
            cmake_exe = self.install_dir / "bin" / "cmake"
            if not cmake_exe.exists():
                # Try macOS .app bundle location
                cmake_exe = (
                    self.install_dir / "CMake.app" / "Contents" / "bin" / "cmake"
                )

        return cmake_exe if cmake_exe.exists() else None

    def download(self, force: bool = False) -> Path:
        """
        Download and install CMake.

        Args:
            force: If True, re-download even if already installed

        Returns:
            Path to CMake installation directory

        Raises:
            ToolDownloadError: If download or installation fails
        """
        if self.is_installed() and not force:
            logger.info(f"CMake {self.version} already installed at {self.install_dir}")
            return self.install_dir

        logger.info(f"Downloading CMake {self.version}...")

        try:
            # Determine download URL
            url = self._get_download_url()
            logger.debug(f"CMake download URL: {url}")

            # Download and extract
            from toolchainkit.core.download import download_file
            from toolchainkit.core.filesystem import extract_archive

            # Create temp download directory
            download_dir = self.tools_dir / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)

            # Download archive
            archive_name = url.split("/")[-1]
            archive_path = download_dir / archive_name

            download_file(url, archive_path)

            # Remove old installation if exists
            if self.install_dir.exists():
                safe_rmtree(self.install_dir)

            # Extract
            logger.info(f"Extracting CMake to {self.install_dir}...")
            extract_dir = self.tools_dir / "cmake"
            extract_dir.mkdir(parents=True, exist_ok=True)

            extract_archive(archive_path, extract_dir)

            # CMake archives contain a top-level directory, rename it
            extracted_dir = self._find_extracted_dir(extract_dir)
            if extracted_dir and extracted_dir != self.install_dir:
                extracted_dir.rename(self.install_dir)

            # Cleanup
            archive_path.unlink()

            # Verify installation
            if not self.is_installed():
                raise ToolDownloadError("CMake installation verification failed")

            logger.info(f"CMake {self.version} installed successfully")
            return self.install_dir

        except Exception as e:
            logger.error(f"Failed to download CMake: {e}")
            raise ToolDownloadError(f"CMake download failed: {e}") from e

    def _get_download_url(self) -> str:
        """
        Get CMake download URL for the current platform.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not supported
        """
        base_url = f"https://github.com/Kitware/CMake/releases/download/v{self.version}"

        if self.platform.os == "linux":
            if self.platform.arch in ("x86_64", "x64"):
                filename = f"cmake-{self.version}-linux-x86_64.tar.gz"
            elif self.platform.arch in ("aarch64", "arm64"):
                filename = f"cmake-{self.version}-linux-aarch64.tar.gz"
            else:
                raise ToolDownloadError(
                    f"Unsupported Linux architecture: {self.platform.arch}"
                )

        elif self.platform.os == "macos":
            # macOS universal binary
            filename = f"cmake-{self.version}-macos-universal.tar.gz"

        elif self.platform.os == "windows":
            if self.platform.arch in ("x86_64", "x64"):
                filename = f"cmake-{self.version}-windows-x86_64.zip"
            elif self.platform.arch == "arm64":
                filename = f"cmake-{self.version}-windows-arm64.zip"
            else:
                raise ToolDownloadError(
                    f"Unsupported Windows architecture: {self.platform.arch}"
                )

        else:
            raise ToolDownloadError(f"Unsupported OS: {self.platform.os}")

        return f"{base_url}/{filename}"

    def _find_extracted_dir(self, extract_dir: Path) -> Optional[Path]:
        """
        Find the extracted CMake directory.

        Args:
            extract_dir: Directory where archive was extracted

        Returns:
            Path to extracted directory, or None if not found
        """
        # Look for cmake-<version>-<platform> directory
        for item in extract_dir.iterdir():
            if item.is_dir() and item.name.startswith(f"cmake-{self.version}"):
                return item
        return None


class NinjaDownloader:
    """
    Download and install Ninja build system.

    Downloads pre-built Ninja binaries from GitHub releases.
    """

    def __init__(
        self,
        tools_dir: Path,
        version: str = "1.11.1",
        platform: Optional[PlatformInfo] = None,
    ):
        """
        Initialize Ninja downloader.

        Args:
            tools_dir: Directory to install tools into
            version: Ninja version to download
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = tools_dir
        self.version = version
        self.platform = platform or detect_platform()
        self.install_dir = tools_dir / "ninja" / version

    def is_installed(self) -> bool:
        """
        Check if Ninja is already installed.

        Returns:
            True if Ninja executable exists, False otherwise
        """
        ninja_exe = self.get_executable_path()
        return ninja_exe.exists() if ninja_exe else False

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to Ninja executable.

        Returns:
            Path to ninja executable if installed, None otherwise
        """
        if not self.install_dir.exists():
            return None

        if self.platform.os == "windows":
            ninja_exe = self.install_dir / "ninja.exe"
        else:
            ninja_exe = self.install_dir / "ninja"

        return ninja_exe if ninja_exe.exists() else None

    def download(self, force: bool = False) -> Path:
        """
        Download and install Ninja.

        Args:
            force: If True, re-download even if already installed

        Returns:
            Path to Ninja installation directory

        Raises:
            ToolDownloadError: If download or installation fails
        """
        if self.is_installed() and not force:
            logger.info(f"Ninja {self.version} already installed at {self.install_dir}")
            return self.install_dir

        logger.info(f"Downloading Ninja {self.version}...")

        try:
            # Determine download URL
            url = self._get_download_url()
            logger.debug(f"Ninja download URL: {url}")

            # Download and extract
            from toolchainkit.core.download import download_file
            from toolchainkit.core.filesystem import extract_archive

            # Create temp download directory
            download_dir = self.tools_dir / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)

            # Download archive
            archive_name = url.split("/")[-1]
            archive_path = download_dir / archive_name

            download_file(url, archive_path)

            # Remove old installation if exists
            if self.install_dir.exists():
                safe_rmtree(self.install_dir)

            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)

            # Extract (Ninja is just a single executable in a zip)
            logger.info(f"Extracting Ninja to {self.install_dir}...")
            extract_archive(archive_path, self.install_dir)

            # Cleanup
            archive_path.unlink()

            # Make executable on Unix-like systems
            if self.platform.os != "windows":
                ninja_exe = self.get_executable_path()
                if ninja_exe:
                    import os

                    os.chmod(ninja_exe, 0o755)

            # Verify installation
            if not self.is_installed():
                raise ToolDownloadError("Ninja installation verification failed")

            logger.info(f"Ninja {self.version} installed successfully")
            return self.install_dir

        except Exception as e:
            logger.error(f"Failed to download Ninja: {e}")
            raise ToolDownloadError(f"Ninja download failed: {e}") from e

    def _get_download_url(self) -> str:
        """
        Get Ninja download URL for the current platform.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not supported
        """
        base_url = (
            f"https://github.com/ninja-build/ninja/releases/download/v{self.version}"
        )

        if self.platform.os == "linux":
            filename = "ninja-linux.zip"
        elif self.platform.os == "macos":
            filename = "ninja-mac.zip"
        elif self.platform.os == "windows":
            filename = "ninja-win.zip"
        else:
            raise ToolDownloadError(f"Unsupported OS: {self.platform.os}")

        return f"{base_url}/{filename}"


def get_system_cmake_path() -> Optional[Path]:
    """
    Get path to system-installed CMake.

    Returns:
        Path to system cmake executable, or None if not found
    """
    cmake_path = shutil.which("cmake")
    return Path(cmake_path) if cmake_path else None


def get_system_ninja_path() -> Optional[Path]:
    """
    Get path to system-installed Ninja.

    Returns:
        Path to system ninja executable, or None if not found
    """
    ninja_path = shutil.which("ninja")
    return Path(ninja_path) if ninja_path else None


class SccacheDownloader:
    """
    Download and install sccache build cache tool.

    Downloads pre-built sccache binaries from GitHub releases.
    sccache is a compiler cache that supports distributed caching
    with S3, Redis, and other backends.
    """

    # sccache release URLs from GitHub
    # https://github.com/mozilla/sccache/releases
    SCCACHE_RELEASES = {
        "linux-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-unknown-linux-musl.tar.gz",
        "macos-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-apple-darwin.tar.gz",
        "macos-arm64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-aarch64-apple-darwin.tar.gz",
        "windows-x64": "https://github.com/mozilla/sccache/releases/download/v{version}/sccache-v{version}-x86_64-pc-windows-msvc.zip",
    }

    DEFAULT_VERSION = "0.7.4"

    def __init__(
        self,
        tools_dir: Path,
        version: str = "0.7.4",
        platform: Optional[PlatformInfo] = None,
    ):
        """
        Initialize sccache downloader.

        Args:
            tools_dir: Directory to install tools into
            version: sccache version to download
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = tools_dir
        self.version = version
        self.platform = platform or detect_platform()
        self.install_dir = tools_dir / "sccache" / version

    def is_installed(self) -> bool:
        """
        Check if sccache is already installed.

        Returns:
            True if sccache executable exists, False otherwise
        """
        sccache_exe = self.get_executable_path()
        return sccache_exe.exists() if sccache_exe else False

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to sccache executable.

        Returns:
            Path to sccache executable if installed, None otherwise
        """
        if not self.install_dir.exists():
            return None

        if self.platform.os == "windows":
            sccache_exe = self.install_dir / "sccache.exe"
        else:
            sccache_exe = self.install_dir / "sccache"

        return sccache_exe if sccache_exe.exists() else None

    def download(self, force: bool = False) -> Path:
        """
        Download and install sccache.

        Args:
            force: If True, re-download even if already installed

        Returns:
            Path to sccache installation directory

        Raises:
            ToolDownloadError: If download or installation fails
        """
        if self.is_installed() and not force:
            logger.info(
                f"sccache {self.version} already installed at {self.install_dir}"
            )
            return self.install_dir

        logger.info(f"Downloading sccache {self.version}...")

        try:
            # Determine download URL
            url = self._get_download_url()
            logger.debug(f"sccache download URL: {url}")

            # Download and extract
            from toolchainkit.core.download import download_file
            from toolchainkit.core.filesystem import extract_archive

            # Create temp download directory
            download_dir = self.tools_dir / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)

            # Download archive
            archive_name = url.split("/")[-1]
            archive_path = download_dir / archive_name

            download_file(url, archive_path)

            # Remove old installation if exists
            if self.install_dir.exists():
                safe_rmtree(self.install_dir)

            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)

            # Extract archive
            logger.info(f"Extracting sccache to {self.install_dir}...")
            temp_extract = download_dir / f"sccache-{self.version}-temp"
            temp_extract.mkdir(exist_ok=True)

            extract_archive(archive_path, temp_extract)

            # Find sccache executable in extracted files
            exe_name = "sccache.exe" if self.platform.os == "windows" else "sccache"
            sccache_exe = self._find_executable_in_dir(temp_extract, exe_name)

            if not sccache_exe:
                safe_rmtree(temp_extract, require_prefix=download_dir)
                raise ToolDownloadError(
                    f"sccache executable not found in archive. "
                    f"Expected to find '{exe_name}' in extracted files."
                )

            # Move to installation directory
            target_path = self.install_dir / exe_name
            shutil.move(str(sccache_exe), str(target_path))

            # Cleanup temp extraction
            safe_rmtree(temp_extract, require_prefix=download_dir)
            archive_path.unlink()

            # Make executable on Unix-like systems
            if self.platform.os != "windows":
                import os

                os.chmod(target_path, 0o755)

            # Verify installation
            if not self.is_installed():
                raise ToolDownloadError("sccache installation verification failed")

            logger.info(f"sccache {self.version} installed successfully")
            return self.install_dir

        except Exception as e:
            logger.error(f"Failed to download sccache: {e}")
            raise ToolDownloadError(f"sccache download failed: {e}") from e

    def _get_download_url(self) -> str:
        """
        Get sccache download URL for the current platform.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not supported
        """
        # Determine platform key
        if self.platform.os == "linux" and self.platform.arch in ("x86_64", "x64"):
            platform_key = "linux-x64"
        elif self.platform.os == "macos" and self.platform.arch in ("x86_64", "x64"):
            platform_key = "macos-x64"
        elif self.platform.os == "macos" and self.platform.arch == "arm64":
            platform_key = "macos-arm64"
        elif self.platform.os == "windows" and self.platform.arch in ("x86_64", "x64"):
            platform_key = "windows-x64"
        else:
            raise ToolDownloadError(
                f"Unsupported platform: {self.platform.os}-{self.platform.arch}"
            )

        url_template = self.SCCACHE_RELEASES.get(platform_key)
        if not url_template:
            raise ToolDownloadError(f"No sccache binary for platform: {platform_key}")

        return url_template.format(version=self.version)

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        # Try without exact name match (in case of different naming)
        for item in directory.rglob("*"):
            if item.is_file() and "sccache" in item.name.lower():
                if self.platform.os == "windows" and item.name.endswith(".exe"):
                    return item
                elif self.platform.os != "windows":
                    # Check if executable on Unix
                    import os

                    if os.access(item, os.X_OK):
                        return item

        return None


def get_system_sccache_path() -> Optional[Path]:
    """
    Get path to system-installed sccache.

    Returns:
        Path to system sccache executable, or None if not found
    """
    sccache_path = shutil.which("sccache")
    return Path(sccache_path) if sccache_path else None


def get_system_ccache_path() -> Optional[Path]:
    """
    Get path to system-installed ccache.

    Returns:
        Path to system ccache executable, or None if not found
    """
    ccache_path = shutil.which("ccache")
    return Path(ccache_path) if ccache_path else None


class PythonDownloader:
    """
    Download and install portable Python for hermetic environments.

    Uses platform-specific Python distributions:
    - Windows: Embedded Python from python.org
    - Linux/macOS: python-build-standalone by Gregory Szorc
    """

    # python-build-standalone releases
    # https://github.com/indygreg/python-build-standalone/releases
    PYTHON_STANDALONE_BASE = (
        "https://github.com/indygreg/python-build-standalone/releases/download"
    )

    # Release tag format: YYYYMMDD (e.g., "20241016")
    PYTHON_STANDALONE_RELEASE = "20241016"

    # Windows embedded Python from python.org
    PYTHON_EMBEDDED_BASE = "https://www.python.org/ftp/python"

    DEFAULT_VERSION = "3.12.7"

    def __init__(
        self,
        tools_dir: Path,
        version: str = DEFAULT_VERSION,
        platform: Optional[PlatformInfo] = None,
    ):
        """
        Initialize Python downloader.

        Args:
            tools_dir: Directory to install tools into
            version: Python version (e.g., "3.12.7", "3.11.9")
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = Path(tools_dir)
        self.version = version
        self.platform = platform or detect_platform()
        self.install_dir = self.tools_dir / "python" / version

    def is_installed(self) -> bool:
        """
        Check if Python is already installed.

        Returns:
            True if Python is installed, False otherwise
        """
        exe_path = self.get_executable_path()
        return exe_path is not None and exe_path.exists()

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to Python executable.

        Returns:
            Path to Python executable, or None if not installed
        """
        if not self.install_dir.exists():
            return None

        # Platform-specific executable names
        if self.platform.os == "windows":
            # Windows embedded Python
            exe_name = "python.exe"
        else:
            # Linux/macOS python-build-standalone
            exe_name = "python3"

        # Search for executable
        exe_path = self._find_executable_in_dir(self.install_dir, exe_name)
        if exe_path and exe_path.exists():
            return exe_path

        # Fallback: try common locations
        if self.platform.os == "windows":
            # Windows embedded Python is in root
            candidate = self.install_dir / "python.exe"
            if candidate.exists():
                return candidate
        else:
            # python-build-standalone typically in python/install/bin/
            for subdir in ["python/install/bin", "bin", "install/bin"]:
                candidate = self.install_dir / subdir / "python3"
                if candidate.exists():
                    return candidate

        return None

    def download(self) -> Path:
        """
        Download and install portable Python.

        Returns:
            Path to Python installation directory

        Raises:
            ToolDownloadError: If download/installation fails
        """
        if self.is_installed():
            logger.info(f"Python {self.version} already installed")
            return self.install_dir

        logger.info(f"Downloading Python {self.version} for {self.platform.os}")

        try:
            from ..core.download import download_file
            import tarfile
            import zipfile

            # Create tools directory
            self.tools_dir.mkdir(parents=True, exist_ok=True)

            # Get download URL
            url = self._get_download_url()
            logger.debug(f"Download URL: {url}")

            # Download archive
            archive_path = self.tools_dir / f"python-{self.version}.archive"
            logger.debug(f"Downloading to {archive_path}")
            download_file(url, archive_path)

            # Extract archive
            logger.debug(f"Extracting to {self.install_dir}")
            self.install_dir.mkdir(parents=True, exist_ok=True)

            if url.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(self.install_dir)
            elif url.endswith((".tar.gz", ".tar.zst")):
                # python-build-standalone uses .tar.zst, need zstd support
                if url.endswith(".tar.zst"):
                    import zstandard as zstd

                    # Decompress zstd first
                    dctx = zstd.ZstdDecompressor()
                    with open(archive_path, "rb") as ifh:
                        with open(archive_path.with_suffix(".tar"), "wb") as ofh:
                            dctx.copy_stream(ifh, ofh)
                    tar_path = archive_path.with_suffix(".tar")
                else:
                    tar_path = archive_path

                with tarfile.open(tar_path, "r:*") as tar_ref:
                    tar_ref.extractall(self.install_dir)

                if url.endswith(".tar.zst"):
                    tar_path.unlink()  # Clean up intermediate tar file

            # Clean up archive
            archive_path.unlink()

            # Make executables executable on Unix-like systems
            if self.platform.os != "windows":
                self._make_executables_executable()

            # Verify installation
            if not self.is_installed():
                raise ToolDownloadError("Python installation verification failed")

            # Install pip if needed (Windows embedded Python doesn't include pip)
            if self.platform.os == "windows":
                self._install_pip_on_windows()

            logger.info(f"Python {self.version} installed successfully")
            return self.install_dir

        except ImportError as e:
            if "zstandard" in str(e):
                raise ToolDownloadError(
                    "zstandard library required for python-build-standalone. "
                    "Install with: pip install zstandard"
                ) from e
            raise ToolDownloadError(f"Python download failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to download Python: {e}")
            raise ToolDownloadError(f"Python download failed: {e}") from e

    def _get_download_url(self) -> str:
        """
        Get Python download URL for the current platform.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not supported
        """
        if self.platform.os == "windows":
            # Windows embedded Python from python.org
            # Format: https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip
            return (
                f"{self.PYTHON_EMBEDDED_BASE}/{self.version}/"
                f"python-{self.version}-embed-amd64.zip"
            )

        # Linux/macOS: python-build-standalone
        # Format: cpython-3.12.7+YYYYMMDD-x86_64-unknown-linux-gnu-install_only.tar.gz
        version_short = self.version  # e.g., "3.12.7"
        release = self.PYTHON_STANDALONE_RELEASE

        if self.platform.os == "linux":
            if self.platform.arch in ("x86_64", "x64"):
                platform_str = "x86_64-unknown-linux-gnu"
            else:
                raise ToolDownloadError(
                    f"Unsupported Linux architecture: {self.platform.arch}"
                )
        elif self.platform.os == "macos":
            if self.platform.arch in ("x86_64", "x64"):
                platform_str = "x86_64-apple-darwin"
            elif self.platform.arch == "arm64":
                platform_str = "aarch64-apple-darwin"
            else:
                raise ToolDownloadError(
                    f"Unsupported macOS architecture: {self.platform.arch}"
                )
        else:
            raise ToolDownloadError(f"Unsupported platform: {self.platform.os}")

        # Construct URL
        filename = (
            f"cpython-{version_short}+{release}-{platform_str}-install_only.tar.gz"
        )
        url = f"{self.PYTHON_STANDALONE_BASE}/{release}/{filename}"

        return url

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        return None

    def _make_executables_executable(self):
        """Make all executables in bin/ directory executable on Unix."""
        import os

        # Find bin directory
        bin_dirs = [
            self.install_dir / "python" / "install" / "bin",
            self.install_dir / "bin",
            self.install_dir / "install" / "bin",
        ]

        for bin_dir in bin_dirs:
            if bin_dir.exists():
                for item in bin_dir.iterdir():
                    if item.is_file():
                        try:
                            os.chmod(item, 0o755)
                        except Exception as e:
                            logger.debug(f"Failed to chmod {item}: {e}")

    def _install_pip_on_windows(self):
        """
        Install pip on Windows embedded Python.

        Windows embedded Python doesn't include pip by default,
        so we download and run get-pip.py.
        """
        python_exe = self.get_executable_path()
        if not python_exe:
            raise ToolDownloadError("Python executable not found after installation")

        # Check if pip is already available
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.debug("pip already installed")
            return

        # Download get-pip.py
        logger.info("Installing pip on Windows embedded Python")
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_path = self.install_dir / "get-pip.py"

        from ..core.download import download_file

        download_file(get_pip_url, get_pip_path)

        # Run get-pip.py
        result = subprocess.run(
            [str(python_exe), str(get_pip_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.warning(f"Failed to install pip: {result.stderr}")
        else:
            logger.info("pip installed successfully")

        # Clean up
        get_pip_path.unlink(missing_ok=True)


def get_system_python_path() -> Optional[Path]:
    """
    Get path to system-installed Python.

    Returns:
        Path to system Python executable, or None if not found
    """
    # Try python3 first (preferred on Unix)
    python_path = shutil.which("python3")
    if python_path:
        return Path(python_path)

    # Fall back to python
    python_path = shutil.which("python")
    return Path(python_path) if python_path else None


class MakeDownloader:
    """
    Download and install Make build tool (Windows focus).

    Linux/macOS typically have system Make available.
    For Windows, downloads MinGW Make from w64devkit.
    """

    # w64devkit includes mingw32-make
    # https://github.com/skeeto/w64devkit/releases
    W64DEVKIT_BASE = "https://github.com/skeeto/w64devkit/releases/download"
    DEFAULT_VERSION = "2.4.0"

    def __init__(
        self,
        tools_dir: Path,
        version: str = DEFAULT_VERSION,
        platform: Optional[PlatformInfo] = None,
    ):
        """
        Initialize Make downloader.

        Args:
            tools_dir: Directory to install tools into
            version: w64devkit version (e.g., "2.0.0")
            platform: Platform information (auto-detected if None)
        """
        self.tools_dir = Path(tools_dir)
        self.version = version
        self.platform = platform or detect_platform()
        self.install_dir = self.tools_dir / "make" / version

    def is_installed(self) -> bool:
        """
        Check if Make is already installed.

        Returns:
            True if Make is installed, False otherwise
        """
        exe_path = self.get_executable_path()
        return exe_path is not None and exe_path.exists()

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to Make executable.

        Returns:
            Path to Make executable, or None if not installed
        """
        if not self.install_dir.exists():
            return None

        # Platform-specific executable names
        if self.platform.os == "windows":
            exe_name = "mingw32-make.exe"
        else:
            exe_name = "make"

        # Search for executable
        exe_path = self._find_executable_in_dir(self.install_dir, exe_name)
        if exe_path and exe_path.exists():
            return exe_path

        # Fallback: try common locations
        if self.platform.os == "windows":
            # w64devkit extracts to w64devkit/bin/
            candidate = self.install_dir / "w64devkit" / "bin" / "mingw32-make.exe"
            if candidate.exists():
                return candidate
            # Or might be directly in bin/
            candidate = self.install_dir / "bin" / "mingw32-make.exe"
            if candidate.exists():
                return candidate

        return None

    def download(self) -> Path:
        """
        Download and install Make.

        Note: Only needed on Windows. Linux/macOS should use system Make.

        Returns:
            Path to Make installation directory

        Raises:
            ToolDownloadError: If download/installation fails or platform is not Windows
        """
        if self.platform.os != "windows":
            raise ToolDownloadError(
                "Make downloader is only needed on Windows. "
                "Linux/macOS should use system Make (install via package manager)."
            )

        if self.is_installed():
            logger.info(f"Make (w64devkit {self.version}) already installed")
            return self.install_dir

        logger.info(
            f"Downloading Make (w64devkit {self.version}) for {self.platform.os}"
        )

        try:
            from ..core.download import download_file
            import zipfile

            # Create tools directory
            self.tools_dir.mkdir(parents=True, exist_ok=True)

            # Get download URL
            url = self._get_download_url()
            logger.debug(f"Download URL: {url}")

            # Download archive
            archive_path = self.tools_dir / f"w64devkit-{self.version}.zip"
            logger.debug(f"Downloading to {archive_path}")
            download_file(url, archive_path)

            # Extract archive
            logger.debug(f"Extracting to {self.install_dir}")
            self.install_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(self.install_dir)

            # Clean up archive
            archive_path.unlink()

            # Verify installation
            if not self.is_installed():
                raise ToolDownloadError("Make installation verification failed")

            logger.info(f"Make (w64devkit {self.version}) installed successfully")
            return self.install_dir

        except Exception as e:
            logger.error(f"Failed to download Make: {e}")
            raise ToolDownloadError(f"Make download failed: {e}") from e

    def _get_download_url(self) -> str:
        """
        Get Make download URL for the current platform.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not Windows x64
        """
        if self.platform.os != "windows":
            raise ToolDownloadError("Make download only supported on Windows")

        if self.platform.arch not in ("x86_64", "x64"):
            raise ToolDownloadError(
                f"Unsupported Windows architecture: {self.platform.arch}"
            )

        # w64devkit format: v2.4.0/w64devkit-x64-2.4.0.7z.exe
        version = self.version
        filename = f"w64devkit-x64-{version}.7z.exe"
        url = f"{self.W64DEVKIT_BASE}/v{version}/{filename}"

        return url

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        return None


class GitDownloader:
    """
    Download and manage Git SCM tool.

    Git is needed for:
    - Version control operations
    - vcpkg bootstrap (requires git)
    - Source code management

    On Windows, downloads MinGit (minimal Git for Windows without GUI/shell integration).
    On Linux/macOS, expects system git to be installed.

    Attributes:
        DEFAULT_VERSION: Default Git version to download
        MINGIT_BASE: Base URL for MinGit releases
    """

    DEFAULT_VERSION = "2.47.1"
    MINGIT_BASE = "https://github.com/git-for-windows/git/releases/download"

    def __init__(
        self,
        platform: PlatformInfo,
        install_dir: Path,
        version: str = DEFAULT_VERSION,
    ):
        """
        Initialize Git downloader.

        Args:
            platform: Platform information
            install_dir: Directory for tool installations
            version: Git version (Windows only, format: "2.47.1")
        """
        self.platform = platform
        self.install_dir = install_dir
        self.version = version
        self.tool_dir = install_dir / "git" / version

    def is_installed(self) -> bool:
        """
        Check if Git is already installed.

        Returns:
            True if git executable exists, False otherwise
        """
        exe_path = self.get_executable_path()
        return exe_path is not None and exe_path.exists()

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to git executable.

        Returns:
            Path to git executable, or None if not found
        """
        if self.platform.os == "windows":
            # MinGit structure: MinGit-<version>-64-bit/cmd/git.exe
            exe_path = (
                self.tool_dir / f"MinGit-{self.version}-64-bit" / "cmd" / "git.exe"
            )
            if exe_path.exists():
                return exe_path

            # Try alternate structure
            exe_path = self._find_executable_in_dir(self.tool_dir, "git.exe")
            return exe_path
        else:
            # On Linux/macOS, use system git
            return get_system_git_path()

    def download(self) -> Path:
        """
        Download and install Git.

        Returns:
            Path to git executable

        Raises:
            ToolDownloadError: If download fails or platform not supported
        """
        if self.platform.os != "windows":
            raise ToolDownloadError(
                "Git download only supported on Windows. "
                "On Linux/macOS, install git via system package manager."
            )

        if self.is_installed():
            exe_path = self.get_executable_path()
            if exe_path:
                return exe_path

        # Ensure tool directory exists
        self.tool_dir.mkdir(parents=True, exist_ok=True)

        # Generate download URL
        url = self._get_download_url()

        # Download and extract
        try:
            from ..core.download import download_file
            from ..core.filesystem import extract_archive

            archive_path = self.tool_dir / f"mingit-{self.version}.zip"
            download_file(url, archive_path)

            # Extract archive
            extract_archive(archive_path, self.tool_dir)

            # Clean up archive
            archive_path.unlink()

            # Verify installation
            exe_path = self.get_executable_path()
            if not exe_path or not exe_path.exists():
                raise ToolDownloadError("Git executable not found after extraction")

            return exe_path

        except Exception as e:
            raise ToolDownloadError(f"Failed to download Git: {e}") from e

    def _get_download_url(self) -> str:
        """
        Generate download URL for Git.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform is not Windows x64
        """
        if self.platform.os != "windows":
            raise ToolDownloadError("Git download only supported on Windows")

        if self.platform.arch not in ("x86_64", "x64"):
            raise ToolDownloadError(
                f"Unsupported Windows architecture: {self.platform.arch}"
            )

        # MinGit format: v2.47.1.windows.1/MinGit-2.47.1-64-bit.zip
        # Note: Git for Windows uses <version>.windows.<build> format
        version_parts = self.version.split(".")
        if len(version_parts) >= 3:
            # Assume latest windows build (.windows.1)
            git_version = f"{self.version}.windows.1"
        else:
            git_version = f"{self.version}.windows.1"

        filename = f"MinGit-{self.version}-64-bit.zip"
        url = f"{self.MINGIT_BASE}/v{git_version}/{filename}"

        return url

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        return None


class ClangToolsDownloader:
    """
    Download and manage Clang analysis tools (clang-tidy, clang-format).

    Downloads LLVM releases which include clang-tidy and clang-format.
    These tools are used for:
    - Static code analysis (clang-tidy)
    - Code formatting (clang-format)
    - Linting and modernization

    Attributes:
        DEFAULT_VERSION: Default LLVM version to download
        LLVM_BASE: Base URL for LLVM releases
    """

    DEFAULT_VERSION = "18.1.8"
    LLVM_BASE = "https://github.com/llvm/llvm-project/releases/download"

    def __init__(
        self,
        platform: PlatformInfo,
        install_dir: Path,
        version: str = DEFAULT_VERSION,
    ):
        """
        Initialize Clang tools downloader.

        Args:
            platform: Platform information
            install_dir: Directory for tool installations
            version: LLVM version (format: "18.1.8")
        """
        self.platform = platform
        self.install_dir = install_dir
        self.version = version
        self.tool_dir = install_dir / "clang-tools" / version

    def is_installed(self) -> bool:
        """
        Check if Clang tools are already installed.

        Returns:
            True if clang-tidy and clang-format exist, False otherwise
        """
        tidy_path = self.get_clang_tidy_path()
        format_path = self.get_clang_format_path()
        return (
            tidy_path is not None
            and tidy_path.exists()
            and format_path is not None
            and format_path.exists()
        )

    def get_clang_tidy_path(self) -> Optional[Path]:
        """
        Get path to clang-tidy executable.

        Returns:
            Path to clang-tidy executable, or None if not found
        """
        exe_name = "clang-tidy.exe" if self.platform.os == "windows" else "clang-tidy"
        exe_path = self._find_executable_in_dir(self.tool_dir, exe_name)
        return exe_path

    def get_clang_format_path(self) -> Optional[Path]:
        """
        Get path to clang-format executable.

        Returns:
            Path to clang-format executable, or None if not found
        """
        exe_name = (
            "clang-format.exe" if self.platform.os == "windows" else "clang-format"
        )
        exe_path = self._find_executable_in_dir(self.tool_dir, exe_name)
        return exe_path

    def download(self) -> tuple[Path, Path]:
        """
        Download and install Clang tools.

        Returns:
            Tuple of (clang-tidy path, clang-format path)

        Raises:
            ToolDownloadError: If download fails or tools not found
        """
        if self.is_installed():
            tidy_path = self.get_clang_tidy_path()
            format_path = self.get_clang_format_path()
            if tidy_path and format_path:
                return (tidy_path, format_path)

        # Ensure tool directory exists
        self.tool_dir.mkdir(parents=True, exist_ok=True)

        # Generate download URL
        url = self._get_download_url()

        # Download and extract
        try:
            from ..core.download import download_file
            from ..core.filesystem import extract_archive

            archive_ext = ".tar.xz" if self.platform.os != "windows" else ".zip"
            archive_path = self.tool_dir / f"llvm-{self.version}{archive_ext}"
            download_file(url, archive_path)

            # Extract archive
            extract_archive(archive_path, self.tool_dir)

            # Clean up archive
            archive_path.unlink()

            # Verify installation
            tidy_path = self.get_clang_tidy_path()
            format_path = self.get_clang_format_path()
            if not tidy_path or not tidy_path.exists():
                raise ToolDownloadError("clang-tidy not found after extraction")
            if not format_path or not format_path.exists():
                raise ToolDownloadError("clang-format not found after extraction")

            return (tidy_path, format_path)

        except Exception as e:
            raise ToolDownloadError(f"Failed to download Clang tools: {e}") from e

    def _get_download_url(self) -> str:
        """
        Generate download URL for Clang tools.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform not supported
        """
        version = self.version

        if self.platform.os == "windows":
            if self.platform.arch not in ("x86_64", "x64"):
                raise ToolDownloadError(
                    f"Unsupported Windows architecture: {self.platform.arch}"
                )
            # Format: llvmorg-18.1.8/LLVM-18.1.8-win64.exe (installer) or
            # llvmorg-18.1.8/LLVM-18.1.8-Windows-X64.tar.xz (archive)
            # We'll use the archive for hermetic installations
            filename = f"LLVM-{version}-win64.exe"
            url = f"{self.LLVM_BASE}/llvmorg-{version}/{filename}"

        elif self.platform.os == "linux":
            if self.platform.arch not in ("x86_64", "x64"):
                raise ToolDownloadError(
                    f"Unsupported Linux architecture: {self.platform.arch}"
                )
            # Format: llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-linux-gnu-ubuntu-18.04.tar.xz
            filename = f"clang+llvm-{version}-x86_64-linux-gnu-ubuntu-18.04.tar.xz"
            url = f"{self.LLVM_BASE}/llvmorg-{version}/{filename}"

        elif self.platform.os == "macos":
            if self.platform.arch == "arm64":
                # Format: llvmorg-18.1.8/clang+llvm-18.1.8-arm64-apple-darwin22.0.tar.xz
                filename = f"clang+llvm-{version}-arm64-apple-darwin22.0.tar.xz"
            else:
                # Format: llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-apple-darwin.tar.xz
                filename = f"clang+llvm-{version}-x86_64-apple-darwin.tar.xz"
            url = f"{self.LLVM_BASE}/llvmorg-{version}/{filename}"

        else:
            raise ToolDownloadError(f"Unsupported platform: {self.platform.os}")

        return url

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        return None


def get_system_git_path() -> Optional[Path]:
    """
    Get path to system-installed Git.

    Returns:
        Path to system git executable, or None if not found
    """
    git_path = shutil.which("git")
    if git_path:
        return Path(git_path)

    return None


def get_system_clang_tidy_path() -> Optional[Path]:
    """
    Get path to system-installed clang-tidy.

    Returns:
        Path to system clang-tidy executable, or None if not found
    """
    clang_tidy_path = shutil.which("clang-tidy")
    if clang_tidy_path:
        return Path(clang_tidy_path)

    return None


def get_system_clang_format_path() -> Optional[Path]:
    """
    Get path to system-installed clang-format.

    Returns:
        Path to system clang-format executable, or None if not found
    """
    clang_format_path = shutil.which("clang-format")
    if clang_format_path:
        return Path(clang_format_path)

    return None


class CppcheckDownloader:
    """
    Download and manage Cppcheck static analysis tool.

    Cppcheck is a static analysis tool for C/C++ code that detects:
    - Bugs
    - Undefined behavior
    - Dangerous coding practices
    - Memory leaks

    Attributes:
        DEFAULT_VERSION: Default Cppcheck version to download
        CPPCHECK_BASE: Base URL for Cppcheck releases
    """

    DEFAULT_VERSION = "2.16.2"
    CPPCHECK_BASE = "https://github.com/danmar/cppcheck/releases/download"

    def __init__(
        self,
        platform: PlatformInfo,
        install_dir: Path,
        version: str = DEFAULT_VERSION,
    ):
        """
        Initialize Cppcheck downloader.

        Args:
            platform: Platform information
            install_dir: Directory for tool installations
            version: Cppcheck version (format: "2.16.2")
        """
        self.platform = platform
        self.install_dir = install_dir
        self.version = version
        self.tool_dir = install_dir / "cppcheck" / version

    def is_installed(self) -> bool:
        """
        Check if Cppcheck is already installed.

        Returns:
            True if cppcheck executable exists, False otherwise
        """
        exe_path = self.get_executable_path()
        return exe_path is not None and exe_path.exists()

    def get_executable_path(self) -> Optional[Path]:
        """
        Get path to cppcheck executable.

        Returns:
            Path to cppcheck executable, or None if not found
        """
        exe_name = "cppcheck.exe" if self.platform.os == "windows" else "cppcheck"
        exe_path = self._find_executable_in_dir(self.tool_dir, exe_name)
        return exe_path

    def download(self) -> Path:
        """
        Download and install Cppcheck.

        Returns:
            Path to cppcheck executable

        Raises:
            ToolDownloadError: If download fails or platform not supported
        """
        if self.is_installed():
            exe_path = self.get_executable_path()
            if exe_path:
                return exe_path

        # Ensure tool directory exists
        self.tool_dir.mkdir(parents=True, exist_ok=True)

        # Generate download URL
        url = self._get_download_url()

        # Download and extract
        try:
            from ..core.download import download_file
            from ..core.filesystem import extract_archive

            archive_ext = ".zip" if self.platform.os == "windows" else ".tar.gz"
            archive_path = self.tool_dir / f"cppcheck-{self.version}{archive_ext}"
            download_file(url, archive_path)

            # Extract archive
            extract_archive(archive_path, self.tool_dir)

            # Clean up archive
            archive_path.unlink()

            # Verify installation
            exe_path = self.get_executable_path()
            if not exe_path or not exe_path.exists():
                raise ToolDownloadError(
                    "Cppcheck executable not found after extraction"
                )

            return exe_path

        except Exception as e:
            raise ToolDownloadError(f"Failed to download Cppcheck: {e}") from e

    def _get_download_url(self) -> str:
        """
        Generate download URL for Cppcheck.

        Returns:
            Download URL string

        Raises:
            ToolDownloadError: If platform not supported
        """
        version = self.version

        if self.platform.os == "windows":
            if self.platform.arch not in ("x86_64", "x64"):
                raise ToolDownloadError(
                    f"Unsupported Windows architecture: {self.platform.arch}"
                )
            # Format: 2.16.2/cppcheck-2.16.2-x64-Setup.msi (installer) or
            # For portable: need to extract from installer or use pre-built
            # Using portable zip if available
            filename = f"cppcheck-{version}-x64-Setup.msi"
            url = f"{self.CPPCHECK_BASE}/{version}/{filename}"

        elif self.platform.os == "linux":
            # Cppcheck doesn't provide pre-built Linux binaries
            # Users should install from package manager or build from source
            raise ToolDownloadError(
                "Cppcheck download not supported on Linux. "
                "Install via package manager: apt-get install cppcheck"
            )

        elif self.platform.os == "macos":
            # Cppcheck doesn't provide pre-built macOS binaries
            # Users should install from Homebrew or build from source
            raise ToolDownloadError(
                "Cppcheck download not supported on macOS. "
                "Install via Homebrew: brew install cppcheck"
            )

        else:
            raise ToolDownloadError(f"Unsupported platform: {self.platform.os}")

        return url

    def _find_executable_in_dir(self, directory: Path, exe_name: str) -> Optional[Path]:
        """
        Find executable in directory tree.

        Args:
            directory: Directory to search
            exe_name: Executable name to find

        Returns:
            Path to executable or None if not found
        """
        # Search recursively for the executable
        for item in directory.rglob("*"):
            if item.is_file() and item.name == exe_name:
                return item

        return None


def get_system_cppcheck_path() -> Optional[Path]:
    """
    Get path to system-installed Cppcheck.

    Returns:
        Path to system cppcheck executable, or None if not found
    """
    cppcheck_path = shutil.which("cppcheck")
    if cppcheck_path:
        return Path(cppcheck_path)

    return None


def get_system_make_path() -> Optional[Path]:
    """
    Get path to system-installed Make.

    Returns:
        Path to system Make executable, or None if not found
    """
    # Try common make variants
    for make_name in ["make", "gmake", "mingw32-make"]:
        make_path = shutil.which(make_name)
        if make_path:
            return Path(make_path)

    return None
