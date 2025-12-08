"""
Tests for Zig Compiler Plugin

Test coverage for the Zig compiler plugin implementation.
"""

import sys
from pathlib import Path

# Add plugin directory to path for importing
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

from unittest.mock import Mock, patch  # noqa: E402
import pytest  # noqa: E402
from zig_plugin import ZigCompilerPlugin  # noqa: E402


class TestZigPluginCreation:
    """Test plugin creation and basic properties."""

    def test_plugin_creation(self):
        """Plugin can be instantiated."""
        plugin = ZigCompilerPlugin()
        assert plugin is not None
        assert plugin.context is None
        assert plugin._config is None

    def test_plugin_metadata(self):
        """Plugin returns correct metadata."""
        plugin = ZigCompilerPlugin()
        metadata = plugin.metadata()

        assert metadata["name"] == "zig-compiler"
        assert metadata["version"] == "1.0.0"
        assert metadata["type"] == "compiler"
        assert "Zig compiler" in metadata["description"]
        assert metadata["author"] == "ToolchainKit Community"
        assert metadata["license"] == "MIT"

    def test_compiler_name(self):
        """Plugin returns correct compiler name."""
        plugin = ZigCompilerPlugin()
        assert plugin.compiler_name() == "zig"

    def test_supported_platforms(self):
        """Plugin returns supported platforms."""
        plugin = ZigCompilerPlugin()
        platforms = plugin.supported_platforms()

        assert "linux-x64" in platforms
        assert "linux-arm64" in platforms
        assert "windows-x64" in platforms
        assert "macos-x64" in platforms
        assert "macos-arm64" in platforms
        assert len(platforms) == 5


class TestZigPluginInitialization:
    """Test plugin initialization."""

    def test_initialize_loads_config(self):
        """initialize() loads compiler configuration from YAML."""
        plugin = ZigCompilerPlugin()

        # Mock context
        mock_context = Mock()
        mock_config = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config

        # Initialize plugin
        plugin.initialize(mock_context)

        # Verify context stored
        assert plugin.context is mock_context

        # Verify config loaded
        assert plugin._config is mock_config

        # Verify load_yaml_compiler called with correct path
        mock_context.load_yaml_compiler.assert_called_once()
        call_args = mock_context.load_yaml_compiler.call_args[0]
        yaml_path = call_args[0]
        assert yaml_path.name == "zig.yaml"
        assert "compilers" in str(yaml_path)

        # Verify compiler registered
        mock_context.register_compiler.assert_called_once_with("zig", mock_config)

    def test_initialize_registers_compiler(self):
        """initialize() registers compiler with context."""
        plugin = ZigCompilerPlugin()

        mock_context = Mock()
        mock_config = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config

        plugin.initialize(mock_context)

        # Verify register_compiler called with name and config
        mock_context.register_compiler.assert_called_once_with("zig", mock_config)

    def test_initialize_missing_yaml_raises_error(self):
        """initialize() raises error if zig.yaml not found."""
        plugin = ZigCompilerPlugin()

        # Mock context to simulate missing file
        mock_context = Mock()
        mock_context.load_yaml_compiler.side_effect = FileNotFoundError(
            "zig.yaml not found"
        )

        # Should raise error
        with pytest.raises(FileNotFoundError):
            plugin.initialize(mock_context)

    def test_initialize_with_logger(self):
        """initialize() logs success message if logger available."""
        plugin = ZigCompilerPlugin()

        mock_context = Mock()
        mock_config = Mock()
        mock_logger = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config
        mock_context.logger = mock_logger

        plugin.initialize(mock_context)

        # Verify logger called
        mock_logger.info.assert_called_once()
        assert "Zig compiler registered" in str(mock_logger.info.call_args)


class TestZigPluginCompilerConfig:
    """Test compiler config retrieval."""

    def test_compiler_config_returns_loaded_config(self):
        """compiler_config() returns config loaded during initialize()."""
        plugin = ZigCompilerPlugin()

        # Initialize with mock context
        mock_context = Mock()
        mock_config = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config

        plugin.initialize(mock_context)

        # Get compiler config
        config = plugin.compiler_config()
        assert config is mock_config

    def test_compiler_config_before_initialize_raises_error(self):
        """compiler_config() raises error if plugin not initialized."""
        plugin = ZigCompilerPlugin()

        with pytest.raises(RuntimeError) as exc_info:
            plugin.compiler_config()

        assert "not initialized" in str(exc_info.value).lower()


class TestZigPluginCleanup:
    """Test plugin cleanup."""

    def test_cleanup_clears_state(self):
        """cleanup() clears plugin state."""
        plugin = ZigCompilerPlugin()

        # Initialize
        mock_context = Mock()
        mock_config = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config
        plugin.initialize(mock_context)

        assert plugin.context is not None
        assert plugin._config is not None

        # Cleanup
        plugin.cleanup()

        assert plugin.context is None
        assert plugin._config is None


