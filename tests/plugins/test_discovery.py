"""
Tests for plugin discovery system.
"""

import os
import pytest
import warnings
from pathlib import Path
from toolchainkit.plugins import PluginDiscoverer


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def plugin_yaml_minimal():
    """Minimal valid plugin.yaml content."""
    return """
name: test-plugin
version: 1.0.0
type: compiler
description: A test plugin
author: Test Author
entry_point: test_module.TestClass
"""


@pytest.fixture
def plugin_yaml_full():
    """Full-featured plugin.yaml content."""
    return """
name: zig-compiler
version: 1.2.3
type: compiler
description: Zig compiler support
author: ToolchainKit Team
entry_point: zig_plugin.ZigCompiler
homepage: https://github.com/example/zig-plugin
license: MIT
requires:
  - base-utils >= 1.0
platforms:
  - linux-x64
  - windows-x64
tags:
  - compiler
  - zig
"""


@pytest.fixture
def plugin_yaml_invalid():
    """Invalid plugin.yaml (missing required fields)."""
    return """
name: invalid-plugin
# Missing version and other required fields
"""


@pytest.fixture
def create_plugin_dir(tmp_path):
    """Factory to create plugin directory structure."""

    def _create(name: str, yaml_content: str):
        plugin_dir = tmp_path / name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = plugin_dir / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        return plugin_dir

    return _create


# ============================================================================
# Test: PluginDiscoverer Initialization
# ============================================================================


class TestPluginDiscovererInit:
    """Test PluginDiscoverer initialization."""

    def test_init_without_project_root(self):
        """Test creating discoverer without project root."""
        discoverer = PluginDiscoverer()
        assert discoverer.project_root is None

    def test_init_with_project_root(self, tmp_path):
        """Test creating discoverer with project root."""
        discoverer = PluginDiscoverer(project_root=tmp_path)
        assert discoverer.project_root == tmp_path


# ============================================================================
# Test: Directory Listing
# ============================================================================


class TestGetPluginDirectories:
    """Test _get_plugin_directories method."""

    def test_get_directories_without_project(self):
        """Test getting directories without project root."""
        discoverer = PluginDiscoverer()
        directories = discoverer._get_plugin_directories()

        # Should have global directory
        assert any(
            ".toolchainkit" in str(d) and "plugins" in str(d) for d in directories
        )

    def test_get_directories_with_project(self, tmp_path):
        """Test getting directories with project root."""
        discoverer = PluginDiscoverer(project_root=tmp_path)
        directories = discoverer._get_plugin_directories()

        # Should have project-local directory
        expected = tmp_path / ".toolchainkit" / "plugins"
        assert expected in directories

    def test_get_directories_includes_global(self):
        """Test that global directory is always included."""
        discoverer = PluginDiscoverer()
        directories = discoverer._get_plugin_directories()

        home = Path.home()
        global_dir = home / ".toolchainkit" / "plugins"
        assert global_dir in directories

    def test_get_directories_from_env_var_unix_separator(self, tmp_path, monkeypatch):
        """Test getting directories from TOOLCHAINKIT_PLUGIN_PATH (Unix)."""
        path1 = tmp_path / "plugins1"
        path2 = tmp_path / "plugins2"
        env_paths = f"{path1}:{path2}"

        # Only test on Unix systems (skip path separator test on Windows)
        if os.name != "nt":
            monkeypatch.setenv("TOOLCHAINKIT_PLUGIN_PATH", env_paths)

            discoverer = PluginDiscoverer()
            directories = discoverer._get_plugin_directories()

            assert path1 in directories
            assert path2 in directories
        else:
            pytest.skip("Unix path separator test only runs on Unix systems")

    def test_get_directories_from_env_var_windows_separator(
        self, tmp_path, monkeypatch
    ):
        """Test getting directories from TOOLCHAINKIT_PLUGIN_PATH (Windows)."""
        path1 = tmp_path / "plugins1"
        path2 = tmp_path / "plugins2"
        env_paths = f"{path1};{path2}"

        # Only test on Windows systems (skip path separator test on Unix)
        if os.name != "nt":
            pytest.skip("Windows path separator test only runs on Windows systems")

        monkeypatch.setenv("TOOLCHAINKIT_PLUGIN_PATH", env_paths)

        discoverer = PluginDiscoverer()
        directories = discoverer._get_plugin_directories()

        assert path1 in directories
        assert path2 in directories

    def test_get_directories_priority_order(self, tmp_path):
        """Test that directories are returned in correct priority order."""
        discoverer = PluginDiscoverer(project_root=tmp_path)
        directories = discoverer._get_plugin_directories()

        # Project-local should come first
        assert directories[0] == tmp_path / ".toolchainkit" / "plugins"


