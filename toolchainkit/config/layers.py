"""Configuration layer system for composable build configurations.

This module implements a layer-based configuration system where complex build
configurations are composed from reusable layers. For example:
    base/clang-18 + platform/linux-x64 + stdlib/libc++ + buildtype/release + optimization/lto-thin

The layer system provides:
- Composability: Stack layers to build configurations
- Reusability: Share layers across projects
- Validation: Automatic requirement and conflict checking
- Flexibility: Support custom layers for advanced needs

Example:
    >>> from toolchainkit.config.layers import LayerContext, BaseCompilerLayer
    >>> context = LayerContext()
    >>> layer = BaseCompilerLayer("clang-18", "clang", "18.1.8")
    >>> layer.validate(context)
    >>> layer.apply(context)
    >>> print(context.compiler)  # "clang"
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any


# ============================================================================
# Exception Classes
# ============================================================================


class LayerError(Exception):
    """Base exception for layer-related errors."""

    pass


class LayerNotFoundError(LayerError):
    """Raised when a layer cannot be found."""

    pass


class LayerValidationError(LayerError):
    """Raised when a layer fails validation."""

    pass


class LayerConflictError(LayerValidationError):
    """Raised when layers have conflicting requirements."""

    pass


class LayerRequirementError(LayerValidationError):
    """Raised when a layer's requirements are not met."""

    pass


# ============================================================================
# LayerContext: State Container
# ============================================================================


@dataclass
class LayerContext:
    """Context holding accumulated configuration state during layer composition.

    The LayerContext tracks all configuration settings as layers are applied.
    Later layers can see and modify settings from earlier layers.

    Attributes:
        compiler: Compiler name (clang, gcc, msvc)
        compiler_version: Compiler version string
        platform: Target platform (linux-x64, windows-x64, etc.)
        stdlib: C++ standard library (libc++, libstdc++, msvc)
        build_type: Build type (debug, release, relwithdebinfo, minsizerel)
        compile_flags: Accumulated compile flags
        link_flags: Accumulated link flags
        defines: Accumulated preprocessor defines
        cmake_variables: CMake toolchain variables
        runtime_env: Runtime environment variables
        applied_layers: List of applied layers (for debugging)
        layer_types: Set of applied layer types (for validation)
        sanitizers: Set of active sanitizers (for conflict detection)
    """

    # Toolchain identification
    compiler: Optional[str] = None
    compiler_version: Optional[str] = None
    platform: Optional[str] = None
    stdlib: Optional[str] = None
    build_type: Optional[str] = None

    # Accumulated flags and settings
    compile_flags: List[str] = field(default_factory=list)
    link_flags: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    cmake_variables: Dict[str, str] = field(default_factory=dict)
    runtime_env: Dict[str, str] = field(default_factory=dict)

    # Tracking for validation
    applied_layers: List["ConfigLayer"] = field(default_factory=list)
    layer_types: Set[str] = field(default_factory=set)
    sanitizers: Set[str] = field(default_factory=set)

    def add_flags(
        self,
        compile: Optional[List[str]] = None,
        link: Optional[List[str]] = None,
        common: Optional[List[str]] = None,
    ) -> None:
        """Add compiler and/or linker flags to the context.

        Args:
            compile: Compile-only flags to add
            link: Link-only flags to add
            common: Flags to add to both compile and link
        """
        if common:
            self.compile_flags.extend(common)
            self.link_flags.extend(common)
        if compile:
            self.compile_flags.extend(compile)
        if link:
            self.link_flags.extend(link)

    def add_defines(self, defines: List[str]) -> None:
        """Add preprocessor defines to the context.

        Duplicates are removed (last occurrence wins).

        Args:
            defines: List of preprocessor defines (e.g., ["DEBUG=1", "PLATFORM_LINUX"])
        """
        for define in defines:
            # Remove duplicates (last wins)
            base_name = define.split("=")[0]
            self.defines = [d for d in self.defines if not d.startswith(base_name)]
            self.defines.append(define)

    def add_cmake_variables(self, variables: Dict[str, str]) -> None:
        """Add CMake variables to the context.

        Later variables override earlier ones.

        Args:
            variables: Dictionary of CMake variable name -> value
        """
        self.cmake_variables.update(variables)

    def add_runtime_env(self, env: Dict[str, str]) -> None:
        """Add runtime environment variables to the context.

        Later variables override earlier ones.

        Args:
            env: Dictionary of environment variable name -> value
        """
        self.runtime_env.update(env)

    def has_layer_type(self, layer_type: str) -> bool:
        """Check if a layer of the given type has been applied.

        Args:
            layer_type: Layer type to check (base, platform, etc.)

        Returns:
            True if a layer of this type has been applied
        """
        return layer_type in self.layer_types

    def has_sanitizer(self, sanitizer: str) -> bool:
        """Check if a sanitizer is active.

        Args:
            sanitizer: Sanitizer name (address, thread, memory, undefined)

        Returns:
            True if this sanitizer is active
        """
        return sanitizer in self.sanitizers

    def interpolate_variables(self, text: str, **extra_vars: Any) -> str:
        """Interpolate {{variable}} placeholders in text.

        Available variables:
        - toolchain_root: Path to toolchain
        - compiler_version: Compiler version
        - platform: Platform string
        - project_root: Project root directory
        - Custom variables from extra_vars

        Args:
            text: Text with {{variable}} placeholders
            **extra_vars: Additional variables for interpolation

        Returns:
            Text with variables interpolated
        """
        variables = {
            "compiler_version": self.compiler_version or "",
            "platform": self.platform or "",
            **extra_vars,
        }

        result = text
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))

        return result


