"""
Plugin context for providing system resources to plugins.

This module implements the PluginContext class that provides plugins with
access to system resources during initialization, including:
- Plugin registry for registration
- Cache directory for plugin data
- Global configuration access
- Helper methods for common operations
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Dict

if TYPE_CHECKING:
    from toolchainkit.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginContext:
    """
    Context provided to plugins during initialization.

    Provides plugins with:
    - Access to plugin registry for registration
    - Cache directory for plugin data
    - Global configuration access
    - Helper methods for common operations

    Example:
        ```python
        class MyPlugin(CompilerPlugin):
            def initialize(self, context: PluginContext) -> None:
                # Get plugin cache directory
                cache = context.cache_dir

                # Load compiler configuration
                config = context.load_yaml_compiler('my_compiler.yaml')

                # Register compiler
                context.register_compiler('my_compiler', config)

                # Log success
                context.log('info', 'My compiler registered')
        ```
    """

    def __init__(
        self,
        registry: PluginRegistry,
        cache_dir: Path,
        config: Dict[str, Any],
    ) -> None:
        """
        Initialize plugin context.

        Args:
            registry: Plugin registry for registration
            cache_dir: Cache directory for plugin data
            config: Global configuration dictionary
        """
        self._registry = registry
        self._cache_dir = cache_dir
        self._config = config

    # Properties

    @property
    def cache_dir(self) -> Path:
        """
        Get plugin cache directory.

        Returns:
            Path to cache directory for this plugin.
            Typically: ~/.toolchainkit/plugins/cache/{plugin_name}/

        Example:
            ```python
            cache_file = context.cache_dir / "downloaded.tar.gz"
            if cache_file.exists():
                print(f"Using cached file: {cache_file}")
            ```
        """
        return self._cache_dir

    @property
    def config(self) -> Dict[str, Any]:
        """
        Get global ToolchainKit configuration.

        Returns:
            Configuration dictionary with global settings.

        Example:
            ```python
            if context.config.get('verbose'):
                context.log('debug', 'Verbose mode enabled')
            ```
        """
        return self._config

    # Registration Methods

    def register_compiler(
        self,
        name: str,
        config: Any,
    ) -> None:
        """
        Register a compiler configuration.

        Args:
            name: Compiler name (e.g., 'zig', 'gcc', 'clang')
            config: CompilerConfig instance

        Raises:
            ValueError: If compiler with this name is already registered

        Example:
            ```python
            zig_config = context.load_yaml_compiler('zig.yaml')
            context.register_compiler('zig', zig_config)
            ```
        """
        self._registry.register_compiler(name, config)

    def register_compiler_strategy(
        self,
        name: str,
        strategy: Any,
    ) -> None:
        """
        Register a compiler strategy.

        Args:
            name: Compiler name (e.g., 'zig', 'gcc', 'clang')
            strategy: CompilerStrategy instance

        Raises:
            ValueError: If strategy with this name is already registered

        Example:
            ```python
            context.register_compiler_strategy('zig', ZigStrategy())
            ```
        """
        self._registry.register_compiler_strategy(name, strategy)

    def register_package_manager(
        self,
        name: str,
        manager: Any,
    ) -> None:
        """
        Register a package manager.

        Args:
            name: Package manager name (e.g., 'hunter', 'conan', 'vcpkg')
            manager: PackageManager instance

        Raises:
            ValueError: If package manager with this name is already registered

        Example:
            ```python
            context.register_package_manager('hunter', self)
            ```
        """
        self._registry.register_package_manager(name, manager)

    def register_backend(
        self,
        name: str,
        backend: Any,
    ) -> None:
        """
        Register a build backend.

        Args:
            name: Backend name (e.g., 'meson', 'bazel', 'cmake')
            backend: BuildBackend instance

        Raises:
            ValueError: If backend with this name is already registered

        Example:
            ```python
            context.register_backend('meson', self)
            ```
        """
        self._registry.register_backend(name, backend)

    def register_toolchain_provider(
        self,
        provider: Any,
    ) -> None:
        """
        Register a toolchain provider.

        Args:
            provider: ToolchainProvider instance that can provide toolchains

        Example:
            ```python
            context.register_toolchain_provider(ZigToolchainProvider())
            ```
        """
        self._registry.register_toolchain_provider(provider)

    # Helper Methods

    def load_yaml_compiler(
        self,
        compiler_name: str,
        platform: Optional[str] = None,
    ) -> Any:
        """
        Load compiler configuration from YAML file.

        Args:
            compiler_name: Name of the compiler (e.g., 'zig', 'gcc', 'clang')
            platform: Optional platform override (e.g., 'linux', 'windows', 'macos')

        Returns:
            YAMLCompilerConfig instance loaded from the compiler directory

        Raises:
            FileNotFoundError: If compiler YAML file doesn't exist
            ValueError: If YAML file is invalid

        Note:
            This method uses the plugin's directory (parent of cache_dir) as the
            data directory. The YAML file should be in <plugin_dir>/compilers/<name>.yaml

        Example:
            ```python
            # Load zig compiler configuration
            # Looks for: <plugin_dir>/compilers/zig.yaml
            config = context.load_yaml_compiler('zig')

            # With platform override
            config = context.load_yaml_compiler('zig', platform='linux')
            ```
        """
        from toolchainkit.cmake.yaml_compiler import YAMLCompilerLoader

        # Use plugin directory as data_dir (parent of cache_dir)
        plugin_dir = self._cache_dir.parent
        loader = YAMLCompilerLoader(plugin_dir)
        return loader.load(compiler_name, platform=platform)

    def get_platform(self) -> Any:
        """
        Get current platform information.

        Returns:
            PlatformInfo with OS, architecture, and ABI information

        Example:
            ```python
            platform = context.get_platform()
            if platform.os == "linux":
                # Linux-specific logic
                pass
            elif platform.os == "windows":
                # Windows-specific logic
                pass
            ```
        """
        from toolchainkit.core.platform import detect_platform

        return detect_platform()

    def log(self, level: str, message: str) -> None:
        """
        Log a message (for plugin debugging).

        Args:
            level: Log level ('debug', 'info', 'warning', 'error')
            message: Log message

        Example:
            context.log('info', 'Zig compiler detected at /usr/bin/zig')
            context.log('warning', 'No system compiler found, using default')
            context.log('error', 'Failed to download compiler')
        """
        level = level.lower()
        formatted = f"[{level.upper()}] {message}"
        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(formatted)
