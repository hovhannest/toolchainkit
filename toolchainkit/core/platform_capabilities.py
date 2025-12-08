"""Platform capability matrix and helper functions.

This module provides a centralized database of platform capabilities and
helper functions to query platform-specific features.

Platform Capability Matrix
=========================

This module provides a centralized database of platform capabilities.

Supported Platforms:
- linux-x64: Linux x86-64 (glibc/musl)
- linux-arm64: Linux ARM64 (glibc/musl)
- windows-x64: Windows x86-64
- macos-x64: macOS x86-64 (Intel)
- macos-arm64: macOS ARM64 (Apple Silicon)

Capabilities:
- symlinks: Whether platform supports symbolic links
- long_paths: Whether platform supports paths > 260 characters
- compilers: List of supported compilers
- stdlib: List of supported standard libraries
- package_managers: List of supported package managers
- build_backends: List of supported build systems
- file_extensions: Executable and library extensions
"""

from typing import Any, List, Dict

# Platform capability database
PLATFORM_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "linux-x64": {
        "symlinks": True,
        "long_paths": True,
        "max_path_length": None,  # No practical limit
        "compilers": ["llvm", "gcc"],
        "stdlib": ["libc++", "libstdc++"],
        "package_managers": ["conan", "vcpkg"],
        "build_backends": ["ninja", "make"],
        "executable_extension": "",
        "shared_library_extension": ".so",
        "static_library_extension": ".a",
        "case_sensitive_filesystem": True,
        "path_separator": "/",
        "supports_rpath": True,
        "supports_execute_bit": True,
    },
    "linux-arm64": {
        "symlinks": True,
        "long_paths": True,
        "max_path_length": None,  # No practical limit
        "compilers": ["llvm", "gcc"],
        "stdlib": ["libc++", "libstdc++"],
        "package_managers": ["conan", "vcpkg"],
        "build_backends": ["ninja", "make"],
        "executable_extension": "",
        "shared_library_extension": ".so",
        "static_library_extension": ".a",
        "case_sensitive_filesystem": True,
        "path_separator": "/",
        "supports_rpath": True,
        "supports_execute_bit": True,
    },
    "windows-x64": {
        "symlinks": False,  # Use junctions instead
        "long_paths": True,  # With registry setting enabled
        "max_path_length": 260,  # Without long path support enabled
        "compilers": ["llvm", "msvc"],
        "stdlib": ["libc++", "msvc"],
        "package_managers": ["conan", "vcpkg"],
        "build_backends": ["ninja", "msbuild", "nmake"],
        "executable_extension": ".exe",
        "shared_library_extension": ".dll",
        "static_library_extension": ".lib",
        "case_sensitive_filesystem": False,
        "path_separator": "\\",
        "supports_rpath": False,
        "supports_execute_bit": False,
    },
    "macos-x64": {
        "symlinks": True,
        "long_paths": True,
        "max_path_length": None,  # No practical limit
        "compilers": ["llvm"],  # Apple Clang
        "stdlib": ["libc++"],
        "package_managers": ["conan", "vcpkg"],
        "build_backends": ["ninja", "make", "xcode"],
        "executable_extension": "",
        "shared_library_extension": ".dylib",
        "static_library_extension": ".a",
        "case_sensitive_filesystem": False,  # Default APFS is case-insensitive
        "path_separator": "/",
        "supports_rpath": True,
        "supports_execute_bit": True,
    },
    "macos-arm64": {
        "symlinks": True,
        "long_paths": True,
        "max_path_length": None,  # No practical limit
        "compilers": ["llvm"],  # Apple Clang
        "stdlib": ["libc++"],
        "package_managers": ["conan", "vcpkg"],
        "build_backends": ["ninja", "make", "xcode"],
        "executable_extension": "",
        "shared_library_extension": ".dylib",
        "static_library_extension": ".a",
        "case_sensitive_filesystem": False,  # Default APFS is case-insensitive
        "path_separator": "/",
        "supports_rpath": True,
        "supports_execute_bit": True,
    },
}


def supports_feature(platform: str, feature: str) -> bool:
    """
    Check if platform supports a specific feature.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')
        feature: Feature name (e.g., 'symlinks', 'long_paths')

    Returns:
        True if platform supports feature, False otherwise.
        Returns False for unknown platforms or features.

    Example:
        >>> supports_feature('linux-x64', 'symlinks')
        True
        >>> supports_feature('windows-x64', 'symlinks')
        False
        >>> supports_feature('unknown-platform', 'symlinks')
        False
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return bool(capabilities.get(feature, False))


def get_supported_compilers(platform: str) -> List[str]:
    """
    Get list of supported compilers for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')

    Returns:
        List of supported compiler names (e.g., ['llvm', 'gcc']).
        Returns empty list for unknown platforms.

    Example:
        >>> get_supported_compilers('linux-x64')
        ['llvm', 'gcc']
        >>> get_supported_compilers('windows-x64')
        ['llvm', 'msvc']
        >>> get_supported_compilers('unknown-platform')
        []
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return capabilities.get("compilers", [])


