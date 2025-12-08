"""Tests for platform capabilities module."""

import pytest

from toolchainkit.core.platform_capabilities import (
    supports_feature,
    get_supported_compilers,
    get_supported_stdlibs,
    get_supported_package_managers,
    get_supported_build_backends,
    get_capability,
    get_all_platforms,
    is_platform_supported,
    get_file_extension,
    get_platform_capabilities,
    PLATFORM_CAPABILITIES,
)


class TestPlatformCapabilities:
    """Tests for platform capability queries."""

    def test_linux_supports_symlinks(self):
        """Test that Linux platforms support symlinks."""
        assert supports_feature("linux-x64", "symlinks") is True
        assert supports_feature("linux-arm64", "symlinks") is True

    def test_windows_no_symlinks(self):
        """Test that Windows uses junctions instead of symlinks."""
        assert supports_feature("windows-x64", "symlinks") is False

    def test_macos_supports_symlinks(self):
        """Test that macOS platforms support symlinks."""
        assert supports_feature("macos-x64", "symlinks") is True
        assert supports_feature("macos-arm64", "symlinks") is True

    def test_all_platforms_support_long_paths(self):
        """Test that all platforms support long paths (with configuration on Windows)."""
        assert supports_feature("linux-x64", "long_paths") is True
        assert supports_feature("linux-arm64", "long_paths") is True
        assert supports_feature("windows-x64", "long_paths") is True
        assert supports_feature("macos-x64", "long_paths") is True
        assert supports_feature("macos-arm64", "long_paths") is True

    def test_get_supported_compilers_linux(self):
        """Test getting supported compilers for Linux."""
        compilers = get_supported_compilers("linux-x64")
        assert "llvm" in compilers
        assert "gcc" in compilers
        assert "msvc" not in compilers

    def test_get_supported_compilers_windows(self):
        """Test getting supported compilers for Windows."""
        compilers = get_supported_compilers("windows-x64")
        assert "llvm" in compilers
        assert "msvc" in compilers
        assert "gcc" not in compilers

    def test_get_supported_compilers_macos(self):
        """Test getting supported compilers for macOS."""
        compilers = get_supported_compilers("macos-x64")
        assert "llvm" in compilers
        assert "gcc" not in compilers
        assert "msvc" not in compilers

    def test_get_supported_stdlibs_linux(self):
        """Test getting supported standard libraries for Linux."""
        stdlibs = get_supported_stdlibs("linux-x64")
        assert "libc++" in stdlibs
        assert "libstdc++" in stdlibs
        assert "msvc" not in stdlibs

    def test_get_supported_stdlibs_windows(self):
        """Test getting supported standard libraries for Windows."""
        stdlibs = get_supported_stdlibs("windows-x64")
        assert "libc++" in stdlibs
        assert "msvc" in stdlibs
        assert "libstdc++" not in stdlibs

    def test_get_supported_stdlibs_macos(self):
        """Test getting supported standard libraries for macOS."""
        stdlibs = get_supported_stdlibs("macos-arm64")
        assert "libc++" in stdlibs
        assert "libstdc++" not in stdlibs
        assert "msvc" not in stdlibs

    def test_get_supported_package_managers(self):
        """Test getting supported package managers."""
        for platform in [
            "linux-x64",
            "linux-arm64",
            "windows-x64",
            "macos-x64",
            "macos-arm64",
        ]:
            pkg_mgrs = get_supported_package_managers(platform)
            assert "conan" in pkg_mgrs
            assert "vcpkg" in pkg_mgrs

    def test_get_supported_build_backends_linux(self):
        """Test getting supported build backends for Linux."""
        backends = get_supported_build_backends("linux-x64")
        assert "ninja" in backends
        assert "make" in backends
        assert "msbuild" not in backends
        assert "xcode" not in backends

    def test_get_supported_build_backends_windows(self):
        """Test getting supported build backends for Windows."""
        backends = get_supported_build_backends("windows-x64")
        assert "ninja" in backends
        assert "msbuild" in backends
        assert "nmake" in backends
        assert "make" not in backends
        assert "xcode" not in backends

    def test_get_supported_build_backends_macos(self):
        """Test getting supported build backends for macOS."""
        backends = get_supported_build_backends("macos-x64")
        assert "ninja" in backends
        assert "make" in backends
        assert "xcode" in backends
        assert "msbuild" not in backends

    def test_unknown_platform_feature(self):
        """Test querying unknown platform returns safe defaults."""
        assert supports_feature("unknown-platform", "symlinks") is False
        assert supports_feature("unknown-platform", "long_paths") is False

    def test_unknown_platform_compilers(self):
        """Test querying compilers for unknown platform returns empty list."""
        assert get_supported_compilers("unknown-platform") == []

    def test_unknown_platform_stdlibs(self):
        """Test querying stdlibs for unknown platform returns empty list."""
        assert get_supported_stdlibs("unknown-platform") == []

    def test_unknown_platform_package_managers(self):
        """Test querying package managers for unknown platform returns empty list."""
        assert get_supported_package_managers("unknown-platform") == []

    def test_unknown_platform_build_backends(self):
        """Test querying build backends for unknown platform returns empty list."""
        assert get_supported_build_backends("unknown-platform") == []

    def test_get_capability_max_path_length(self):
        """Test getting max_path_length capability."""
        assert get_capability("linux-x64", "max_path_length") is None
        assert get_capability("windows-x64", "max_path_length") == 260
        assert get_capability("macos-x64", "max_path_length") is None

    def test_get_capability_executable_extension(self):
        """Test getting executable extension capability."""
        assert get_capability("linux-x64", "executable_extension") == ""
        assert get_capability("windows-x64", "executable_extension") == ".exe"
        assert get_capability("macos-x64", "executable_extension") == ""

    def test_get_capability_shared_library_extension(self):
        """Test getting shared library extension capability."""
        assert get_capability("linux-x64", "shared_library_extension") == ".so"
        assert get_capability("windows-x64", "shared_library_extension") == ".dll"
        assert get_capability("macos-x64", "shared_library_extension") == ".dylib"

    def test_get_capability_static_library_extension(self):
        """Test getting static library extension capability."""
        assert get_capability("linux-x64", "static_library_extension") == ".a"
        assert get_capability("windows-x64", "static_library_extension") == ".lib"
        assert get_capability("macos-x64", "static_library_extension") == ".a"

    def test_get_capability_case_sensitive_filesystem(self):
        """Test getting case_sensitive_filesystem capability."""
        assert get_capability("linux-x64", "case_sensitive_filesystem") is True
        assert get_capability("windows-x64", "case_sensitive_filesystem") is False
        assert get_capability("macos-x64", "case_sensitive_filesystem") is False

    def test_get_capability_path_separator(self):
        """Test getting path_separator capability."""
        assert get_capability("linux-x64", "path_separator") == "/"
        assert get_capability("windows-x64", "path_separator") == "\\"
        assert get_capability("macos-x64", "path_separator") == "/"

    def test_get_capability_supports_rpath(self):
        """Test getting supports_rpath capability."""
        assert get_capability("linux-x64", "supports_rpath") is True
        assert get_capability("windows-x64", "supports_rpath") is False
        assert get_capability("macos-x64", "supports_rpath") is True

    def test_get_capability_supports_execute_bit(self):
        """Test getting supports_execute_bit capability."""
        assert get_capability("linux-x64", "supports_execute_bit") is True
        assert get_capability("windows-x64", "supports_execute_bit") is False
        assert get_capability("macos-x64", "supports_execute_bit") is True

    def test_get_capability_unknown_platform(self):
        """Test getting capability for unknown platform returns None."""
        assert get_capability("unknown-platform", "symlinks") is None
        assert get_capability("unknown-platform", "max_path_length") is None

    def test_get_capability_unknown_capability(self):
        """Test getting unknown capability returns None."""
        assert get_capability("linux-x64", "nonexistent_capability") is None

    def test_get_all_platforms(self):
        """Test getting all supported platforms."""
        platforms = get_all_platforms()
        assert "linux-x64" in platforms
        assert "linux-arm64" in platforms
        assert "windows-x64" in platforms
        assert "macos-x64" in platforms
        assert "macos-arm64" in platforms
        assert len(platforms) == 5

    def test_is_platform_supported(self):
        """Test checking if platform is supported."""
        assert is_platform_supported("linux-x64") is True
        assert is_platform_supported("linux-arm64") is True
        assert is_platform_supported("windows-x64") is True
        assert is_platform_supported("macos-x64") is True
        assert is_platform_supported("macos-arm64") is True
        assert is_platform_supported("unknown-platform") is False

    def test_get_file_extension_executable(self):
        """Test getting executable file extensions."""
        assert get_file_extension("linux-x64", "executable") == ""
        assert get_file_extension("windows-x64", "executable") == ".exe"
        assert get_file_extension("macos-x64", "executable") == ""

    def test_get_file_extension_shared_library(self):
        """Test getting shared library file extensions."""
        assert get_file_extension("linux-x64", "shared_library") == ".so"
        assert get_file_extension("windows-x64", "shared_library") == ".dll"
        assert get_file_extension("macos-x64", "shared_library") == ".dylib"

    def test_get_file_extension_static_library(self):
        """Test getting static library file extensions."""
        assert get_file_extension("linux-x64", "static_library") == ".a"
        assert get_file_extension("windows-x64", "static_library") == ".lib"
        assert get_file_extension("macos-x64", "static_library") == ".a"

    def test_get_file_extension_unknown_type(self):
        """Test getting unknown extension type returns empty string."""
        assert get_file_extension("linux-x64", "unknown_type") == ""

    def test_get_file_extension_unknown_platform(self):
        """Test getting file extension for unknown platform returns empty string."""
        assert get_file_extension("unknown-platform", "executable") == ""

    def test_get_platform_capabilities(self):
        """Test getting all capabilities for a platform."""
        caps = get_platform_capabilities("linux-x64")
        assert caps["symlinks"] is True
        assert caps["compilers"] == ["llvm", "gcc"]
        assert caps["stdlib"] == ["libc++", "libstdc++"]
        assert caps["executable_extension"] == ""
        assert caps["shared_library_extension"] == ".so"

    def test_get_platform_capabilities_returns_copy(self):
        """Test that get_platform_capabilities returns a copy, not original dict."""
        caps = get_platform_capabilities("linux-x64")
        caps["symlinks"] = False  # Modify returned dict
        # Original should not be modified
        assert PLATFORM_CAPABILITIES["linux-x64"]["symlinks"] is True

    def test_get_platform_capabilities_unknown_platform(self):
        """Test getting capabilities for unknown platform returns empty dict."""
        caps = get_platform_capabilities("unknown-platform")
        assert caps == {}

    def test_platform_capabilities_structure(self):
        """Test that all platforms have required capability keys."""
        required_keys = [
            "symlinks",
            "long_paths",
            "max_path_length",
            "compilers",
            "stdlib",
            "package_managers",
            "build_backends",
            "executable_extension",
            "shared_library_extension",
            "static_library_extension",
            "case_sensitive_filesystem",
            "path_separator",
            "supports_rpath",
            "supports_execute_bit",
        ]

        for platform, capabilities in PLATFORM_CAPABILITIES.items():
            for key in required_keys:
                assert key in capabilities, f"Platform {platform} missing key: {key}"

    def test_platform_capabilities_types(self):
        """Test that platform capability values have correct types."""
        for platform, capabilities in PLATFORM_CAPABILITIES.items():
            assert isinstance(capabilities["symlinks"], bool)
            assert isinstance(capabilities["long_paths"], bool)
            assert capabilities["max_path_length"] is None or isinstance(
                capabilities["max_path_length"], int
            )
            assert isinstance(capabilities["compilers"], list)
            assert isinstance(capabilities["stdlib"], list)
            assert isinstance(capabilities["package_managers"], list)
            assert isinstance(capabilities["build_backends"], list)
            assert isinstance(capabilities["executable_extension"], str)
            assert isinstance(capabilities["shared_library_extension"], str)
            assert isinstance(capabilities["static_library_extension"], str)
            assert isinstance(capabilities["case_sensitive_filesystem"], bool)
            assert isinstance(capabilities["path_separator"], str)
            assert isinstance(capabilities["supports_rpath"], bool)
            assert isinstance(capabilities["supports_execute_bit"], bool)

    def test_all_platforms_have_ninja(self):
        """Test that all platforms support Ninja build backend."""
        for platform in get_all_platforms():
            backends = get_supported_build_backends(platform)
            assert "ninja" in backends, f"Platform {platform} should support Ninja"

    def test_all_platforms_have_conan_vcpkg(self):
        """Test that all platforms support Conan and vcpkg."""
        for platform in get_all_platforms():
            pkg_mgrs = get_supported_package_managers(platform)
            assert "conan" in pkg_mgrs, f"Platform {platform} should support Conan"
            assert "vcpkg" in pkg_mgrs, f"Platform {platform} should support vcpkg"

    def test_linux_platforms_consistency(self):
        """Test that Linux x64 and ARM64 have consistent capabilities."""
        linux_x64 = get_platform_capabilities("linux-x64")
        linux_arm64 = get_platform_capabilities("linux-arm64")

        # Most capabilities should be identical
        for key in [
            "symlinks",
            "long_paths",
            "max_path_length",
            "compilers",
            "stdlib",
            "package_managers",
            "build_backends",
            "executable_extension",
            "shared_library_extension",
            "static_library_extension",
            "case_sensitive_filesystem",
            "path_separator",
            "supports_rpath",
            "supports_execute_bit",
        ]:
            assert (
                linux_x64[key] == linux_arm64[key]
            ), f"Linux platforms differ on {key}"

    def test_macos_platforms_consistency(self):
        """Test that macOS x64 and ARM64 have consistent capabilities."""
        macos_x64 = get_platform_capabilities("macos-x64")
        macos_arm64 = get_platform_capabilities("macos-arm64")

        # All capabilities should be identical
        for key in macos_x64:
            assert (
                macos_x64[key] == macos_arm64[key]
            ), f"macOS platforms differ on {key}"


