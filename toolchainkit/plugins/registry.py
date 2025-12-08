"""
Plugin registry for managing registered plugins.

This module provides a central registry for storing and accessing
registered compilers, package managers, and build backends from plugins.
"""

from typing import Dict, List, Any, Optional


class PluginRegistry:
    """
    Registry for managing registered plugins and their functionality.

    The registry stores:
    - Compiler configurations registered by plugins
    - Compiler strategies registered by plugins
    - Package manager instances registered by plugins
    - Build backend instances registered by plugins

    Each item is stored by name and can be retrieved later.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._compilers: Dict[str, Any] = {}
        self._compiler_strategies: Dict[str, Any] = {}
        self._package_managers: Dict[str, Any] = {}
        self._backends: Dict[str, Any] = {}
        self._toolchain_providers: List[Any] = []  # List of ToolchainProvider instances

    # ========================================================================
    # Registration Methods
    # ========================================================================

    def register_compiler(self, name: str, config: Any) -> None:
        """
        Register a compiler configuration.

        Args:
            name: Compiler name (e.g., 'zig', 'gcc', 'clang')
            config: Compiler configuration object

        Raises:
            ValueError: If compiler with same name already registered

        Example:
            registry.register_compiler('zig', zig_config)
        """
        if name in self._compilers:
            raise ValueError(f"Compiler '{name}' is already registered")
        self._compilers[name] = config

    def register_compiler_strategy(self, name: str, strategy: Any) -> None:
        """
        Register a compiler strategy.

        Args:
            name: Compiler type name (e.g., 'clang', 'gcc', 'msvc')
            strategy: CompilerStrategy instance

        Raises:
            ValueError: If strategy with same name already registered

        Example:
            registry.register_compiler_strategy('zig', zig_strategy)
        """
        if name in self._compiler_strategies:
            raise ValueError(f"Compiler strategy '{name}' is already registered")
        self._compiler_strategies[name] = strategy

    def register_package_manager(self, name: str, manager: Any) -> None:
        """
        Register a package manager.

        Args:
            name: Package manager name (e.g., 'hunter', 'vcpkg', 'conan')
            manager: Package manager instance

        Raises:
            ValueError: If package manager with same name already registered

        Example:
            registry.register_package_manager('hunter', hunter_manager)
        """
        if name in self._package_managers:
            raise ValueError(f"Package manager '{name}' is already registered")
        self._package_managers[name] = manager

    def register_backend(self, name: str, backend: Any) -> None:
        """
        Register a build backend.

        Args:
            name: Backend name (e.g., 'meson', 'premake', 'xmake')
            backend: Build backend instance

        Raises:
            ValueError: If backend with same name already registered

        Example:
            registry.register_backend('meson', meson_backend)
        """
        if name in self._backends:
            raise ValueError(f"Build backend '{name}' is already registered")
        self._backends[name] = backend

    def register_toolchain_provider(self, provider: Any) -> None:
        """
        Register a toolchain provider.

        Args:
            provider: ToolchainProvider instance that can provide toolchains

        Example:
            registry.register_toolchain_provider(zig_provider)
        """
        self._toolchain_providers.append(provider)

    # ========================================================================
    # Lookup Methods
    # ========================================================================

    def get_compiler(self, name: str) -> Any:
        """
        Get registered compiler by name.

        Args:
            name: Compiler name

        Returns:
            Compiler configuration object

        Raises:
            KeyError: If compiler not found

        Example:
            zig_config = registry.get_compiler('zig')
        """
        if name not in self._compilers:
            raise KeyError(f"Compiler '{name}' not found in registry")
        return self._compilers[name]

    def get_compiler_strategy(self, name: str) -> Any:
        """
        Get registered compiler strategy by name.

        Args:
            name: Compiler type name

        Returns:
            CompilerStrategy instance

        Raises:
            KeyError: If strategy not found

        Example:
            zig_strategy = registry.get_compiler_strategy('zig')
        """
        if name not in self._compiler_strategies:
            raise KeyError(f"Compiler strategy '{name}' not found in registry")
        return self._compiler_strategies[name]

    def get_package_manager(self, name: str) -> Any:
        """
        Get registered package manager by name.

        Args:
            name: Package manager name

        Returns:
            Package manager instance

        Raises:
            KeyError: If package manager not found

        Example:
            hunter = registry.get_package_manager('hunter')
        """
        if name not in self._package_managers:
            raise KeyError(f"Package manager '{name}' not found in registry")
        return self._package_managers[name]

    def get_backend(self, name: str) -> Any:
        """
        Get registered build backend by name.

        Args:
            name: Backend name

        Returns:
            Build backend instance

        Raises:
            KeyError: If backend not found

        Example:
            meson = registry.get_backend('meson')
        """
        if name not in self._backends:
            raise KeyError(f"Build backend '{name}' not found in registry")
        return self._backends[name]

    # ========================================================================
    # Query Methods
    # ========================================================================

    def has_compiler(self, name: str) -> bool:
        """
        Check if compiler is registered.

        Args:
            name: Compiler name

        Returns:
            True if registered, False otherwise

        Example:
            if registry.has_compiler('zig'):
                config = registry.get_compiler('zig')
        """
        return name in self._compilers

    def has_compiler_strategy(self, name: str) -> bool:
        """
        Check if compiler strategy is registered.

        Args:
            name: Compiler type name

        Returns:
            True if registered, False otherwise
        """
        return name in self._compiler_strategies

    def has_package_manager(self, name: str) -> bool:
        """
        Check if package manager is registered.

        Args:
            name: Package manager name

        Returns:
            True if registered, False otherwise
        """
        return name in self._package_managers

    def has_backend(self, name: str) -> bool:
        """
        Check if build backend is registered.

        Args:
            name: Backend name

        Returns:
            True if registered, False otherwise
        """
        return name in self._backends

    def get_toolchain_providers(self) -> List[Any]:
        """
        Get all registered toolchain providers.

        Returns:
            List of ToolchainProvider instances

        Example:
            providers = registry.get_toolchain_providers()
            for provider in providers:
                if provider.can_provide('zig', '0.13.0'):
                    path = provider.provide_toolchain('zig', '0.13.0', 'windows-x64')
        """
        return self._toolchain_providers.copy()

    def list_compilers(self) -> List[str]:
        """
        List all registered compiler names.

        Returns:
            List of compiler names

        Example:
            compilers = registry.list_compilers()
            print(f"Available compilers: {', '.join(compilers)}")
        """
        return list(self._compilers.keys())

    def list_compiler_strategies(self) -> List[str]:
        """
        List all registered compiler strategy names.

        Returns:
            List of compiler strategy names
        """
        return list(self._compiler_strategies.keys())

    def list_package_managers(self) -> List[str]:
        """
        List all registered package manager names.

        Returns:
            List of package manager names
        """
        return list(self._package_managers.keys())

    def list_backends(self) -> List[str]:
        """
        List all registered build backend names.

        Returns:
            List of backend names
        """
        return list(self._backends.keys())

    # ========================================================================
    # Management Methods
    # ========================================================================

    def clear(self) -> None:
        """
        Clear all registered items.

        Removes all compilers, compiler strategies, package managers, and backends.
        Useful for testing or reinitialization.

        Example:
            registry.clear()  # Start fresh
        """
        self._compilers.clear()
        self._compiler_strategies.clear()
        self._package_managers.clear()
        self._backends.clear()


# ============================================================================
# Global Registry Singleton
# ============================================================================

_global_registry: Optional[PluginRegistry] = None


def get_global_registry() -> PluginRegistry:
    """
    Get the global plugin registry singleton.

    Returns:
        Global PluginRegistry instance

    Example:
        registry = get_global_registry()
        registry.register_compiler('zig', zig_config)
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """
    Reset the global registry (for testing).

    Creates a new empty global registry instance.

    Example:
        # In test setup
        reset_global_registry()
    """
    global _global_registry
    _global_registry = None


__all__ = ["PluginRegistry", "get_global_registry", "reset_global_registry"]
