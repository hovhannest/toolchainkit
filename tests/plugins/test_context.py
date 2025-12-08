"""
Tests for the plugin context module.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from toolchainkit.plugins.context import PluginContext


# Mock Objects


class MockRegistry:
    """Mock registry for testing."""

    def __init__(self):
        self.compilers = {}
        self.package_managers = {}
        self.backends = {}

    def register_compiler(self, name, config):
        if name in self.compilers:
            raise ValueError(f"Compiler '{name}' already registered")
        self.compilers[name] = config

    def register_package_manager(self, name, manager):
        if name in self.package_managers:
            raise ValueError(f"Package manager '{name}' already registered")
        self.package_managers[name] = manager

    def register_backend(self, name, backend):
        if name in self.backends:
            raise ValueError(f"Backend '{name}' already registered")
        self.backends[name] = backend


@pytest.fixture
def mock_registry():
    """Create mock registry."""
    return MockRegistry()


@pytest.fixture
def cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def config():
    """Create test configuration."""
    return {"verbose": True, "debug": False, "timeout": 30}


@pytest.fixture
def context(mock_registry, cache_dir, config):
    """Create plugin context for testing."""
    return PluginContext(mock_registry, cache_dir, config)


# Test Context Creation


class TestPluginContextCreation:
    """Test plugin context creation."""

    def test_context_can_be_created(self, mock_registry, cache_dir, config):
        """Test that context can be instantiated."""
        context = PluginContext(mock_registry, cache_dir, config)
        assert context is not None

    def test_context_stores_registry(self, context, mock_registry):
        """Test that context stores registry reference."""
        assert context._registry is mock_registry

    def test_context_stores_cache_dir(self, context, cache_dir):
        """Test that context stores cache directory."""
        assert context._cache_dir == cache_dir

    def test_context_stores_config(self, context, config):
        """Test that context stores configuration."""
        assert context._config is config


# Test Properties


class TestPluginContextProperties:
    """Test plugin context properties."""

    def test_cache_dir_property(self, context, cache_dir):
        """Test cache_dir property returns cache directory."""
        assert context.cache_dir == cache_dir

    def test_cache_dir_is_path(self, context):
        """Test cache_dir returns Path object."""
        assert isinstance(context.cache_dir, Path)

    def test_config_property(self, context, config):
        """Test config property returns configuration."""
        assert context.config is config

    def test_config_is_dict(self, context):
        """Test config returns dictionary."""
        assert isinstance(context.config, dict)

    def test_config_access(self, context):
        """Test accessing config values."""
        assert context.config["verbose"] is True
        assert context.config["debug"] is False
        assert context.config["timeout"] == 30


# Test Registration Methods


class TestRegisterCompiler:
    """Test compiler registration through context."""

    def test_register_compiler_calls_registry(self, context, mock_registry):
        """Test register_compiler delegates to registry."""
        config = Mock()
        context.register_compiler("gcc", config)
        assert "gcc" in mock_registry.compilers
        assert mock_registry.compilers["gcc"] is config

    def test_register_multiple_compilers(self, context, mock_registry):
        """Test registering multiple compilers."""
        gcc = Mock()
        clang = Mock()
        context.register_compiler("gcc", gcc)
        context.register_compiler("clang", clang)
        assert len(mock_registry.compilers) == 2
        assert mock_registry.compilers["gcc"] is gcc
        assert mock_registry.compilers["clang"] is clang

    def test_register_duplicate_compiler_raises_error(self, context):
        """Test registering duplicate compiler raises ValueError."""
        config = Mock()
        context.register_compiler("gcc", config)
        with pytest.raises(ValueError, match="already registered"):
            context.register_compiler("gcc", Mock())


class TestRegisterPackageManager:
    """Test package manager registration through context."""

    def test_register_package_manager_calls_registry(self, context, mock_registry):
        """Test register_package_manager delegates to registry."""
        manager = Mock()
        context.register_package_manager("conan", manager)
        assert "conan" in mock_registry.package_managers
        assert mock_registry.package_managers["conan"] is manager

    def test_register_multiple_package_managers(self, context, mock_registry):
        """Test registering multiple package managers."""
        conan = Mock()
        vcpkg = Mock()
        context.register_package_manager("conan", conan)
        context.register_package_manager("vcpkg", vcpkg)
        assert len(mock_registry.package_managers) == 2

    def test_register_duplicate_package_manager_raises_error(self, context):
        """Test registering duplicate package manager raises ValueError."""
        manager = Mock()
        context.register_package_manager("conan", manager)
        with pytest.raises(ValueError, match="already registered"):
            context.register_package_manager("conan", Mock())


class TestRegisterBackend:
    """Test build backend registration through context."""

    def test_register_backend_calls_registry(self, context, mock_registry):
        """Test register_backend delegates to registry."""
        backend = Mock()
        context.register_backend("meson", backend)
        assert "meson" in mock_registry.backends
        assert mock_registry.backends["meson"] is backend

    def test_register_multiple_backends(self, context, mock_registry):
        """Test registering multiple backends."""
        meson = Mock()
        bazel = Mock()
        context.register_backend("meson", meson)
        context.register_backend("bazel", bazel)
        assert len(mock_registry.backends) == 2

    def test_register_duplicate_backend_raises_error(self, context):
        """Test registering duplicate backend raises ValueError."""
        backend = Mock()
        context.register_backend("meson", backend)
        with pytest.raises(ValueError, match="already registered"):
            context.register_backend("meson", Mock())


# Test Helper Methods


class TestLoadYamlCompiler:
    """Test load_yaml_compiler helper method."""

    @patch("toolchainkit.cmake.yaml_compiler.YAMLCompilerLoader")
    def test_load_yaml_compiler_basic(self, mock_loader_class, context):
        """Test loading compiler by name."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_config = Mock()
        mock_loader.load.return_value = mock_config

        result = context.load_yaml_compiler("zig")

        # Verify loader created with plugin directory as data_dir
        mock_loader_class.assert_called_once_with(context.cache_dir.parent)
        # Verify load called with compiler name
        mock_loader.load.assert_called_once_with("zig", platform=None)
        assert result is mock_config

    @patch("toolchainkit.cmake.yaml_compiler.YAMLCompilerLoader")
    def test_load_yaml_compiler_different_compiler(self, mock_loader_class, context):
        """Test loading different compiler by name."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_config = Mock()
        mock_loader.load.return_value = mock_config

        result = context.load_yaml_compiler("gcc")

        mock_loader_class.assert_called_once_with(context.cache_dir.parent)
        mock_loader.load.assert_called_once_with("gcc", platform=None)
        assert result is mock_config

    @patch("toolchainkit.cmake.yaml_compiler.YAMLCompilerLoader")
    def test_load_yaml_compiler_with_platform(self, mock_loader_class, context):
        """Test loading compiler with platform override."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_config = Mock()
        mock_loader.load.return_value = mock_config

        result = context.load_yaml_compiler("zig", platform="linux")

        mock_loader_class.assert_called_once_with(context.cache_dir.parent)
        mock_loader.load.assert_called_once_with("zig", platform="linux")
        assert result is mock_config

    @patch("toolchainkit.cmake.yaml_compiler.YAMLCompilerLoader")
    def test_load_yaml_compiler_uses_plugin_directory(self, mock_loader_class, context):
        """Test that loader uses plugin directory (parent of cache_dir)."""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_config = Mock()
        mock_loader.load.return_value = mock_config

        context.load_yaml_compiler("test")

        # Verify the data_dir passed to loader is plugin_dir (cache_dir.parent)
        expected_data_dir = context.cache_dir.parent
        mock_loader_class.assert_called_once_with(expected_data_dir)


