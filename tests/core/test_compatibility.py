"""
Unit tests for configuration compatibility validation.

Tests cover:
- Compiler/platform compatibility checking
- Bootstrap validation for unsupported configurations
- Platform-specific compiler restrictions
- Standard library compatibility
- Generator compatibility
"""

import pytest
from unittest.mock import patch

from toolchainkit.core.compatibility import (
    CompatibilityValidator,
    validate_bootstrap_compatibility,
    check_compiler_platform_compatibility,
)
from toolchainkit.core.platform import PlatformInfo


@pytest.fixture
def linux_platform():
    """Create a Linux x64 platform."""
    return PlatformInfo(
        os="linux",
        arch="x64",
        os_version="5.15",
        distribution="ubuntu",
        abi="glibc-2.31",
    )


@pytest.fixture
def windows_platform():
    """Create a Windows x64 platform."""
    return PlatformInfo(
        os="windows",
        arch="x64",
        os_version="10.0.19041",
        distribution="",
        abi="msvc",
    )


@pytest.fixture
def macos_platform():
    """Create a macOS ARM64 platform."""
    return PlatformInfo(
        os="macos",
        arch="arm64",
        os_version="14.1",
        distribution="",
        abi="macos-11.0",
    )


class TestCompatibilityValidator:
    """Test CompatibilityValidator class."""

    def test_init_with_platform(self, linux_platform):
        """Test validator initialization with platform."""
        validator = CompatibilityValidator(linux_platform)
        assert validator.target_platform == linux_platform
        assert validator.platform_string == "linux-x64"

    def test_init_without_platform(self):
        """Test validator uses current platform when not specified."""
        validator = CompatibilityValidator()
        assert validator.target_platform is not None
        assert validator.platform_string is not None

    def test_compiler_aliases_normalization(self, linux_platform):
        """Test compiler type normalization."""
        validator = CompatibilityValidator(linux_platform)
        # Note: llvm and clang both normalize to "llvm" (platform_capabilities canonical name)
        assert validator._normalize_compiler_type("llvm") == "llvm"
        assert validator._normalize_compiler_type("LLVM") == "llvm"
        assert validator._normalize_compiler_type("clang") == "llvm"
        assert validator._normalize_compiler_type("gcc") == "gcc"
        assert validator._normalize_compiler_type("msvc") == "msvc"


