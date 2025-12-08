"""
Tests for plugin registry.
"""

import pytest
from toolchainkit.plugins import (
    PluginRegistry,
    get_global_registry,
    reset_global_registry,
)


# ============================================================================
# Mock Objects for Testing
# ============================================================================


class MockCompilerConfig:
    """Mock compiler configuration."""

    def __init__(self, name: str):
        self.name = name


class MockPackageManager:
    """Mock package manager."""

    def __init__(self, name: str):
        self.name = name


class MockBackend:
    """Mock build backend."""

    def __init__(self, name: str):
        self.name = name


# ============================================================================
# Test: PluginRegistry Initialization
# ============================================================================


class TestPluginRegistryInit:
    """Test PluginRegistry initialization."""

    def test_registry_can_be_instantiated(self):
        """Test creating registry instance."""
        registry = PluginRegistry()
        assert isinstance(registry, PluginRegistry)

    def test_registry_starts_empty(self):
        """Test that new registry has no registered items."""
        registry = PluginRegistry()
        assert registry.list_compilers() == []
        assert registry.list_package_managers() == []
        assert registry.list_backends() == []


# ============================================================================
# Test: Register Compilers
# ============================================================================


class TestRegisterCompilers:
    """Test registering compilers."""

    def test_register_single_compiler(self):
        """Test registering a single compiler."""
        registry = PluginRegistry()
        config = MockCompilerConfig("zig")

        registry.register_compiler("zig", config)

        assert registry.has_compiler("zig")
        assert registry.get_compiler("zig") is config

    def test_register_multiple_compilers(self):
        """Test registering multiple compilers."""
        registry = PluginRegistry()
        zig_config = MockCompilerConfig("zig")
        d_config = MockCompilerConfig("d")

        registry.register_compiler("zig", zig_config)
        registry.register_compiler("d", d_config)

        assert registry.has_compiler("zig")
        assert registry.has_compiler("d")
        assert registry.get_compiler("zig") is zig_config
        assert registry.get_compiler("d") is d_config

    def test_register_duplicate_compiler_raises_error(self):
        """Test that registering duplicate compiler raises ValueError."""
        registry = PluginRegistry()
        config1 = MockCompilerConfig("zig")
        config2 = MockCompilerConfig("zig")

        registry.register_compiler("zig", config1)

        with pytest.raises(ValueError) as exc_info:
            registry.register_compiler("zig", config2)

        assert "already registered" in str(exc_info.value)
        assert "zig" in str(exc_info.value)

    def test_list_compilers(self):
        """Test listing registered compilers."""
        registry = PluginRegistry()
        registry.register_compiler("zig", MockCompilerConfig("zig"))
        registry.register_compiler("d", MockCompilerConfig("d"))

        compilers = registry.list_compilers()

        assert len(compilers) == 2
        assert "zig" in compilers
        assert "d" in compilers


# ============================================================================
# Test: Register Package Managers
# ============================================================================


class TestRegisterPackageManagers:
    """Test registering package managers."""

    def test_register_single_package_manager(self):
        """Test registering a single package manager."""
        registry = PluginRegistry()
        manager = MockPackageManager("hunter")

        registry.register_package_manager("hunter", manager)

        assert registry.has_package_manager("hunter")
        assert registry.get_package_manager("hunter") is manager

    def test_register_multiple_package_managers(self):
        """Test registering multiple package managers."""
        registry = PluginRegistry()
        hunter = MockPackageManager("hunter")
        vcpkg = MockPackageManager("vcpkg")

        registry.register_package_manager("hunter", hunter)
        registry.register_package_manager("vcpkg", vcpkg)

        assert registry.has_package_manager("hunter")
        assert registry.has_package_manager("vcpkg")
        assert registry.get_package_manager("hunter") is hunter
        assert registry.get_package_manager("vcpkg") is vcpkg

    def test_register_duplicate_package_manager_raises_error(self):
        """Test that registering duplicate package manager raises ValueError."""
        registry = PluginRegistry()
        manager1 = MockPackageManager("hunter")
        manager2 = MockPackageManager("hunter")

        registry.register_package_manager("hunter", manager1)

        with pytest.raises(ValueError) as exc_info:
            registry.register_package_manager("hunter", manager2)

        assert "already registered" in str(exc_info.value)
        assert "hunter" in str(exc_info.value)

    def test_list_package_managers(self):
        """Test listing registered package managers."""
        registry = PluginRegistry()
        registry.register_package_manager("hunter", MockPackageManager("hunter"))
        registry.register_package_manager("vcpkg", MockPackageManager("vcpkg"))

        managers = registry.list_package_managers()

        assert len(managers) == 2
        assert "hunter" in managers
        assert "vcpkg" in managers