class TestGetPlatform:
    """Test get_platform helper method."""

    @patch("toolchainkit.core.platform.detect_platform")
    def test_get_platform_calls_detect_platform(self, mock_detect, context):
        """Test get_platform calls detect_platform function."""
        mock_platform = Mock()
        mock_detect.return_value = mock_platform

        result = context.get_platform()

        mock_detect.assert_called_once_with()
        assert result is mock_platform

    @patch("toolchainkit.core.platform.detect_platform")
    def test_get_platform_returns_platform_info(self, mock_detect, context):
        """Test get_platform returns PlatformInfo object."""
        mock_platform = Mock()
        mock_platform.os = "linux"
        mock_platform.arch = "x86_64"
        mock_detect.return_value = mock_platform

        result = context.get_platform()

        assert result.os == "linux"
        assert result.arch == "x86_64"


class TestLog:
    """Test log helper method."""

    def test_log_prints_message(self, context, caplog):
        """Test log method logs message at appropriate level."""
        import logging

        with caplog.at_level(logging.INFO):
            context.log("info", "Test message")
        assert "Test message" in caplog.text
        assert any(record.levelname == "INFO" for record in caplog.records)

    def test_log_debug_level(self, context, caplog):
        """Test log with debug level."""
        import logging

        with caplog.at_level(logging.DEBUG):
            context.log("debug", "Debug message")
        assert "Debug message" in caplog.text
        assert any(record.levelname == "DEBUG" for record in caplog.records)

    def test_log_warning_level(self, context, caplog):
        """Test log with warning level."""
        import logging

        with caplog.at_level(logging.WARNING):
            context.log("warning", "Warning message")
        assert "Warning message" in caplog.text
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_log_error_level(self, context, caplog):
        """Test log with error level."""
        import logging

        with caplog.at_level(logging.ERROR):
            context.log("error", "Error message")
        assert "Error message" in caplog.text
        assert any(record.levelname == "ERROR" for record in caplog.records)

    def test_log_multiple_messages(self, context, caplog):
        """Test logging multiple messages."""
        import logging

        with caplog.at_level(logging.INFO):
            context.log("info", "First message")
            context.log("error", "Second message")
        assert "First message" in caplog.text
        assert "Second message" in caplog.text
        assert any(
            record.levelname == "INFO" and "First message" in record.message
            for record in caplog.records
        )
        assert any(
            record.levelname == "ERROR" and "Second message" in record.message
            for record in caplog.records
        )


# Test Module Exports


class TestContextModuleExports:
    """Test that PluginContext is properly exported."""

    def test_plugin_context_exported(self):
        """Test PluginContext is exported from plugins module."""
        from toolchainkit.plugins import PluginContext as ExportedContext

        assert ExportedContext is PluginContext

    def test_plugin_context_in_all(self):
        """Test PluginContext is in __all__ list."""
        from toolchainkit import plugins

        assert "PluginContext" in plugins.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
