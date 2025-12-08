"""Unit tests for configuration validation."""

import pytest
from toolchainkit.config.parser import parse_config
from toolchainkit.config.validation import (
    ConfigValidator,
    ValidationResult,
    format_validation_results,
)
from toolchainkit.core.platform import PlatformInfo


def create_test_platform(os="linux", arch="x64"):
    """Create a test platform info object."""
    return PlatformInfo(
        os=os,
        arch=arch,
        abi="glibc-2.31" if os == "linux" else "msvc" if os == "windows" else "11.0",
        os_version="20.04" if os == "linux" else "10.0" if os == "windows" else "12.0",
        distribution="ubuntu" if os == "linux" else "",
    )


@pytest.mark.unit
def test_validate_valid_config(tmp_path):
    """Test validation of valid configuration."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True


@pytest.mark.unit
def test_validate_msvc_on_linux(tmp_path):
    """Test MSVC toolchain on Linux generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: msvc-2022
    type: msvc
    version: 17.8.0
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    assert len([i for i in result.issues if i.level == "error"]) == 1
    error = next(i for i in result.issues if i.level == "error")
    assert "msvc-2022" in error.field
    assert "Windows" in error.message


@pytest.mark.unit
def test_validate_invalid_version_format(tmp_path):
    """Test invalid version format generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc
    type: gcc
    version: invalid
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    assert len(errors) == 1
    assert "version" in errors[0].field
    assert "Invalid version format" in errors[0].message


@pytest.mark.unit
def test_validate_gcc_with_wrong_stdlib(tmp_path):
    """Test GCC with wrong stdlib generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0
    stdlib: libc++
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "stdlib" in i.field), None)
    assert warning is not None
    assert "libstdc++" in warning.message


@pytest.mark.unit
def test_validate_msvc_with_stdlib(tmp_path):
    """Test MSVC with stdlib generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: msvc-2022
    type: msvc
    version: 17.8.0
    stdlib: libc++
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("windows", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "stdlib" in i.field), None)
    assert warning is not None


@pytest.mark.unit
def test_validate_caching_enabled_without_tool(tmp_path):
    """Test caching enabled without tool generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

build:
  caching:
    enabled: true
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    assert len(errors) == 1
    assert "caching" in errors[0].field
    assert "no tool specified" in errors[0].message


@pytest.mark.unit
def test_validate_invalid_caching_tool(tmp_path):
    """Test invalid caching tool generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

build:
  caching:
    enabled: true
    tool: invalid
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    assert any("Unsupported caching tool" in e.message for e in errors)


@pytest.mark.unit
def test_validate_android_without_api_level(tmp_path):
    """Test Android target without API level generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: android
    arch: arm64
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "android" in i.field), None)
    assert warning is not None
    assert "api_level" in warning.message


@pytest.mark.unit
def test_validate_android_old_api_level(tmp_path):
    """Test Android target with old API level generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: android
    arch: arm64
    api_level: 16
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "api_level" in i.field), None)
    assert warning is not None
    assert "16" in warning.message


@pytest.mark.unit
def test_validate_ios_on_linux(tmp_path):
    """Test iOS target on Linux generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: ios
    arch: arm64
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    assert len(errors) == 1
    assert "ios" in errors[0].field
    assert "macOS" in errors[0].message


@pytest.mark.unit
def test_validate_ios_on_macos(tmp_path):
    """Test iOS target on macOS is valid."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: ios
    arch: arm64
    sdk: iphoneos
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("macos", "arm64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True
    errors = [i for i in result.issues if i.level == "error"]
    assert len(errors) == 0


@pytest.mark.unit
def test_validate_missing_required_module(tmp_path):
    """Test missing required module generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

modules:
  - caching
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    # Should have 2 errors: missing 'core' and missing 'cmake'
    assert len(errors) >= 2