class TestCompilerPlatformCompatibility:
    """Test compiler/platform compatibility checks."""

    def test_gcc_supported_on_linux(self, linux_platform):
        """Test GCC is supported on Linux."""
        validator = CompatibilityValidator(linux_platform)
        assert validator.validate_compiler_for_platform("gcc") is True
        assert validator.get_unsupported_reason("gcc") == ""

    def test_gcc_not_supported_on_windows(self, windows_platform):
        """Test GCC is not supported on Windows."""
        validator = CompatibilityValidator(windows_platform)
        assert validator.validate_compiler_for_platform("gcc") is False
        reason = validator.get_unsupported_reason("gcc")
        assert "not supported on Windows" in reason
        assert "MinGW" in reason

    def test_gcc_not_supported_on_macos(self, macos_platform):
        """Test GCC is not supported on macOS."""
        validator = CompatibilityValidator(macos_platform)
        assert validator.validate_compiler_for_platform("gcc") is False
        reason = validator.get_unsupported_reason("gcc")
        assert "not officially supported on macOS" in reason
        assert "Apple Clang" in reason

    def test_msvc_supported_on_windows(self, windows_platform):
        """Test MSVC is supported on Windows."""
        validator = CompatibilityValidator(windows_platform)
        assert validator.validate_compiler_for_platform("msvc") is True
        assert validator.get_unsupported_reason("msvc") == ""

    def test_msvc_not_supported_on_linux(self, linux_platform):
        """Test MSVC is not supported on Linux."""
        validator = CompatibilityValidator(linux_platform)
        assert validator.validate_compiler_for_platform("msvc") is False
        reason = validator.get_unsupported_reason("msvc")
        assert "only available on Windows" in reason

    def test_msvc_not_supported_on_macos(self, macos_platform):
        """Test MSVC is not supported on macOS."""
        validator = CompatibilityValidator(macos_platform)
        assert validator.validate_compiler_for_platform("msvc") is False
        reason = validator.get_unsupported_reason("msvc")
        assert "only available on Windows" in reason

    def test_clang_supported_on_linux(self, linux_platform):
        """Test Clang is supported on Linux."""
        validator = CompatibilityValidator(linux_platform)
        assert validator.validate_compiler_for_platform("clang") is True
        assert validator.validate_compiler_for_platform("llvm") is True

    def test_clang_supported_on_windows(self, windows_platform):
        """Test Clang is supported on Windows."""
        validator = CompatibilityValidator(windows_platform)
        assert validator.validate_compiler_for_platform("clang") is True
        assert validator.validate_compiler_for_platform("llvm") is True

    def test_clang_supported_on_macos(self, macos_platform):
        """Test Clang is supported on macOS."""
        validator = CompatibilityValidator(macos_platform)
        assert validator.validate_compiler_for_platform("clang") is True
        assert validator.validate_compiler_for_platform("llvm") is True


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_valid_gcc_on_linux(self, linux_platform):
        """Test valid GCC configuration on Linux."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}
        result = validator.validate_configuration(config)
        assert result.valid is True
        assert len(result.issues) == 0

    def test_invalid_gcc_on_windows(self, windows_platform):
        """Test invalid GCC configuration on Windows."""
        validator = CompatibilityValidator(windows_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}
        result = validator.validate_configuration(config, for_bootstrap=True)
        assert result.valid is False
        assert len(result.issues) > 0
        assert result.issues[0].level == "error"
        assert result.issues[0].category == "compiler"
        assert "not supported on Windows" in result.issues[0].message

    def test_invalid_gcc_on_macos(self, macos_platform):
        """Test invalid GCC configuration on macOS."""
        validator = CompatibilityValidator(macos_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}
        result = validator.validate_configuration(config, for_bootstrap=True)
        assert result.valid is False
        assert len(result.issues) > 0
        assert result.issues[0].level == "error"
        assert "not officially supported on macOS" in result.issues[0].message

    def test_invalid_msvc_on_linux(self, linux_platform):
        """Test invalid MSVC configuration on Linux."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "msvc", "name": "msvc-2022"}}
        result = validator.validate_configuration(config, for_bootstrap=True)
        assert result.valid is False
        assert len(result.issues) > 0
        assert "only available on Windows" in result.issues[0].message

    def test_valid_clang_on_all_platforms(
        self, linux_platform, windows_platform, macos_platform
    ):
        """Test Clang is valid on all platforms."""
        config = {"toolchain": {"type": "clang", "name": "llvm-18"}}

        for platform in [linux_platform, windows_platform, macos_platform]:
            validator = CompatibilityValidator(platform)
            result = validator.validate_configuration(config)
            assert (
                result.valid is True
            ), f"Clang should be valid on {platform.platform_string()}"

    def test_toolchain_name_inference(self, linux_platform):
        """Test toolchain type inference from name."""
        validator = CompatibilityValidator(linux_platform)

        # Should infer gcc from name
        config = {"toolchain": "gcc-13"}
        result = validator.validate_configuration(config)
        assert result.valid is True

        # Should infer clang from name
        config = {"toolchain": "llvm-18"}
        result = validator.validate_configuration(config)
        assert result.valid is True