# ============================================================================
# ConfigLayer: Abstract Base Class
# ============================================================================


class ConfigLayer(ABC):
    """Abstract base class for configuration layers.

    A layer represents a focused aspect of build configuration (compiler,
    platform, optimizations, etc.). Layers can specify requirements and
    conflicts, and apply their settings to a LayerContext.

    Subclasses must implement the apply() method to modify the context.

    Attributes:
        name: Layer name (e.g., "clang-18", "linux-x64")
        layer_type: Layer type (base, platform, stdlib, etc.)
        description: Human-readable description
        _compile_flags: Compile flags for this layer
        _link_flags: Link flags for this layer
        _common_flags: Flags for both compile and link
        _defines: Preprocessor defines
        _cmake_variables: CMake toolchain variables
        _runtime_env: Runtime environment variables
        _requires: Requirements (e.g., {"compiler": ["clang"]})
        _conflicts_with: Conflicts (e.g., {"sanitizer": ["thread"]})
    """

    def __init__(self, name: str, layer_type: str, description: str = ""):
        """Initialize a configuration layer.

        Args:
            name: Layer name
            layer_type: Layer type (base, platform, stdlib, buildtype, optimization, sanitizer)
            description: Human-readable description
        """
        self.name = name
        self.layer_type = layer_type
        self.description = description

        # Flags and settings
        self._compile_flags: List[str] = []
        self._link_flags: List[str] = []
        self._common_flags: List[str] = []
        self._defines: List[str] = []
        self._cmake_variables: Dict[str, str] = {}
        self._runtime_env: Dict[str, str] = {}

        # Validation constraints
        self._requires: Dict[str, List[str]] = {}
        self._conflicts_with: Dict[str, List[str]] = {}

    @abstractmethod
    def apply(self, context: LayerContext) -> None:
        """Apply this layer's settings to the context.

        Subclasses must implement this to modify the context appropriately.

        Args:
            context: Context to modify
        """
        pass

    def validate(self, context: LayerContext) -> None:
        """Validate that this layer can be applied to the context.

        Checks requirements and conflicts. Raises exception if validation fails.

        Args:
            context: Context to validate against

        Raises:
            LayerRequirementError: If requirements are not met
            LayerConflictError: If conflicts are detected
        """
        # Check requirements
        for req_type, req_values in self._requires.items():
            if req_type == "compiler":
                if context.compiler and context.compiler not in req_values:
                    raise LayerRequirementError(
                        f"Layer '{self.name}' requires compiler: {req_values}, "
                        f"but got: '{context.compiler}'"
                    )
            elif req_type == "platform":
                if context.platform and context.platform not in req_values:
                    raise LayerRequirementError(
                        f"Layer '{self.name}' requires platform: {req_values}, "
                        f"but got: '{context.platform}'"
                    )
            elif req_type == "linker":
                # Linker checking requires looking at flags (simplified for now)
                pass

        # Check conflicts
        for conflict_type, conflict_values in self._conflicts_with.items():
            if conflict_type == "sanitizer":
                for sanitizer in conflict_values:
                    if sanitizer in context.sanitizers:
                        raise LayerConflictError(
                            f"Layer '{self.name}' conflicts with sanitizer '{sanitizer}'. "
                            f"Cannot use {self.layer_type}/{self.name} with sanitizer/{sanitizer} "
                            f"because they are mutually exclusive."
                        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', type='{self.layer_type}')"
        )


