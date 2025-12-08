"""
YAML-based compiler configuration loader for ToolchainKit.

This module provides functionality to load compiler configurations from
YAML files, enabling declarative compiler definitions without Python code.
Supports composition, platform overrides, and variable interpolation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml


class YAMLCompilerError(Exception):
    """Base exception for YAML compiler errors."""

    pass


class YAMLCompilerNotFoundError(YAMLCompilerError):
    """Raised when a YAML compiler configuration file is not found."""

    pass


class YAMLCompilerInvalidError(YAMLCompilerError):
    """Raised when a YAML compiler configuration is invalid."""

    pass


class YAMLCompilerLoader:
    """
    Load compiler configurations from YAML files.

    This loader supports:
    - Basic YAML parsing
    - Composition (extends) for inheritance
    - Platform-specific overrides
    - Caching for performance

    Example:
        >>> loader = YAMLCompilerLoader(Path("data/compilers"))
        >>> config = loader.load("clang", platform="linux")
        >>> flags = config.get_flags_for_build_type("release")
    """

    def __init__(self, data_dir: Union[str, Path]):
        """
        Initialize the YAML compiler loader.

        Args:
            data_dir: Path to data directory (contains compilers/ subdirectory)
        """
        self.data_dir = Path(data_dir)
        self.compilers_dir = self.data_dir / "compilers"
        self.layers_dir = self.data_dir / "layers"
        self._yaml_cache: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Dict[str, "YAMLCompilerConfig"] = {}

    def load(
        self, compiler_name: str, platform: Optional[str] = None
    ) -> "YAMLCompilerConfig":
        """
        Load a compiler configuration from YAML.

        Args:
            compiler_name: Name of the compiler (e.g., "clang", "gcc", "msvc")
            platform: Optional platform string for platform-specific overrides
                     (e.g., "windows", "linux", "macos", "linux-x64")

        Returns:
            YAMLCompilerConfig instance

        Raises:
            YAMLCompilerNotFoundError: If compiler YAML file not found
            YAMLCompilerInvalidError: If YAML is invalid or malformed

        Example:
            >>> loader = YAMLCompilerLoader(Path("data/compilers"))
            >>> clang = loader.load("clang", "linux")
            >>> gcc = loader.load("gcc")
        """
        # Check cache first (cache by compiler_name + platform)
        cache_key = f"{compiler_name}:{platform or 'default'}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Load base configuration
        config_data = self._load_yaml_file(compiler_name)

        # Handle composition (extends) with circular dependency detection
        if "extends" in config_data:
            visited = {compiler_name}
            config_data = self._resolve_extends(config_data, visited)

        # Apply platform overrides if specified (platform overrides replace, not append)
        if platform and "platform_overrides" in config_data:
            # Try exact match first (e.g., "linux-x64")
            if platform in config_data["platform_overrides"]:
                override_data = config_data["platform_overrides"][platform]
                config_data = self._merge_configs(
                    config_data, override_data, append_lists=False
                )
            else:
                # Try OS-only match (e.g., "linux" for "linux-x64")
                os_name = platform.split("-")[0]
                if os_name in config_data["platform_overrides"]:
                    override_data = config_data["platform_overrides"][os_name]
                    config_data = self._merge_configs(
                        config_data, override_data, append_lists=False
                    )

        # Create and cache config
        config = YAMLCompilerConfig(config_data, compiler_name, self.layers_dir)
        self._config_cache[cache_key] = config
        return config

    def list_available(self) -> List[str]:
        """
        List all available compiler configurations.

        Returns:
            List of compiler names (without .yaml extension)

        Example:
            >>> loader = YAMLCompilerLoader(Path("data/compilers"))
            >>> compilers = loader.list_available()
            >>> print(compilers)  # ['clang', 'gcc', 'msvc']
        """
        if not self.compilers_dir.exists():
            return []

        yaml_files = self.compilers_dir.glob("*.yaml")
        return [f.stem for f in yaml_files]

    def _load_yaml_file(self, name: str) -> Dict[str, Any]:
        """
        Load and cache a YAML file.

        Args:
            name: Compiler name (without .yaml extension)

        Returns:
            Parsed YAML data as dictionary

        Raises:
            YAMLCompilerNotFoundError: If file doesn't exist
            YAMLCompilerInvalidError: If YAML is malformed
        """
        # Return from cache if available
        if name in self._yaml_cache:
            return self._yaml_cache[name].copy()

        # Try with .yaml extension
        yaml_file = self.compilers_dir / f"{name}.yaml"
        if not yaml_file.exists():
            raise YAMLCompilerNotFoundError(
                f"Compiler configuration not found: {yaml_file}\n"
                f"Available compilers: {', '.join(self.list_available())}"
            )

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise YAMLCompilerInvalidError(
                    f"Empty or invalid YAML file: {yaml_file}"
                )

            if not isinstance(data, dict):
                raise YAMLCompilerInvalidError(
                    f"YAML must be a dictionary (object), got {type(data).__name__}: {yaml_file}"
                )

            # Cache the loaded data
            self._yaml_cache[name] = data.copy()
            return data

        except yaml.YAMLError as e:
            raise YAMLCompilerInvalidError(
                f"Invalid YAML syntax in {yaml_file}: {e}"
            ) from e
        except Exception as e:
            raise YAMLCompilerError(f"Failed to load {yaml_file}: {e}") from e

    def _resolve_extends(
        self, config_data: Dict[str, Any], visited: set
    ) -> Dict[str, Any]:
        """
        Recursively resolve extends relationships with circular dependency detection.

        Args:
            config_data: Configuration dictionary
            visited: Set of already visited compiler names (for cycle detection)

        Returns:
            Merged configuration with all extends resolved

        Raises:
            YAMLCompilerError: If circular extends detected
        """
        if "extends" not in config_data:
            return config_data

        base_name = config_data["extends"]
        # Remove .yaml extension if present
        if base_name.endswith(".yaml"):
            base_name = base_name[:-5]

        # Check for circular dependency
        if base_name in visited:
            raise YAMLCompilerError(
                f"Circular extends detected: {' -> '.join(visited)} -> {base_name}"
            )

        # Load base and recursively resolve its extends
        visited.add(base_name)
        base_data = self._load_yaml_file(base_name)
        base_data = self._resolve_extends(base_data, visited)

        # Merge base with current config
        return self._merge_configs(base_data, config_data)

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any], append_lists: bool = True
    ) -> Dict[str, Any]:
        """
        Deep merge two configurations, with override taking precedence.

        Merge semantics:
        - Nested dictionaries: Deep merge keys
        - Lists: Append if append_lists=True, replace if False
        - Primitives: Override value replaces base value

        Args:
            base: Base configuration (lower priority)
            override: Override configuration (higher priority)
            append_lists: If True, append lists; if False, replace them

        Returns:
            Merged configuration dictionary

        Example:
            >>> base = {'flags': {'debug': ['-g']}, 'name': 'clang'}
            >>> override = {'flags': {'release': ['-O3']}, 'version': '18'}
            >>> result = loader._merge_configs(base, override)
            >>> # result: {'flags': {'debug': ['-g'], 'release': ['-O3']},
            >>> #          'name': 'clang', 'version': '18'}
        """
        result = base.copy()

        for key, value in override.items():
            if key in result:
                base_value = result[key]

                # Deep merge nested dictionaries
                if isinstance(base_value, dict) and isinstance(value, dict):
                    result[key] = self._merge_configs(base_value, value, append_lists)
                # Merge or replace lists based on append_lists
                elif isinstance(base_value, list) and isinstance(value, list):
                    if append_lists:
                        result[key] = base_value + value
                    else:
                        result[key] = value
                else:
                    # For primitives, override replaces base
                    result[key] = value
            else:
                # New key, just add it
                result[key] = value

        return result


class YAMLCompilerConfig:
    """
    Compiler configuration loaded from YAML.

    This class provides an interface to query compiler settings such as
    flags, standards, stdlib, linkers, sanitizers, etc. It's compatible
    with the existing CompilerConfig interface for backward compatibility.

    Example:
        >>> config = YAMLCompilerConfig(config_data, "clang")
        >>> flags = config.get_flags_for_build_type("release")
        >>> print(flags)  # ['-O3', '-DNDEBUG']
    """

    def __init__(
        self, config_data: Dict[str, Any], name: str, layers_dir: Optional[Path] = None
    ):
        """
        Initialize compiler configuration from parsed YAML data.

        Args:
            config_data: Parsed YAML configuration dictionary
            name: Compiler name (for error messages)
            layers_dir: Path to layers directory (for loading linker configs)
        """
        self._config = config_data
        self.config_data = config_data  # Alias for internal use
        self.name = name
        self.layers_dir = layers_dir
        self._validate_required_fields()

    def _validate_required_fields(self) -> None:
        """
        Validate that required fields are present.

        Raises:
            YAMLCompilerInvalidError: If required fields are missing
        """
        # Only check minimal required fields
        required_fields = ["name", "compiler_family"]

        missing_fields = [
            field for field in required_fields if field not in self.config_data
        ]

        if missing_fields:
            raise YAMLCompilerInvalidError(
                f"Compiler '{self.name}' is missing required fields: "
                f"{', '.join(missing_fields)}"
            )

    def get_flags_for_build_type(self, build_type: str) -> List[str]:
        """
        Get compiler flags for a specific build type.

        Args:
            build_type: Build type name (e.g., "Debug", "Release",
                       "RelWithDebInfo", "MinSizeRel")

        Returns:
            List of compiler flags

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flags = config.get_flags_for_build_type("Release")
            >>> print(flags)  # ['-O3', '-DNDEBUG']
        """
        flags_section = self.config_data.get("flags", {})
        build_type_lower = build_type.lower()
        return flags_section.get(build_type_lower, [])

    def get_warning_flags(self, level: str = "standard") -> List[str]:
        """
        Get warning flags for a specific warning level.

        Args:
            level: Warning level ('off', 'minimal', 'standard', 'strict', 'paranoid')

        Returns:
            List of warning flags

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> warnings = config.get_warning_flags('standard')
            >>> print(warnings)  # ['-Wall', '-Wextra']
        """
        warning_levels = self.config_data.get("warning_levels", {})
        return warning_levels.get(level, [])

    def get_standard_flag(self, language: str, standard: str) -> Optional[str]:
        """
        Get the flag for a specific language standard.

        Args:
            language: Language ('c' or 'cpp')
            standard: Standard version (e.g., 'cpp20', 'c17')

        Returns:
            Flag string (e.g., '-std=c++20') or None if not found

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flag = config.get_standard_flag('cpp', 'cpp20')
            >>> print(flag)  # '-std=c++20'
        """
        language_standards = self.config_data.get("language_standards", {})
        if language not in language_standards:
            return None

        lang_standards = language_standards[language]
        return lang_standards.get(standard, None)

    def get_default_standard(self, language: str) -> str:
        """
        Get the default language standard.

        Args:
            language: Language ('c' or 'cxx')

        Returns:
            Default standard (e.g., 'c++20')

        Raises:
            YAMLCompilerInvalidError: If language not supported
        """
        standards = self.config_data.get("standards", {})
        if language not in standards:
            raise YAMLCompilerInvalidError(
                f"Language '{language}' not supported by compiler '{self.name}'"
            )

        return standards[language].get("default", "")

    def get_stdlib_flags(self, stdlib_name: str) -> Optional[Dict[str, List[str]]]:
        """
        Get standard library flags.

        Args:
            stdlib_name: Standard library name (e.g., 'libc++', 'libstdc++', 'msvc')

        Returns:
            Dictionary with 'flags', 'defines', 'link_flags' keys or None if not found

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flags = config.get_stdlib_flags('libc++')
            >>> print(flags['compile_flags'])  # ['-stdlib=libc++']
            >>> print(flags['link_flags'])      # ['-lc++', '-lc++abi']
        """
        stdlib = self.config_data.get("stdlib", {})
        if stdlib_name not in stdlib:
            return None

        stdlib_config = stdlib[stdlib_name]
        return {
            "compile_flags": stdlib_config.get("compile_flags", []),
            "defines": stdlib_config.get("defines", []),
            "link_flags": stdlib_config.get("link_flags", []),
        }

    def get_linker_flag(self, linker_name: str) -> Optional[str]:
        """
        Get linker selection flag.

        Args:
            linker_name: Linker name (e.g., 'lld', 'gold', 'mold', 'ld')

        Returns:
            Linker flag (e.g., '-fuse-ld=lld') or None if not found

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flag = config.get_linker_flag('lld')
            >>> print(flag)  # '-fuse-ld=lld'
        """
        linker_config = self.config_data.get("linker", {})
        if not linker_config:
            return None

        # Try loading linker layer from linker directory
        if self.layers_dir:
            linker_file = self.layers_dir / "linker" / f"{linker_name}.yaml"
            if linker_file.exists():
                try:
                    with open(linker_file, "r", encoding="utf-8") as f:
                        linker_data = yaml.safe_load(f)
                    # Extract flag from linker data
                    flag = linker_data.get("flag")
                    if flag:
                        return flag
                except Exception:
                    pass

        # Fall back to inline linker config if external file not found
        if linker_name in linker_config:
            return linker_config[linker_name].get("flag")

        # Linker not found
        return None

    def get_sanitizer_flags(self, sanitizer: str) -> Optional[Dict[str, List[str]]]:
        """
        Get sanitizer flags.

        Args:
            sanitizer: Sanitizer name (e.g., 'address', 'undefined', 'thread')

        Returns:
            Dictionary with 'flags', 'defines', 'link_flags' keys or None if not found

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flags = config.get_sanitizer_flags('address')
            >>> print(flags['compile_flags'])  # ['-fsanitize=address']
        """
        features = self.config_data.get("features", {})
        sanitizers = features.get("sanitizers", {})
        if sanitizer not in sanitizers:
            return None

        san_config = sanitizers[sanitizer]
        return {
            "compile_flags": san_config.get("compile_flags", []),
            "defines": san_config.get("defines", []),
            "link_flags": san_config.get("link_flags", []),
        }

    def get_lto_flags(self, lto_type: str = "full") -> Optional[Dict[str, List[str]]]:
        """
        Get LTO (Link-Time Optimization) flags.

        Args:
            lto_type: LTO type ('thin' or 'full')

        Returns:
            Dictionary with 'flags' and 'link_flags' keys or None if not found

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flags = config.get_lto_flags('thin')
            >>> print(flags['compile_flags'])  # ['-flto=thin']
        """
        features = self.config_data.get("features", {})
        lto = features.get("lto", {})
        if lto_type not in lto:
            return None

        lto_config = lto[lto_type]
        return {
            "compile_flags": lto_config.get("compile_flags", []),
            "link_flags": lto_config.get("link_flags", []),
        }

    def get_coverage_flags(self) -> List[str]:
        """
        Get code coverage flags.

        Returns:
            List of coverage compile flags, or empty list if not configured

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> flags = config.get_coverage_flags()
            >>> print(flags)  # ['--coverage']
        """
        features = self.config_data.get("features", {})
        coverage = features.get("coverage", {})
        # Return just the compile flags as a list
        return coverage.get("flags", [])

    def get_cmake_variables(
        self, toolchain_root: Optional[Path] = None, **kwargs: Any
    ) -> Dict[str, str]:
        """
        Get CMake variables for this compiler.

        Performs variable interpolation for:
        - {toolchain_root}: Path to toolchain installation
        - {version}: Compiler version
        - {platform}: Platform string
        - Any additional kwargs

        Args:
            toolchain_root: Path to toolchain installation
            **kwargs: Additional variables for interpolation

        Returns:
            Dictionary of CMake variable name -> value

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> vars = config.get_cmake_variables(Path("/opt/clang-18"))
            >>> print(vars['CMAKE_C_COMPILER'])  # '/opt/clang-18/bin/clang'
        """
        # Support both cmake.variables and cmake_variables formats
        cmake = self.config_data.get("cmake", {})
        cmake_vars = cmake.get("variables", {})

        # Backward compatibility: also check top-level cmake_variables
        if not cmake_vars:
            cmake_vars = self.config_data.get("cmake_variables", {})

        # Build interpolation context
        context = kwargs.copy()
        if toolchain_root:
            context["toolchain_root"] = str(toolchain_root)

        # Interpolate variables
        result = {}
        for key, value in cmake_vars.items():
            if isinstance(value, str):
                result[key] = self.interpolate_variables(value, **context)
            else:
                result[key] = value

        return result

    def interpolate_variables(self, value: str, **kwargs: Any) -> str:
        """
        Interpolate variables in a string.

        Supports placeholders like {toolchain_root}, {version}, {platform}, etc.

        Args:
            value: String with placeholders
            **kwargs: Variables for interpolation

        Returns:
            String with placeholders replaced

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> result = config.interpolate_variables(
            ...     "{toolchain_root}/bin/clang",
            ...     toolchain_root="/opt/clang-18"
            ... )
            >>> print(result)  # '/opt/clang-18/bin/clang'
        """
        # Handle different value types
        if isinstance(value, str):
            # Check if we have {{ }} format (needs interpolation)
            if "{{" in value and "}}" in value:
                # Replace {{var}} with {var} for format string compatibility
                temp_value = value.replace("{{", "{").replace("}}", "}")
                try:
                    return temp_value.format(**kwargs)
                except KeyError:
                    # Missing variable, return original with {{ }}
                    return value
            else:
                # Already has single braces, just try format
                try:
                    return value.format(**kwargs)
                except KeyError:
                    # Missing variable, return as-is
                    return value
        elif isinstance(value, list):
            return [self.interpolate_variables(item, **kwargs) for item in value]
        elif isinstance(value, dict):
            return {
                key: self.interpolate_variables(val, **kwargs)
                for key, val in value.items()
            }
        else:
            return value

    def get_executables(self) -> Dict[str, str]:
        """
        Get compiler executable names.

        Returns:
            Dictionary with keys: 'c', 'cxx', 'ar', 'ranlib'

        Example:
            >>> config = YAMLCompilerConfig(data, "clang")
            >>> exes = config.get_executables()
            >>> print(exes['cxx'])  # 'clang++'
        """
        return self.config_data.get("executables", {})

    def get_display_name(self) -> str:
        """Get human-readable compiler name."""
        return self.config_data.get("display_name", self.name)

    def get_type(self) -> str:
        """Get compiler type ('clang', 'gcc', or 'msvc')."""
        return self.config_data.get("type", "")

    def get_version_command(self) -> List[str]:
        """Get command to query compiler version."""
        return self.config_data.get("version_command", [])

    def get_version_regex(self) -> str:
        """Get regex to extract version from compiler output."""
        return self.config_data.get("version_regex", "")
