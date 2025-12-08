"""
Platform detection for ToolchainKit.

This module provides accurate detection of the current platform (OS, architecture, ABI)
to select appropriate toolchain downloads and generate correct CMake configuration.

Features:
- Operating system detection (Windows, Linux, macOS, Android, iOS)
- CPU architecture detection (x64, ARM64, x86, ARM, RISC-V)
- ABI detection (glibc version, musl, MSVC runtime, macOS deployment target)
- Linux distribution detection (Ubuntu, Debian, CentOS, Arch, etc.)
- Canonical platform string generation (e.g., 'linux-x64', 'macos-arm64')
- Platform validation and support checking
- Fast detection with caching (<100ms)

Usage:
    from toolchainkit.core.platform import detect_platform, is_supported_platform

    # Detect current platform
    platform_info = detect_platform()
    print(f"OS: {platform_info.os}")
    print(f"Architecture: {platform_info.arch}")
    print(f"Platform string: {platform_info.platform_string()}")

    # Check if platform is supported
    if is_supported_platform(platform_info):
        print("Platform is supported!")
"""

import platform
import subprocess
import functools
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class PlatformInfo:
    """
    Comprehensive platform information.

    Attributes:
        os: Operating system ('windows', 'linux', 'macos', 'android', 'ios')
        arch: CPU architecture ('x64', 'arm64', 'x86', 'arm')
        os_version: OS version string (e.g., '10.0.19041', '22.04', '14.1')
        distribution: Linux distribution ('ubuntu', 'centos', 'arch', etc.) or empty
        abi: ABI information ('glibc-2.31', 'musl', 'msvc', 'macos-11.0')
    """

    os: str
    arch: str
    os_version: str
    distribution: str
    abi: str

    def platform_string(self) -> str:
        """
        Get canonical platform string (e.g., 'linux-x64', 'macos-arm64').

        Returns:
            Canonical platform string used for toolchain selection

        Example:
            >>> info = PlatformInfo('linux', 'x64', '5.15', 'ubuntu', 'glibc-2.31')
            >>> info.platform_string()
            'linux-x64'
        """
        return f"{self.os}-{self.arch}"

    def toolchain_suffix(self) -> str:
        """
        Get platform suffix for toolchain names (some use different conventions).

        Returns:
            Platform suffix for toolchain naming

        Example:
            >>> info = PlatformInfo('linux', 'x64', '5.15', 'ubuntu', 'glibc-2.31')
            >>> info.toolchain_suffix()
            'linux-x86_64'
        """
        # Some toolchains use different architecture names
        arch_map = {
            "x64": "x86_64",
            "arm64": "aarch64",
            "x86": "i686",
            "arm": "armv7l",
        }
        return f"{self.os}-{arch_map.get(self.arch, self.arch)}"

    def __str__(self) -> str:
        """String representation of platform info."""
        parts = [f"{self.os}-{self.arch}"]
        if self.distribution:
            parts.append(f"({self.distribution})")
        parts.append(f"v{self.os_version}")
        parts.append(f"[{self.abi}]")
        return " ".join(parts)


@functools.lru_cache(maxsize=1)
def detect_platform() -> PlatformInfo:
    """
    Detect current platform information.

    This function is cached - it only runs detection once per process.

    Returns:
        PlatformInfo instance with detected platform information

    Example:
        >>> platform_info = detect_platform()
        >>> print(f"Running on {platform_info.platform_string()}")
        Running on linux-x64
    """
    os_name = _detect_os()
    arch = _detect_architecture()
    os_version = _detect_os_version()
    distribution = _detect_distribution() if os_name == "linux" else ""
    abi = _detect_abi()

    return PlatformInfo(
        os=os_name, arch=arch, os_version=os_version, distribution=distribution, abi=abi
    )


def _detect_os() -> str:
    """
    Detect operating system.

    Returns:
        Normalized OS name: 'windows', 'linux', 'macos', 'android', 'ios'

    Raises:
        RuntimeError: If OS is not supported
    """
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "linux":
        # Check if running on Android
        if "android" in platform.platform().lower():
            return "android"
        return "linux"
    elif system == "darwin":
        # Check if iOS (rare, but possible in cross-compilation scenarios)
        if (
            "iphone" in platform.platform().lower()
            or "ios" in platform.platform().lower()
        ):
            return "ios"
        return "macos"
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")


def _detect_architecture() -> str:
    """
    Detect CPU architecture.

    Returns:
        Normalized architecture: 'x64', 'arm64', 'x86', 'arm'
    """
    machine = platform.machine().lower()

    # Normalize architecture names
    if machine in ("x86_64", "amd64", "x64"):
        return "x64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    elif machine in ("i386", "i686", "x86"):
        return "x86"
    elif machine.startswith("arm"):
        return "arm"
    elif machine.startswith("riscv"):
        return "riscv"  # Future support
    else:
        # Return original for unknown architectures
        return machine


