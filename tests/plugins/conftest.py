"""
Pytest configuration and fixtures for plugin tests.
"""

import pytest
from pathlib import Path
from typing import Any


@pytest.fixture
def mock_plugin_context():
    """Create a mock PluginContext for testing."""

    class MockPluginContext:
        def __init__(self):
            self.registered_compilers = {}
            self.registered_package_managers = {}
            self.registered_backends = {}
            self.cache_dir = Path("/tmp/test-cache")

        def register_compiler(self, name: str, config: Any):
            """Mock compiler registration."""
            self.registered_compilers[name] = config

        def register_package_manager(self, name: str, manager: Any):
            """Mock package manager registration."""
            self.registered_package_managers[name] = manager

        def register_backend(self, name: str, backend: Any):
            """Mock backend registration."""
            self.registered_backends[name] = backend

    return MockPluginContext()


@pytest.fixture
def sample_plugin_metadata():
    """Sample plugin metadata for testing."""
    return {
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "Test plugin for unit tests",
        "author": "Test Author",
        "homepage": "https://example.com/test-plugin",
        "license": "MIT",
        "requires": ["base-plugin >= 1.0.0"],
        "tags": ["test", "example", "unit-test"],
    }


@pytest.fixture
def plugin_directory(tmp_path):
    """Create a temporary plugin directory structure."""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()

    # Create plugin.yaml
    plugin_yaml = plugin_dir / "plugin.yaml"
    plugin_yaml.write_text(
        """
name: test-plugin
version: 1.0.0
description: Test plugin
author: Test Author
type: compiler
entry_point: test_plugin.TestPlugin
"""
    )

    # Create plugin module
    plugin_py = plugin_dir / "test_plugin.py"
    plugin_py.write_text(
        """
from toolchainkit.plugins import Plugin

class TestPlugin(Plugin):
    def metadata(self):
        return {
            'name': 'test-plugin',
            'version': '1.0.0',
            'description': 'Test plugin',
            'author': 'Test Author'
        }

    def initialize(self, context):
        pass
"""
    )

    return plugin_dir
