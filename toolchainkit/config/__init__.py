"""Configuration module for ToolchainKit.

This module provides YAML configuration parsing and validation for toolchainkit.yaml,
as well as the layer-based composable configuration system.
"""

from toolchainkit.config.parser import (
    ToolchainConfig,
    CachingConfig,
    BuildConfig,
    PackageManagerConfig,
    CrossCompilationTarget,
    ToolchainKitConfig,
    ConfigError,
    parse_config,
)
from toolchainkit.config.validation import (
    ValidationIssue,
    ValidationResult,
    ConfigValidator,
    format_validation_results,
)
from toolchainkit.config.layers import (
    ConfigLayer,
    LayerContext,
    LayerError,
    LayerNotFoundError,
    LayerValidationError,
    LayerConflictError,
    LayerRequirementError,
    BaseCompilerLayer,
    PlatformLayer,
    StdLibLayer,
    BuildTypeLayer,
    OptimizationLayer,
    SanitizerLayer,
)
from toolchainkit.config.composer import (
    ComposedConfig,
    LayerComposer,
)

__all__ = [
    # Original config system
    "ToolchainConfig",
    "CachingConfig",
    "BuildConfig",
    "PackageManagerConfig",
    "CrossCompilationTarget",
    "ToolchainKitConfig",
    "ConfigError",
    "parse_config",
    "ValidationIssue",
    "ValidationResult",
    "ConfigValidator",
    "format_validation_results",
    # Layer system
    "ConfigLayer",
    "LayerContext",
    "LayerError",
    "LayerNotFoundError",
    "LayerValidationError",
    "LayerConflictError",
    "LayerRequirementError",
    "BaseCompilerLayer",
    "PlatformLayer",
    "StdLibLayer",
    "BuildTypeLayer",
    "OptimizationLayer",
    "SanitizerLayer",
    "ComposedConfig",
    "LayerComposer",
]