# ============================================================================
# Concrete Layer Types
# ============================================================================


class BaseCompilerLayer(ConfigLayer):
    """Base compiler layer (Clang, GCC, MSVC).

    Defines the foundation compiler toolchain with default flags and CMake variables.

    Attributes:
        compiler: Compiler name (clang, gcc, msvc)
        version: Compiler version string
    """

    def __init__(self, name: str, compiler: str, version: str, description: str = ""):
        """Initialize base compiler layer.

        Args:
            name: Layer name (e.g., "clang-18")
            compiler: Compiler name (clang, gcc, msvc)
            version: Compiler version (e.g., "18.1.8")
            description: Human-readable description
        """
        super().__init__(name, "base", description)
        self.compiler = compiler
        self.version = version

    def apply(self, context: LayerContext) -> None:
        """Apply base compiler settings to context."""
        context.compiler = self.compiler
        context.compiler_version = self.version
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class PlatformLayer(ConfigLayer):
    """Platform layer (Linux, Windows, macOS, Android, etc.).

    Defines platform-specific settings like architecture, OS defines, etc.

    Attributes:
        platform: Platform string (linux-x64, windows-x64, etc.)
    """

    def __init__(self, name: str, platform: str, description: str = ""):
        """Initialize platform layer.

        Args:
            name: Layer name (e.g., "linux-x64")
            platform: Platform string
            description: Human-readable description
        """
        super().__init__(name, "platform", description)
        self.platform = platform

    def apply(self, context: LayerContext) -> None:
        """Apply platform settings to context."""
        context.platform = self.platform
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class StdLibLayer(ConfigLayer):
    """Standard library layer (libc++, libstdc++, MSVC stdlib).

    Defines C++ standard library selection and linking flags.

    Attributes:
        stdlib: Standard library name
    """

    def __init__(self, name: str, stdlib: str, description: str = ""):
        """Initialize standard library layer.

        Args:
            name: Layer name (e.g., "libc++")
            stdlib: Standard library name (libc++, libstdc++, msvc)
            description: Human-readable description
        """
        super().__init__(name, "stdlib", description)
        self.stdlib = stdlib

    def apply(self, context: LayerContext) -> None:
        """Apply standard library settings to context."""
        context.stdlib = self.stdlib
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class BuildTypeLayer(ConfigLayer):
    """Build type layer (Debug, Release, RelWithDebInfo, MinSizeRel).

    Defines optimization level, debug information, and assertions.

    Attributes:
        build_type: Build type name
    """

    def __init__(self, name: str, build_type: str, description: str = ""):
        """Initialize build type layer.

        Args:
            name: Layer name (e.g., "debug", "release")
            build_type: Build type (debug, release, relwithdebinfo, minsizerel)
            description: Human-readable description
        """
        super().__init__(name, "buildtype", description)
        self.build_type = build_type

    def apply(self, context: LayerContext) -> None:
        """Apply build type settings to context."""
        context.build_type = self.build_type
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class OptimizationLayer(ConfigLayer):
    """Optimization layer (LTO, PGO, etc.).

    Defines advanced optimization techniques.

    Attributes:
        optimization: Optimization name
    """

    def __init__(self, name: str, optimization: str, description: str = ""):
        """Initialize optimization layer.

        Args:
            name: Layer name (e.g., "lto-thin")
            optimization: Optimization type (lto-thin, lto-full, pgo)
            description: Human-readable description
        """
        super().__init__(name, "optimization", description)
        self.optimization = optimization

    def apply(self, context: LayerContext) -> None:
        """Apply optimization settings to context."""
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.add_runtime_env(self._runtime_env)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class SanitizerLayer(ConfigLayer):
    """Sanitizer layer (ASAN, TSAN, MSAN, UBSAN).

    Defines runtime error detection with sanitizers.

    Attributes:
        sanitizer: Sanitizer name
    """

    def __init__(self, name: str, sanitizer: str, description: str = ""):
        """Initialize sanitizer layer.

        Args:
            name: Layer name (e.g., "address")
            sanitizer: Sanitizer type (address, thread, memory, undefined, leak)
            description: Human-readable description
        """
        super().__init__(name, "sanitizer", description)
        self.sanitizer = sanitizer

    def apply(self, context: LayerContext) -> None:
        """Apply sanitizer settings to context."""
        context.sanitizers.add(self.sanitizer)
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.add_runtime_env(self._runtime_env)
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)