# ============================================================================
# Test: Discover in Single Directory
# ============================================================================


class TestDiscoverInDirectory:
    """Test discover_in_directory method."""

    def test_discover_in_nonexistent_directory(self, tmp_path):
        """Test discovery in non-existent directory."""
        discoverer = PluginDiscoverer()
        nonexistent = tmp_path / "nonexistent"

        plugins = discoverer.discover_in_directory(nonexistent)
        assert plugins == []

    def test_discover_in_empty_directory(self, tmp_path):
        """Test discovery in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        discoverer = PluginDiscoverer()
        plugins = discoverer.discover_in_directory(empty_dir)
        assert plugins == []

    def test_discover_single_plugin(
        self, tmp_path, plugin_yaml_minimal, create_plugin_dir
    ):
        """Test discovering a single plugin."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create plugin
        create_plugin_dir("test-plugin", plugin_yaml_minimal)

        discoverer = PluginDiscoverer()
        # Move plugin to plugins_dir
        (tmp_path / "test-plugin").rename(plugins_dir / "test-plugin")

        plugins = discoverer.discover_in_directory(plugins_dir)

        assert len(plugins) == 1
        assert plugins[0].name == "test-plugin"
        assert plugins[0].version == "1.0.0"

    def test_discover_multiple_plugins(
        self, tmp_path, plugin_yaml_minimal, plugin_yaml_full
    ):
        """Test discovering multiple plugins."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create two plugins
        plugin1_dir = plugins_dir / "plugin1"
        plugin1_dir.mkdir()
        (plugin1_dir / "plugin.yaml").write_text(plugin_yaml_minimal, encoding="utf-8")

        plugin2_dir = plugins_dir / "plugin2"
        plugin2_dir.mkdir()
        (plugin2_dir / "plugin.yaml").write_text(plugin_yaml_full, encoding="utf-8")

        discoverer = PluginDiscoverer()
        plugins = discoverer.discover_in_directory(plugins_dir)

        assert len(plugins) == 2
        names = [p.name for p in plugins]
        assert "test-plugin" in names
        assert "zig-compiler" in names

    def test_discover_skips_files_in_root(self, tmp_path):
        """Test that files in plugin directory root are ignored."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create file (not directory) with plugin.yaml
        (plugins_dir / "plugin.yaml").write_text("name: test", encoding="utf-8")

        discoverer = PluginDiscoverer()
        plugins = discoverer.discover_in_directory(plugins_dir)

        # Should not discover file
        assert len(plugins) == 0

    def test_discover_skips_dirs_without_yaml(self, tmp_path):
        """Test that directories without plugin.yaml are ignored."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create directory without plugin.yaml
        plugin_dir = plugins_dir / "test-plugin"
        plugin_dir.mkdir()

        discoverer = PluginDiscoverer()
        plugins = discoverer.discover_in_directory(plugins_dir)

        # Should not discover directory without yaml
        assert len(plugins) == 0

    def test_discover_handles_invalid_plugin_gracefully(
        self, tmp_path, plugin_yaml_minimal, plugin_yaml_invalid
    ):
        """Test that invalid plugin doesn't stop discovery."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create valid plugin
        valid_dir = plugins_dir / "valid-plugin"
        valid_dir.mkdir()
        (valid_dir / "plugin.yaml").write_text(plugin_yaml_minimal, encoding="utf-8")

        # Create invalid plugin
        invalid_dir = plugins_dir / "invalid-plugin"
        invalid_dir.mkdir()
        (invalid_dir / "plugin.yaml").write_text(plugin_yaml_invalid, encoding="utf-8")

        discoverer = PluginDiscoverer()

        # Should warn about invalid plugin
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            plugins = discoverer.discover_in_directory(plugins_dir)

            # Should have warning
            assert len(w) > 0
            assert "invalid plugin" in str(w[0].message).lower()

        # Should still discover valid plugin
        assert len(plugins) == 1
        assert plugins[0].name == "test-plugin"

    def test_discover_handles_permission_error(self, tmp_path, monkeypatch):
        """Test handling permission errors gracefully."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        discoverer = PluginDiscoverer()

        # Mock iterdir to raise PermissionError
        original_iterdir = Path.iterdir

        def mock_iterdir(self):
            if self == plugins_dir:
                raise PermissionError("Access denied")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        # Should handle gracefully and return empty list
        plugins = discoverer.discover_in_directory(plugins_dir)
        assert plugins == []


# ============================================================================
# Test: Full Discovery
# ============================================================================


class TestDiscover:
    """Test discover method (all locations)."""

    def test_discover_with_no_plugins(self, tmp_path):
        """Test discovery when no plugins exist."""
        discoverer = PluginDiscoverer(project_root=tmp_path)
        plugins = discoverer.discover()

        # May be empty or have system plugins
        assert isinstance(plugins, list)

    def test_discover_from_project_directory(self, tmp_path, plugin_yaml_minimal):
        """Test discovering plugins from project directory."""
        # Create project plugin directory
        project_plugins = tmp_path / ".toolchainkit" / "plugins"
        project_plugins.mkdir(parents=True)

        # Create plugin
        plugin_dir = project_plugins / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(plugin_yaml_minimal, encoding="utf-8")

        discoverer = PluginDiscoverer(project_root=tmp_path)
        plugins = discoverer.discover()

        # Should find project plugin
        names = [p.name for p in plugins]
        assert "test-plugin" in names

    def test_discover_deduplication_project_overrides_global(
        self, tmp_path, plugin_yaml_minimal, plugin_yaml_full, monkeypatch
    ):
        """Test that project plugins override global plugins with same name."""
        # Create global plugins directory
        global_plugins = tmp_path / "global_plugins"
        global_plugins.mkdir()

        # Create global plugin (zig-compiler)
        global_plugin = global_plugins / "zig-compiler"
        global_plugin.mkdir()
        (global_plugin / "plugin.yaml").write_text(plugin_yaml_full, encoding="utf-8")

        # Create project plugins directory
        project_root = tmp_path / "project"
        project_root.mkdir()
        project_plugins = project_root / ".toolchainkit" / "plugins"
        project_plugins.mkdir(parents=True)

        # Create project plugin with same name (zig-compiler) but different version
        project_plugin_yaml = plugin_yaml_full.replace(
            "version: 1.2.3", "version: 2.0.0"
        )
        project_plugin = project_plugins / "zig-compiler"
        project_plugin.mkdir()
        (project_plugin / "plugin.yaml").write_text(
            project_plugin_yaml, encoding="utf-8"
        )

        # Mock global plugins directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake_home")
        fake_global = tmp_path / "fake_home" / ".toolchainkit" / "plugins"
        fake_global.mkdir(parents=True)

        # Copy global plugin to fake global
        import shutil

        shutil.copytree(global_plugin, fake_global / "zig-compiler")

        discoverer = PluginDiscoverer(project_root=project_root)
        plugins = discoverer.discover()

        # Should find only one zig-compiler (project version)
        zig_plugins = [p for p in plugins if p.name == "zig-compiler"]
        assert len(zig_plugins) == 1
        assert zig_plugins[0].version == "2.0.0"  # Project version

    def test_discover_multiple_locations(
        self, tmp_path, plugin_yaml_minimal, plugin_yaml_full, monkeypatch
    ):
        """Test discovering plugins from multiple locations."""
        # Setup fake home
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Create global plugin
        global_plugins = fake_home / ".toolchainkit" / "plugins"
        global_plugins.mkdir(parents=True)
        global_plugin = global_plugins / "global-plugin"
        global_plugin.mkdir()
        (global_plugin / "plugin.yaml").write_text(
            plugin_yaml_minimal, encoding="utf-8"
        )

        # Create project plugin
        project_root = tmp_path / "project"
        project_root.mkdir()
        project_plugins = project_root / ".toolchainkit" / "plugins"
        project_plugins.mkdir(parents=True)
        project_plugin = project_plugins / "project-plugin"
        project_plugin.mkdir()
        (project_plugin / "plugin.yaml").write_text(plugin_yaml_full, encoding="utf-8")

        discoverer = PluginDiscoverer(project_root=project_root)
        plugins = discoverer.discover()

        # Should find both plugins
        names = [p.name for p in plugins]
        assert "test-plugin" in names
        assert "zig-compiler" in names


# ============================================================================
# Test: Module Exports
# ============================================================================


class TestDiscoveryModuleExports:
    """Test module exports correct API."""

    def test_plugin_discoverer_exported(self):
        """Test PluginDiscoverer is exported."""
        from toolchainkit.plugins.discovery import PluginDiscoverer as DirectImport
        from toolchainkit.plugins import PluginDiscoverer as PackageImport

        assert DirectImport is PackageImport


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
