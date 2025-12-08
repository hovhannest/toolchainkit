"""
Unit tests for CompilerPlugin interface.
"""

import pytest
from pathlib import Path
from toolchainkit.plugins import CompilerPlugin, Plugin


# Test Compiler Plugin Implementation
class TestCompilerPluginImpl(CompilerPlugin):
    """Concrete compiler plugin for testing."""

    def __init__(self, name="test-compiler"):
        self.name = name
        self._platforms = ["linux-x64", "windows-x64", "macos-x64"]

    def metadata(self):
        return {
            "name": f"{self.name}-plugin",
            "version": "1.0.0",
            "description": f"{self.name} compiler plugin",
            "author": "Test Author",
        }

    def initialize(self, context):
        self.context = context

    def compiler_name(self):
        return self.name

    def compiler_config(self):
        # Return mock config for testing
        class MockCompilerConfig:
            def __init__(self, name):
                self.compiler_name = name

        return MockCompilerConfig(self.name)

    def supported_platforms(self):
        return self._platforms


class SystemInstalledCompilerPlugin(TestCompilerPluginImpl):
    """Compiler plugin with system detection."""

    def __init__(self):
        super().__init__("system-compiler")
        self.install_path = Path("/usr/local/bin")

    def detect_system_installation(self):
        return self.install_path


class DownloadableCompilerPlugin(TestCompilerPluginImpl):
    """Compiler plugin with download support."""

    def __init__(self):
        super().__init__("downloadable-compiler")
        self.downloaded = False
        self.download_dest = None

    def download_compiler(self, version, platform, destination):
        self.downloaded = True
        self.download_dest = destination
        return destination / f"{self.name}-{version}"


class VersionDetectingCompilerPlugin(TestCompilerPluginImpl):
    """Compiler plugin with version detection."""

    def __init__(self):
        super().__init__("versioned-compiler")

    def get_version(self, compiler_path):
        return "1.2.3"