class AllocatorLayer(ConfigLayer):
    """Memory allocator layer (jemalloc, tcmalloc, mimalloc, etc.).

    Defines memory allocator selection and integration method.

    Supported allocators:
    - jemalloc: High-performance, low-fragmentation, multi-threaded
    - tcmalloc: Google's allocator with profiling integration
    - mimalloc: Microsoft's secure allocator with free-list sharding
    - snmalloc: Microsoft Research concurrent allocator
    - hoard: Prevents false sharing in multi-threaded apps
    - nedmalloc: Windows performance allocator
    - tbbmalloc: Intel TBB scalable allocator
    - default: System default malloc

    Integration methods:
    - link: Compile-time linking (e.g., -ljemalloc)
    - ld_preload: Runtime replacement via LD_PRELOAD (Linux/macOS only)
    - proxy: Proxy library approach (fallback)
    - auto: Automatic method selection (default)

    Attributes:
        allocator_name: Name of the allocator
        method: Integration method (auto, link, ld_preload, proxy)
    """

    def __init__(
        self,
        name: str,
        allocator_name: str,
        method: str = "auto",
        description: str = "",
    ):
        """Initialize memory allocator layer.

        Args:
            name: Layer name (e.g., "jemalloc")
            allocator_name: Allocator name (jemalloc, tcmalloc, mimalloc, etc.)
            method: Integration method (auto, link, ld_preload, proxy)
            description: Human-readable description
        """
        if not description:
            description = f"Memory allocator: {allocator_name}"
        super().__init__(name, "allocator", description)
        self.allocator_name = allocator_name
        self.method = method
        self._detected = False
        self._available_library: Optional[str] = None

    def apply(self, context: LayerContext) -> None:
        """Apply allocator settings to context.

        Raises:
            LayerRequirementError: If allocator is not available on the system
            LayerConflictError: If allocator conflicts with active sanitizers
        """
        # Check for conflicts with sanitizers first
        if context.has_sanitizer("address"):
            raise LayerConflictError(
                f"Allocator '{self.allocator_name}' conflicts with AddressSanitizer. "
                f"AddressSanitizer uses its own allocator and cannot be combined with "
                f"custom allocators like jemalloc, tcmalloc, etc."
            )
        if context.has_sanitizer("thread") and self.allocator_name not in ["default"]:
            raise LayerConflictError(
                f"Allocator '{self.allocator_name}' may conflict with ThreadSanitizer. "
                f"TSan requires careful allocator integration. Use default allocator with TSan."
            )
        if context.has_sanitizer("memory") and self.allocator_name not in ["default"]:
            raise LayerConflictError(
                f"Allocator '{self.allocator_name}' conflicts with MemorySanitizer. "
                f"MSan requires custom allocator support. Use default allocator with MSan."
            )

        # Default allocator needs no special configuration
        if self.allocator_name == "default":
            context.layer_types.add(self.layer_type)
            context.applied_layers.append(self)
            return

        # Detect allocator availability
        if not self._detect_allocator(context):
            raise LayerRequirementError(
                f"Allocator '{self.allocator_name}' not found on system. "
                f"Please install it using your package manager:\n"
                f"  Ubuntu/Debian: sudo apt install lib{self.allocator_name}-dev\n"
                f"  macOS (Homebrew): brew install {self.allocator_name}\n"
                f"  Fedora/RHEL: sudo dnf install {self.allocator_name}-devel"
            )

        # Choose integration method
        integration_method = self._choose_integration_method(context)

        # Apply method-specific configuration
        if integration_method == "link":
            self._apply_link_method(context)
        elif integration_method == "ld_preload":
            self._apply_ld_preload_method(context)
        elif integration_method == "proxy":
            self._apply_proxy_method(context)

        # Apply common settings from YAML
        context.add_flags(
            compile=self._compile_flags,
            link=self._link_flags,
            common=self._common_flags,
        )
        context.add_defines(self._defines)
        context.add_cmake_variables(self._cmake_variables)
        context.add_runtime_env(self._runtime_env)

        # Mark as applied
        context.layer_types.add(self.layer_type)
        context.applied_layers.append(self)

    def _detect_allocator(self, context: LayerContext) -> bool:
        """Detect if allocator is available on the system.

        Args:
            context: Layer context with platform information

        Returns:
            True if allocator is detected, False otherwise
        """
        if self._detected:
            return True

        platform = context.platform or ""

        # Define library names to search for
        lib_patterns = self._get_library_patterns(platform)

        # Search for library
        for pattern in lib_patterns:
            library = self._find_library(pattern, platform)
            if library:
                self._available_library = library
                self._detected = True
                return True

        return False

    def _get_library_patterns(self, platform: str) -> List[str]:
        """Get library filename patterns for the allocator on the given platform.

        Args:
            platform: Platform string (e.g., "linux-x64", "windows-x64")

        Returns:
            List of library filename patterns to search for
        """
        allocator_libs = {
            "jemalloc": {
                "linux": ["libjemalloc.so", "libjemalloc.so.2"],
                "macos": ["libjemalloc.dylib", "libjemalloc.2.dylib"],
                "windows": ["jemalloc.lib", "jemalloc.dll"],
            },
            "tcmalloc": {
                "linux": ["libtcmalloc.so", "libtcmalloc.so.4"],
                "macos": ["libtcmalloc.dylib"],
                "windows": ["libtcmalloc.lib"],
            },
            "mimalloc": {
                "linux": ["libmimalloc.so", "libmimalloc.so.2"],
                "macos": ["libmimalloc.dylib"],
                "windows": ["mimalloc.lib", "mimalloc.dll"],
            },
            "snmalloc": {
                "linux": ["libsnmalloc.so"],
                "macos": ["libsnmalloc.dylib"],
                "windows": ["snmalloc.lib"],
            },
            "hoard": {
                "linux": ["libhoard.so"],
                "macos": ["libhoard.dylib"],
                "windows": ["libhoard.lib"],
            },
            "nedmalloc": {
                "linux": ["libnedmalloc.so"],
                "macos": ["libnedmalloc.dylib"],
                "windows": ["nedmalloc.lib"],
            },
            "tbbmalloc": {
                "linux": ["libtbbmalloc.so", "libtbbmalloc.so.2"],
                "macos": ["libtbbmalloc.dylib"],
                "windows": ["tbbmalloc.lib"],
            },
        }

        # Determine OS from platform string
        os_name = "linux"
        if "windows" in platform.lower():
            os_name = "windows"
        elif "macos" in platform.lower() or "darwin" in platform.lower():
            os_name = "macos"

        return allocator_libs.get(self.allocator_name, {}).get(os_name, [])

    def _find_library(self, lib_name: str, platform: str) -> Optional[str]:
        """Find library file in standard system paths.

        Args:
            lib_name: Library filename to search for
            platform: Platform string

        Returns:
            Path to library if found, None otherwise
        """
        from pathlib import Path

        # Determine search paths based on platform
        search_paths = self._get_search_paths(platform)

        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                continue

            # Search in directory
            for lib_file in path.rglob(lib_name):
                return str(lib_file)

        return None

    def _get_search_paths(self, platform: str) -> List[str]:
        """Get library search paths for the platform.

        Args:
            platform: Platform string

        Returns:
            List of directory paths to search
        """
        if "windows" in platform.lower():
            return [
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                "C:\\Windows\\System32",
            ]
        elif "macos" in platform.lower() or "darwin" in platform.lower():
            return [
                "/usr/local/lib",
                "/opt/homebrew/lib",
                f"/usr/local/opt/{self.allocator_name}/lib",
                "/usr/lib",
            ]
        else:  # Linux
            return [
                "/usr/lib",
                "/usr/local/lib",
                "/usr/lib/x86_64-linux-gnu",
                "/usr/lib/aarch64-linux-gnu",
                "/lib",
            ]

    def _choose_integration_method(self, context: LayerContext) -> str:
        """Choose the best integration method for the allocator.

        Args:
            context: Layer context

        Returns:
            Integration method name (link, ld_preload, proxy)
        """
        if self.method != "auto":
            return self.method

        # Auto-select method based on platform and availability
        platform = context.platform or ""

        # Windows: Only link method supported (no LD_PRELOAD)
        if "windows" in platform.lower():
            return "link"

        # Prefer link method for reliability and performance
        return "link"

    def _apply_link_method(self, context: LayerContext) -> None:
        """Apply link-time integration (add linker flags).

        Args:
            context: Layer context to modify
        """
        # Add linker flag
        link_flag = f"-l{self.allocator_name}"
        if link_flag not in context.link_flags:
            context.link_flags.append(link_flag)

    def _apply_ld_preload_method(self, context: LayerContext) -> None:
        """Apply LD_PRELOAD runtime integration.

        Args:
            context: Layer context to modify
        """
        if self._available_library:
            # Set LD_PRELOAD environment variable
            context.runtime_env["LD_PRELOAD"] = self._available_library

    def _apply_proxy_method(self, context: LayerContext) -> None:
        """Apply proxy library integration.

        Args:
            context: Layer context to modify
        """
        # Proxy method: Create a small library that wraps malloc/free
        # and forwards to the actual allocator
        # This is a fallback method, not commonly used
        # For now, we fall back to link method
        self._apply_link_method(context)


