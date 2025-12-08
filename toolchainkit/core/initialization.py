"""
Core initialization module.

This module provides functions to initialize core framework components,
including registering standard compiler strategies and package managers.
"""

import logging

logger = logging.getLogger(__name__)


def initialize_core_strategies(registry) -> None:
    """
    Register standard compiler strategies with the registry.

    This function registers the built-in compiler strategies (Clang, GCC, MSVC)
    that are part of the core framework. It should be called during application
    initialization.

    Args:
        registry: PluginRegistry instance to register strategies with
    """
    from toolchainkit.toolchain.strategies.standard import (
        ClangStrategy,
        GccStrategy,
        MsvcStrategy,
    )

    # Register standard strategies if not already registered
    if not registry.has_compiler_strategy("clang"):
        registry.register_compiler_strategy("clang", ClangStrategy())
        logger.debug("Registered standard Clang strategy")

    if not registry.has_compiler_strategy("gcc"):
        registry.register_compiler_strategy("gcc", GccStrategy())
        logger.debug("Registered standard GCC strategy")

    if not registry.has_compiler_strategy("msvc"):
        registry.register_compiler_strategy("msvc", MsvcStrategy())
        logger.debug("Registered standard MSVC strategy")


def initialize_core_package_managers(registry) -> None:
    """
    Register standard package managers with the registry.

    This function registers the built-in package manager integrations (Conan, vcpkg)
    that are part of the core framework.

    Args:
        registry: PluginRegistry instance to register package managers with
    """
    # Import conditionally to avoid errors if dependencies missing
    try:
        from toolchainkit.packages.conan import ConanIntegration

        if not registry.has_package_manager("conan"):
            registry.register_package_manager("conan", ConanIntegration)
            logger.debug("Registered Conan package manager")
    except ImportError:
        logger.debug("Conan integration not available")

    try:
        from toolchainkit.packages.vcpkg import VcpkgIntegration

        if not registry.has_package_manager("vcpkg"):
            registry.register_package_manager("vcpkg", VcpkgIntegration)
            logger.debug("Registered vcpkg package manager")
    except ImportError:
        logger.debug("vcpkg integration not available")


def initialize_core(registry=None) -> None:
    """
    Initialize the core framework.

    This function performs all necessary initialization steps for the core
    framework, including registering standard strategies and package managers.
    It should be called once at application startup.

    Args:
        registry: Optional PluginRegistry instance. If None, uses global registry.
    """
    if registry is None:
        from toolchainkit.plugins.registry import get_global_registry

        registry = get_global_registry()

    initialize_core_strategies(registry)
    initialize_core_package_managers(registry)
    logger.info("Core framework initialized")


__all__ = [
    "initialize_core",
    "initialize_core_strategies",
    "initialize_core_package_managers",
]
