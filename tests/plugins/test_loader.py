"""
Tests for plugin loader.
"""

import sys
import pytest
from toolchainkit.plugins import (
    PluginLoader,
    CompilerPlugin,
    PackageManagerPlugin,
    BuildBackendPlugin,
    PluginLoadError,
    PluginValidationError,
)
from toolchainkit.plugins.metadata import PluginMetadata


# ============================================================================
# Test Fixtures - Create mock plugins
# ============================================================================


@pytest.fixture
def mock_plugin_dir(tmp_path):
    """Create directory for mock plugins."""
    plugin_dir = tmp_path / "mock_plugins"
    plugin_dir.mkdir()
    return plugin_dir


@pytest.fixture
def create_mock_plugin(mock_plugin_dir):
    """Factory to create mock plugin modules."""

    def _create(module_name: str, class_name: str, plugin_code: str):
        """
        Create a mock plugin module.

        Args:
            module_name: Module name (e.g., 'test_plugin')
            class_name: Plugin class name (e.g., 'TestPlugin')
            plugin_code: Python code for the plugin
        """
        module_file = mock_plugin_dir / f"{module_name}.py"
        module_file.write_text(plugin_code, encoding="utf-8")
        return mock_plugin_dir

    return _create


@pytest.fixture
def valid_compiler_plugin_code():
    """Code for a valid compiler plugin."""
    return """
from toolchainkit.plugins import CompilerPlugin

class ValidCompilerPlugin(CompilerPlugin):
    def metadata(self):
        return {
            'name': 'valid-compiler',
            'version': '1.0.0',
            'description': 'Test compiler',
            'author': 'Test'
        }

    def initialize(self, context):
        pass

    def compiler_name(self):
        return "valid-compiler"

    def compiler_config(self):
        return {}

    def supported_platforms(self):
        return ["linux-x64"]
"""


@pytest.fixture
def valid_package_manager_plugin_code():
    """Code for a valid package manager plugin."""
    return """
from toolchainkit.plugins import PackageManagerPlugin

class ValidPMPlugin(PackageManagerPlugin):
    def metadata(self):
        return {
            'name': 'valid-pm',
            'version': '1.0.0',
            'description': 'Test PM',
            'author': 'Test'
        }

    def initialize(self, context):
        pass

    def package_manager_name(self):
        return "valid-pm"

    def detect(self, project_dir):
        return False

    def install_dependencies(self, project_dir, dependencies):
        pass

    def generate_toolchain_integration(self, project_dir, output_dir):
        pass
"""


@pytest.fixture
def valid_backend_plugin_code():
    """Code for a valid build backend plugin."""
    return """
from toolchainkit.plugins import BuildBackendPlugin

class ValidBackendPlugin(BuildBackendPlugin):
    def metadata(self):
        return {
            'name': 'valid-backend',
            'version': '1.0.0',
            'description': 'Test backend',
            'author': 'Test'
        }

    def initialize(self, context):
        pass

    def backend_name(self):
        return "valid-backend"

    def detect(self, project_dir):
        return False

    def configure(self, project_dir, build_dir, options):
        pass

    def build(self, build_dir, target, jobs):
        pass
"""


# ============================================================================
# Test: PluginLoader Initialization
# ============================================================================


class TestPluginLoaderInit:
    """Test PluginLoader initialization."""

    def test_loader_can_be_instantiated(self):
        """Test creating loader instance."""
        loader = PluginLoader()
        assert isinstance(loader, PluginLoader)

    def test_loader_has_plugin_type_map(self):
        """Test loader has PLUGIN_TYPE_MAP constant."""
        assert hasattr(PluginLoader, "PLUGIN_TYPE_MAP")
        assert "compiler" in PluginLoader.PLUGIN_TYPE_MAP
        assert "package_manager" in PluginLoader.PLUGIN_TYPE_MAP
        assert "backend" in PluginLoader.PLUGIN_TYPE_MAP


# ============================================================================
# Test: Load Valid Plugins
# ============================================================================