# CompilerPlugin Interface Tests
class TestCompilerPluginInterface:
    """Test CompilerPlugin interface."""

    def test_compiler_plugin_is_abstract(self):
        """Test that CompilerPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CompilerPlugin()

    def test_compiler_plugin_extends_plugin(self):
        """Test that CompilerPlugin extends base Plugin."""
        assert issubclass(CompilerPlugin, Plugin)

    def test_concrete_compiler_plugin_instantiation(self):
        """Test that concrete compiler plugin can be instantiated."""
        plugin = TestCompilerPluginImpl()
        assert plugin is not None
        assert isinstance(plugin, CompilerPlugin)
        assert isinstance(plugin, Plugin)

    def test_compiler_name_method(self):
        """Test compiler_name method returns correct identifier."""
        plugin = TestCompilerPluginImpl(name="zig")
        assert plugin.compiler_name() == "zig"

        plugin2 = TestCompilerPluginImpl(name="dmd")
        assert plugin2.compiler_name() == "dmd"

    def test_compiler_config_method(self):
        """Test compiler_config method returns config object."""
        plugin = TestCompilerPluginImpl()
        config = plugin.compiler_config()

        assert config is not None
        assert hasattr(config, "compiler_name")
        assert config.compiler_name == "test-compiler"

    def test_supported_platforms_method(self):
        """Test supported_platforms returns list of platform strings."""
        plugin = TestCompilerPluginImpl()
        platforms = plugin.supported_platforms()

        assert isinstance(platforms, list)
        assert len(platforms) > 0
        assert all(isinstance(p, str) for p in platforms)
        assert "linux-x64" in platforms
        assert "windows-x64" in platforms

    def test_platform_format(self):
        """Test that platform strings follow expected format."""
        plugin = TestCompilerPluginImpl()
        platforms = plugin.supported_platforms()

        for platform in platforms:
            # Should be lowercase
            assert platform == platform.lower()
            # Should contain at least os-arch
            parts = platform.split("-")
            assert len(parts) >= 2


class TestCompilerPluginOptionalMethods:
    """Test optional compiler plugin methods."""

    def test_detect_system_installation_default(self):
        """Test detect_system_installation returns None by default."""
        plugin = TestCompilerPluginImpl()
        result = plugin.detect_system_installation()
        assert result is None

    def test_detect_system_installation_override(self):
        """Test detect_system_installation can be overridden."""
        plugin = SystemInstalledCompilerPlugin()
        result = plugin.detect_system_installation()

        assert result is not None
        assert isinstance(result, Path)
        assert result == Path("/usr/local/bin")

    def test_download_compiler_not_implemented_by_default(self):
        """Test download_compiler raises NotImplementedError by default."""
        plugin = TestCompilerPluginImpl()

        with pytest.raises(NotImplementedError) as exc_info:
            plugin.download_compiler("1.0.0", "linux-x64", Path("/tmp"))

        assert "Automatic download not supported" in str(exc_info.value)
        assert "test-compiler" in str(exc_info.value)

    def test_download_compiler_override(self):
        """Test download_compiler can be overridden."""
        plugin = DownloadableCompilerPlugin()
        destination = Path("/tmp/compilers")

        result = plugin.download_compiler("1.0.0", "linux-x64", destination)

        assert plugin.downloaded
        assert plugin.download_dest == destination
        assert isinstance(result, Path)
        assert result == destination / "downloadable-compiler-1.0.0"

    def test_get_version_not_implemented_by_default(self):
        """Test get_version raises NotImplementedError by default."""
        plugin = TestCompilerPluginImpl()

        with pytest.raises(NotImplementedError) as exc_info:
            plugin.get_version(Path("/usr/bin/compiler"))

        assert "Version detection not implemented" in str(exc_info.value)

    def test_get_version_override(self):
        """Test get_version can be overridden."""
        plugin = VersionDetectingCompilerPlugin()
        version = plugin.get_version(Path("/usr/bin/compiler"))

        assert version == "1.2.3"


class TestCompilerPluginLifecycle:
    """Test compiler plugin lifecycle."""

    def test_complete_compiler_plugin_lifecycle(self):
        """Test complete lifecycle: create -> initialize -> use."""
        plugin = TestCompilerPluginImpl(name="zig")

        # 1. Create plugin
        metadata = plugin.metadata()
        assert metadata["name"] == "zig-plugin"

        # 2. Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)
        assert plugin.context is context

        # 3. Use plugin
        assert plugin.compiler_name() == "zig"
        config = plugin.compiler_config()
        assert config.compiler_name == "zig"
        platforms = plugin.supported_platforms()
        assert isinstance(platforms, list)

    def test_compiler_plugin_with_system_detection(self):
        """Test plugin lifecycle with system detection."""
        plugin = SystemInstalledCompilerPlugin()

        # Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)

        # Check system installation
        install_path = plugin.detect_system_installation()
        assert install_path == Path("/usr/local/bin")

        # Get compiler info
        name = plugin.compiler_name()
        assert name == "system-compiler"

    def test_compiler_plugin_with_download(self):
        """Test plugin lifecycle with download support."""
        plugin = DownloadableCompilerPlugin()

        # Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)

        # Download compiler
        dest = Path("/tmp/downloads")
        install_path = plugin.download_compiler("1.0.0", "linux-x64", dest)

        assert plugin.downloaded
        assert install_path.parent == dest


class TestCompilerPluginUseCases:
    """Test real-world compiler plugin use cases."""

    def test_simple_yaml_based_compiler(self):
        """Test simple compiler using YAML config."""

        class SimpleYAMLCompiler(CompilerPlugin):
            def metadata(self):
                return {
                    "name": "simple-compiler",
                    "version": "1.0.0",
                    "description": "Simple YAML-based compiler",
                    "author": "Test",
                }

            def initialize(self, context):
                pass

            def compiler_name(self):
                return "simple"

            def compiler_config(self):
                # In real implementation, would load YAML file
                class YAMLConfig:
                    pass

                return YAMLConfig()

            def supported_platforms(self):
                return ["linux-x64", "windows-x64"]

        plugin = SimpleYAMLCompiler()
        assert plugin.compiler_name() == "simple"
        assert len(plugin.supported_platforms()) == 2

    def test_cross_platform_compiler(self):
        """Test compiler supporting many platforms."""

        class CrossPlatformCompiler(CompilerPlugin):
            def metadata(self):
                return {
                    "name": "cross-compiler",
                    "version": "1.0.0",
                    "description": "Cross-platform compiler",
                    "author": "Test",
                }

            def initialize(self, context):
                pass

            def compiler_name(self):
                return "cross"

            def compiler_config(self):
                return None

            def supported_platforms(self):
                return [
                    "linux-x64",
                    "linux-arm64",
                    "linux-riscv64",
                    "windows-x64",
                    "windows-arm64",
                    "macos-x64",
                    "macos-arm64",
                ]

        plugin = CrossPlatformCompiler()
        platforms = plugin.supported_platforms()
        assert len(platforms) == 7
        assert "linux-riscv64" in platforms

    def test_compiler_with_all_features(self):
        """Test compiler plugin using all available features."""

        class FullFeaturedCompiler(CompilerPlugin):
            def metadata(self):
                return {
                    "name": "full-featured",
                    "version": "1.0.0",
                    "description": "Compiler with all features",
                    "author": "Test",
                }

            def initialize(self, context):
                self.context = context

            def compiler_name(self):
                return "full"

            def compiler_config(self):
                return type("Config", (), {})()

            def supported_platforms(self):
                return ["linux-x64", "windows-x64"]

            def detect_system_installation(self):
                return Path("/opt/full")

            def download_compiler(self, version, platform, destination):
                return destination / f"full-{version}"

            def get_version(self, compiler_path):
                return "2.0.0"

        plugin = FullFeaturedCompiler()

        # Test all methods
        assert plugin.compiler_name() == "full"
        assert plugin.compiler_config() is not None
        assert len(plugin.supported_platforms()) == 2
        assert plugin.detect_system_installation() == Path("/opt/full")
        assert plugin.get_version(Path("/opt/full")) == "2.0.0"

        dest = Path("/tmp")
        install = plugin.download_compiler("2.0.0", "linux-x64", dest)
        assert install == dest / "full-2.0.0"


class TestCompilerPluginExportsAPI:
    """Test that CompilerPlugin is properly exported."""

    def test_compiler_plugin_exported(self):
        """Test that CompilerPlugin is exported from plugins package."""
        from toolchainkit.plugins import CompilerPlugin

        assert CompilerPlugin is not None

    def test_compiler_plugin_in_all(self):
        """Test that CompilerPlugin is in __all__."""
        from toolchainkit import plugins

        assert "CompilerPlugin" in plugins.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
