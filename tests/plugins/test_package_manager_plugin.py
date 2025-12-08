"""
Unit tests for PackageManagerPlugin interface.
"""

import pytest
from toolchainkit.plugins import (
    PackageManagerPlugin,
    Plugin,
    PackageManagerError,
)


# Test Package Manager Plugin Implementations
class TestPackageManagerImpl(PackageManagerPlugin):
    """Concrete package manager plugin for testing."""

    def __init__(self, name="test-pm"):
        self.name = name
        self.installed = False
        self.detected = False

    def metadata(self):
        return {
            "name": f"{self.name}-plugin",
            "version": "1.0.0",
            "description": f"{self.name} package manager plugin",
            "author": "Test Author",
        }

    def initialize(self, context):
        self.context = context

    def package_manager_name(self):
        return self.name

    def detect(self, project_root):
        # Check for test marker file
        self.detected = (project_root / f".{self.name}").exists()
        return self.detected

    def install_dependencies(self, project_root):
        self.installed = True

    def generate_toolchain_integration(self, toolchain_file, config):
        content = f"# {self.name} integration\n"
        with open(toolchain_file, "a") as f:
            f.write(content)


class HunterLikePlugin(PackageManagerPlugin):
    """Hunter-like package manager (CMake-integrated)."""

    def metadata(self):
        return {
            "name": "hunter-like",
            "version": "1.0.0",
            "description": "Hunter-like package manager",
            "author": "Test",
        }

    def initialize(self, context):
        pass

    def package_manager_name(self):
        return "hunter"

    def detect(self, project_root):
        return (project_root / "cmake" / "HunterGate.cmake").exists()

    def install_dependencies(self, project_root):
        # CMake-integrated, no explicit install
        pass

    def generate_toolchain_integration(self, toolchain_file, config):
        url = config.get("url", "https://github.com/cpp-pm/hunter/archive.tar.gz")
        sha1 = config.get("sha1", "abc123")

        cmake_code = f"""
# Hunter package manager integration
include(cmake/HunterGate.cmake)
HunterGate(
    URL "{url}"
    SHA1 "{sha1}"
)
"""
        with open(toolchain_file, "a") as f:
            f.write(cmake_code)


class FullFeaturedPM(PackageManagerPlugin):
    """Package manager with all optional features."""

    def __init__(self):
        self.packages = [
            {"name": "boost", "version": "1.83.0", "path": "/opt/boost"},
            {"name": "fmt", "version": "10.1.1", "path": "/opt/fmt"},
        ]

    def metadata(self):
        return {
            "name": "full-featured-pm",
            "version": "1.0.0",
            "description": "Full-featured package manager",
            "author": "Test",
        }

    def initialize(self, context):
        pass

    def package_manager_name(self):
        return "fullpm"

    def detect(self, project_root):
        return (project_root / "packages.json").exists()

    def install_dependencies(self, project_root):
        pass

    def generate_toolchain_integration(self, toolchain_file, config):
        with open(toolchain_file, "a") as f:
            f.write("# FullPM integration\n")

    def get_installed_packages(self, project_root):
        return self.packages

    def update_dependencies(self, project_root):
        # Simulate update
        self.packages[0]["version"] = "1.84.0"

    def clean_cache(self, project_root):
        # Simulate cache cleanup
        pass