class TestStdlibValidation:
    """Test standard library validation."""

    def test_valid_libcxx_on_linux(self, linux_platform):
        """Test libc++ is valid on Linux."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "clang", "name": "llvm-18", "stdlib": "libc++"}}
        result = validator.validate_configuration(config)
        assert result.valid is True

    def test_valid_libstdcxx_on_linux(self, linux_platform):
        """Test libstdc++ is valid on Linux."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13", "stdlib": "libstdc++"}}
        result = validator.validate_configuration(config)
        assert result.valid is True

    def test_gcc_with_libcxx_warning(self, linux_platform):
        """Test warning for GCC with libc++."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13", "stdlib": "libc++"}}
        result = validator.validate_configuration(config)
        # Should be valid but with warnings
        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("manual setup" in w.message for w in result.warnings)

    def test_msvc_with_wrong_stdlib_warning(self, windows_platform):
        """Test warning for MSVC with non-msvc stdlib."""
        validator = CompatibilityValidator(windows_platform)
        config = {
            "toolchain": {"type": "msvc", "name": "msvc-2022", "stdlib": "libc++"}
        }
        result = validator.validate_configuration(config)
        # Should be valid but with warnings
        assert result.valid is True
        assert len(result.warnings) > 0


class TestGeneratorValidation:
    """Test CMake generator validation."""

    def test_xcode_only_on_macos(self, macos_platform, linux_platform):
        """Test Xcode generator only works on macOS."""
        # Valid on macOS
        validator = CompatibilityValidator(macos_platform)
        config = {
            "toolchain": {"type": "clang", "name": "llvm-18"},
            "generator": "Xcode",
        }
        result = validator.validate_configuration(config)
        assert result.valid is True

        # Invalid on Linux
        validator = CompatibilityValidator(linux_platform)
        result = validator.validate_configuration(config)
        assert result.valid is False
        assert any("Xcode" in i.message for i in result.issues)

    def test_visual_studio_only_on_windows(self, windows_platform, linux_platform):
        """Test Visual Studio generator only works on Windows."""
        # Valid on Windows
        validator = CompatibilityValidator(windows_platform)
        config = {
            "toolchain": {"type": "msvc", "name": "msvc-2022"},
            "generator": "Visual Studio 17 2022",
        }
        result = validator.validate_configuration(config)
        assert result.valid is True

        # Invalid on Linux
        validator = CompatibilityValidator(linux_platform)
        config = {
            "toolchain": {"type": "clang", "name": "llvm-18"},
            "generator": "Visual Studio 17 2022",
        }
        result = validator.validate_configuration(config)
        assert result.valid is False
        assert any("Visual Studio" in i.message for i in result.issues)

    def test_msbuild_only_on_windows(self, windows_platform, linux_platform):
        """Test MSBuild generator only works on Windows."""
        validator = CompatibilityValidator(linux_platform)
        config = {
            "toolchain": {"type": "clang", "name": "llvm-18"},
            "generator": "MSBuild",
        }
        result = validator.validate_configuration(config)
        assert result.valid is False


class TestBootstrapValidation:
    """Test bootstrap-specific validation."""

    def test_bootstrap_validation_errors_are_strict(self, windows_platform):
        """Test bootstrap validation treats issues as errors."""
        validator = CompatibilityValidator(windows_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}

        # Bootstrap validation should be error
        result_bootstrap = validator.validate_configuration(config, for_bootstrap=True)
        assert result_bootstrap.valid is False
        assert len(result_bootstrap.issues) > 0
        assert result_bootstrap.issues[0].level == "error"

    def test_validate_bootstrap_compatibility_function(self):
        """Test convenience function for bootstrap validation."""
        with patch("toolchainkit.core.compatibility.detect_platform") as mock_detect:
            mock_detect.return_value = PlatformInfo(
                os="windows", arch="x64", os_version="10.0", distribution="", abi="msvc"
            )

            config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}
            result = validate_bootstrap_compatibility(config)

            assert result.valid is False
            assert len(result.issues) > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_check_compiler_platform_compatibility(self):
        """Test check_compiler_platform_compatibility function."""
        # GCC on Linux should be OK
        assert check_compiler_platform_compatibility("gcc", "linux-x64") is True

        # GCC on Windows should fail
        assert check_compiler_platform_compatibility("gcc", "windows-x64") is False

        # Clang everywhere should be OK
        assert check_compiler_platform_compatibility("clang", "linux-x64") is True
        assert check_compiler_platform_compatibility("clang", "windows-x64") is True
        assert check_compiler_platform_compatibility("clang", "macos-arm64") is True


class TestExtractToolchainInfo:
    """Test toolchain info extraction from config."""

    def test_extract_from_toolchain_dict(self, linux_platform):
        """Test extraction from toolchain dict."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": {"type": "gcc", "name": "gcc-13"}}
        info = validator._extract_toolchain_info(config)
        assert info is not None
        assert info["type"] == "gcc"
        assert info["name"] == "gcc-13"

    def test_extract_from_toolchain_string(self, linux_platform):
        """Test extraction from toolchain string."""
        validator = CompatibilityValidator(linux_platform)
        config = {"toolchain": "gcc-13"}
        info = validator._extract_toolchain_info(config)
        assert info is not None
        assert info["type"] == "gcc"  # Inferred from name

    def test_extract_from_defaults(self, linux_platform):
        """Test extraction from defaults section."""
        validator = CompatibilityValidator(linux_platform)
        config = {
            "defaults": {"toolchain": "main-toolchain"},
            "toolchains": [
                {"name": "main-toolchain", "type": "gcc", "version": "13.2.0"}
            ],
        }
        info = validator._extract_toolchain_info(config)
        assert info is not None
        assert info["type"] == "gcc"

    def test_no_toolchain_returns_none(self, linux_platform):
        """Test returns None when no toolchain specified."""
        validator = CompatibilityValidator(linux_platform)
        config = {}
        info = validator._extract_toolchain_info(config)
        assert info is None


class TestAlternativeCompilersSuggestion:
    """Test alternative compiler suggestions."""

    def test_linux_suggestions(self, linux_platform):
        """Test suggestions for Linux."""
        validator = CompatibilityValidator(linux_platform)
        suggestion = validator._get_alternative_compilers_suggestion()
        assert "linux-x64" in suggestion
        assert any(compiler in suggestion for compiler in ["llvm", "gcc", "clang"])

    def test_windows_suggestions(self, windows_platform):
        """Test suggestions for Windows."""
        validator = CompatibilityValidator(windows_platform)
        suggestion = validator._get_alternative_compilers_suggestion()
        assert "windows-x64" in suggestion
        assert any(compiler in suggestion for compiler in ["llvm", "msvc", "clang"])

    def test_macos_suggestions(self, macos_platform):
        """Test suggestions for macOS."""
        validator = CompatibilityValidator(macos_platform)
        suggestion = validator._get_alternative_compilers_suggestion()
        assert "macos-arm64" in suggestion
        assert any(compiler in suggestion for compiler in ["llvm", "clang"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
