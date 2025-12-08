"""
Unit tests for BuildBackendPlugin interface.
"""

import pytest
from pathlib import Path
from toolchainkit.plugins import (
    BuildBackendPlugin,
    Plugin,
    BuildBackendError,
)


# Test Build Backend Plugin Implementations
class TestBuildBackendImpl(BuildBackendPlugin):
    """Concrete build backend plugin for testing."""

    def __init__(self, name="test-backend"):
        self.name = name
        self.configured = False
        self.built = False
        self.last_config = None

    def metadata(self):
        return {
            "name": f"{self.name}-plugin",
            "version": "1.0.0",
            "description": f"{self.name} build backend plugin",
            "author": "Test Author",
        }

    def initialize(self, context):
        self.context = context

    def backend_name(self):
        return self.name

    def detect(self, project_root):
        # Check for test marker file
        return (project_root / f"{self.name}.build").exists()

    def configure(self, project_root, build_dir, config):
        self.configured = True
        self.last_config = config
        build_dir.mkdir(parents=True, exist_ok=True)

    def build(self, build_dir, target=None, jobs=None):
        self.built = True
        self.last_target = target
        self.last_jobs = jobs


class MesonLikePlugin(BuildBackendPlugin):
    """Meson-like build backend."""

    def __init__(self):
        self.test_executed = False

    def metadata(self):
        return {
            "name": "meson-like",
            "version": "1.0.0",
            "description": "Meson-like build backend",
            "author": "Test",
        }

    def initialize(self, context):
        pass

    def backend_name(self):
        return "meson"

    def detect(self, project_root):
        return (project_root / "meson.build").exists()

    def configure(self, project_root, build_dir, config):
        build_dir.mkdir(parents=True, exist_ok=True)
        # Simulate meson setup
        (build_dir / "build.ninja").write_text("# Ninja build file")

    def build(self, build_dir, target=None, jobs=None):
        # Simulate meson compile
        pass

    def test(self, build_dir, test_name=None):
        # Override to provide test support
        self.test_executed = True
        self.last_test = test_name


class FullFeaturedBackend(BuildBackendPlugin):
    """Build backend with all optional features."""

    def __init__(self):
        self.cleaned = False
        self.installed = False

    def metadata(self):
        return {
            "name": "full-featured-backend",
            "version": "1.0.0",
            "description": "Full-featured build backend",
            "author": "Test",
        }

    def initialize(self, context):
        pass

    def backend_name(self):
        return "fullbackend"

    def detect(self, project_root):
        return (project_root / "build.cfg").exists()

    def configure(self, project_root, build_dir, config):
        build_dir.mkdir(parents=True, exist_ok=True)

    def build(self, build_dir, target=None, jobs=None):
        pass

    def test(self, build_dir, test_name=None):
        pass

    def clean(self, build_dir):
        self.cleaned = True

    def install(self, build_dir, install_dir):
        self.installed = True
        self.install_dest = install_dir


