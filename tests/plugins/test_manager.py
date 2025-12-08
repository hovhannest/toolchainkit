"""
Tests for the plugin manager module.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from toolchainkit.plugins.manager import PluginManager
from toolchainkit.plugins.metadata import PluginMetadata


# Mock Objects


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self):
        self.initialized = False
        self.cleaned_up = False

    def metadata(self):
        return {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test",
        }

    def initialize(self, context):
        self.initialized = True

    def cleanup(self):
        self.cleaned_up = True


@pytest.fixture
def mock_registry():
    """Create mock registry."""
    return Mock()


@pytest.fixture
def mock_discoverer():
    """Create mock discoverer."""
    return Mock()


@pytest.fixture
def mock_loader():
    """Create mock loader."""
    return Mock()


@pytest.fixture
def plugin_manager(mock_registry):
    """Create plugin manager with mock registry."""
    return PluginManager(registry=mock_registry)


@pytest.fixture
def sample_metadata():
    """Create sample plugin metadata."""
    return PluginMetadata(
        name="test-plugin",
        version="1.0.0",
        type="compiler",
        description="Test plugin",
        author="Test Author",
        entry_point="test_plugin.TestPlugin",
        plugin_dir=Path("/fake/plugin/dir"),
    )


# Test Plugin Manager Creation


class TestPluginManagerCreation:
    """Test plugin manager creation."""

    def test_manager_can_be_created(self):
        """Test that manager can be instantiated."""
        manager = PluginManager()
        assert manager is not None

    def test_manager_uses_provided_registry(self, mock_registry):
        """Test that manager uses provided registry."""
        manager = PluginManager(registry=mock_registry)
        assert manager.registry is mock_registry

    def test_manager_uses_global_registry_by_default(self):
        """Test that manager uses global registry if none provided."""
        manager = PluginManager()
        assert manager.registry is not None

    def test_manager_creates_discoverer(self):
        """Test that manager creates discoverer."""
        manager = PluginManager()
        assert manager.discoverer is not None

    def test_manager_creates_loader(self):
        """Test that manager creates loader."""
        manager = PluginManager()
        assert manager.loader is not None

    def test_manager_starts_with_no_loaded_plugins(self):
        """Test that manager starts with empty loaded plugins list."""
        manager = PluginManager()
        assert len(manager.get_loaded_plugins()) == 0


# Test Discover and Load All


class TestDiscoverAndLoadAll:
    """Test discover_and_load_all method."""

    def test_discover_and_load_all_discovers_plugins(
        self, plugin_manager, sample_metadata
    ):
        """Test that method discovers plugins."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        plugin_manager.discover_and_load_all()

        plugin_manager.discoverer.discover.assert_called_once()

    def test_discover_and_load_all_loads_each_plugin(
        self, plugin_manager, sample_metadata
    ):
        """Test that method loads each discovered plugin."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        mock_plugin = MockPlugin()
        plugin_manager.loader.load = Mock(return_value=mock_plugin)

        plugin_manager.discover_and_load_all()

        plugin_manager.loader.load.assert_called_once_with(sample_metadata)

    def test_discover_and_load_all_initializes_plugins(
        self, plugin_manager, sample_metadata
    ):
        """Test that method initializes each plugin."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        mock_plugin = MockPlugin()
        plugin_manager.loader.load = Mock(return_value=mock_plugin)

        plugin_manager.discover_and_load_all()

        assert mock_plugin.initialized is True

    def test_discover_and_load_all_returns_count(self, plugin_manager, sample_metadata):
        """Test that method returns number of loaded plugins."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        count = plugin_manager.discover_and_load_all()

        assert count == 1

    def test_discover_and_load_all_handles_multiple_plugins(self, plugin_manager):
        """Test loading multiple plugins."""
        metadata1 = PluginMetadata(
            name="plugin1",
            version="1.0.0",
            type="compiler",
            description="Plugin 1",
            author="Test",
            entry_point="plugin1.Plugin1",
            plugin_dir=Path("/fake/plugin1"),
        )
        metadata2 = PluginMetadata(
            name="plugin2",
            version="2.0.0",
            type="package_manager",
            description="Plugin 2",
            author="Test",
            entry_point="plugin2.Plugin2",
            plugin_dir=Path("/fake/plugin2"),
        )

        plugin_manager.discoverer.discover = Mock(return_value=[metadata1, metadata2])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        count = plugin_manager.discover_and_load_all()

        assert count == 2
        assert len(plugin_manager.get_loaded_plugins()) == 2

    def test_discover_and_load_all_creates_cache_dirs(
        self, plugin_manager, sample_metadata, tmp_path
    ):
        """Test that cache directories are created."""
        cache_base = tmp_path / "cache"
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        plugin_manager.discover_and_load_all(cache_base_dir=cache_base)

        expected_cache = cache_base / sample_metadata.name
        assert expected_cache.exists()

    def test_discover_and_load_all_passes_config_to_plugins(
        self, plugin_manager, sample_metadata
    ):
        """Test that configuration is passed to plugins via context."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        mock_plugin = MockPlugin()
        plugin_manager.loader.load = Mock(return_value=mock_plugin)

        config = {"verbose": True, "debug": False}
        plugin_manager.discover_and_load_all(config=config)

        assert mock_plugin.initialized is True

    def test_discover_and_load_all_handles_load_errors(
        self, plugin_manager, sample_metadata
    ):
        """Test that load errors are handled gracefully."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(side_effect=Exception("Load failed"))

        count = plugin_manager.discover_and_load_all()

        assert count == 0  # No plugins loaded
        assert len(plugin_manager.get_loaded_plugins()) == 0

    def test_discover_and_load_all_handles_init_errors(
        self, plugin_manager, sample_metadata
    ):
        """Test that initialization errors are handled gracefully."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])

        class FailingPlugin:
            def initialize(self, context):
                raise Exception("Init failed")

        plugin_manager.loader.load = Mock(return_value=FailingPlugin())

        count = plugin_manager.discover_and_load_all()

        assert count == 0

    def test_discover_and_load_all_continues_after_errors(self, plugin_manager):
        """Test that loading continues after individual plugin errors."""
        metadata1 = PluginMetadata(
            name="failing-plugin",
            version="1.0.0",
            type="compiler",
            description="Failing",
            author="Test",
            entry_point="fail.Fail",
            plugin_dir=Path("/fake/fail"),
        )
        metadata2 = PluginMetadata(
            name="working-plugin",
            version="1.0.0",
            type="compiler",
            description="Working",
            author="Test",
            entry_point="work.Work",
            plugin_dir=Path("/fake/work"),
        )

        plugin_manager.discoverer.discover = Mock(return_value=[metadata1, metadata2])

        def load_side_effect(metadata):
            if metadata.name == "failing-plugin":
                raise Exception("Load failed")
            return MockPlugin()

        plugin_manager.loader.load = Mock(side_effect=load_side_effect)

        count = plugin_manager.discover_and_load_all()

        assert count == 1  # Only working plugin loaded
        assert plugin_manager.get_loaded_plugins() == ["working-plugin"]


