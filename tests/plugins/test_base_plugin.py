"""
Unit tests for base Plugin interface and exception hierarchy.
"""

import pytest
from toolchainkit.plugins import (
    Plugin,
    PluginError,
    PluginNotFoundError,
    PluginLoadError,
    PluginValidationError,
    PluginDependencyError,
    PluginInitializationError,
)
from pathlib import Path


# Test Plugin Implementation
class TestPlugin(Plugin):
    """Concrete plugin implementation for testing."""

    def __init__(self, name="test-plugin", version="1.0.0"):
        self.name = name
        self.version = version
        self.initialized = False
        self.cleaned_up = False

    def metadata(self):
        return {
            "name": self.name,
            "version": self.version,
            "description": "Test plugin",
            "author": "Test Author",
            "homepage": "https://example.com",
            "license": "MIT",
            "requires": ["base-utils >= 1.0"],
            "tags": ["test", "example"],
        }

    def initialize(self, context):
        self.initialized = True
        self.context = context

    def cleanup(self):
        self.cleaned_up = True

    def validate(self):
        return True


class FailingValidationPlugin(Plugin):
    """Plugin that fails validation."""

    def metadata(self):
        return {
            "name": "failing-plugin",
            "version": "1.0.0",
            "description": "Failing test plugin",
            "author": "Test",
        }

    def initialize(self, context):
        pass

    def validate(self):
        return False


class FailingInitPlugin(Plugin):
    """Plugin that fails initialization."""

    def metadata(self):
        return {
            "name": "failing-init-plugin",
            "version": "1.0.0",
            "description": "Failing init plugin",
            "author": "Test",
        }

    def initialize(self, context):
        raise PluginInitializationError("failing-init-plugin", "Initialization failed")


# Exception Tests
class TestPluginExceptions:
    """Test plugin exception hierarchy."""

    def test_plugin_error_base(self):
        """Test base PluginError exception."""
        error = PluginError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_plugin_not_found_error(self):
        """Test PluginNotFoundError with search paths."""
        search_paths = [Path("/path1"), Path("/path2")]
        error = PluginNotFoundError("my-plugin", search_paths)

        assert error.plugin_name == "my-plugin"
        assert error.search_paths == search_paths
        assert "my-plugin" in str(error)
        assert "path1" in str(error)
        assert "path2" in str(error)
        assert isinstance(error, PluginError)

    def test_plugin_load_error(self):
        """Test PluginLoadError with reason."""
        error = PluginLoadError("my-plugin", "Module not found")

        assert error.plugin_name == "my-plugin"
        assert error.reason == "Module not found"
        assert "my-plugin" in str(error)
        assert "Module not found" in str(error)
        assert isinstance(error, PluginError)

    def test_plugin_validation_error(self):
        """Test PluginValidationError with multiple issues."""
        issues = ["Missing required field: name", "Invalid version format"]
        error = PluginValidationError("my-plugin", issues)

        assert error.plugin_name == "my-plugin"
        assert error.issues == issues
        assert "my-plugin" in str(error)
        assert "Missing required field: name" in str(error)
        assert "Invalid version format" in str(error)
        assert isinstance(error, PluginError)

    def test_plugin_dependency_error(self):
        """Test PluginDependencyError with dependency info."""
        error = PluginDependencyError("my-plugin", "base-utils >= 1.0", "Not installed")

        assert error.plugin_name == "my-plugin"
        assert error.dependency == "base-utils >= 1.0"
        assert error.reason == "Not installed"
        assert "my-plugin" in str(error)
        assert "base-utils >= 1.0" in str(error)
        assert "Not installed" in str(error)
        assert isinstance(error, PluginError)

    def test_plugin_initialization_error(self):
        """Test PluginInitializationError."""
        error = PluginInitializationError("my-plugin", "Missing configuration")

        assert error.plugin_name == "my-plugin"
        assert error.reason == "Missing configuration"
        assert "my-plugin" in str(error)
        assert "Missing configuration" in str(error)
        assert isinstance(error, PluginError)