# Build Backend Plugin Interface Tests
class TestBuildBackendPluginInterface:
    """Test BuildBackendPlugin interface."""

    def test_build_backend_plugin_is_abstract(self):
        """Test that BuildBackendPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BuildBackendPlugin()

    def test_build_backend_plugin_extends_plugin(self):
        """Test that BuildBackendPlugin extends base Plugin."""
        assert issubclass(BuildBackendPlugin, Plugin)

    def test_concrete_build_backend_plugin_instantiation(self):
        """Test that concrete build backend plugin can be instantiated."""
        plugin = TestBuildBackendImpl()
        assert plugin is not None
        assert isinstance(plugin, BuildBackendPlugin)
        assert isinstance(plugin, Plugin)

    def test_backend_name_method(self):
        """Test backend_name method returns correct identifier."""
        plugin = TestBuildBackendImpl(name="meson")
        assert plugin.backend_name() == "meson"

        plugin2 = TestBuildBackendImpl(name="xmake")
        assert plugin2.backend_name() == "xmake"

    def test_detect_method(self, tmp_path):
        """Test detect method checks for build system files."""
        plugin = TestBuildBackendImpl(name="meson")
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initially not detected
        assert not plugin.detect(project_root)

        # Create marker file
        (project_root / "meson.build").touch()

        # Now detected
        assert plugin.detect(project_root)

    def test_configure_method(self, tmp_path):
        """Test configure method."""
        plugin = TestBuildBackendImpl()
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        config = {
            "toolchain_path": Path("/usr/local/toolchain"),
            "build_type": "Release",
            "compiler": "clang",
        }

        assert not plugin.configured
        plugin.configure(project_root, build_dir, config)

        assert plugin.configured
        assert plugin.last_config == config
        assert build_dir.exists()

    def test_build_method(self, tmp_path):
        """Test build method."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        assert not plugin.built
        plugin.build(build_dir)
        assert plugin.built

    def test_build_with_target(self, tmp_path):
        """Test build method with specific target."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        plugin.build(build_dir, target="myapp")

        assert plugin.built
        assert plugin.last_target == "myapp"

    def test_build_with_jobs(self, tmp_path):
        """Test build method with parallel jobs."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        plugin.build(build_dir, jobs=8)

        assert plugin.built
        assert plugin.last_jobs == 8


class TestBuildBackendPluginOptionalMethods:
    """Test optional build backend plugin methods."""

    def test_test_not_implemented_by_default(self, tmp_path):
        """Test test() raises NotImplementedError by default."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"

        with pytest.raises(NotImplementedError) as exc_info:
            plugin.test(build_dir)

        assert "Testing not supported" in str(exc_info.value)
        assert "test-backend" in str(exc_info.value)

    def test_test_override(self, tmp_path):
        """Test test() can be overridden."""
        plugin = MesonLikePlugin()
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        assert not plugin.test_executed
        plugin.test(build_dir)
        assert plugin.test_executed

    def test_test_with_test_name(self, tmp_path):
        """Test test() with specific test name."""
        plugin = MesonLikePlugin()
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        plugin.test(build_dir, test_name="unit_tests")

        assert plugin.test_executed
        assert plugin.last_test == "unit_tests"

    def test_clean_default(self, tmp_path):
        """Test clean() has default empty implementation."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"
        # Should not raise
        plugin.clean(build_dir)

    def test_clean_override(self, tmp_path):
        """Test clean() can be overridden."""
        plugin = FullFeaturedBackend()
        build_dir = tmp_path / "build"

        assert not plugin.cleaned
        plugin.clean(build_dir)
        assert plugin.cleaned

    def test_install_not_implemented_by_default(self, tmp_path):
        """Test install() raises NotImplementedError by default."""
        plugin = TestBuildBackendImpl()
        build_dir = tmp_path / "build"
        install_dir = tmp_path / "install"

        with pytest.raises(NotImplementedError) as exc_info:
            plugin.install(build_dir, install_dir)

        assert "Installation not supported" in str(exc_info.value)
        assert "test-backend" in str(exc_info.value)

    def test_install_override(self, tmp_path):
        """Test install() can be overridden."""
        plugin = FullFeaturedBackend()
        build_dir = tmp_path / "build"
        install_dir = tmp_path / "install"

        assert not plugin.installed
        plugin.install(build_dir, install_dir)

        assert plugin.installed
        assert plugin.install_dest == install_dir