# Test Discover and Load One


class TestDiscoverAndLoadOne:
    """Test discover_and_load_one method."""

    def test_discover_and_load_one_finds_plugin(self, plugin_manager, sample_metadata):
        """Test loading a specific plugin by name."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        result = plugin_manager.discover_and_load_one("test-plugin")

        assert result is True
        assert "test-plugin" in plugin_manager.get_loaded_plugins()

    def test_discover_and_load_one_returns_false_if_not_found(self, plugin_manager):
        """Test that method returns False if plugin not found."""
        plugin_manager.discoverer.discover = Mock(return_value=[])

        result = plugin_manager.discover_and_load_one("nonexistent")

        assert result is False

    def test_discover_and_load_one_handles_load_error(
        self, plugin_manager, sample_metadata
    ):
        """Test that load errors return False."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(side_effect=Exception("Load failed"))

        result = plugin_manager.discover_and_load_one("test-plugin")

        assert result is False


# Test Cleanup


class TestCleanupAll:
    """Test cleanup_all method."""

    def test_cleanup_all_calls_cleanup_on_plugins(
        self, plugin_manager, sample_metadata
    ):
        """Test that cleanup is called on all loaded plugins."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        mock_plugin = MockPlugin()
        plugin_manager.loader.load = Mock(return_value=mock_plugin)

        plugin_manager.discover_and_load_all()
        plugin_manager.cleanup_all()

        assert mock_plugin.cleaned_up is True

    def test_cleanup_all_clears_loaded_plugins(self, plugin_manager, sample_metadata):
        """Test that loaded plugins list is cleared."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        plugin_manager.discover_and_load_all()
        assert len(plugin_manager.get_loaded_plugins()) == 1

        plugin_manager.cleanup_all()
        assert len(plugin_manager.get_loaded_plugins()) == 0

    def test_cleanup_all_handles_cleanup_errors(self, plugin_manager, sample_metadata):
        """Test that cleanup errors are handled gracefully."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])

        class FailingCleanupPlugin:
            def initialize(self, context):
                pass

            def cleanup(self):
                raise Exception("Cleanup failed")

        plugin_manager.loader.load = Mock(return_value=FailingCleanupPlugin())

        plugin_manager.discover_and_load_all()
        plugin_manager.cleanup_all()  # Should not raise

        assert len(plugin_manager.get_loaded_plugins()) == 0


# Test Get Loaded Plugins


class TestGetLoadedPlugins:
    """Test get_loaded_plugins method."""

    def test_get_loaded_plugins_returns_empty_list_initially(self, plugin_manager):
        """Test that method returns empty list when no plugins loaded."""
        plugins = plugin_manager.get_loaded_plugins()
        assert plugins == []

    def test_get_loaded_plugins_returns_loaded_plugin_names(
        self, plugin_manager, sample_metadata
    ):
        """Test that method returns list of loaded plugin names."""
        plugin_manager.discoverer.discover = Mock(return_value=[sample_metadata])
        plugin_manager.loader.load = Mock(return_value=MockPlugin())

        plugin_manager.discover_and_load_all()
        plugins = plugin_manager.get_loaded_plugins()

        assert plugins == ["test-plugin"]


# Test Module Exports


class TestManagerModuleExports:
    """Test that PluginManager is properly exported."""

    def test_plugin_manager_exported(self):
        """Test PluginManager is exported from plugins module."""
        from toolchainkit.plugins import PluginManager as ExportedManager

        assert ExportedManager is PluginManager

    def test_plugin_manager_in_all(self):
        """Test PluginManager is in __all__ list."""
        from toolchainkit import plugins

        assert "PluginManager" in plugins.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
