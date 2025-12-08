"""
Adapters that bridge the plugin system to core interfaces.

These adapters implement the core interfaces using the plugin registry,
allowing the core to remain decoupled from the plugin implementation.
"""

from typing import Any

from toolchainkit.core.interfaces import (
    StrategyResolver,
    PackageManagerResolver,
)


class PluginStrategyResolver(StrategyResolver):
    """
    Resolves compiler strategies from the plugin registry.

    This adapter allows the core to use strategies without directly
    depending on the plugin registry implementation.
    """

    def __init__(self, registry):
        """
        Initialize resolver with a plugin registry.

        Args:
            registry: PluginRegistry instance
        """
        self._registry = registry

    def resolve_strategy(self, compiler_type: str) -> Any:
        """Resolve strategy from plugin registry."""
        return self._registry.get_compiler_strategy(compiler_type)

    def has_strategy(self, compiler_type: str) -> bool:
        """Check if strategy exists in plugin registry."""
        return self._registry.has_compiler_strategy(compiler_type)


class PluginPackageManagerResolver(PackageManagerResolver):
    """
    Resolves package managers from the plugin registry.

    This adapter allows the core to work with package managers without
    directly depending on the plugin registry implementation.
    """

    def __init__(self, registry):
        """
        Initialize resolver with a plugin registry.

        Args:
            registry: PluginRegistry instance
        """
        self._registry = registry

    def resolve_manager(self, manager_name: str) -> Any:
        """Resolve package manager from plugin registry."""
        return self._registry.get_package_manager(manager_name)

    def has_manager(self, manager_name: str) -> bool:
        """Check if package manager exists in plugin registry."""
        return self._registry.has_package_manager(manager_name)


__all__ = [
    "PluginStrategyResolver",
    "PluginPackageManagerResolver",
]