class TestBuildBackendPluginLifecycle:
    """Test build backend plugin lifecycle."""

    def test_complete_build_workflow(self, tmp_path):
        """Test complete workflow: detect -> configure -> build."""
        plugin = TestBuildBackendImpl(name="meson")
        project_root = tmp_path / "project"
        project_root.mkdir()
        build_dir = tmp_path / "build"

        # 1. Create plugin
        metadata = plugin.metadata()
        assert metadata["name"] == "meson-plugin"

        # 2. Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)

        # 3. Detect
        (project_root / "meson.build").touch()
        assert plugin.detect(project_root)

        # 4. Configure
        config = {
            "toolchain_path": Path("/usr/local/toolchain"),
            "build_type": "Debug",
        }
        plugin.configure(project_root, build_dir, config)
        assert plugin.configured

        # 5. Build
        plugin.build(build_dir)
        assert plugin.built

    def test_meson_like_full_workflow(self, tmp_path):
        """Test Meson-like workflow with tests."""
        plugin = MesonLikePlugin()
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "meson.build").write_text("project('test', 'cpp')")
        build_dir = tmp_path / "build"

        # Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)

        # Detect
        assert plugin.detect(project_root)

        # Configure
        config = {"toolchain_path": Path("/opt/clang"), "build_type": "Release"}
        plugin.configure(project_root, build_dir, config)
        assert (build_dir / "build.ninja").exists()

        # Build
        plugin.build(build_dir)

        # Test
        plugin.test(build_dir)
        assert plugin.test_executed

    def test_full_featured_workflow(self, tmp_path):
        """Test complete workflow with all optional features."""
        plugin = FullFeaturedBackend()
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "build.cfg").write_text("# build config")
        build_dir = tmp_path / "build"
        install_dir = tmp_path / "install"

        # Detect
        assert plugin.detect(project_root)

        # Configure
        config = {"toolchain_path": Path("/toolchain"), "build_type": "Release"}
        plugin.configure(project_root, build_dir, config)

        # Build
        plugin.build(build_dir)

        # Test
        plugin.test(build_dir)

        # Clean
        plugin.clean(build_dir)
        assert plugin.cleaned

        # Install
        plugin.install(build_dir, install_dir)
        assert plugin.installed


class TestBuildBackendPluginUseCases:
    """Test real-world build backend plugin use cases."""

    def test_simple_build_system(self, tmp_path):
        """Test simple build system plugin."""

        class SimpleBuild(BuildBackendPlugin):
            def metadata(self):
                return {
                    "name": "simple-build",
                    "version": "1.0.0",
                    "description": "Simple build system",
                    "author": "Test",
                }

            def initialize(self, context):
                pass

            def backend_name(self):
                return "simple"

            def detect(self, project_root):
                return (project_root / "build.txt").exists()

            def configure(self, project_root, build_dir, config):
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / "config.txt").write_text("configured")

            def build(self, build_dir, target=None, jobs=None):
                (build_dir / "output.exe").write_text("built")

        project = tmp_path / "project"
        project.mkdir()
        (project / "build.txt").touch()
        build_dir = tmp_path / "build"

        plugin = SimpleBuild()
        assert plugin.detect(project)

        plugin.configure(project, build_dir, {})
        assert (build_dir / "config.txt").exists()

        plugin.build(build_dir)
        assert (build_dir / "output.exe").exists()


class TestBuildBackendError:
    """Test BuildBackendError exception."""

    def test_build_backend_error_is_toolchainkit_error(self):
        """Test that BuildBackendError extends ToolchainKitError."""
        from toolchainkit.core.exceptions import ToolchainKitError

        assert issubclass(BuildBackendError, ToolchainKitError)

    def test_build_backend_error_creation(self):
        """Test creating BuildBackendError."""
        from toolchainkit.core.exceptions import ToolchainKitError

        error = BuildBackendError("Build failed")
        assert str(error) == "Build failed"
        assert isinstance(error, ToolchainKitError)
        assert isinstance(error, Exception)


class TestBuildBackendPluginExportsAPI:
    """Test that BuildBackendPlugin is properly exported."""

    def test_build_backend_plugin_exported(self):
        """Test that BuildBackendPlugin is exported from plugins package."""
        from toolchainkit.plugins import BuildBackendPlugin

        assert BuildBackendPlugin is not None

    def test_build_backend_error_exported(self):
        """Test that BuildBackendError is exported."""
        from toolchainkit.plugins import BuildBackendError

        assert BuildBackendError is not None

    def test_build_backend_plugin_in_all(self):
        """Test that BuildBackendPlugin is in __all__."""
        from toolchainkit import plugins

        assert "BuildBackendPlugin" in plugins.__all__
        assert "BuildBackendError" in plugins.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
