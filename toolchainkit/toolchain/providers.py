"""
Toolchain provider implementations.

This module implements the ToolchainProvider interface for different
sources of toolchains (downloads, plugins, system installations).
"""

from pathlib import Path
from typing import Optional
import logging

from toolchainkit.core.interfaces import ToolchainProvider

logger = logging.getLogger(__name__)


class DownloadToolchainProvider(ToolchainProvider):
    """
    Provides toolchains through the download mechanism.

    This is the standard provider that downloads and caches toolchains
    from official sources.
    """

    def __init__(self, downloader, cache_dir: Optional[Path] = None):
        """
        Initialize download provider.

        Args:
            downloader: ToolchainDownloader instance
            cache_dir: Optional cache directory override
        """
        self._downloader = downloader
        self._cache_dir = cache_dir
        self._last_result = None

    def can_provide(self, toolchain_type: str, version: str) -> bool:
        """Check if toolchain is available for download."""
        try:
            # Check if toolchain is in registry
            metadata = self._downloader.metadata_registry.get_toolchain(toolchain_type)
            return metadata is not None
        except Exception:
            return False

    def provide_toolchain(
        self,
        toolchain_type: str,
        version: str,
        platform: str,
        progress_callback=None,
        **kwargs,
    ) -> Optional[Path]:
        """Download and provide toolchain."""
        try:
            result = self._downloader.download_toolchain(
                toolchain_name=toolchain_type,
                version=version,
                platform=platform,
                force=False,
                progress_callback=progress_callback,
            )
            self._last_result = result
            return result.toolchain_path
        except Exception as e:
            logger.error(f"Failed to download toolchain: {e}")
            return None

    def get_toolchain_id(self, toolchain_type: str, version: str, platform: str) -> str:
        """Get toolchain identifier."""
        if self._last_result:
            return self._last_result.toolchain_id
        return f"{toolchain_type}-{version}-{platform}"


class PluginToolchainProvider(ToolchainProvider):
    """
    Provides toolchains through loaded plugins.

    This provider checks all loaded compiler plugins to see if any
    can provide the requested toolchain.
    """

    def __init__(self, plugin_manager):
        """
        Initialize plugin provider.

        Args:
            plugin_manager: PluginManager instance with loaded plugins
        """
        self._plugin_manager = plugin_manager
        self._last_provider_name = None

    def can_provide(self, toolchain_type: str, version: str) -> bool:
        """Check if any plugin can provide this toolchain."""
        for plugin_name, plugin_instance in self._plugin_manager._loaded_plugins:
            if hasattr(plugin_instance, "get_toolchain_path"):
                try:
                    # Just check if the plugin can handle this type
                    if hasattr(plugin_instance, "compiler_name"):
                        if plugin_instance.compiler_name() == toolchain_type:
                            return True
                except Exception:
                    continue
        return False

    def provide_toolchain(
        self,
        toolchain_type: str,
        version: str,
        platform: str,
        root: Optional[Path] = None,
        **kwargs,
    ) -> Optional[Path]:
        """Get toolchain from plugin."""
        for plugin_name, plugin_instance in self._plugin_manager._loaded_plugins:
            if hasattr(plugin_instance, "get_toolchain_path"):
                try:
                    if hasattr(plugin_instance, "compiler_name"):
                        if plugin_instance.compiler_name() == toolchain_type:
                            path = plugin_instance.get_toolchain_path(
                                version, root=root
                            )
                            if path:
                                self._last_provider_name = plugin_name
                                logger.info(
                                    f"Plugin '{plugin_name}' provided toolchain at: {path}"
                                )
                                return path
                except Exception as e:
                    logger.debug(
                        f"Plugin '{plugin_name}' cannot provide toolchain: {e}"
                    )
                    continue
        return None

    def get_toolchain_id(self, toolchain_type: str, version: str, platform: str) -> str:
        """Get toolchain identifier."""
        return f"{toolchain_type}-{version}"


class ChainedToolchainProvider(ToolchainProvider):
    """
    Chains multiple toolchain providers together.

    This provider tries each provider in order until one succeeds.
    """

    def __init__(self, providers: list[ToolchainProvider]):
        """
        Initialize chained provider.

        Args:
            providers: List of providers to try in order
        """
        self._providers = providers
        self._last_provider: Optional[ToolchainProvider] = None

    def can_provide(self, toolchain_type: str, version: str) -> bool:
        """Check if any provider can provide this toolchain."""
        for provider in self._providers:
            if provider.can_provide(toolchain_type, version):
                return True
        return False

    def provide_toolchain(
        self, toolchain_type: str, version: str, platform: str, **kwargs
    ) -> Optional[Path]:
        """Try each provider in order."""
        for provider in self._providers:
            if provider.can_provide(toolchain_type, version):
                path = provider.provide_toolchain(
                    toolchain_type, version, platform, **kwargs
                )
                if path:
                    self._last_provider = provider
                    return path
        return None

    def get_toolchain_id(self, toolchain_type: str, version: str, platform: str) -> str:
        """Get toolchain identifier from last successful provider."""
        if self._last_provider:
            return self._last_provider.get_toolchain_id(
                toolchain_type, version, platform
            )
        return f"{toolchain_type}-{version}-{platform}"


__all__ = [
    "DownloadToolchainProvider",
    "PluginToolchainProvider",
    "ChainedToolchainProvider",
]