# ============================================================================
# Test: Register Backends
# ============================================================================


class TestRegisterBackends:
    """Test registering build backends."""

    def test_register_single_backend(self):
        """Test registering a single backend."""
        registry = PluginRegistry()
        backend = MockBackend("meson")

        registry.register_backend("meson", backend)

        assert registry.has_backend("meson")
        assert registry.get_backend("meson") is backend

    def test_register_multiple_backends(self):
        """Test registering multiple backends."""
        registry = PluginRegistry()
        meson = MockBackend("meson")
        premake = MockBackend("premake")

        registry.register_backend("meson", meson)
        registry.register_backend("premake", premake)

        assert registry.has_backend("meson")
        assert registry.has_backend("premake")
        assert registry.get_backend("meson") is meson
        assert registry.get_backend("premake") is premake

    def test_register_duplicate_backend_raises_error(self):
        """Test that registering duplicate backend raises ValueError."""
        registry = PluginRegistry()
        backend1 = MockBackend("meson")
        backend2 = MockBackend("meson")

        registry.register_backend("meson", backend1)

        with pytest.raises(ValueError) as exc_info:
            registry.register_backend("meson", backend2)

        assert "already registered" in str(exc_info.value)
        assert "meson" in str(exc_info.value)

    def test_list_backends(self):
        """Test listing registered backends."""
        registry = PluginRegistry()
        registry.register_backend("meson", MockBackend("meson"))
        registry.register_backend("premake", MockBackend("premake"))

        backends = registry.list_backends()

        assert len(backends) == 2
        assert "meson" in backends
        assert "premake" in backends


# ============================================================================
# Test: Lookup Errors
# ============================================================================