class TestPlatformCapabilitiesIntegration:
    """Integration tests showing how platform capabilities would be used."""

    def test_filesystem_link_strategy(self):
        """Test determining link strategy based on platform."""
        # On Linux/macOS: use symlinks
        for platform in ["linux-x64", "linux-arm64", "macos-x64", "macos-arm64"]:
            if supports_feature(platform, "symlinks"):
                link_strategy = "symlink"
            else:
                link_strategy = "junction"
            assert link_strategy == "symlink"

        # On Windows: use junctions
        if not supports_feature("windows-x64", "symlinks"):
            link_strategy = "junction"
        assert link_strategy == "junction"

    def test_toolchain_selection_by_platform(self):
        """Test selecting appropriate toolchain based on platform."""
        # Linux can use LLVM or GCC
        linux_compilers = get_supported_compilers("linux-x64")
        assert "llvm" in linux_compilers or "gcc" in linux_compilers

        # Windows can use LLVM or MSVC
        windows_compilers = get_supported_compilers("windows-x64")
        assert "llvm" in windows_compilers or "msvc" in windows_compilers

        # macOS only uses LLVM (Apple Clang)
        macos_compilers = get_supported_compilers("macos-arm64")
        assert "llvm" in macos_compilers
        assert "gcc" not in macos_compilers

    def test_executable_naming(self):
        """Test constructing executable names based on platform."""
        # Linux/macOS: no extension
        for platform in ["linux-x64", "macos-x64"]:
            ext = get_file_extension(platform, "executable")
            assert ext == ""

        # Windows: .exe extension
        ext = get_file_extension("windows-x64", "executable")
        assert ext == ".exe"

    def test_library_naming(self):
        """Test constructing library names based on platform."""
        # Linux: .so
        ext = get_file_extension("linux-x64", "shared_library")
        assert ext == ".so"

        # Windows: .dll
        ext = get_file_extension("windows-x64", "shared_library")
        assert ext == ".dll"

        # macOS: .dylib
        ext = get_file_extension("macos-x64", "shared_library")
        assert ext == ".dylib"

    def test_path_handling(self):
        """Test path handling based on platform."""
        # Unix-like systems use forward slash
        for platform in ["linux-x64", "macos-x64"]:
            sep = get_capability(platform, "path_separator")
            assert sep == "/"

        # Windows uses backslash
        sep = get_capability("windows-x64", "path_separator")
        assert sep == "\\"

    def test_rpath_support(self):
        """Test checking RPATH support for linking."""
        # Linux and macOS support RPATH
        for platform in ["linux-x64", "macos-x64"]:
            assert get_capability(platform, "supports_rpath") is True

        # Windows doesn't support RPATH
        assert get_capability("windows-x64", "supports_rpath") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