def get_supported_stdlibs(platform: str) -> List[str]:
    """
    Get list of supported standard libraries for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')

    Returns:
        List of supported standard library names (e.g., ['libc++', 'libstdc++']).
        Returns empty list for unknown platforms.

    Example:
        >>> get_supported_stdlibs('linux-x64')
        ['libc++', 'libstdc++']
        >>> get_supported_stdlibs('macos-arm64')
        ['libc++']
        >>> get_supported_stdlibs('unknown-platform')
        []
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return capabilities.get("stdlib", [])


def get_supported_package_managers(platform: str) -> List[str]:
    """
    Get list of supported package managers for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')

    Returns:
        List of supported package manager names (e.g., ['conan', 'vcpkg']).
        Returns empty list for unknown platforms.

    Example:
        >>> get_supported_package_managers('linux-x64')
        ['conan', 'vcpkg']
        >>> get_supported_package_managers('unknown-platform')
        []
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return capabilities.get("package_managers", [])


def get_supported_build_backends(platform: str) -> List[str]:
    """
    Get list of supported build backends for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')

    Returns:
        List of supported build backend names (e.g., ['ninja', 'make']).
        Returns empty list for unknown platforms.

    Example:
        >>> get_supported_build_backends('linux-x64')
        ['ninja', 'make']
        >>> get_supported_build_backends('windows-x64')
        ['ninja', 'msbuild', 'nmake']
        >>> get_supported_build_backends('unknown-platform')
        []
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return capabilities.get("build_backends", [])


def get_capability(platform: str, capability: str) -> Any:
    """
    Get specific capability value for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')
        capability: Capability name (any key in the platform's capability dict)

    Returns:
        Capability value if found, None otherwise.

    Example:
        >>> get_capability('linux-x64', 'max_path_length')
        None
        >>> get_capability('windows-x64', 'max_path_length')
        260
        >>> get_capability('linux-x64', 'executable_extension')
        ''
        >>> get_capability('windows-x64', 'executable_extension')
        '.exe'
    """
    capabilities = PLATFORM_CAPABILITIES.get(platform, {})
    return capabilities.get(capability)


def get_all_platforms() -> List[str]:
    """
    Get list of all supported platforms.

    Returns:
        List of all platform strings defined in the capability matrix.

    Example:
        >>> platforms = get_all_platforms()
        >>> 'linux-x64' in platforms
        True
        >>> 'windows-x64' in platforms
        True
    """
    return list(PLATFORM_CAPABILITIES.keys())


def is_platform_supported(platform: str) -> bool:
    """
    Check if platform is supported.

    Args:
        platform: Platform string to check

    Returns:
        True if platform is in the capability matrix, False otherwise.

    Example:
        >>> is_platform_supported('linux-x64')
        True
        >>> is_platform_supported('unknown-platform')
        False
    """
    return platform in PLATFORM_CAPABILITIES


def get_file_extension(platform: str, extension_type: str) -> str:
    """
    Get file extension for platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')
        extension_type: Type of extension ('executable', 'shared_library', 'static_library')

    Returns:
        File extension string (e.g., '.exe', '.so', '.dll').
        Returns empty string for unknown platforms/types.

    Example:
        >>> get_file_extension('windows-x64', 'executable')
        '.exe'
        >>> get_file_extension('linux-x64', 'executable')
        ''
        >>> get_file_extension('linux-x64', 'shared_library')
        '.so'
        >>> get_file_extension('macos-x64', 'shared_library')
        '.dylib'
    """
    extension_map = {
        "executable": "executable_extension",
        "shared_library": "shared_library_extension",
        "static_library": "static_library_extension",
    }

    capability_key = extension_map.get(extension_type)
    if capability_key is None:
        return ""

    return get_capability(platform, capability_key) or ""


def get_platform_capabilities(platform: str) -> Dict[str, Any]:
    """
    Get all capabilities for a platform.

    Args:
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')

    Returns:
        Dictionary of all capabilities for the platform.
        Returns empty dict for unknown platforms.

    Example:
        >>> caps = get_platform_capabilities('linux-x64')
        >>> caps['symlinks']
        True
        >>> caps['compilers']
        ['llvm', 'gcc']
    """
    return PLATFORM_CAPABILITIES.get(platform, {}).copy()
