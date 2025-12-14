"""
CMake Toolchain File Generator

This module generates CMake toolchain files that configure compilers, linkers,
and other build settings for ToolchainKit-managed toolchains.
"""

from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging

from ..core.platform import detect_platform
from ..core.filesystem import atomic_write
from ..config import LayerComposer, ComposedConfig
from toolchainkit.toolchain.strategy import CompilerStrategy
from toolchainkit.core.interfaces import StrategyResolver

logger = logging.getLogger(__name__)


class CMakeToolchainGeneratorError(Exception):
    """Base exception for CMake toolchain generation errors."""

    pass


class InvalidToolchainConfigError(CMakeToolchainGeneratorError):
    """Raised when toolchain configuration is invalid."""

    pass


@dataclass
class ToolchainFileConfig:
    """Configuration for generating a CMake toolchain file.

    Attributes:
        toolchain_id: Unique identifier for the toolchain (e.g., 'llvm-18.1.8-linux-x64')
        toolchain_path: Absolute path to the toolchain installation directory
        compiler_type: Type of compiler ('clang', 'gcc', 'msvc', 'zig')
        stdlib: C++ standard library to use ('libc++', 'libstdc++', 'msvc', None for default)
        build_type: CMake build type ('Release', 'Debug', 'RelWithDebInfo', 'MinSizeRel')
        linker: Linker to use ('lld', 'gold', 'mold', 'bfd', None for default)
        caching_enabled: Whether to enable compiler caching
        cache_tool: Cache tool to use ('sccache', 'ccache', None)
        cross_compile: Cross-compilation settings dict with keys: os, arch, sysroot (optional)
        package_manager: Package manager integration ('conan', 'vcpkg', None)
        clang_tidy_path: Path to clang-tidy executable (optional)
        clang_format_path: Path to clang-format executable (optional)
        custom_flags: Custom compiler/linker flags dict with keys: cxx, c, linker, etc. (optional)
    """

    toolchain_id: str
    toolchain_path: Path
    compiler_type: str
    stdlib: Optional[str] = None
    build_type: str = "Release"
    linker: Optional[str] = None
    caching_enabled: bool = False
    cache_tool: Optional[str] = None
    cross_compile: Optional[Dict[str, str]] = None
    package_manager: Optional[str] = None
    clang_tidy_path: Optional[Path] = None
    clang_format_path: Optional[Path] = None
    custom_flags: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate compiler type
        valid_compilers = ["clang", "gcc", "msvc", "zig"]
        if self.compiler_type not in valid_compilers:
            raise InvalidToolchainConfigError(
                f"Invalid compiler_type '{self.compiler_type}'. "
                f"Must be one of: {', '.join(valid_compilers)}"
            )

        # Validate build type
        valid_build_types = ["Release", "Debug", "RelWithDebInfo", "MinSizeRel"]
        if self.build_type not in valid_build_types:
            raise InvalidToolchainConfigError(
                f"Invalid build_type '{self.build_type}'. "
                f"Must be one of: {', '.join(valid_build_types)}"
            )

        # Validate stdlib
        if self.stdlib:
            valid_stdlibs = ["libc++", "libstdc++", "msvc"]
            if self.stdlib not in valid_stdlibs:
                raise InvalidToolchainConfigError(
                    f"Invalid stdlib '{self.stdlib}'. "
                    f"Must be one of: {', '.join(valid_stdlibs)}"
                )

        # Validate linker
        if self.linker:
            valid_linkers = ["lld", "gold", "mold", "bfd"]
            if self.linker not in valid_linkers:
                raise InvalidToolchainConfigError(
                    f"Invalid linker '{self.linker}'. "
                    f"Must be one of: {', '.join(valid_linkers)}"
                )

        # Validate cache tool
        if self.caching_enabled and not self.cache_tool:
            raise InvalidToolchainConfigError(
                "cache_tool must be specified when caching_enabled is True"
            )

        if self.cache_tool:
            valid_cache_tools = ["sccache", "ccache"]
            if self.cache_tool not in valid_cache_tools:
                raise InvalidToolchainConfigError(
                    f"Invalid cache_tool '{self.cache_tool}'. "
                    f"Must be one of: {', '.join(valid_cache_tools)}"
                )

        # Validate package manager
        if self.package_manager:
            valid_package_managers = ["conan", "vcpkg"]
            if self.package_manager not in valid_package_managers:
                raise InvalidToolchainConfigError(
                    f"Invalid package_manager '{self.package_manager}'. "
                    f"Must be one of: {', '.join(valid_package_managers)}"
                )

        # Validate cross-compile
        if self.cross_compile:
            if "os" not in self.cross_compile or "arch" not in self.cross_compile:
                raise InvalidToolchainConfigError(
                    "cross_compile dict must contain 'os' and 'arch' keys"
                )