class SecurityLayer(ConfigLayer):
    """Layer for configuring security hardening features.

    Supports:
    - Stack protector: strong, all, basic, none
    - Fortify source: levels 0-3
    - RELRO: full, partial, none
    - PIE: Position Independent Executable
    - Stack size limits
    - Hardened composite
    """

    def __init__(
        self,
        name: str,
        security_type: str,
        level: Optional[str] = None,
        mode: Optional[str] = None,
        stack_size: Optional[int] = None,
        description: str = "",
    ):
        """Initialize security layer.

        Args:
            name: Layer name (e.g., "stack-protector-strong")
            security_type: Type of security feature (stack_protector, fortify, relro, pie, stack_size, hardened)
            level: Security level for stack_protector/fortify (strong, all, basic, none, 0-3)
            mode: Mode for RELRO (full, partial, none)
            stack_size: Stack size limit in bytes (for stack_size type)
            description: Human-readable description
        """
        if not description:
            description = f"Security hardening: {security_type}"
        super().__init__(name, "security", description)
        self.security_type = security_type
        self.level = level
        self.mode = mode
        self.stack_size = stack_size

    def apply(self, context: LayerContext) -> None:
        """Apply security settings to context.

        Raises:
            ValueError: If security configuration is invalid
        """
        if self.security_type == "stack_protector":
            self._apply_stack_protector(context)
        elif self.security_type == "fortify":
            self._apply_fortify(context)
        elif self.security_type == "relro":
            self._apply_relro(context)
        elif self.security_type == "pie":
            self._apply_pie(context)
        elif self.security_type == "stack_size":
            self._apply_stack_size(context)
        elif self.security_type == "hardened":
            self._apply_hardened(context)
        else:
            raise ValueError(f"Unknown security type: {self.security_type}")

    def _apply_stack_protector(self, context: LayerContext) -> None:
        """Apply stack protector flags.

        Args:
            context: Layer context to modify
        """
        level = self.level or "strong"
        if level == "none":
            flag = "-fno-stack-protector"
        elif level == "basic":
            flag = "-fstack-protector"
        elif level == "strong":
            flag = "-fstack-protector-strong"
        elif level == "all":
            flag = "-fstack-protector-all"
        else:
            raise ValueError(f"Invalid stack protector level: {level}")

        if flag not in context.compile_flags:
            context.compile_flags.append(flag)

    def _apply_fortify(self, context: LayerContext) -> None:
        """Apply fortify source flags.

        Args:
            context: Layer context to modify
        """
        level = self.level or "2"
        if level not in ["0", "1", "2", "3"]:
            raise ValueError(f"Invalid fortify level: {level}")

        flag = f"-D_FORTIFY_SOURCE={level}"
        if flag not in context.compile_flags:
            context.compile_flags.append(flag)

        # Fortify requires optimization
        if level != "0" and not any("-O" in f for f in context.compile_flags):
            context.compile_flags.append("-O2")

    def _apply_relro(self, context: LayerContext) -> None:
        """Apply RELRO flags.

        Args:
            context: Layer context to modify
        """
        mode = self.mode or "full"
        if mode == "none":
            flag = "-Wl,-z,norelro"
        elif mode == "partial":
            flag = "-Wl,-z,relro"
        elif mode == "full":
            flag = "-Wl,-z,relro,-z,now"
        else:
            raise ValueError(f"Invalid RELRO mode: {mode}")

        if flag not in context.link_flags:
            context.link_flags.append(flag)

    def _apply_pie(self, context: LayerContext) -> None:
        """Apply PIE flags.

        Args:
            context: Layer context to modify
        """
        # Compiler flag for position-independent code
        if "-fPIE" not in context.compile_flags:
            context.compile_flags.append("-fPIE")

        # Linker flag for position-independent executable
        if "-pie" not in context.link_flags:
            context.link_flags.append("-pie")

    def _apply_stack_size(self, context: LayerContext) -> None:
        """Apply stack size limit.

        Args:
            context: Layer context to modify
        """
        if not self.stack_size:
            raise ValueError(
                "stack_size must be specified for stack_size security type"
            )

        flag = f"-Wl,-z,stack-size={self.stack_size}"
        if flag not in context.link_flags:
            context.link_flags.append(flag)

    def _apply_hardened(self, context: LayerContext) -> None:
        """Apply composite hardened flags.

        Args:
            context: Layer context to modify
        """
        # Stack protector strong
        if "-fstack-protector-strong" not in context.compile_flags:
            context.compile_flags.append("-fstack-protector-strong")

        # Fortify level 2
        if not any("_FORTIFY_SOURCE" in f for f in context.compile_flags):
            context.compile_flags.append("-D_FORTIFY_SOURCE=2")
            if not any("-O" in f for f in context.compile_flags):
                context.compile_flags.append("-O2")

        # Full RELRO
        if not any("relro" in f for f in context.link_flags):
            context.link_flags.append("-Wl,-z,relro,-z,now")

        # PIE
        if "-fPIE" not in context.compile_flags:
            context.compile_flags.append("-fPIE")
        if "-pie" not in context.link_flags:
            context.link_flags.append("-pie")