class TestZigPluginDetection:
    """Test system installation detection."""

    @patch("shutil.which")
    def test_detect_system_installation_finds_zig_in_path(self, mock_which):
        """detect_system_installation() finds Zig in PATH."""
        plugin = ZigCompilerPlugin()

        # Mock 'which' to return Zig path
        mock_which.return_value = "/usr/local/zig/zig"

        result = plugin.detect_system_installation()

        assert result is not None
        # Use string comparison to avoid Path resolution issues on Windows
        assert str(result).replace("\\", "/").endswith("usr/local/zig")
        mock_which.assert_called_once_with("zig")

    @patch("shutil.which")
    def test_detect_system_installation_not_found(self, mock_which):
        """detect_system_installation() returns None if Zig not found."""
        plugin = ZigCompilerPlugin()

        # Mock 'which' to return None
        mock_which.return_value = None

        # Mock Path.exists to return False for all common paths
        with patch.object(Path, "exists", return_value=False):
            result = plugin.detect_system_installation()

        assert result is None

    @patch("shutil.which")
    def test_detect_system_installation_checks_common_paths(self, mock_which):
        """detect_system_installation() checks common installation paths."""
        plugin = ZigCompilerPlugin()

        # Mock 'which' to return None
        mock_which.return_value = None

        # Mock one of the common paths to exist
        def mock_exists(self):
            # Normalize path for comparison (handle Windows paths)
            path_str = str(self).replace("\\", "/")
            return path_str.endswith("/usr/local/zig/zig") or path_str.endswith(
                "/usr/local/zig/zig.exe"
            )

        with patch.object(Path, "exists", mock_exists):
            result = plugin.detect_system_installation()

        assert result is not None
        assert str(result).replace("\\", "/").endswith("usr/local/zig")


class TestZigPluginVersionDetection:
    """Test version detection."""

    @patch("subprocess.run")
    def test_get_version_returns_version_string(self, mock_run):
        """get_version() extracts version from Zig installation."""
        plugin = ZigCompilerPlugin()

        # Mock subprocess to return version
        mock_result = Mock()
        mock_result.stdout = "0.11.0\n"
        mock_run.return_value = mock_result

        # Create mock Zig path
        zig_path = Path("/usr/local/zig")

        # Mock Path.exists to return True for zig executable
        with patch.object(Path, "exists", return_value=True):
            version = plugin.get_version(zig_path)

        assert version == "0.11.0"

        # Verify subprocess called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "version" in call_args[0][0]

    @patch("subprocess.run")
    def test_get_version_zig_not_found_raises_error(self, mock_run):
        """get_version() raises error if Zig executable not found."""
        plugin = ZigCompilerPlugin()

        zig_path = Path("/nonexistent/zig")

        # Mock Path.exists to return False
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                plugin.get_version(zig_path)

        assert "not found" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_version_subprocess_error_raises_error(self, mock_run):
        """get_version() raises error if subprocess fails."""
        plugin = ZigCompilerPlugin()

        # Mock subprocess to raise error
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "zig", stderr="error")

        zig_path = Path("/usr/local/zig")

        with patch.object(Path, "exists", return_value=True):
            with pytest.raises(RuntimeError) as exc_info:
                plugin.get_version(zig_path)

        assert "failed" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_version_timeout_raises_error(self, mock_run):
        """get_version() raises error on timeout."""
        plugin = ZigCompilerPlugin()

        # Mock subprocess to timeout
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("zig version", 5)

        zig_path = Path("/usr/local/zig")

        with patch.object(Path, "exists", return_value=True):
            with pytest.raises(RuntimeError) as exc_info:
                plugin.get_version(zig_path)

        assert "timeout" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_get_version_empty_output_raises_error(self, mock_run):
        """get_version() raises error if version output is empty."""
        plugin = ZigCompilerPlugin()

        # Mock subprocess to return empty output
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        zig_path = Path("/usr/local/zig")

        with patch.object(Path, "exists", return_value=True):
            with pytest.raises(RuntimeError) as exc_info:
                plugin.get_version(zig_path)

        assert "empty" in str(exc_info.value).lower()


class TestZigPluginModuleExports:
    """Test module exports."""

    def test_module_exports_plugin_class(self):
        """Module exports ZigCompilerPlugin in __all__."""
        import zig_plugin

        assert hasattr(zig_plugin, "__all__")
        assert "ZigCompilerPlugin" in zig_plugin.__all__


class TestZigPluginIntegration:
    """Integration tests for Zig plugin."""

    def test_plugin_workflow(self):
        """Test complete plugin workflow: create → initialize → use → cleanup."""
        plugin = ZigCompilerPlugin()

        # 1. Check metadata
        metadata = plugin.metadata()
        assert metadata["name"] == "zig-compiler"

        # 2. Initialize
        mock_context = Mock()
        mock_config = Mock()
        mock_context.load_yaml_compiler.return_value = mock_config

        plugin.initialize(mock_context)

        # 3. Verify registered
        mock_context.register_compiler.assert_called_once_with("zig", mock_config)

        # 4. Get compiler info
        assert plugin.compiler_name() == "zig"
        assert plugin.compiler_config() is mock_config
        assert len(plugin.supported_platforms()) == 5

        # 5. Cleanup
        plugin.cleanup()
        assert plugin.context is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
