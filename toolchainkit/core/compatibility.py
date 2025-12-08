"""Configuration compatibility validation module.

This module validates compiler/platform combinations and other configuration
compatibility issues before generating bootstrap scripts or configuring toolchains.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from toolchainkit.core.platform import PlatformInfo, detect_platform
from toolchainkit.core.platform_capabilities import (
    get_supported_compilers,
    get_supported_stdlibs,
)

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityIssue:
    """Represents a compatibility issue."""

    level: str  # 'error', 'warning', 'info'
    category: str  # 'compiler', 'stdlib', 'platform', 'generator', etc.
    message: str
    suggestion: str


@dataclass
class CompatibilityResult:
    """Result of compatibility validation."""

    valid: bool
    issues: List[CompatibilityIssue]
    warnings: List[CompatibilityIssue]


class CompatibilityValidator:
    """Validates compatibility of configuration with target platform."""

    # Compiler to platform compatibility mapping
    COMPILER_PLATFORM_SUPPORT = {
        "gcc": [
            "linux-x64",
            "linux-arm64",
        ],  # GCC not supported on Windows/macOS in toolchainkit
        "clang": [
            "linux-x64",
            "linux-arm64",
            "macos-x64",
            "macos-arm64",
            "windows-x64",
        ],  # Clang everywhere
        "llvm": [
            "linux-x64",
            "linux-arm64",
            "macos-x64",
            "macos-arm64",
            "windows-x64",
        ],  # LLVM/Clang everywhere
        "msvc": ["windows-x64"],  # MSVC only on Windows
    }

    # Compiler type normalization (handle aliases)
    # Note: platform_capabilities uses "llvm" as the canonical name for Clang/LLVM
    COMPILER_ALIASES = {
        "llvm": "llvm",
        "clang": "llvm",  # Normalize clang to llvm (used in platform_capabilities)
        "gcc": "gcc",
        "msvc": "msvc",
    }

    def __init__(self, target_platform: Optional[PlatformInfo] = None):
        """Initialize validator with target platform.

        Args:
            target_platform: Target platform to validate against. If None, uses current platform.
        """
        self.target_platform = target_platform or detect_platform()
        self.platform_string = self.target_platform.platform_string()
        self.issues: List[CompatibilityIssue] = []

    def validate_configuration(
        self, config: Dict[str, Any], for_bootstrap: bool = False
    ) -> CompatibilityResult:
        """Validate complete configuration for compatibility.

        Args:
            config: Configuration dictionary (flattened config from toolchainkit.yaml)
            for_bootstrap: If True, validation is for bootstrap script generation

        Returns:
            CompatibilityResult with validation results
        """
        self.issues = []

        # Extract toolchain information
        toolchain = self._extract_toolchain_info(config)
        if not toolchain:
            # No toolchain specified - this is handled elsewhere
            return CompatibilityResult(valid=True, issues=[], warnings=[])

        compiler_type = toolchain.get("type", "").lower()
        stdlib = toolchain.get("stdlib")
        generator = config.get("generator")

        # Validate compiler/platform compatibility
        self._validate_compiler_platform(compiler_type, for_bootstrap)

        # Validate stdlib compatibility
        if stdlib:
            self._validate_stdlib_platform(stdlib, compiler_type)

        # Validate generator compatibility
        if generator:
            self._validate_generator_platform(generator)

        # Separate errors and warnings
        errors = [issue for issue in self.issues if issue.level == "error"]
        warnings = [issue for issue in self.issues if issue.level == "warning"]

        return CompatibilityResult(
            valid=len(errors) == 0,
            issues=errors,
            warnings=warnings,
        )

    def validate_compiler_for_platform(
        self, compiler_type: str, platform_string: Optional[str] = None
    ) -> bool:
        """Check if compiler is supported on platform.

        Args:
            compiler_type: Compiler type (gcc, clang, llvm, msvc)
            platform_string: Platform string (e.g., 'linux-x64'). Uses target platform if None.

        Returns:
            True if compiler is supported on platform
        """
        platform = platform_string or self.platform_string
        compiler = self._normalize_compiler_type(compiler_type)

        supported_compilers = get_supported_compilers(platform)
        return compiler in supported_compilers

    def get_unsupported_reason(
        self, compiler_type: str, platform_string: Optional[str] = None
    ) -> str:
        """Get reason why compiler is not supported on platform.

        Args:
            compiler_type: Compiler type (gcc, clang, llvm, msvc)
            platform_string: Platform string. Uses target platform if None.

        Returns:
            Human-readable reason, or empty string if supported
        """
        platform = platform_string or self.platform_string
        compiler = self._normalize_compiler_type(compiler_type)

        if self.validate_compiler_for_platform(compiler, platform):
            return ""

        # Generate helpful message
        if compiler == "gcc":
            if platform.startswith("windows"):
                return (
                    "GCC is not supported on Windows in toolchainkit. "
                    "Use LLVM/Clang or MSVC instead. "
                    "MinGW/MinGW-w64 support may be added in future releases."
                )
            elif platform.startswith("macos"):
                return (
                    "GCC is not officially supported on macOS in toolchainkit. "
                    "macOS uses Apple Clang as the primary compiler. "
                    "Use LLVM/Clang instead."
                )
        elif compiler == "msvc":
            if not platform.startswith("windows"):
                return (
                    f"MSVC is only available on Windows. "
                    f"For {platform}, use LLVM/Clang or GCC instead."
                )
        elif compiler in ["clang", "llvm"]:
            # Clang should be supported everywhere
            return f"Unexpected: Clang/LLVM should be supported on {platform}"

        return f"Compiler '{compiler_type}' is not supported on {platform}"

    def _extract_toolchain_info(
        self, config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract toolchain information from flattened config.

        Args:
            config: Flattened configuration dictionary

        Returns:
            Dictionary with toolchain info, or None if not found
        """
        # Handle different config structures
        if "toolchain" in config:
            if isinstance(config["toolchain"], dict):
                return config["toolchain"]
            elif isinstance(config["toolchain"], str):
                # Just a name, need to infer type
                name = config["toolchain"]
                # Try to infer from name
                for compiler in ["gcc", "clang", "llvm", "msvc"]:
                    if compiler in name.lower():
                        return {"type": compiler, "name": name}
                return {"type": "unknown", "name": name}

        # Try to extract from defaults
        if "defaults" in config and isinstance(config["defaults"], dict):
            toolchain_name = config["defaults"].get("toolchain")
            if toolchain_name:
                # Try to find in toolchains list
                if "toolchains" in config:
                    for tc in config["toolchains"]:
                        if tc.get("name") == toolchain_name:
                            return tc

        return None

    def _normalize_compiler_type(self, compiler_type: str) -> str:
        """Normalize compiler type (handle aliases).

        Args:
            compiler_type: Raw compiler type string

        Returns:
            Normalized compiler type
        """
        normalized = compiler_type.lower()
        return self.COMPILER_ALIASES.get(normalized, normalized)

    def _validate_compiler_platform(self, compiler_type: str, for_bootstrap: bool):
        """Validate compiler is supported on target platform.

        Args:
            compiler_type: Compiler type
            for_bootstrap: If True, this is for bootstrap generation
        """
        if not compiler_type or compiler_type == "unknown":
            return

        normalized_compiler = self._normalize_compiler_type(compiler_type)
        supported = self.validate_compiler_for_platform(normalized_compiler)

        if not supported:
            reason = self.get_unsupported_reason(normalized_compiler)

            if for_bootstrap:
                self.issues.append(
                    CompatibilityIssue(
                        level="error",
                        category="compiler",
                        message=(
                            f"Cannot generate bootstrap scripts for {compiler_type} on "
                            f"{self.platform_string}: {reason}"
                        ),
                        suggestion=self._get_alternative_compilers_suggestion(),
                    )
                )
            else:
                self.issues.append(
                    CompatibilityIssue(
                        level="warning",
                        category="compiler",
                        message=(
                            f"Compiler {compiler_type} may not work on {self.platform_string}: "
                            f"{reason}"
                        ),
                        suggestion=self._get_alternative_compilers_suggestion(),
                    )
                )

    def _validate_stdlib_platform(self, stdlib: str, compiler_type: str):
        """Validate standard library is supported on platform.

        Args:
            stdlib: Standard library name (libc++, libstdc++, msvc)
            compiler_type: Compiler type
        """
        supported_stdlibs = get_supported_stdlibs(self.platform_string)

        if stdlib not in supported_stdlibs:
            self.issues.append(
                CompatibilityIssue(
                    level="warning",
                    category="stdlib",
                    message=(
                        f"Standard library '{stdlib}' may not be available on "
                        f"{self.platform_string}"
                    ),
                    suggestion=f"Supported standard libraries: {', '.join(supported_stdlibs)}",
                )
            )

        # Cross-check stdlib with compiler
        if compiler_type == "gcc" and stdlib == "libc++":
            self.issues.append(
                CompatibilityIssue(
                    level="warning",
                    category="stdlib",
                    message="GCC with libc++ requires manual setup",
                    suggestion="GCC typically uses libstdc++. Using libc++ with GCC requires additional configuration.",
                )
            )
        elif compiler_type == "msvc" and stdlib != "msvc":
            self.issues.append(
                CompatibilityIssue(
                    level="warning",
                    category="stdlib",
                    message=f"MSVC with {stdlib} is not standard",
                    suggestion="MSVC typically uses its own standard library.",
                )
            )

    def _validate_generator_platform(self, generator: str):
        """Validate CMake generator is supported on platform.

        Args:
            generator: CMake generator name
        """
        generator_lower = generator.lower()

        # Platform-specific generator checks
        if "xcode" in generator_lower and self.target_platform.os != "macos":
            self.issues.append(
                CompatibilityIssue(
                    level="error",
                    category="generator",
                    message=f"Xcode generator only works on macOS, not on {self.platform_string}",
                    suggestion="Use Ninja or Unix Makefiles generator",
                )
            )
        elif "visual studio" in generator_lower or generator_lower == "msbuild":
            if self.target_platform.os != "windows":
                self.issues.append(
                    CompatibilityIssue(
                        level="error",
                        category="generator",
                        message=(
                            f"Visual Studio/MSBuild generator only works on Windows, "
                            f"not on {self.platform_string}"
                        ),
                        suggestion="Use Ninja or Unix Makefiles generator",
                    )
                )

    def _get_alternative_compilers_suggestion(self) -> str:
        """Get suggestion for alternative compilers for current platform.

        Returns:
            Suggestion string with supported compilers
        """
        supported = get_supported_compilers(self.platform_string)
        if supported:
            return f"Use one of the supported compilers for {self.platform_string}: {', '.join(supported)}"
        return f"No compilers currently configured for {self.platform_string}"


def validate_bootstrap_compatibility(config: Dict[str, Any]) -> CompatibilityResult:
    """Validate configuration is compatible for bootstrap script generation.

    This is a convenience function for validating bootstrap compatibility.

    Args:
        config: Configuration dictionary

    Returns:
        CompatibilityResult with validation results
    """
    validator = CompatibilityValidator()
    return validator.validate_configuration(config, for_bootstrap=True)


def check_compiler_platform_compatibility(
    compiler_type: str, platform_string: Optional[str] = None
) -> bool:
    """Check if compiler is compatible with platform.

    Args:
        compiler_type: Compiler type (gcc, clang, llvm, msvc)
        platform_string: Platform string. Uses current platform if None.

    Returns:
        True if compatible, False otherwise
    """
    validator = CompatibilityValidator()
    return validator.validate_compiler_for_platform(compiler_type, platform_string)


__all__ = [
    "CompatibilityIssue",
    "CompatibilityResult",
    "CompatibilityValidator",
    "validate_bootstrap_compatibility",
    "check_compiler_platform_compatibility",
]
