import pytest
from toolchainkit.plugins.registry import get_global_registry
from toolchainkit.packages.base import PackageManager
from toolchainkit.packages.conan import ConanIntegration


def test_conan_registration(tmp_path):
    """Test that Conan package manager is automatically registered."""
    registry = get_global_registry()

    # Check if conan is registered
    manager_cls = registry.get_package_manager("conan")
    assert manager_cls is ConanIntegration

    # Check if it can be instantiated
    manager = manager_cls(project_root=tmp_path)
    assert isinstance(manager, PackageManager)
    assert isinstance(manager, ConanIntegration)


def test_get_unknown_package_manager():
    """Test getting an unknown package manager."""
    registry = get_global_registry()
    with pytest.raises(KeyError):
        registry.get_package_manager("unknown_manager")