# Package Manager Plugin Interface Tests
class TestPackageManagerPluginInterface:
    """Test PackageManagerPlugin interface."""

    def test_package_manager_plugin_is_abstract(self):
        """Test that PackageManagerPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PackageManagerPlugin()

    def test_package_manager_plugin_extends_plugin(self):
        """Test that PackageManagerPlugin extends base Plugin."""
        assert issubclass(PackageManagerPlugin, Plugin)

    def test_concrete_package_manager_plugin_instantiation(self):
        """Test that concrete package manager plugin can be instantiated."""
        plugin = TestPackageManagerImpl()
        assert plugin is not None
        assert isinstance(plugin, PackageManagerPlugin)
        assert isinstance(plugin, Plugin)

    def test_package_manager_name_method(self):
        """Test package_manager_name method returns correct identifier."""
        plugin = TestPackageManagerImpl(name="hunter")
        assert plugin.package_manager_name() == "hunter"

        plugin2 = TestPackageManagerImpl(name="bazel")
        assert plugin2.package_manager_name() == "bazel"

    def test_detect_method(self, tmp_path):
        """Test detect method checks for package manager files."""
        plugin = TestPackageManagerImpl(name="xmake")
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initially not detected
        assert not plugin.detect(project_root)

        # Create marker file
        (project_root / ".xmake").touch()

        # Now detected
        assert plugin.detect(project_root)
        assert plugin.detected

    def test_install_dependencies_method(self, tmp_path):
        """Test install_dependencies method."""
        plugin = TestPackageManagerImpl()
        project_root = tmp_path / "project"
        project_root.mkdir()

        assert not plugin.installed
        plugin.install_dependencies(project_root)
        assert plugin.installed

    def test_generate_toolchain_integration_method(self, tmp_path):
        """Test generate_toolchain_integration method."""
        plugin = TestPackageManagerImpl(name="test-pm")
        toolchain_file = tmp_path / "toolchain.cmake"
        toolchain_file.write_text("# Toolchain file\n")

        config = {"some": "config"}
        plugin.generate_toolchain_integration(toolchain_file, config)

        content = toolchain_file.read_text()
        assert "# test-pm integration" in content


class TestPackageManagerPluginOptionalMethods:
    """Test optional package manager plugin methods."""

    def test_get_installed_packages_default(self, tmp_path):
        """Test get_installed_packages returns empty list by default."""
        plugin = TestPackageManagerImpl()
        packages = plugin.get_installed_packages(tmp_path)

        assert isinstance(packages, list)
        assert len(packages) == 0

    def test_get_installed_packages_override(self, tmp_path):
        """Test get_installed_packages can be overridden."""
        plugin = FullFeaturedPM()
        packages = plugin.get_installed_packages(tmp_path)

        assert len(packages) == 2
        assert packages[0]["name"] == "boost"
        assert packages[0]["version"] == "1.83.0"
        assert packages[1]["name"] == "fmt"

    def test_update_dependencies_not_implemented_by_default(self, tmp_path):
        """Test update_dependencies raises NotImplementedError by default."""
        plugin = TestPackageManagerImpl()

        with pytest.raises(NotImplementedError) as exc_info:
            plugin.update_dependencies(tmp_path)

        assert "Dependency updates not supported" in str(exc_info.value)
        assert "test-pm" in str(exc_info.value)

    def test_update_dependencies_override(self, tmp_path):
        """Test update_dependencies can be overridden."""
        plugin = FullFeaturedPM()

        packages_before = plugin.get_installed_packages(tmp_path)
        assert packages_before[0]["version"] == "1.83.0"

        plugin.update_dependencies(tmp_path)

        packages_after = plugin.get_installed_packages(tmp_path)
        assert packages_after[0]["version"] == "1.84.0"

    def test_clean_cache_default(self, tmp_path):
        """Test clean_cache has default empty implementation."""
        plugin = TestPackageManagerImpl()
        # Should not raise
        plugin.clean_cache(tmp_path)

    def test_clean_cache_override(self, tmp_path):
        """Test clean_cache can be overridden."""
        plugin = FullFeaturedPM()
        # Should not raise
        plugin.clean_cache(tmp_path)


class TestPackageManagerPluginLifecycle:
    """Test package manager plugin lifecycle."""

    def test_complete_lifecycle(self, tmp_path):
        """Test complete lifecycle: create -> initialize -> detect -> install."""
        plugin = TestPackageManagerImpl(name="xmake")
        project_root = tmp_path / "project"
        project_root.mkdir()

        # 1. Create plugin
        metadata = plugin.metadata()
        assert metadata["name"] == "xmake-plugin"

        # 2. Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)
        assert plugin.context is context

        # 3. Detect
        (project_root / ".xmake").touch()
        detected = plugin.detect(project_root)
        assert detected

        # 4. Install
        plugin.install_dependencies(project_root)
        assert plugin.installed

        # 5. Generate integration
        toolchain_file = tmp_path / "toolchain.cmake"
        toolchain_file.write_text("")
        plugin.generate_toolchain_integration(toolchain_file, {})
        assert "# xmake integration" in toolchain_file.read_text()

    def test_hunter_like_workflow(self, tmp_path):
        """Test Hunter-like CMake-integrated package manager workflow."""
        plugin = HunterLikePlugin()
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "cmake").mkdir()
        (project_root / "cmake" / "HunterGate.cmake").write_text("# HunterGate")

        # Initialize
        context = type("Context", (), {})()
        plugin.initialize(context)

        # Detect
        assert plugin.detect(project_root)

        # Install (no-op for CMake-integrated)
        plugin.install_dependencies(project_root)

        # Generate integration
        toolchain_file = tmp_path / "toolchain.cmake"
        toolchain_file.write_text("")
        config = {"url": "https://custom.url", "sha1": "custom123"}
        plugin.generate_toolchain_integration(toolchain_file, config)

        content = toolchain_file.read_text()
        assert "Hunter package manager integration" in content
        assert "https://custom.url" in content
        assert "custom123" in content


class TestPackageManagerPluginUseCases:
    """Test real-world package manager plugin use cases."""

    def test_simple_detection_based_pm(self, tmp_path):
        """Test simple package manager with file-based detection."""

        class SimplePM(PackageManagerPlugin):
            def metadata(self):
                return {
                    "name": "simple-pm",
                    "version": "1.0.0",
                    "description": "Simple package manager",
                    "author": "Test",
                }

            def initialize(self, context):
                pass

            def package_manager_name(self):
                return "simple"

            def detect(self, project_root):
                return (project_root / "packages.txt").exists()

            def install_dependencies(self, project_root):
                pass

            def generate_toolchain_integration(self, toolchain_file, config):
                with open(toolchain_file, "a") as f:
                    f.write("set(SIMPLE_PM_ENABLED ON)\n")

        project = tmp_path / "project"
        project.mkdir()
        (project / "packages.txt").write_text("boost\nfmt\n")

        plugin = SimplePM()
        assert plugin.detect(project)
        assert plugin.package_manager_name() == "simple"

    def test_full_featured_pm_workflow(self, tmp_path):
        """Test package manager with all features."""
        plugin = FullFeaturedPM()
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "packages.json").write_text('{"packages": []}')

        # Detect
        assert plugin.detect(project_root)

        # Install
        plugin.install_dependencies(project_root)

        # Get installed packages
        packages = plugin.get_installed_packages(project_root)
        assert len(packages) == 2

        # Update
        plugin.update_dependencies(project_root)

        # Clean cache
        plugin.clean_cache(project_root)


class TestPackageManagerError:
    """Test PackageManagerError exception."""

    def test_package_manager_error_is_toolchainkit_error(self):
        """Test that PackageManagerError extends ToolchainKitError."""
        from toolchainkit.core.exceptions import ToolchainKitError

        assert issubclass(PackageManagerError, ToolchainKitError)

    def test_package_manager_error_creation(self):
        """Test creating PackageManagerError."""
        from toolchainkit.core.exceptions import ToolchainKitError

        error = PackageManagerError("Installation failed")
        assert str(error) == "Installation failed"
        assert isinstance(error, ToolchainKitError)
        assert isinstance(error, Exception)


class TestPackageManagerPluginExportsAPI:
    """Test that PackageManagerPlugin is properly exported."""

    def test_package_manager_plugin_exported(self):
        """Test that PackageManagerPlugin is exported from plugins package."""
        from toolchainkit.plugins import PackageManagerPlugin

        assert PackageManagerPlugin is not None

    def test_package_manager_error_exported(self):
        """Test that PackageManagerError is exported."""
        from toolchainkit.plugins import PackageManagerError

        assert PackageManagerError is not None

    def test_package_manager_plugin_in_all(self):
        """Test that PackageManagerPlugin is in __all__."""
        from toolchainkit import plugins

        assert "PackageManagerPlugin" in plugins.__all__
        assert "PackageManagerError" in plugins.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
