"""Configuration validation module for ToolchainKit.

This module provides semantic validation for parsed configuration with
platform compatibility checks, version validation, and helpful suggestions.
"""

from dataclasses import dataclass
from typing import List
import re
import shutil
from toolchainkit.config.parser import ToolchainKitConfig, ToolchainConfig
from toolchainkit.core.platform import PlatformInfo
from toolchainkit.core.platform_capabilities import get_supported_compilers


@dataclass
class ValidationIssue:
    """A single validation issue."""

    level: str  # 'error', 'warning', 'info'
    field: str  # Configuration field path
    message: str  # Human-readable message
    suggestion: str  # How to fix it


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    issues: List[ValidationIssue]


class ConfigValidator:
    """Validates ToolchainKit configuration."""

    def __init__(self, platform_info: PlatformInfo):
        """
        Initialize validator with platform information.

        Args:
            platform_info: Current platform information
        """
        self.platform = platform_info
        self.issues: List[ValidationIssue] = []

    def validate(self, config: ToolchainKitConfig) -> ValidationResult:
        """
        Perform comprehensive validation.

        Args:
            config: Parsed configuration to validate

        Returns:
            ValidationResult with any issues found
        """
        self.issues = []

        # Run all validation checks
        self._validate_toolchains(config)
        self._validate_defaults(config)
        self._validate_build_config(config)
        self._validate_packages(config)
        self._validate_targets(config)
        self._validate_modules(config)

        # Check for errors
        has_errors = any(issue.level == "error" for issue in self.issues)

        return ValidationResult(valid=not has_errors, issues=self.issues)

    def _validate_toolchains(self, config: ToolchainKitConfig):
        """Validate toolchain definitions."""
        for tc in config.toolchains:
            # Check platform compatibility using platform_capabilities
            platform_string = self.platform.platform_string()
            supported_compilers = get_supported_compilers(platform_string)

            # Normalize compiler type for comparison (clang -> llvm for canonical name)
            compiler_type = tc.type.lower()
            if compiler_type == "clang":
                compiler_type = "llvm"  # Normalize clang to llvm (canonical name)

            if compiler_type not in supported_compilers:
                if tc.type == "msvc" and self.platform.os != "windows":
                    self._add_error(
                        f"toolchains.{tc.name}",
                        "MSVC toolchain only works on Windows",
                        f"Use clang or gcc for {self.platform.os}",
                    )
                elif tc.type.lower() in ["gcc"] and self.platform.os == "windows":
                    self._add_error(
                        f"toolchains.{tc.name}",
                        "GCC is not supported on Windows in toolchainkit",
                        "Use LLVM/Clang or MSVC instead. MinGW support may be added in future releases.",
                    )
                elif tc.type.lower() in ["gcc"] and self.platform.os == "macos":
                    self._add_error(
                        f"toolchains.{tc.name}",
                        "GCC is not officially supported on macOS in toolchainkit",
                        "Use LLVM/Clang (Apple Clang) instead.",
                    )
                else:
                    self._add_error(
                        f"toolchains.{tc.name}",
                        f"Compiler type '{tc.type}' is not supported on {platform_string}",
                        f"Supported compilers for {platform_string}: {', '.join(supported_compilers)}",
                    )

            # Validate version format
            if not self._is_valid_version(tc.version):
                self._add_error(
                    f"toolchains.{tc.name}.version",
                    f"Invalid version format: {tc.version}",
                    "Use semantic version format (e.g., 18.1.8)",
                )

            # Check stdlib compatibility
            if tc.stdlib:
                self._validate_stdlib(tc)

    def _validate_stdlib(self, tc: ToolchainConfig):
        """Validate standard library configuration."""
        if tc.type == "gcc" and tc.stdlib not in [None, "libstdc++"]:
            self._add_warning(
                f"toolchains.{tc.name}.stdlib",
                f"GCC typically uses libstdc++, not {tc.stdlib}",
                "Remove stdlib or set to libstdc++",
            )

        if (
            tc.type == "clang"
            and tc.stdlib
            and tc.stdlib not in ["libc++", "libstdc++"]
        ):
            self._add_warning(
                f"toolchains.{tc.name}.stdlib",
                f"Clang typically uses libc++ or libstdc++, not {tc.stdlib}",
                "Set stdlib to libc++ or libstdc++",
            )

        if tc.type == "msvc" and tc.stdlib not in [None, "msvc"]:
            self._add_warning(
                f"toolchains.{tc.name}.stdlib",
                "MSVC uses its own standard library",
                "Remove stdlib setting for MSVC",
            )

    def _validate_defaults(self, config: ToolchainKitConfig):
        """Validate default toolchain selections."""
        # Check if current platform has a default
        platform_name = self.platform.os
        if platform_name not in config.defaults and len(config.toolchains) > 1:
            self._add_info(
                "defaults",
                f"No default toolchain for {platform_name}",
                f'Add "defaults.{platform_name}: {config.toolchains[0].name}" to specify',
            )

    def _validate_build_config(self, config: ToolchainKitConfig):
        """Validate build configuration."""
        build = config.build

        # Check backend availability
        if build.backend == "ninja":
            if not self._is_tool_available("ninja"):
                self._add_warning(
                    "build.backend",
                    "Ninja not found on PATH",
                    "Install ninja or bootstrap will download it",
                )
        elif build.backend == "make":
            if not self._is_tool_available("make"):
                self._add_warning(
                    "build.backend",
                    "Make not found on PATH",
                    "Install make or change backend to ninja",
                )

        # Validate caching config
        if build.caching.enabled:
            if not build.caching.tool:
                self._add_error(
                    "build.caching",
                    "Caching enabled but no tool specified",
                    "Set build.caching.tool to sccache or ccache",
                )
            elif build.caching.tool not in ["sccache", "ccache"]:
                self._add_error(
                    "build.caching.tool",
                    f"Unsupported caching tool: {build.caching.tool}",
                    "Use sccache or ccache",
                )
            elif not self._is_tool_available(build.caching.tool):
                self._add_warning(
                    "build.caching.tool",
                    f"{build.caching.tool} not found on PATH",
                    f"Install {build.caching.tool} or bootstrap will download it",
                )

    def _validate_packages(self, config: ToolchainKitConfig):
        """Validate package manager configuration."""
        if not config.packages:
            return

        pkg = config.packages

        if pkg.manager == "conan":
            if not pkg.conan:
                self._add_info(
                    "packages.conan",
                    "Using default Conan configuration",
                    "Customize with packages.conan section if needed",
                )
        elif pkg.manager == "vcpkg":
            if not pkg.vcpkg:
                self._add_info(
                    "packages.vcpkg",
                    "Using default vcpkg configuration",
                    "Customize with packages.vcpkg section if needed",
                )

    def _validate_targets(self, config: ToolchainKitConfig):
        """Validate cross-compilation targets."""
        for target in config.targets:
            # Android-specific validation
            if target.os == "android":
                if not target.api_level:
                    self._add_warning(
                        f"targets.{target.os}-{target.arch}",
                        "Android target without api_level",
                        "Specify api_level (e.g., 29 for Android 10)",
                    )
                elif target.api_level < 21:
                    self._add_warning(
                        f"targets.{target.os}-{target.arch}.api_level",
                        f"Android API {target.api_level} is very old",
                        "Consider API 21+ for modern features",
                    )

            # iOS-specific validation
            if target.os == "ios":
                if self.platform.os != "macos":
                    self._add_error(
                        f"targets.{target.os}-{target.arch}",
                        "iOS targets require macOS host",
                        "Remove iOS target or build on macOS",
                    )

                if not target.sdk:
                    self._add_info(
                        f"targets.{target.os}-{target.arch}",
                        "iOS target without SDK specified",
                        "Specify sdk (e.g., iphoneos or iphonesimulator)",
                    )

            # Check if toolchain is specified and exists
            if target.toolchain:
                toolchain_exists = any(
                    tc.name == target.toolchain for tc in config.toolchains
                )
                if not toolchain_exists:
                    self._add_error(
                        f"targets.{target.os}-{target.arch}.toolchain",
                        f"Target references undefined toolchain: {target.toolchain}",
                        "Use a toolchain name from the toolchains list",
                    )

    def _validate_modules(self, config: ToolchainKitConfig):
        """Validate module selection."""
        required_modules = ["core", "cmake"]

        for module in required_modules:
            if module not in config.modules:
                self._add_error(
                    "modules",
                    f"Required module missing: {module}",
                    f"Add {module} to modules list",
                )

        # Check module dependencies
        if "caching" in config.modules and not config.build.caching.enabled:
            self._add_warning(
                "modules",
                "caching module enabled but build.caching.enabled is false",
                "Either enable caching or remove module",
            )

        if "packages" in config.modules and not config.packages:
            self._add_warning(
                "modules",
                "packages module enabled but no package manager configured",
                "Configure a package manager or remove module",
            )

    def _add_error(self, field: str, message: str, suggestion: str):
        """Add error issue."""
        self.issues.append(
            ValidationIssue(
                level="error", field=field, message=message, suggestion=suggestion
            )
        )

    def _add_warning(self, field: str, message: str, suggestion: str):
        """Add warning issue."""
        self.issues.append(
            ValidationIssue(
                level="warning", field=field, message=message, suggestion=suggestion
            )
        )

    def _add_info(self, field: str, message: str, suggestion: str):
        """Add info issue."""
        self.issues.append(
            ValidationIssue(
                level="info", field=field, message=message, suggestion=suggestion
            )
        )

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Check if version string is valid."""
        # Semantic version: X.Y.Z or X.Y
        pattern = r"^\d+\.\d+(\.\d+)?$"
        return re.match(pattern, version) is not None

    @staticmethod
    def _is_tool_available(tool: str) -> bool:
        """Check if tool is available on PATH."""
        return shutil.which(tool) is not None


def format_validation_results(result: ValidationResult) -> str:
    """
    Format validation results for display.

    Args:
        result: Validation result to format

    Returns:
        Formatted string for display
    """
    if result.valid and not result.issues:
        return "✓ Configuration is valid"

    lines = []

    # Group by level
    errors = [i for i in result.issues if i.level == "error"]
    warnings = [i for i in result.issues if i.level == "warning"]
    infos = [i for i in result.issues if i.level == "info"]

    if errors:
        lines.append("❌ Errors:")
        for issue in errors:
            lines.append(f"  {issue.field}: {issue.message}")
            lines.append(f"    → {issue.suggestion}")
        lines.append("")

    if warnings:
        lines.append("⚠️  Warnings:")
        for issue in warnings:
            lines.append(f"  {issue.field}: {issue.message}")
            lines.append(f"    → {issue.suggestion}")
        lines.append("")

    if infos:
        lines.append("ℹ️  Info:")
        for issue in infos:
            lines.append(f"  {issue.field}: {issue.message}")
            lines.append(f"    → {issue.suggestion}")

    return "\n".join(lines).rstrip()