def _detect_os_version() -> str:
    """
    Detect OS version.

    Returns:
        OS version string
    """
    system = platform.system().lower()

    if system == "windows":
        # Windows version (e.g., '10.0.19041')
        return platform.version()
    elif system == "darwin":
        # macOS version (e.g., '14.1.0')
        version = platform.mac_ver()[0]
        return version if version else "unknown"
    elif system == "linux":
        # Kernel version (e.g., '5.15.0-56-generic')
        return platform.release()
    else:
        return platform.version()


def _detect_distribution() -> str:
    """
    Detect Linux distribution.

    Returns:
        Distribution ID: 'ubuntu', 'centos', 'arch', etc., or 'unknown'
    """
    # Try using distro library if available
    try:
        import distro

        return distro.id()
    except ImportError:
        pass

    # Fallback: parse /etc/os-release
    try:
        os_release_path = Path("/etc/os-release")
        if os_release_path.exists():
            content = os_release_path.read_text()
            for line in content.split("\n"):
                if line.startswith("ID="):
                    # Remove quotes and extract value
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return value
    except Exception:
        pass

    # Last resort: check for specific files
    distro_files = {
        "/etc/debian_version": "debian",
        "/etc/redhat-release": "redhat",
        "/etc/arch-release": "arch",
        "/etc/gentoo-release": "gentoo",
    }

    for file_path, distro_name in distro_files.items():
        if Path(file_path).exists():
            return distro_name

    return "unknown"


def _detect_abi() -> str:
    """
    Detect C++ ABI information.

    Returns:
        ABI string
    """
    system = platform.system().lower()

    if system == "linux":
        return _detect_linux_abi()
    elif system == "windows":
        return _detect_windows_abi()
    elif system == "darwin":
        return _detect_macos_abi()
    else:
        return "unknown"


def _detect_linux_abi() -> str:
    """
    Detect Linux ABI (glibc version or musl).

    Returns:
        ABI string: 'glibc-X.Y', 'musl', or 'unknown'
    """
    try:
        # Check for musl
        result = subprocess.run(
            ["ldd", "--version"], capture_output=True, text=True, timeout=5
        )

        output = result.stdout.lower() + result.stderr.lower()

        if "musl" in output:
            return "musl"

        # Parse glibc version
        for line in output.split("\n"):
            if "glibc" in line or "gnu libc" in line:
                # Extract version (e.g., "2.31")
                import re

                match = re.search(r"(\d+)\.(\d+)", line)
                if match:
                    return f"glibc-{match.group(1)}.{match.group(2)}"

        return "glibc-unknown"

    except Exception:
        return "unknown"


def _detect_windows_abi() -> str:
    """
    Detect Windows MSVC runtime version.

    Returns:
        ABI string: 'msvc' (generic for now)

    Note:
        Detailed MSVC version detection is complex and typically
        determined by the compiler used, not the system.
    """
    # This is complex - MSVC runtime version depends on installed Visual Studio
    # For now, just return generic 'msvc'
    return "msvc"


def _detect_macos_abi() -> str:
    """
    Detect macOS deployment target.

    Returns:
        ABI string: 'macos-X.Y'
    """
    import os

    # Check MACOSX_DEPLOYMENT_TARGET environment variable
    deployment_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET")
    if deployment_target:
        return f"macos-{deployment_target}"

    # Use current OS version as fallback
    version = platform.mac_ver()[0]
    if version:
        parts = version.split(".")
        if len(parts) >= 2:
            return f"macos-{parts[0]}.{parts[1]}"

    return "macos-unknown"


def is_supported_platform(info: Optional[PlatformInfo] = None) -> bool:
    """
    Check if platform is supported by ToolchainKit.

    Args:
        info: PlatformInfo to check. If None, detects current platform.

    Returns:
        True if platform is supported

    Example:
        >>> if is_supported_platform():
        ...     print("Your platform is supported!")
    """
    if info is None:
        info = detect_platform()

    supported_os = ["windows", "linux", "macos"]
    supported_arch = ["x64", "arm64", "x86", "arm"]

    return info.os in supported_os and info.arch in supported_arch


def get_supported_platforms() -> list[str]:
    """
    Get list of all supported platform strings.

    Returns:
        List of platform strings

    Example:
        >>> platforms = get_supported_platforms()
        >>> print("Supported platforms:", ', '.join(platforms))
        Supported platforms: windows-x64, linux-x64, linux-arm64, ...
    """
    return [
        "windows-x64",
        "windows-x86",
        "windows-arm64",
        "linux-x64",
        "linux-x86",
        "linux-arm64",
        "linux-arm",
        "macos-x64",
        "macos-arm64",
        "android-arm64",
        "android-x64",
        "ios-arm64",
    ]


def clear_platform_cache():
    """
    Clear the platform detection cache.

    This forces the next call to detect_platform() to re-detect.
    Useful for testing or when platform information changes.
    """
    detect_platform.cache_clear()


__all__ = [
    "PlatformInfo",
    "detect_platform",
    "is_supported_platform",
    "get_supported_platforms",
    "clear_platform_cache",
]