@pytest.mark.unit
def test_validate_caching_module_without_enabled(tmp_path):
    """Test caching module without enabled generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

modules:
  - core
  - cmake
  - caching
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "modules" in i.field), None)
    assert warning is not None
    assert "caching" in warning.message


@pytest.mark.unit
def test_validate_packages_module_without_config(tmp_path):
    """Test packages module without package config generates warning."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: gcc-13
    type: gcc
    version: 13.2.0

modules:
  - core
  - cmake
  - packages
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is True  # Warning, not error
    warnings = [i for i in result.issues if i.level == "warning"]
    assert len(warnings) >= 1
    warning = next((i for i in warnings if "packages" in i.message), None)
    assert warning is not None


@pytest.mark.unit
def test_validate_target_undefined_toolchain(tmp_path):
    """Test target referencing undefined toolchain generates error."""
    # Arrange
    config_file = tmp_path / "toolchainkit.yaml"
    config_file.write_text(
        """
version: 1
toolchains:
  - name: llvm-18
    type: clang
    version: 18.1.8

targets:
  - os: android
    arch: arm64
    toolchain: gcc-13
"""
    )

    config = parse_config(config_file)
    platform = create_test_platform("linux", "x64")
    validator = ConfigValidator(platform)

    # Act
    result = validator.validate(config)

    # Assert
    assert result.valid is False
    errors = [i for i in result.issues if i.level == "error"]
    assert len(errors) == 1
    assert "toolchain" in errors[0].field
    assert "undefined toolchain" in errors[0].message


@pytest.mark.unit
def test_format_validation_results_valid():
    """Test formatting valid result."""
    # Arrange
    result = ValidationResult(valid=True, issues=[])

    # Act
    output = format_validation_results(result)

    # Assert
    assert "✓ Configuration is valid" in output


@pytest.mark.unit
def test_format_validation_results_with_errors():
    """Test formatting result with errors."""
    # Arrange
    from toolchainkit.config.validation import ValidationIssue

    result = ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                level="error",
                field="toolchains.msvc",
                message="MSVC only works on Windows",
                suggestion="Use clang or gcc",
            )
        ],
    )

    # Act
    output = format_validation_results(result)

    # Assert
    assert "❌ Errors:" in output
    assert "toolchains.msvc" in output
    assert "MSVC only works on Windows" in output
    assert "Use clang or gcc" in output


@pytest.mark.unit
def test_format_validation_results_with_warnings():
    """Test formatting result with warnings."""
    # Arrange
    from toolchainkit.config.validation import ValidationIssue

    result = ValidationResult(
        valid=True,
        issues=[
            ValidationIssue(
                level="warning",
                field="build.backend",
                message="Ninja not found on PATH",
                suggestion="Install ninja",
            )
        ],
    )

    # Act
    output = format_validation_results(result)

    # Assert
    assert "⚠️  Warnings:" in output
    assert "build.backend" in output
    assert "Ninja not found" in output


@pytest.mark.unit
def test_format_validation_results_with_info():
    """Test formatting result with info."""
    # Arrange
    from toolchainkit.config.validation import ValidationIssue

    result = ValidationResult(
        valid=True,
        issues=[
            ValidationIssue(
                level="info",
                field="defaults",
                message="No default for linux",
                suggestion="Add defaults.linux",
            )
        ],
    )

    # Act
    output = format_validation_results(result)

    # Assert
    assert "ℹ️  Info:" in output
    assert "defaults" in output
    assert "No default for linux" in output


@pytest.mark.unit
def test_format_validation_results_mixed():
    """Test formatting result with mixed issue levels."""
    # Arrange
    from toolchainkit.config.validation import ValidationIssue

    result = ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                level="error",
                field="build.caching",
                message="No tool specified",
                suggestion="Set tool",
            ),
            ValidationIssue(
                level="warning",
                field="targets.android",
                message="No API level",
                suggestion="Specify api_level",
            ),
            ValidationIssue(
                level="info",
                field="defaults",
                message="No default",
                suggestion="Add default",
            ),
        ],
    )

    # Act
    output = format_validation_results(result)

    # Assert
    assert "❌ Errors:" in output
    assert "⚠️  Warnings:" in output
    assert "ℹ️  Info:" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