class CMakeToolchainGenerator:
    """Generates CMake toolchain files for managed toolchains.

    This class creates CMake toolchain files that configure compilers, linkers,
    standard libraries, build caching, and package manager integration.

    Example:
        >>> from pathlib import Path
        >>> generator = CMakeToolchainGenerator(Path('/my/project'))
        >>> config = ToolchainFileConfig(
        ...     toolchain_id='llvm-18.1.8-linux-x64',
        ...     toolchain_path=Path('/cache/toolchains/llvm-18.1.8'),
        ...     compiler_type='clang',
        ...     stdlib='libc++',
        ...     linker='lld'
        ... )
        >>> toolchain_file = generator.generate(config)
    """

    def __init__(
        self, project_root: Path, strategy_resolver: Optional[StrategyResolver] = None
    ):
        """Initialize the generator.

        Args:
            project_root: Root directory of the project
            strategy_resolver: Optional strategy resolver for looking up compiler strategies.
                             If None, uses default plugin registry resolver.
        """
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / ".toolchainkit" / "cmake"
        self.layer_composer = LayerComposer(project_root=project_root)
        self._strategy_resolver = strategy_resolver

    def generate(self, config: ToolchainFileConfig) -> Path:
        """Generate a CMake toolchain file.

        Args:
            config: Toolchain configuration

        Returns:
            Path to the generated toolchain file

        Raises:
            CMakeToolchainGeneratorError: If generation fails
            InvalidToolchainConfigError: If configuration is invalid
        """
        # Validate toolchain path exists
        if not config.toolchain_path.exists():
            raise CMakeToolchainGeneratorError(
                f"Toolchain path does not exist: {config.toolchain_path}"
            )

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Determine output filename
        filename = f"toolchain-{config.toolchain_id}.cmake"
        output_path = self.output_dir / filename

        # Generate content
        content = self._generate_content(config)

        # Write file atomically
        atomic_write(output_path, content)

        logger.info(f"Generated CMake toolchain file: {output_path}")
        return output_path

    def generate_from_layers(
        self,
        layer_specs: List[Dict[str, str]],
        toolchain_name: Optional[str] = None,
    ) -> Path:
        """Generate a CMake toolchain file from configuration layers.

        This method composes a configuration from layers and generates a CMake
        toolchain file with all the settings from the composed configuration.

        Args:
            layer_specs: List of layer specifications (e.g., [{'type': 'base', 'name': 'clang-18'}])
            toolchain_name: Optional custom name for the toolchain file.
                           If not provided, auto-generated from layer names.

        Returns:
            Path to the generated toolchain file

        Raises:
            CMakeToolchainGeneratorError: If generation fails
            LayerError: If layer composition fails

        Example:
            >>> generator = CMakeToolchainGenerator(Path('/my/project'))
            >>> layers = [
            ...     {'type': 'base', 'name': 'clang-18'},
            ...     {'type': 'platform', 'name': 'linux-x64'},
            ...     {'type': 'buildtype', 'name': 'release'},
            ...     {'type': 'optimization', 'name': 'lto-thin'}
            ... ]
            >>> toolchain_file = generator.generate_from_layers(layers)
        """
        # Compose configuration from layers
        composed = self.layer_composer.compose(layer_specs)

        # Generate toolchain name if not provided
        if not toolchain_name:
            layer_names = [spec.get("name", "unknown") for spec in layer_specs]
            toolchain_name = "-".join(layer_names[:4])  # First 4 layers for brevity

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Determine output filename
        filename = f"toolchain-{toolchain_name}.cmake"
        output_path = self.output_dir / filename

        # Generate content from composed configuration
        content = self._generate_content_from_layers(composed, toolchain_name)

        # Write file atomically
        atomic_write(output_path, content)

        logger.info(
            f"Generated CMake toolchain file from layers: {output_path} "
            f"(composed from {len(layer_specs)} layers)"
        )
        return output_path

    def _generate_content_from_layers(
        self, composed: ComposedConfig, toolchain_name: str
    ) -> str:
        """Generate toolchain file content from composed configuration.

        Args:
            composed: Composed configuration from layers
            toolchain_name: Name for the toolchain

        Returns:
            Complete file content as string
        """
        lines: List[str] = []

        # Header
        lines.extend(self._generate_layer_header(composed, toolchain_name))
        lines.append("")

        # Compiler configuration (from base layer)
        lines.extend(self._generate_layer_compiler_config(composed))
        lines.append("")

        # Compiler and linker flags (from all layers)
        lines.extend(self._generate_layer_flags(composed))
        lines.append("")

        # CMake variables (from layers)
        if composed.cmake_variables:
            lines.extend(self._generate_layer_cmake_variables(composed))
            lines.append("")

        # Runtime environment (for wrapper scripts)
        if composed.runtime_env:
            lines.extend(self._generate_layer_runtime_env(composed))
            lines.append("")

        # Debug info
        lines.extend(self._generate_layer_debug_info(composed))

        return "\n".join(lines)

    def _generate_layer_header(
        self, composed: ComposedConfig, toolchain_name: str
    ) -> List[str]:
        """Generate header for layer-based toolchain file.

        Args:
            composed: Composed configuration
            toolchain_name: Toolchain name

        Returns:
            List of header lines
        """
        platform = detect_platform()
        timestamp = datetime.now().isoformat()

        lines = [
            "# Generated by ToolchainKit - Layer-Based Configuration",
            f"# Toolchain: {toolchain_name}",
            f"# Platform: {platform.platform_string()}",
            f"# Generated: {timestamp}",
            "#",
            f"# Composed from {len(composed.layers)} layers:",
        ]

        # List applied layers
        for layer in composed.layers:
            lines.append(f"#   - {layer.layer_type}/{layer.name}")

        lines.extend(
            [
                "#",
                "# DO NOT EDIT - This file is auto-generated",
                "# Any manual changes will be overwritten on next generation",
                "",
                'set(TOOLCHAINKIT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../..")',
                'set(TOOLCHAINKIT_VERSION "0.1.0")',
            ]
        )

        return lines

    def _generate_layer_compiler_config(self, composed: ComposedConfig) -> List[str]:
        """Generate compiler configuration from layers.

        Args:
            composed: Composed configuration

        Returns:
            List of compiler configuration lines
        """
        lines = ["# Compiler configuration"]

        # Compiler paths (from toolchain_root if available)
        # Use CACHE FORCE to ensure these override other toolchain files (e.g., Conan)
        if "CMAKE_CXX_COMPILER" in composed.cmake_variables:
            lines.append(
                f'set(CMAKE_CXX_COMPILER "{composed.cmake_variables["CMAKE_CXX_COMPILER"]}" CACHE FILEPATH "CXX compiler" FORCE)'
            )
        if "CMAKE_C_COMPILER" in composed.cmake_variables:
            lines.append(
                f'set(CMAKE_C_COMPILER "{composed.cmake_variables["CMAKE_C_COMPILER"]}" CACHE FILEPATH "C compiler" FORCE)'
            )

        # If toolchain_root is set but compilers aren't, construct paths
        if (
            "CMAKE_CXX_COMPILER" not in composed.cmake_variables
            and "toolchain_root" in composed.cmake_variables
        ):
            toolchain_root = composed.cmake_variables["toolchain_root"]

            if composed.compiler == "clang":
                lines.append(
                    f'set(CMAKE_C_COMPILER "{toolchain_root}/bin/clang" CACHE FILEPATH "C compiler" FORCE)'
                )
                lines.append(
                    f'set(CMAKE_CXX_COMPILER "{toolchain_root}/bin/clang++" CACHE FILEPATH "CXX compiler" FORCE)'
                )
            elif composed.compiler == "gcc":
                lines.append(
                    f'set(CMAKE_C_COMPILER "{toolchain_root}/bin/gcc" CACHE FILEPATH "C compiler" FORCE)'
                )
                lines.append(
                    f'set(CMAKE_CXX_COMPILER "{toolchain_root}/bin/g++" CACHE FILEPATH "CXX compiler" FORCE)'
                )
            elif composed.compiler == "zig":
                # Zig uses wrapper commands, not direct executables
                lines.append(
                    f'set(CMAKE_C_COMPILER "{toolchain_root}/zig" CACHE FILEPATH "C compiler" FORCE)'
                )
                lines.append(
                    f'set(CMAKE_CXX_COMPILER "{toolchain_root}/zig" CACHE FILEPATH "CXX compiler" FORCE)'
                )
                # Set compiler arguments to use zig as a C/C++ compiler
                lines.append(
                    'set(CMAKE_C_COMPILER_ARG1 "cc" CACHE STRING "Zig C compiler argument")'
                )
                lines.append(
                    'set(CMAKE_CXX_COMPILER_ARG1 "c++" CACHE STRING "Zig C++ compiler argument")'
                )
            elif composed.compiler == "msvc":
                lines.append(
                    "# MSVC compiler (using CMake's automatic detection or environment variables)"
                )

        # Cross-compilation settings
        if "CMAKE_SYSTEM_NAME" in composed.cmake_variables:
            lines.append("# Cross-compilation")
            lines.append(
                f'set(CMAKE_SYSTEM_NAME "{composed.cmake_variables["CMAKE_SYSTEM_NAME"]}")'
            )

        if "CMAKE_SYSTEM_PROCESSOR" in composed.cmake_variables:
            lines.append(
                f'set(CMAKE_SYSTEM_PROCESSOR "{composed.cmake_variables["CMAKE_SYSTEM_PROCESSOR"]}")'
            )

        if "CMAKE_SYSROOT" in composed.cmake_variables:
            lines.append(
                f'set(CMAKE_SYSROOT "{composed.cmake_variables["CMAKE_SYSROOT"]}")'
            )

        return lines

    def _generate_layer_flags(self, composed: ComposedConfig) -> List[str]:
        """Generate compiler and linker flags from layers.

        Args:
            composed: Composed configuration

        Returns:
            List of flag configuration lines
        """
        lines = ["# Compiler and linker flags"]

        # Compile flags
        if composed.compile_flags:
            flags_str = " ".join(composed.compile_flags)
            lines.append(f'set(CMAKE_CXX_FLAGS_INIT "{flags_str}")')
            lines.append(f'set(CMAKE_C_FLAGS_INIT "{flags_str}")')

        # Link flags
        if composed.link_flags:
            flags_str = " ".join(composed.link_flags)
            lines.append(f'set(CMAKE_EXE_LINKER_FLAGS_INIT "{flags_str}")')
            lines.append(f'set(CMAKE_SHARED_LINKER_FLAGS_INIT "{flags_str}")')

        # Defines as compiler flags
        if composed.defines:
            defines_str = " ".join([f"-D{d}" for d in composed.defines])
            lines.append(f'string(APPEND CMAKE_CXX_FLAGS_INIT " {defines_str}")')
            lines.append(f'string(APPEND CMAKE_C_FLAGS_INIT " {defines_str}")')

        return lines

    def _generate_layer_cmake_variables(self, composed: ComposedConfig) -> List[str]:
        """Generate CMake variables from layers.

        Args:
            composed: Composed configuration

        Returns:
            List of CMake variable lines
        """
        lines = ["# CMake variables from layers"]

        # Skip variables we already handled (compilers, system settings)
        skip_vars = {
            "CMAKE_CXX_COMPILER",
            "CMAKE_C_COMPILER",
            "CMAKE_SYSTEM_NAME",
            "CMAKE_SYSTEM_PROCESSOR",
            "CMAKE_SYSROOT",
            "toolchain_root",  # Internal variable
        }

        for key, value in composed.cmake_variables.items():
            if key in skip_vars:
                continue

            # Convert value to appropriate CMake type
            if isinstance(value, bool):
                cmake_value = "ON" if value else "OFF"
            else:
                cmake_value = str(value)

            lines.append(f'set({key} "{cmake_value}")')

        return lines

    def _generate_layer_runtime_env(self, composed: ComposedConfig) -> List[str]:
        """Generate runtime environment settings from layers.

        Args:
            composed: Composed configuration

        Returns:
            List of runtime environment lines
        """
        lines = [
            "# Runtime environment variables",
            "# These should be set when running the compiled executables",
        ]

        for key, value in composed.runtime_env.items():
            lines.append(f"# {key}={value}")

        lines.extend(
            [
                "#",
                "# Note: CMake does not set runtime environment variables automatically.",
                "# You may need to set these in your shell or create a wrapper script.",
            ]
        )

        return lines

    def _generate_layer_debug_info(self, composed: ComposedConfig) -> List[str]:
        """Generate debug information for layer-based config.

        Args:
            composed: Composed configuration

        Returns:
            List of debug message lines
        """
        lines = [
            "# Toolchain info (for debugging)",
            'message(STATUS "ToolchainKit: Layer-based configuration")',
            f'message(STATUS "ToolchainKit: Compiler: {composed.compiler}")',
        ]

        if composed.platform:
            lines.append(
                f'message(STATUS "ToolchainKit: Platform: {composed.platform}")'
            )

        if composed.linker:
            lines.append(f'message(STATUS "ToolchainKit: Linker: {composed.linker}")')

        if composed.sanitizers:
            sanitizers_str = ", ".join(composed.sanitizers)
            lines.append(
                f'message(STATUS "ToolchainKit: Sanitizers: {sanitizers_str}")'
            )

        layer_names = [f"{layer.layer_type}/{layer.name}" for layer in composed.layers]
        lines.append(
            f'message(STATUS "ToolchainKit: Applied layers: {"; ".join(layer_names)}")'
        )

        return lines

    def _generate_content(self, config: ToolchainFileConfig) -> str:
        """Generate the complete toolchain file content.

        Args:
            config: Toolchain configuration

        Returns:
            Complete file content as string
        """
        lines: List[str] = []

        # Header
        lines.extend(self._generate_header(config))
        lines.append("")

        # Compiler configuration
        lines.extend(self._generate_compiler_config(config))
        lines.append("")

        # Compiler flags
        flags = self._generate_compiler_flags(config)
        if flags:
            lines.extend(flags)
            lines.append("")

        # Build caching
        if config.caching_enabled:
            lines.extend(self._generate_caching_config(config))
            lines.append("")

        # Package manager integration
        if config.package_manager:
            lines.extend(self._generate_package_manager_config(config))
            lines.append("")

        # Cross-compilation
        if config.cross_compile:
            lines.extend(self._generate_cross_compile_config(config))
            lines.append("")

        # Conan toolchain integration (if CONAN_TOOLCHAIN_FILE is provided)
        lines.extend(self._generate_conan_include())
        lines.append("")

        # Debug info
        lines.extend(self._generate_debug_info(config))

        return "\n".join(lines)

    def _generate_header(self, config: ToolchainFileConfig) -> List[str]:
        """Generate the file header with metadata.

        Args:
            config: Toolchain configuration

        Returns:
            List of header lines
        """
        platform = detect_platform()
        timestamp = datetime.now().isoformat()

        return [
            "# Generated by ToolchainKit",
            f"# Toolchain: {config.toolchain_id}",
            f"# Platform: {platform.platform_string()}",
            f"# Generated: {timestamp}",
            "#",
            "# DO NOT EDIT - This file is auto-generated",
            "# Any manual changes will be overwritten on next generation",
            "",
            'set(TOOLCHAINKIT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../..")',
            'set(TOOLCHAINKIT_VERSION "0.1.0")',
        ]

    def _get_strategy(self, compiler_type: str) -> "CompilerStrategy":
        """Get compiler strategy for the given type."""
        # Use injected resolver if available
        if self._strategy_resolver:
            if self._strategy_resolver.has_strategy(compiler_type):
                return self._strategy_resolver.resolve_strategy(compiler_type)
            # Fallback to Clang for unknown types
            from toolchainkit.toolchain.strategies.standard import ClangStrategy

            return ClangStrategy()

        # Fallback: use global registry (for backwards compatibility)
        from toolchainkit.plugins.registry import get_global_registry

        registry = get_global_registry()
        try:
            return registry.get_compiler_strategy(compiler_type)
        except KeyError:
            from toolchainkit.toolchain.strategies.standard import ClangStrategy

            return ClangStrategy()

    def _generate_compiler_config(self, config: ToolchainFileConfig) -> List[str]:
        """Generate compiler configuration.

        Args:
            config: Toolchain configuration

        Returns:
            List of compiler configuration lines
        """
        lines = ["# Compiler paths"]

        strategy = self._get_strategy(config.compiler_type)
        platform = detect_platform()

        paths = strategy.get_compiler_paths(config.toolchain_path, platform)

        if not paths:
            if config.compiler_type == "msvc":
                lines.append("# MSVC compiler (using CMake's automatic detection)")
                lines.append(
                    "# Set environment variables (VCToolsInstallDir, etc.) before running CMake"
                )
            else:
                # Fallback if strategy returns nothing but it's not MSVC
                logger.warning(f"No compiler paths found for {config.compiler_type}")

        for var, path in paths.items():
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Compiler not found at: {path}")
            # Convert Windows backslashes to forward slashes for CMake
            cmake_path = str(path_obj).replace("\\", "/")
            # Save to TOOLCHAINKIT_* variable for restoration after Conan include
            toolchainkit_var = f"TOOLCHAINKIT_{var.replace('CMAKE_', '')}"
            lines.append(f'set({toolchainkit_var} "{cmake_path}")')
            # First unset any previous value, then use CACHE FORCE to ensure override
            # First unset any previous value, then use CACHE FORCE to ensure override
            lines.append(f"unset({var} CACHE)")
            lines.append(f'set({var} "{cmake_path}" CACHE FILEPATH "{var}" FORCE)')

        # Static Analysis (Clang-Tidy)
        if config.clang_tidy_path:
            tidy_path = str(config.clang_tidy_path).replace("\\", "/")
            lines.append("")
            lines.append("# Clang-Tidy configuration")
            # Enable Clang-Tidy for C and C++ globally
            # CMake expects a list: "executable;arg1;arg2"
            lines.append(
                f'set(CMAKE_CXX_CLANG_TIDY "{tidy_path}" CACHE STRING "Clang-Tidy setup" FORCE)'
            )
            lines.append(
                f'set(CMAKE_C_CLANG_TIDY "{tidy_path}" CACHE STRING "Clang-Tidy setup" FORCE)'
            )

        return lines

    def _generate_compiler_flags(self, config: ToolchainFileConfig) -> List[str]:
        """Generate compiler and linker flags.

        Args:
            config: Toolchain configuration

        Returns:
            List of flag configuration lines
        """
        strategy = self._get_strategy(config.compiler_type)
        lines = strategy.get_flags(config)

        # Append custom flags if provided
        if config.custom_flags:
            if not lines:
                lines = []
            lines.append("")
            lines.append("# Custom compiler and linker flags")

            # C++ flags
            if "cxx" in config.custom_flags:
                cxx_flags = config.custom_flags["cxx"]
                lines.append(f'string(APPEND CMAKE_CXX_FLAGS_INIT " {cxx_flags}")')

            # C flags
            if "c" in config.custom_flags:
                c_flags = config.custom_flags["c"]
                lines.append(f'string(APPEND CMAKE_C_FLAGS_INIT " {c_flags}")')

            # Linker flags (both shared and exe)
            if "linker" in config.custom_flags:
                linker_flags = config.custom_flags["linker"]
                lines.append(
                    f'string(APPEND CMAKE_EXE_LINKER_FLAGS_INIT " {linker_flags}")'
                )
                lines.append(
                    f'string(APPEND CMAKE_SHARED_LINKER_FLAGS_INIT " {linker_flags}")'
                )

            # Exe linker flags only
            if "exe_linker" in config.custom_flags:
                exe_linker_flags = config.custom_flags["exe_linker"]
                lines.append(
                    f'string(APPEND CMAKE_EXE_LINKER_FLAGS_INIT " {exe_linker_flags}")'
                )

            # Shared linker flags only
            if "shared_linker" in config.custom_flags:
                shared_linker_flags = config.custom_flags["shared_linker"]
                lines.append(
                    f'string(APPEND CMAKE_SHARED_LINKER_FLAGS_INIT " {shared_linker_flags}")'
                )

        return lines

    def _generate_caching_config(self, config: ToolchainFileConfig) -> List[str]:
        """Generate build caching configuration.

        Args:
            config: Toolchain configuration

        Returns:
            List of caching configuration lines
        """
        lines = [
            "# Build caching",
            f"# Using {config.cache_tool} for compiler caching",
            f"set(CMAKE_C_COMPILER_LAUNCHER {config.cache_tool})",
            f"set(CMAKE_CXX_COMPILER_LAUNCHER {config.cache_tool})",
        ]
        return lines

    def _generate_package_manager_config(
        self, config: ToolchainFileConfig
    ) -> List[str]:
        """Generate package manager integration.

        Args:
            config: Toolchain configuration

        Returns:
            List of package manager configuration lines
        """
        lines = [
            "# Package manager integration",
            f"include(${{CMAKE_CURRENT_LIST_DIR}}/{config.package_manager}-integration.cmake OPTIONAL)",
        ]
        return lines

    def _generate_cross_compile_config(self, config: ToolchainFileConfig) -> List[str]:
        """Generate cross-compilation configuration.

        Args:
            config: Toolchain configuration

        Returns:
            List of cross-compilation configuration lines
        """
        cross = config.cross_compile
        lines = [
            "# Cross-compilation settings",
            f'set(CMAKE_SYSTEM_NAME {cross["os"]})',
            f'set(CMAKE_SYSTEM_PROCESSOR {cross["arch"]})',
        ]

        # Add sysroot if specified
        if "sysroot" in cross:
            lines.append(f'set(CMAKE_SYSROOT "{cross["sysroot"]}")')

        # Add Android-specific settings
        if cross["os"].lower() == "android":
            lines.append("# Android-specific settings")
            if "api_level" in cross:
                lines.append(f'set(CMAKE_SYSTEM_VERSION {cross["api_level"]})')

        # Add iOS-specific settings
        elif cross["os"].lower() == "ios":
            lines.append("# iOS-specific settings")
            if "deployment_target" in cross:
                lines.append(
                    f'set(CMAKE_OSX_DEPLOYMENT_TARGET {cross["deployment_target"]})'
                )

        return lines

    def _generate_conan_include(self) -> List[str]:
        """Generate Conan toolchain include if CONAN_TOOLCHAIN_FILE is defined.

        Returns:
            List of lines to include Conan toolchain
        """
        return [
            "# Include Conan toolchain if provided (for package dependencies)",
            "if(DEFINED CONAN_TOOLCHAIN_FILE AND EXISTS ${CONAN_TOOLCHAIN_FILE})",
            '    message(STATUS "ToolchainKit: Including Conan toolchain: ${CONAN_TOOLCHAIN_FILE}")',
            "    include(${CONAN_TOOLCHAIN_FILE})",
            "    # Unset Conan's compiler settings since ToolchainKit manages compilers",
            "    unset(CMAKE_C_COMPILER CACHE)",
            "    unset(CMAKE_CXX_COMPILER CACHE)",
            "    # Unset MSVC runtime library setting - not compatible with Clang",
            "    unset(CMAKE_MSVC_RUNTIME_LIBRARY)",
            "    unset(CMAKE_MSVC_RUNTIME_LIBRARY CACHE)",
            "    # Restore ToolchainKit's compiler settings with FORCE",
            "    if(DEFINED TOOLCHAINKIT_C_COMPILER)",
            '        set(CMAKE_C_COMPILER ${TOOLCHAINKIT_C_COMPILER} CACHE FILEPATH "C compiler" FORCE)',
            "    endif()",
            "    if(DEFINED TOOLCHAINKIT_CXX_COMPILER)",
            '        set(CMAKE_CXX_COMPILER ${TOOLCHAINKIT_CXX_COMPILER} CACHE FILEPATH "CXX compiler" FORCE)',
            "    endif()",
            "endif()",
        ]

    def _generate_debug_info(self, config: ToolchainFileConfig) -> List[str]:
        """Generate debug information messages.

        Args:
            config: Toolchain configuration

        Returns:
            List of debug message lines
        """
        lines = [
            "# Toolchain info (for debugging)",
            f'message(STATUS "ToolchainKit: Using toolchain {config.toolchain_id}")',
            'message(STATUS "ToolchainKit: C compiler: ${CMAKE_C_COMPILER}")',
            'message(STATUS "ToolchainKit: CXX compiler: ${CMAKE_CXX_COMPILER}")',
        ]

        if config.stdlib:
            lines.append(f'message(STATUS "ToolchainKit: C++ stdlib: {config.stdlib}")')

        if config.linker:
            lines.append(f'message(STATUS "ToolchainKit: Linker: {config.linker}")')

        if config.caching_enabled:
            lines.append(
                f'message(STATUS "ToolchainKit: Build caching: {config.cache_tool}")'
            )

        return lines


def example_usage():
    """Example: Generate a CMake toolchain file."""
    from pathlib import Path

    # Example configuration for LLVM/Clang toolchain
    config = ToolchainFileConfig(
        toolchain_id="llvm-18.1.8-linux-x64",
        toolchain_path=Path("/opt/llvm-18.1.8"),
        compiler_type="clang",
        stdlib="libc++",
        build_type="Release",
        linker="lld",
        caching_enabled=True,
        cache_tool="sccache",
        package_manager="conan",
    )

    # Generate toolchain file
    generator = CMakeToolchainGenerator(Path("/my/project"))
    toolchain_file = generator.generate(config)

    print(f"Generated toolchain file: {toolchain_file}")

    # Read and print the content
    with open(toolchain_file, "r") as f:
        print("\nGenerated content:")
        print(f.read())


if __name__ == "__main__":
    example_usage()