class ProfilingLayer(ConfigLayer):
    """Layer for configuring profiling instrumentation.

    Supports:
    - gprof: GNU profiler
    - instrument-functions: Function entry/exit instrumentation
    - asan-profile: AddressSanitizer with profiling
    - perf: Linux perf profiling
    """

    def __init__(
        self,
        name: str,
        profiling_type: str,
        description: str = "",
    ):
        """Initialize profiling layer.

        Args:
            name: Layer name (e.g., "gprof")
            profiling_type: Type of profiling (gprof, instrument_functions, asan_profile, perf)
            description: Human-readable description
        """
        if not description:
            description = f"Profiling: {profiling_type}"
        super().__init__(name, "profiling", description)
        self.profiling_type = profiling_type

    def apply(self, context: LayerContext) -> None:
        """Apply profiling settings to context.

        Raises:
            ValueError: If profiling configuration is invalid
        """
        if self.profiling_type == "gprof":
            self._apply_gprof(context)
        elif self.profiling_type == "instrument_functions":
            self._apply_instrument_functions(context)
        elif self.profiling_type == "asan_profile":
            self._apply_asan_profile(context)
        elif self.profiling_type == "perf":
            self._apply_perf(context)
        else:
            raise ValueError(f"Unknown profiling type: {self.profiling_type}")

    def _apply_gprof(self, context: LayerContext) -> None:
        """Apply gprof flags.

        Args:
            context: Layer context to modify
        """
        if "-pg" not in context.compile_flags:
            context.compile_flags.append("-pg")
        if "-pg" not in context.link_flags:
            context.link_flags.append("-pg")

    def _apply_instrument_functions(self, context: LayerContext) -> None:
        """Apply function instrumentation flags.

        Args:
            context: Layer context to modify
        """
        flag = "-finstrument-functions"
        if flag not in context.compile_flags:
            context.compile_flags.append(flag)

    def _apply_asan_profile(self, context: LayerContext) -> None:
        """Apply ASan profiling flags.

        Args:
            context: Layer context to modify
        """
        # Check if ASan is already enabled
        if not any("fsanitize=address" in f for f in context.compile_flags):
            raise ValueError(
                "asan_profile requires AddressSanitizer layer to be enabled"
            )

        # Add profiling-specific ASan flags
        flag = "-fsanitize-address-use-after-scope"
        if flag not in context.compile_flags:
            context.compile_flags.append(flag)

    def _apply_perf(self, context: LayerContext) -> None:
        """Apply perf profiling flags.

        Args:
            context: Layer context to modify
        """
        # Frame pointers for better stack traces
        if "-fno-omit-frame-pointer" not in context.compile_flags:
            context.compile_flags.append("-fno-omit-frame-pointer")

        # Debug info for symbol resolution
        if not any("-g" in f for f in context.compile_flags):
            context.compile_flags.append("-g")