class TestLoadValidPlugins:
    """Test loading valid plugins."""

    def test_load_compiler_plugin(self, create_mock_plugin, valid_compiler_plugin_code):
        """Test loading a valid compiler plugin."""
        plugin_dir = create_mock_plugin(
            "test_compiler", "ValidCompilerPlugin", valid_compiler_plugin_code
        )

        metadata = PluginMetadata(
            name="test-compiler",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_compiler.ValidCompilerPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        plugin = loader.load(metadata)

        assert isinstance(plugin, CompilerPlugin)
        assert plugin.compiler_name() == "valid-compiler"

    def test_load_package_manager_plugin(
        self, create_mock_plugin, valid_package_manager_plugin_code
    ):
        """Test loading a valid package manager plugin."""
        plugin_dir = create_mock_plugin(
            "test_pm", "ValidPMPlugin", valid_package_manager_plugin_code
        )

        metadata = PluginMetadata(
            name="test-pm",
            version="1.0.0",
            type="package_manager",
            description="Test",
            author="Test",
            entry_point="test_pm.ValidPMPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        plugin = loader.load(metadata)

        assert isinstance(plugin, PackageManagerPlugin)
        assert plugin.package_manager_name() == "valid-pm"

    def test_load_backend_plugin(self, create_mock_plugin, valid_backend_plugin_code):
        """Test loading a valid backend plugin."""
        plugin_dir = create_mock_plugin(
            "test_backend", "ValidBackendPlugin", valid_backend_plugin_code
        )

        metadata = PluginMetadata(
            name="test-backend",
            version="1.0.0",
            type="backend",
            description="Test",
            author="Test",
            entry_point="test_backend.ValidBackendPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        plugin = loader.load(metadata)

        assert isinstance(plugin, BuildBackendPlugin)
        assert plugin.backend_name() == "valid-backend"

    def test_load_adds_plugin_dir_to_sys_path(
        self, create_mock_plugin, valid_compiler_plugin_code
    ):
        """Test that plugin directory is added to sys.path."""
        plugin_dir = create_mock_plugin(
            "test_path", "ValidCompilerPlugin", valid_compiler_plugin_code
        )

        # Remove from sys.path if present
        plugin_dir_str = str(plugin_dir)
        if plugin_dir_str in sys.path:
            sys.path.remove(plugin_dir_str)

        metadata = PluginMetadata(
            name="test-path",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_path.ValidCompilerPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        loader.load(metadata)

        # Check plugin dir was added
        assert plugin_dir_str in sys.path


# ============================================================================
# Test: Load Errors - Module Not Found
# ============================================================================


class TestLoadModuleNotFound:
    """Test handling of module not found errors."""

    def test_load_nonexistent_module(self, mock_plugin_dir):
        """Test loading plugin with non-existent module."""
        metadata = PluginMetadata(
            name="nonexistent",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="nonexistent_module.SomeClass",
            plugin_dir=mock_plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "nonexistent_module" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Test: Load Errors - Class Not Found
# ============================================================================


class TestLoadClassNotFound:
    """Test handling of class not found errors."""

    def test_load_nonexistent_class(
        self, create_mock_plugin, valid_compiler_plugin_code
    ):
        """Test loading plugin with non-existent class."""
        plugin_dir = create_mock_plugin(
            "test_no_class", "ValidCompilerPlugin", valid_compiler_plugin_code
        )

        # Reference wrong class name
        metadata = PluginMetadata(
            name="test-no-class",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_no_class.WrongClassName",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "WrongClassName" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Test: Load Errors - Invalid Plugin Type
# ============================================================================


class TestLoadInvalidPluginType:
    """Test handling of invalid plugin types."""

    def test_load_plugin_not_extending_plugin(self, create_mock_plugin):
        """Test loading class that doesn't extend Plugin."""
        plugin_code = """
class NotAPlugin:
    pass
"""
        plugin_dir = create_mock_plugin("test_not_plugin", "NotAPlugin", plugin_code)

        metadata = PluginMetadata(
            name="test-not-plugin",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_not_plugin.NotAPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginValidationError) as exc_info:
            loader.load(metadata)

        assert "must extend Plugin" in str(exc_info.value)

    def test_load_wrong_plugin_type(self, create_mock_plugin):
        """Test loading plugin with wrong type (compiler plugin registered as PM)."""
        # Create a compiler plugin
        plugin_code = """
from toolchainkit.plugins import CompilerPlugin

class TestPlugin(CompilerPlugin):
    def metadata(self):
        return {'name': 'test', 'version': '1.0.0', 'description': 'Test', 'author': 'Test'}

    def initialize(self, context):
        pass

    def compiler_name(self):
        return "test"

    def compiler_config(self):
        return {}

    def supported_platforms(self):
        return []
"""
        plugin_dir = create_mock_plugin("test_wrong_type", "TestPlugin", plugin_code)

        # Metadata says it's a package_manager, but code extends CompilerPlugin
        metadata = PluginMetadata(
            name="test-wrong-type",
            version="1.0.0",
            type="package_manager",  # Wrong type!
            description="Test",
            author="Test",
            entry_point="test_wrong_type.TestPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginValidationError) as exc_info:
            loader.load(metadata)

        assert "package_manager" in str(exc_info.value)
        assert "PackageManagerPlugin" in str(exc_info.value)


# ============================================================================
# Test: Load Errors - Instantiation Errors
# ============================================================================


class TestLoadInstantiationErrors:
    """Test handling of instantiation errors."""

    def test_load_plugin_requiring_arguments(self, create_mock_plugin):
        """Test loading plugin class that requires __init__ arguments."""
        plugin_code = """
from toolchainkit.plugins import CompilerPlugin

class RequiresArgsPlugin(CompilerPlugin):
    def __init__(self, required_arg):
        self.required_arg = required_arg

    def metadata(self):
        return {'name': 'test', 'version': '1.0.0', 'description': 'Test', 'author': 'Test'}

    def initialize(self, context):
        pass

    def compiler_name(self):
        return "test"

    def compiler_config(self):
        return {}

    def supported_platforms(self):
        return []
"""
        plugin_dir = create_mock_plugin(
            "test_requires_args", "RequiresArgsPlugin", plugin_code
        )

        metadata = PluginMetadata(
            name="test-requires-args",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_requires_args.RequiresArgsPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "instantiate" in str(exc_info.value).lower()
        assert "require arguments" in str(exc_info.value).lower()

    def test_load_plugin_with_init_error(self, create_mock_plugin):
        """Test loading plugin that raises error in __init__."""
        plugin_code = """
from toolchainkit.plugins import CompilerPlugin

class InitErrorPlugin(CompilerPlugin):
    def __init__(self):
        raise RuntimeError("Initialization failed!")

    def metadata(self):
        return {'name': 'test', 'version': '1.0.0', 'description': 'Test', 'author': 'Test'}

    def initialize(self, context):
        pass

    def compiler_name(self):
        return "test"

    def compiler_config(self):
        return {}

    def supported_platforms(self):
        return []
"""
        plugin_dir = create_mock_plugin(
            "test_init_error", "InitErrorPlugin", plugin_code
        )

        metadata = PluginMetadata(
            name="test-init-error",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_init_error.InitErrorPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "Error instantiating" in str(exc_info.value)


# ============================================================================
# Test: Load Errors - Not a Class
# ============================================================================


class TestLoadNotAClass:
    """Test handling when entry point is not a class."""

    def test_load_entry_point_not_a_class(self, create_mock_plugin):
        """Test loading when entry point refers to a function, not a class."""
        plugin_code = """
def not_a_class():
    return "I'm a function!"
"""
        plugin_dir = create_mock_plugin("test_not_class", "not_a_class", plugin_code)

        metadata = PluginMetadata(
            name="test-not-class",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_not_class.not_a_class",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "not a class" in str(exc_info.value).lower()


# ============================================================================
# Test: Load Errors - Import Errors
# ============================================================================


class TestLoadImportErrors:
    """Test handling of various import errors."""

    def test_load_module_with_syntax_error(self, create_mock_plugin):
        """Test loading module with syntax error."""
        plugin_code = """
# Invalid Python syntax
class SyntaxErrorPlugin(CompilerPlugin
    # Missing closing parenthesis
"""
        plugin_dir = create_mock_plugin(
            "test_syntax_error", "SyntaxErrorPlugin", plugin_code
        )

        metadata = PluginMetadata(
            name="test-syntax-error",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_syntax_error.SyntaxErrorPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "test_syntax_error" in str(exc_info.value)

    def test_load_module_with_import_error(self, create_mock_plugin):
        """Test loading module that imports non-existent module."""
        plugin_code = """
import nonexistent_module_xyz

from toolchainkit.plugins import CompilerPlugin

class ImportErrorPlugin(CompilerPlugin):
    pass
"""
        plugin_dir = create_mock_plugin(
            "test_import_error", "ImportErrorPlugin", plugin_code
        )

        metadata = PluginMetadata(
            name="test-import-error",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_import_error.ImportErrorPlugin",
            plugin_dir=plugin_dir,
        )

        loader = PluginLoader()
        with pytest.raises(PluginLoadError) as exc_info:
            loader.load(metadata)

        assert "import" in str(exc_info.value).lower()


# ============================================================================
# Test: Load with No Plugin Dir
# ============================================================================


class TestLoadNoPluginDir:
    """Test loading when metadata has no plugin_dir."""

    def test_load_plugin_without_plugin_dir(
        self, create_mock_plugin, valid_compiler_plugin_code
    ):
        """Test loading plugin when metadata.plugin_dir is None."""
        # Create plugin in a directory that's already in sys.path
        plugin_dir = create_mock_plugin(
            "test_no_dir", "ValidCompilerPlugin", valid_compiler_plugin_code
        )

        # Add to sys.path manually
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))

        # Create metadata without plugin_dir
        metadata = PluginMetadata(
            name="test-no-dir",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test_no_dir.ValidCompilerPlugin",
            plugin_dir=None,  # No plugin_dir
        )

        loader = PluginLoader()
        plugin = loader.load(metadata)

        assert isinstance(plugin, CompilerPlugin)


# ============================================================================
# Test: Module Exports
# ============================================================================


class TestLoaderModuleExports:
    """Test module exports correct API."""

    def test_plugin_loader_exported(self):
        """Test PluginLoader is exported."""
        from toolchainkit.plugins.loader import PluginLoader as DirectImport
        from toolchainkit.plugins import PluginLoader as PackageImport

        assert DirectImport is PackageImport


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