# Plugin Interface Tests
class TestPluginInterface:
    """Test base Plugin interface."""

    def test_plugin_is_abstract(self):
        """Test that Plugin is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Plugin()

    def test_concrete_plugin_instantiation(self):
        """Test that concrete plugin can be instantiated."""
        plugin = TestPlugin()
        assert plugin is not None
        assert isinstance(plugin, Plugin)

    def test_plugin_metadata(self):
        """Test plugin metadata method."""
        plugin = TestPlugin(name="custom-plugin", version="2.0.0")
        metadata = plugin.metadata()

        # Required fields
        assert metadata["name"] == "custom-plugin"
        assert metadata["version"] == "2.0.0"
        assert metadata["description"] == "Test plugin"
        assert metadata["author"] == "Test Author"

        # Optional fields
        assert metadata["homepage"] == "https://example.com"
        assert metadata["license"] == "MIT"
        assert metadata["requires"] == ["base-utils >= 1.0"]
        assert metadata["tags"] == ["test", "example"]

    def test_plugin_metadata_required_fields(self):
        """Test that metadata contains all required fields."""
        plugin = TestPlugin()
        metadata = plugin.metadata()

        required_fields = ["name", "version", "description", "author"]
        for field in required_fields:
            assert field in metadata, f"Required field '{field}' missing from metadata"
            assert metadata[field], f"Required field '{field}' is empty"

    def test_plugin_initialize(self):
        """Test plugin initialization."""
        plugin = TestPlugin()
        assert not plugin.initialized

        # Mock context
        context = type("Context", (), {})()
        plugin.initialize(context)

        assert plugin.initialized
        assert plugin.context is context

    def test_plugin_cleanup(self):
        """Test plugin cleanup."""
        plugin = TestPlugin()
        assert not plugin.cleaned_up

        plugin.cleanup()
        assert plugin.cleaned_up

    def test_plugin_validate_default(self):
        """Test plugin validation returns True by default."""
        plugin = TestPlugin()
        assert plugin.validate() is True

    def test_plugin_validate_override(self):
        """Test plugin validation can be overridden."""
        plugin = FailingValidationPlugin()
        assert plugin.validate() is False

    def test_plugin_initialization_error_raised(self):
        """Test that initialization can raise PluginInitializationError."""
        plugin = FailingInitPlugin()
        context = type("Context", (), {})()

        with pytest.raises(PluginInitializationError) as exc_info:
            plugin.initialize(context)

        assert exc_info.value.plugin_name == "failing-init-plugin"
        assert exc_info.value.reason == "Initialization failed"


class TestPluginLifecycle:
    """Test plugin lifecycle."""

    def test_complete_lifecycle(self):
        """Test complete plugin lifecycle: create -> initialize -> use -> cleanup."""
        plugin = TestPlugin()

        # 1. Create
        assert not plugin.initialized
        assert not plugin.cleaned_up

        # 2. Initialize
        context = type("Context", (), {"data": "test"})()
        plugin.initialize(context)
        assert plugin.initialized
        assert plugin.context.data == "test"

        # 3. Use (validate)
        assert plugin.validate()

        # 4. Cleanup
        plugin.cleanup()
        assert plugin.cleaned_up

    def test_initialize_before_use(self):
        """Test that plugin is initialized before use."""
        plugin = TestPlugin()
        context = type("Context", (), {})()

        # Initialize first
        plugin.initialize(context)

        # Then use
        metadata = plugin.metadata()
        assert metadata["name"] == "test-plugin"

        valid = plugin.validate()
        assert valid is True

    def test_cleanup_is_optional(self):
        """Test that cleanup is optional and has default implementation."""
        plugin = TestPlugin()

        # Should not raise even without initialization
        plugin.cleanup()
        assert plugin.cleaned_up


class TestPluginMetadataContract:
    """Test plugin metadata contract."""

    def test_metadata_is_dict(self):
        """Test that metadata returns a dictionary."""
        plugin = TestPlugin()
        metadata = plugin.metadata()
        assert isinstance(metadata, dict)

    def test_metadata_name_is_string(self):
        """Test that name is a string."""
        plugin = TestPlugin()
        metadata = plugin.metadata()
        assert isinstance(metadata["name"], str)
        assert len(metadata["name"]) > 0

    def test_metadata_version_is_string(self):
        """Test that version is a string."""
        plugin = TestPlugin()
        metadata = plugin.metadata()
        assert isinstance(metadata["version"], str)
        assert len(metadata["version"]) > 0

    def test_metadata_description_is_string(self):
        """Test that description is a string."""
        plugin = TestPlugin()
        metadata = plugin.metadata()
        assert isinstance(metadata["description"], str)
        assert len(metadata["description"]) > 0

    def test_metadata_author_is_string(self):
        """Test that author is a string."""
        plugin = TestPlugin()
        metadata = plugin.metadata()
        assert isinstance(metadata["author"], str)
        assert len(metadata["author"]) > 0

    def test_metadata_optional_fields(self):
        """Test that optional fields have correct types when present."""
        plugin = TestPlugin()
        metadata = plugin.metadata()

        if "homepage" in metadata:
            assert isinstance(metadata["homepage"], str)

        if "license" in metadata:
            assert isinstance(metadata["license"], str)

        if "requires" in metadata:
            assert isinstance(metadata["requires"], list)
            assert all(isinstance(r, str) for r in metadata["requires"])

        if "tags" in metadata:
            assert isinstance(metadata["tags"], list)
            assert all(isinstance(t, str) for t in metadata["tags"])


class TestPluginExportsAPI:
    """Test that __init__.py exports correct public API."""

    def test_plugin_class_exported(self):
        """Test that Plugin class is exported."""
        from toolchainkit.plugins import Plugin

        assert Plugin is not None

    def test_all_exceptions_exported(self):
        """Test that all exception classes are exported."""
        from toolchainkit.plugins import (
            PluginError,
            PluginNotFoundError,
            PluginLoadError,
            PluginValidationError,
            PluginDependencyError,
            PluginInitializationError,
        )

        assert PluginError is not None
        assert PluginNotFoundError is not None
        assert PluginLoadError is not None
        assert PluginValidationError is not None
        assert PluginDependencyError is not None
        assert PluginInitializationError is not None

    def test_all_exports_in_all(self):
        """Test that __all__ contains expected exports."""
        from toolchainkit import plugins

        expected_exports = [
            "Plugin",
            "PluginError",
            "PluginNotFoundError",
            "PluginLoadError",
            "PluginValidationError",
            "PluginDependencyError",
            "PluginInitializationError",
        ]

        for export in expected_exports:
            assert export in plugins.__all__, f"{export} not in __all__"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