class TestLookupErrors:
    """Test error handling for lookups."""

    def test_get_nonexistent_compiler_raises_error(self):
        """Test that getting non-existent compiler raises KeyError."""
        registry = PluginRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get_compiler("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_get_nonexistent_package_manager_raises_error(self):
        """Test that getting non-existent package manager raises KeyError."""
        registry = PluginRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get_package_manager("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_get_nonexistent_backend_raises_error(self):
        """Test that getting non-existent backend raises KeyError."""
        registry = PluginRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get_backend("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Test: Has Methods
# ============================================================================


class TestHasMethods:
    """Test has_* query methods."""

    def test_has_compiler_returns_false_for_missing(self):
        """Test has_compiler returns False for missing compiler."""
        registry = PluginRegistry()
        assert not registry.has_compiler("zig")

    def test_has_compiler_returns_true_for_existing(self):
        """Test has_compiler returns True for existing compiler."""
        registry = PluginRegistry()
        registry.register_compiler("zig", MockCompilerConfig("zig"))
        assert registry.has_compiler("zig")

    def test_has_package_manager_returns_false_for_missing(self):
        """Test has_package_manager returns False for missing manager."""
        registry = PluginRegistry()
        assert not registry.has_package_manager("hunter")

    def test_has_package_manager_returns_true_for_existing(self):
        """Test has_package_manager returns True for existing manager."""
        registry = PluginRegistry()
        registry.register_package_manager("hunter", MockPackageManager("hunter"))
        assert registry.has_package_manager("hunter")

    def test_has_backend_returns_false_for_missing(self):
        """Test has_backend returns False for missing backend."""
        registry = PluginRegistry()
        assert not registry.has_backend("meson")

    def test_has_backend_returns_true_for_existing(self):
        """Test has_backend returns True for existing backend."""
        registry = PluginRegistry()
        registry.register_backend("meson", MockBackend("meson"))
        assert registry.has_backend("meson")


# ============================================================================
# Test: Clear Registry
# ============================================================================


class TestClearRegistry:
    """Test clearing registry."""

    def test_clear_removes_all_items(self):
        """Test that clear removes all registered items."""
        registry = PluginRegistry()
        registry.register_compiler("zig", MockCompilerConfig("zig"))
        registry.register_package_manager("hunter", MockPackageManager("hunter"))
        registry.register_backend("meson", MockBackend("meson"))

        assert len(registry.list_compilers()) == 1
        assert len(registry.list_package_managers()) == 1
        assert len(registry.list_backends()) == 1

        registry.clear()

        assert len(registry.list_compilers()) == 0
        assert len(registry.list_package_managers()) == 0
        assert len(registry.list_backends()) == 0

    def test_clear_allows_reregistration(self):
        """Test that items can be registered again after clear."""
        registry = PluginRegistry()
        config1 = MockCompilerConfig("zig")
        config2 = MockCompilerConfig("zig")

        registry.register_compiler("zig", config1)
        registry.clear()
        registry.register_compiler("zig", config2)

        assert registry.get_compiler("zig") is config2


# ============================================================================
# Test: Global Registry
# ============================================================================


class TestGlobalRegistry:
    """Test global registry singleton."""

    def test_get_global_registry_returns_instance(self):
        """Test that get_global_registry returns a registry."""
        reset_global_registry()  # Ensure clean state
        registry = get_global_registry()
        assert isinstance(registry, PluginRegistry)

    def test_get_global_registry_returns_same_instance(self):
        """Test that get_global_registry returns same instance."""
        reset_global_registry()  # Ensure clean state
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        assert registry1 is registry2

    def test_reset_global_registry_creates_new_instance(self):
        """Test that reset creates new registry."""
        reset_global_registry()
        registry1 = get_global_registry()
        registry1.register_compiler("zig", MockCompilerConfig("zig"))

        reset_global_registry()
        registry2 = get_global_registry()

        assert registry1 is not registry2
        assert len(registry2.list_compilers()) == 0

    def test_global_registry_persists_data(self):
        """Test that global registry persists data between calls."""
        reset_global_registry()
        registry1 = get_global_registry()
        config = MockCompilerConfig("zig")
        registry1.register_compiler("zig", config)

        registry2 = get_global_registry()
        assert registry2.has_compiler("zig")
        assert registry2.get_compiler("zig") is config


# ============================================================================
# Test: Module Exports
# ============================================================================


class TestRegistryModuleExports:
    """Test module exports correct API."""

    def test_plugin_registry_exported(self):
        """Test PluginRegistry is exported."""
        from toolchainkit.plugins.registry import PluginRegistry as DirectImport
        from toolchainkit.plugins import PluginRegistry as PackageImport

        assert DirectImport is PackageImport

    def test_get_global_registry_exported(self):
        """Test get_global_registry is exported."""
        from toolchainkit.plugins.registry import get_global_registry as DirectImport
        from toolchainkit.plugins import get_global_registry as PackageImport

        assert DirectImport is PackageImport

    def test_reset_global_registry_exported(self):
        """Test reset_global_registry is exported."""
        from toolchainkit.plugins.registry import (
            reset_global_registry as DirectImport,
        )
        from toolchainkit.plugins import reset_global_registry as PackageImport

        assert DirectImport is PackageImport


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
