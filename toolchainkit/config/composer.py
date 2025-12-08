"""Layer composition system for building configurations from layers.

This module implements the LayerComposer which loads layers from YAML files
and composes them into a complete configuration. It handles:
- Layer discovery (project-local, global, built-in)
- YAML parsing and layer instantiation
- Layer composition and validation
- Configuration caching

Example:
    >>> from toolchainkit.config.composer import LayerComposer
    >>> composer = LayerComposer()
    >>> layer_specs = [
    ...     {"type": "base", "name": "clang-18"},
    ...     {"type": "platform", "name": "linux-x64"},
    ...     {"type": "buildtype", "name": "release"},
    ... ]
    >>> config = composer.compose(layer_specs)
    >>> print(config.compile_flags)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
import yaml

from toolchainkit.config.layers import (
    ConfigLayer,
    LayerContext,
    LayerError,
    LayerNotFoundError,
    LayerValidationError,
    BaseCompilerLayer,
    PlatformLayer,
    StdLibLayer,
    BuildTypeLayer,
    OptimizationLayer,
    SanitizerLayer,
    AllocatorLayer,
    SecurityLayer,
    ProfilingLayer,
)


# ============================================================================
# ComposedConfig: Final Configuration Result
# ============================================================================


@dataclass
class ComposedConfig:
    """Result of layer composition containing final configuration.

    This class wraps the final LayerContext after all layers have been applied.
    It provides convenient property access and conversion methods.

    Attributes:
        context: Final layer context with all layers applied
        layers: List of applied layers (for debugging/documentation)
    """

    def __init__(self, context: LayerContext, layers: List[ConfigLayer]):
        """Initialize ComposedConfig.

        Args:
            context: Final layer context
            layers: List of applied layers
        """
        self.context = context
        self.layers = layers

    @property
    def compiler(self) -> Optional[str]:
        """Compiler name (clang, gcc, msvc)."""
        return self.context.compiler

    @property
    def compiler_version(self) -> Optional[str]:
        """Compiler version string."""
        return self.context.compiler_version

    @property
    def platform(self) -> Optional[str]:
        """Target platform string."""
        return self.context.platform

    @property
    def stdlib(self) -> Optional[str]:
        """C++ standard library."""
        return self.context.stdlib

    @property
    def build_type(self) -> Optional[str]:
        """Build type (debug, release, etc.)."""
        return self.context.build_type

    @property
    def compile_flags(self) -> List[str]:
        """All compile flags."""
        return self.context.compile_flags

    @property
    def link_flags(self) -> List[str]:
        """All link flags."""
        return self.context.link_flags

    @property
    def defines(self) -> List[str]:
        """All preprocessor defines."""
        return self.context.defines

    @property
    def cmake_variables(self) -> Dict[str, str]:
        """All CMake variables."""
        return self.context.cmake_variables

    @property
    def runtime_env(self) -> Dict[str, str]:
        """All runtime environment variables."""
        return self.context.runtime_env

    @property
    def sanitizers(self) -> Set[str]:
        """Active sanitizers."""
        return self.context.sanitizers

    @property
    def linker(self) -> Optional[str]:
        """Linker name (if explicitly set via CMake variables)."""
        # Extract linker from link flags like -fuse-ld=lld
        for flag in self.context.link_flags:
            if "-fuse-ld=" in flag:
                return flag.split("=")[1]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "compiler": self.compiler,
            "compiler_version": self.compiler_version,
            "platform": self.platform,
            "stdlib": self.stdlib,
            "build_type": self.build_type,
            "compile_flags": self.compile_flags,
            "link_flags": self.link_flags,
            "defines": self.defines,
            "cmake_variables": self.cmake_variables,
            "runtime_env": self.runtime_env,
            "layers": [f"{layer.layer_type}/{layer.name}" for layer in self.layers],
        }

    def layer_info(self) -> List[Dict[str, str]]:
        """Get information about applied layers.

        Returns:
            List of layer info dictionaries
        """
        return [
            {
                "type": layer.layer_type,
                "name": layer.name,
                "description": layer.description,
            }
            for layer in self.layers
        ]


# ============================================================================
# LayerComposer: Main Composition Engine
# ============================================================================


class LayerComposer:
    """Compose configuration from layers loaded from YAML files.

    The LayerComposer handles:
    - Layer discovery: Searches project-local, global, and built-in directories
    - YAML parsing: Loads layer definitions from YAML
    - Layer instantiation: Creates ConfigLayer objects
    - Composition: Applies layers in order with validation
    - Caching: Caches loaded layers for performance

    Layer Discovery Order:
    1. Project-local: .toolchainkit/layers/{type}/{name}.yaml
    2. Global: ~/.toolchainkit/layers/{type}/{name}.yaml
    3. Built-in: toolchainkit/data/layers/{type}/{name}.yaml

    Example:
        >>> composer = LayerComposer()
        >>> layers = [
        ...     {"type": "base", "name": "clang-18"},
        ...     {"type": "platform", "name": "linux-x64"},
        ... ]
        >>> config = composer.compose(layers)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        global_layers_dir: Optional[Path] = None,
        builtin_layers_dir: Optional[Path] = None,
    ):
        """Initialize layer composer.

        Args:
            project_root: Project root directory (for project-local layers)
            global_layers_dir: Global layers directory (defaults to ~/.toolchainkit/layers)
            builtin_layers_dir: Built-in layers directory (defaults to package data)
        """
        self.project_root = project_root
        self.global_layers_dir = global_layers_dir or (
            Path.home() / ".toolchainkit" / "layers"
        )
        self.builtin_layers_dir = builtin_layers_dir or (
            Path(__file__).parent.parent / "data" / "layers"
        )

        # Cache for loaded layers
        self._layer_cache: Dict[str, ConfigLayer] = {}
        self._yaml_cache: Dict[str, Dict] = {}

    def compose(
        self, layer_specs: List[Dict[str, str]], **interpolation_vars: Any
    ) -> ComposedConfig:
        """Compose configuration from layer specifications.

        Args:
            layer_specs: List of layer specs, each with "type" and "name" keys
            **interpolation_vars: Variables for interpolation (e.g., toolchain_root)

        Returns:
            ComposedConfig with final configuration

        Raises:
            LayerValidationError: If validation fails
            LayerNotFoundError: If a layer cannot be found

        Example:
            >>> specs = [
            ...     {"type": "base", "name": "clang-18"},
            ...     {"type": "platform", "name": "linux-x64"},
            ... ]
            >>> config = composer.compose(specs, toolchain_root="/opt/llvm-18")
        """
        # Validate required layers are present
        self._validate_layer_specs(layer_specs)

        # Initialize context
        context = LayerContext()

        # Apply layers in order
        applied_layers = []
        for spec in layer_specs:
            layer = self.load_layer(spec["type"], spec["name"])

            # Validate layer can be applied
            layer.validate(context)

            # Apply layer
            layer.apply(context)
            applied_layers.append(layer)

        # Interpolate variables in CMake variables and runtime env
        if interpolation_vars:
            self._interpolate_context(context, interpolation_vars)

        return ComposedConfig(context, applied_layers)

    def load_layer(self, layer_type: str, name: str) -> ConfigLayer:
        """Load a layer by type and name.

        Searches in order: project-local → global → built-in

        Args:
            layer_type: Layer type (base, platform, stdlib, buildtype, optimization, sanitizer)
            name: Layer name (e.g., "clang-18", "linux-x64")

        Returns:
            Loaded ConfigLayer instance

        Raises:
            LayerNotFoundError: If layer cannot be found
        """
        cache_key = f"{layer_type}/{name}"

        # Check cache
        if cache_key in self._layer_cache:
            return self._layer_cache[cache_key]

        # Find layer file
        layer_file = self._find_layer_file(layer_type, name)
        if not layer_file:
            raise LayerNotFoundError(
                f"Layer '{cache_key}' not found. Searched:\n"
                f"  - Project: {self._get_project_layer_path(layer_type, name)}\n"
                f"  - Global: {self.global_layers_dir / layer_type / f'{name}.yaml'}\n"
                f"  - Built-in: {self.builtin_layers_dir / layer_type / f'{name}.yaml'}"
            )

        # Load and parse YAML
        yaml_data = self._load_yaml(layer_file)

        # Create layer instance
        layer = self._create_layer_instance(yaml_data, layer_type, name)

        # Cache and return
        self._layer_cache[cache_key] = layer
        return layer

    def list_layers(self, layer_type: Optional[str] = None) -> List[str]:
        """List available layers.

        Args:
            layer_type: If specified, list only this layer type

        Returns:
            List of layer identifiers (e.g., ["base/clang-18", "platform/linux-x64"])
        """
        layers = []

        # Determine which layer types to search
        layer_types = (
            [layer_type]
            if layer_type
            else [
                "base",
                "platform",
                "stdlib",
                "buildtype",
                "optimization",
                "sanitizer",
            ]
        )

        # Search all directories
        for ltype in layer_types:
            # Built-in layers
            builtin_dir = self.builtin_layers_dir / ltype
            if builtin_dir.exists():
                for yaml_file in builtin_dir.glob("*.yaml"):
                    layers.append(f"{ltype}/{yaml_file.stem}")

            # Global layers
            global_dir = self.global_layers_dir / ltype
            if global_dir.exists():
                for yaml_file in global_dir.glob("*.yaml"):
                    layer_id = f"{ltype}/{yaml_file.stem}"
                    if layer_id not in layers:  # Avoid duplicates
                        layers.append(layer_id)

            # Project-local layers
            if self.project_root:
                project_dir = self.project_root / ".toolchainkit" / "layers" / ltype
                if project_dir.exists():
                    for yaml_file in project_dir.glob("*.yaml"):
                        layer_id = f"{ltype}/{yaml_file.stem}"
                        if layer_id not in layers:  # Avoid duplicates
                            layers.append(layer_id)

        return sorted(layers)

    # ------------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------------

    def _validate_layer_specs(self, layer_specs: List[Dict[str, str]]) -> None:
        """Validate that required layer types are present.

        Args:
            layer_specs: Layer specifications to validate

        Raises:
            LayerValidationError: If validation fails
        """
        layer_types = [spec["type"] for spec in layer_specs]

        # Required layer types
        if "base" not in layer_types:
            raise LayerValidationError(
                "Missing required layer type 'base'. Every configuration must have a base compiler layer."
            )
        if "platform" not in layer_types:
            raise LayerValidationError(
                "Missing required layer type 'platform'. Every configuration must specify a target platform."
            )
        if "buildtype" not in layer_types:
            raise LayerValidationError(
                "Missing required layer type 'buildtype'. Every configuration must specify a build type (debug, release, etc.)."
            )

        # Check for duplicates of single-instance layer types
        for ltype in ["base", "platform", "stdlib", "buildtype"]:
            if layer_types.count(ltype) > 1:
                raise LayerValidationError(
                    f"Multiple '{ltype}' layers are not allowed. Only one {ltype} layer per configuration."
                )

    def _find_layer_file(self, layer_type: str, name: str) -> Optional[Path]:
        """Find layer file by searching discovery paths.

        Args:
            layer_type: Layer type
            name: Layer name

        Returns:
            Path to layer file, or None if not found
        """
        # 1. Project-local
        if self.project_root:
            project_file = self._get_project_layer_path(layer_type, name)
            if project_file.exists():
                return project_file

        # 2. Global
        global_file = self.global_layers_dir / layer_type / f"{name}.yaml"
        if global_file.exists():
            return global_file

        # 3. Built-in
        builtin_file = self.builtin_layers_dir / layer_type / f"{name}.yaml"
        if builtin_file.exists():
            return builtin_file

        return None

    def _get_project_layer_path(self, layer_type: str, name: str) -> Path:
        """Get path to project-local layer file.

        Args:
            layer_type: Layer type
            name: Layer name

        Returns:
            Path to project-local layer file
        """
        if not self.project_root:
            return Path("/nonexistent")  # Placeholder when no project root
        return (
            self.project_root / ".toolchainkit" / "layers" / layer_type / f"{name}.yaml"
        )

    def _load_yaml(self, yaml_file: Path) -> Dict:
        """Load and parse YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            Parsed YAML data

        Raises:
            LayerError: If YAML parsing fails
        """
        cache_key = str(yaml_file)

        # Check cache
        if cache_key in self._yaml_cache:
            return self._yaml_cache[cache_key]

        # Load YAML
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise LayerError(f"Failed to parse YAML file '{yaml_file}': {e}")
        except OSError as e:
            raise LayerError(f"Failed to read YAML file '{yaml_file}': {e}")

        # Cache and return
        self._yaml_cache[cache_key] = data
        return data

    def _create_layer_instance(
        self, yaml_data: Dict, layer_type: str, name: str
    ) -> ConfigLayer:
        """Create ConfigLayer instance from YAML data.

        Args:
            yaml_data: Parsed YAML data
            layer_type: Expected layer type
            name: Layer name

        Returns:
            ConfigLayer instance

        Raises:
            LayerError: If layer creation fails
        """
        # Validate layer type matches
        if yaml_data.get("type") != layer_type:
            raise LayerError(
                f"Layer type mismatch: expected '{layer_type}', got '{yaml_data.get('type')}'"
            )

        # Get description
        description = yaml_data.get("description", "")

        # Create layer based on type
        layer: ConfigLayer
        if layer_type == "base":
            layer = BaseCompilerLayer(
                name=name,
                compiler=yaml_data.get("compiler", ""),
                version=yaml_data.get("version", ""),
                description=description,
            )
        elif layer_type == "platform":
            layer = PlatformLayer(
                name=name,
                platform=yaml_data.get("platform", name),
                description=description,
            )
        elif layer_type == "stdlib":
            layer = StdLibLayer(
                name=name, stdlib=yaml_data.get("stdlib", name), description=description
            )
        elif layer_type == "buildtype":
            layer = BuildTypeLayer(name=name, build_type=name, description=description)
        elif layer_type == "optimization":
            layer = OptimizationLayer(
                name=name, optimization=name, description=description
            )
        elif layer_type == "sanitizer":
            layer = SanitizerLayer(name=name, sanitizer=name, description=description)
        elif layer_type == "allocator":
            method = yaml_data.get("method", "auto")
            layer = AllocatorLayer(
                name=name,
                allocator_name=name,
                method=method,
                description=description,
            )
        elif layer_type == "security":
            security_type = yaml_data.get("security_type", name)
            level = yaml_data.get("level")
            mode = yaml_data.get("mode")
            stack_size = yaml_data.get("stack_size")
            layer = SecurityLayer(
                name=name,
                security_type=security_type,
                level=level,
                mode=mode,
                stack_size=stack_size,
                description=description,
            )
        elif layer_type == "profiling":
            profiling_type = yaml_data.get("profiling_type", name)
            layer = ProfilingLayer(
                name=name,
                profiling_type=profiling_type,
                description=description,
            )
        else:
            raise LayerError(f"Unknown layer type: {layer_type}")

        # Populate layer settings from YAML
        self._populate_layer_settings(layer, yaml_data)

        return layer

    def _populate_layer_settings(self, layer: ConfigLayer, yaml_data: Dict) -> None:
        """Populate layer settings from YAML data.

        Args:
            layer: Layer to populate
            yaml_data: YAML data
        """
        # Flags
        flags = yaml_data.get("flags", {})
        layer._common_flags = flags.get("common", [])
        layer._compile_flags = flags.get("compile", [])
        layer._link_flags = flags.get("link", [])

        # Defines
        layer._defines = yaml_data.get("defines", [])

        # CMake variables
        layer._cmake_variables = yaml_data.get("cmake_variables", {})

        # Runtime environment
        layer._runtime_env = yaml_data.get("runtime_env", {})

        # Requirements
        layer._requires = yaml_data.get("requires", {})

        # Conflicts
        layer._conflicts_with = yaml_data.get("conflicts_with", {})

    def _interpolate_context(
        self, context: LayerContext, variables: Dict[str, Any]
    ) -> None:
        """Interpolate variables in context CMake variables and runtime env.

        Args:
            context: Context to interpolate
            variables: Variables for interpolation
        """
        # Interpolate CMake variables
        interpolated_cmake = {}
        for key, value in context.cmake_variables.items():
            interpolated_cmake[key] = context.interpolate_variables(value, **variables)
        context.cmake_variables = interpolated_cmake

        # Interpolate runtime environment
        interpolated_env = {}
        for key, value in context.runtime_env.items():
            interpolated_env[key] = context.interpolate_variables(value, **variables)
        context.runtime_env = interpolated_env
