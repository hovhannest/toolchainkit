"""YAML configuration parser for ToolchainKit.

This module provides parsing and validation for toolchainkit.yaml configuration files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import yaml


class ConfigError(Exception):
    """Configuration parsing or validation error."""

    pass


@dataclass
class ToolchainConfig:
    """Configuration for a single toolchain."""

    name: str
    type: str  # 'clang', 'gcc', 'msvc', 'zig'
    version: str
    stdlib: Optional[str] = None  # 'libc++', 'libstdc++', 'msvc'
    source: str = "prebuilt"  # 'prebuilt', 'build-from-source'
    require_installed: bool = False  # Use system installation only
    custom_paths: Optional[Dict[str, str]] = None  # Custom paths for components
    # Supported custom_paths keys:
    #   Compiler tools: compiler, linker, ar, ranlib, strip, objcopy, objdump
    #   Build tools: cmake, ninja, make, meson
    #   Caching tools: ccache, sccache
    #   Other: python (for Conan)


@dataclass
class CachingConfig:
    """Build caching configuration."""

    enabled: bool = False
    tool: Optional[str] = None  # 'sccache', 'ccache'
    directory: Optional[str] = None
    remote: Optional[dict] = None


@dataclass
class BuildConfig:
    """Build system configuration."""

    backend: str = "ninja"  # 'ninja', 'make', 'msbuild', 'xcode'
    parallel: str = "auto"  # 'auto' or number
    caching: CachingConfig = field(default_factory=CachingConfig)


@dataclass
class PackageManagerConfig:
    """Package manager configuration."""

    manager: Optional[str] = None  # 'conan', 'vcpkg', 'cpm'
    conan: Optional[dict] = None
    vcpkg: Optional[dict] = None
    use_system: bool = False  # Use system-installed package manager
    custom_path: Optional[str] = None  # Path to custom package manager installation
    conan_home: Optional[str] = None  # Custom CONAN_HOME directory
    vcpkg_root: Optional[str] = None  # Custom VCPKG_ROOT directory


@dataclass
class CrossCompilationTarget:
    """Cross-compilation target configuration."""

    os: str
    arch: str
    toolchain: Optional[str] = None
    api_level: Optional[int] = None  # Android
    sdk: Optional[str] = None  # iOS


@dataclass
class ToolchainKitConfig:
    """Complete ToolchainKit configuration."""

    version: int
    project: Optional[str] = None
    toolchains: List[ToolchainConfig] = field(default_factory=list)
    defaults: Dict[str, str] = field(default_factory=dict)
    toolchain_cache: Dict[str, str] = field(default_factory=dict)
    packages: Optional[PackageManagerConfig] = None
    build: BuildConfig = field(default_factory=BuildConfig)
    targets: List[CrossCompilationTarget] = field(default_factory=list)
    modules: List[str] = field(default_factory=lambda: ["core", "cmake"])


def parse_config(config_path: Path) -> ToolchainKitConfig:
    """
    Parse toolchainkit.yaml configuration file.

    Args:
        config_path: Path to toolchainkit.yaml

    Returns:
        Parsed and validated configuration

    Raises:
        ConfigError: If configuration is invalid
    """
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax: {e}")

    if data is None:
        raise ConfigError("Configuration file is empty")

    # Validate and parse
    config = _parse_and_validate(data)

    return config


def _parse_and_validate(data: dict) -> ToolchainKitConfig:
    """Parse and validate configuration data."""
    # Check version
    if "version" not in data:
        raise ConfigError("Missing required field: version")

    if data["version"] != 1:
        raise ConfigError(f"Unsupported version: {data['version']} (expected 1)")

    # Parse toolchains
    if "toolchains" not in data or not data["toolchains"]:
        raise ConfigError("At least one toolchain must be defined")

    toolchains = []
    toolchain_names = set()

    for tc_data in data["toolchains"]:
        tc = _parse_toolchain(tc_data)

        if tc.name in toolchain_names:
            raise ConfigError(f"Duplicate toolchain name: {tc.name}")

        toolchain_names.add(tc.name)
        toolchains.append(tc)

    # Validate defaults reference defined toolchains
    defaults = data.get("defaults", {})
    for platform, toolchain_name in defaults.items():
        if toolchain_name not in toolchain_names:
            raise ConfigError(
                f"defaults.{platform} references undefined toolchain: {toolchain_name}"
            )

    # Parse other sections
    build_config = _parse_build_config(data.get("build", {}))
    packages_config = _parse_packages_config(data.get("packages"))
    targets = _parse_targets(data.get("targets", []))

    # Parse toolchain_cache with support for legacy toolchain_dir/cache_dir fields
    toolchain_cache = _parse_toolchain_cache(data)

    return ToolchainKitConfig(
        version=data["version"],
        project=data.get("project"),
        toolchains=toolchains,
        defaults=defaults,
        toolchain_cache=toolchain_cache,
        packages=packages_config,
        build=build_config,
        targets=targets,
        modules=data.get("modules", ["core", "cmake"]),
    )


def _parse_toolchain(data: dict) -> ToolchainConfig:
    """Parse toolchain configuration."""
    required = ["name", "type", "version"]
    for field_name in required:
        if field_name not in data:
            raise ConfigError(f"Toolchain missing required field: {field_name}")

    valid_types = ["clang", "gcc", "msvc", "zig"]
    if data["type"] not in valid_types:
        raise ConfigError(
            f"Invalid toolchain type: {data['type']} (expected one of {valid_types})"
        )

    # Parse custom_paths if provided
    custom_paths = data.get("custom_paths")
    if custom_paths and not isinstance(custom_paths, dict):
        raise ConfigError("custom_paths must be a dictionary")

    return ToolchainConfig(
        name=data["name"],
        type=data["type"],
        version=data["version"],
        stdlib=data.get("stdlib"),
        source=data.get("source", "prebuilt"),
        require_installed=data.get("require_installed", False),
        custom_paths=custom_paths,
    )


def _parse_build_config(data: dict) -> BuildConfig:
    """Parse build configuration."""
    valid_backends = ["ninja", "make", "msbuild", "xcode"]
    backend = data.get("backend", "ninja")

    if backend not in valid_backends:
        raise ConfigError(
            f"Invalid build backend: {backend} (expected one of {valid_backends})"
        )

    caching_data = data.get("caching", {})
    caching = CachingConfig(
        enabled=caching_data.get("enabled", False),
        tool=caching_data.get("tool"),
        directory=caching_data.get("directory"),
        remote=caching_data.get("remote"),
    )

    return BuildConfig(
        backend=backend, parallel=data.get("parallel", "auto"), caching=caching
    )


def _parse_packages_config(data: Optional[dict]) -> Optional[PackageManagerConfig]:
    """Parse package manager configuration."""
    if data is None:
        return None

    manager = data.get("manager")
    if manager and manager not in ["conan", "vcpkg", "cpm"]:
        raise ConfigError(
            f"Invalid package manager: {manager} (expected conan, vcpkg, or cpm)"
        )

    return PackageManagerConfig(
        manager=manager,
        conan=data.get("conan"),
        vcpkg=data.get("vcpkg"),
        use_system=data.get("use_system", False),
        custom_path=data.get("custom_path"),
        conan_home=data.get("conan_home"),
        vcpkg_root=data.get("vcpkg_root"),
    )


def _parse_targets(data: list) -> List[CrossCompilationTarget]:
    """Parse cross-compilation targets."""
    targets = []

    for target_data in data:
        if "os" not in target_data or "arch" not in target_data:
            raise ConfigError("Cross-compilation target must specify 'os' and 'arch'")

        targets.append(
            CrossCompilationTarget(
                os=target_data["os"],
                arch=target_data["arch"],
                toolchain=target_data.get("toolchain"),
                api_level=target_data.get("api_level"),
                sdk=target_data.get("sdk"),
            )
        )

    return targets


def _parse_toolchain_cache(data: dict) -> Dict[str, str]:
    """
    Parse toolchain cache configuration.

    Supports both the new toolchain_cache format and legacy toolchain_dir/cache_dir fields.

    Args:
        data: Configuration dictionary

    Returns:
        Dictionary with 'location' and optionally 'path' keys
    """
    # Check for explicit toolchain_cache section (preferred)
    if "toolchain_cache" in data:
        toolchain_cache = data["toolchain_cache"]
        if "location" not in toolchain_cache:
            toolchain_cache["location"] = "shared"
        return toolchain_cache

    # Check for legacy toolchain_dir field (backwards compatibility)
    if "toolchain_dir" in data:
        toolchain_dir = data["toolchain_dir"]

        # If it's a relative path starting with ".", treat as local
        if isinstance(toolchain_dir, str):
            if toolchain_dir.startswith("."):
                return {"location": "local", "path": toolchain_dir}
            else:
                return {"location": "custom", "path": toolchain_dir}

    # Check for legacy cache_dir field (backwards compatibility)
    if "cache_dir" in data:
        cache_dir = data["cache_dir"]

        # If it's a relative path starting with ".", treat as local
        if isinstance(cache_dir, str):
            if cache_dir.startswith("."):
                return {"location": "local", "path": cache_dir}
            else:
                return {"location": "custom", "path": cache_dir}

    # Default to shared cache
    return {"location": "shared"}
