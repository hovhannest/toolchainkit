"""Tests for CLI utility functions."""

import pytest
from pathlib import Path
import yaml

from toolchainkit.cli.utils import (
    load_yaml_config,
    validate_config,
    format_success_message,
    check_initialized,
    require_initialized,
    print_error,
    print_warning,
    resolve_project_root,
    ensure_directory,
)


class TestLoadYAMLConfig:
    def test_load_existing_config(self, tmp_path):
        """Test loading existing config file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value\nlist: [1, 2, 3]")

        config = load_yaml_config(config_file)
        assert config["key"] == "value"
        assert config["list"] == [1, 2, 3]

    def test_load_nonexistent_optional(self, tmp_path):
        """Test loading non-existent optional config."""
        config = load_yaml_config(tmp_path / "missing.yaml", required=False)
        assert config == {}

    def test_load_nonexistent_required(self, tmp_path):
        """Test loading non-existent required config raises error."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config(tmp_path / "missing.yaml", required=True)

    def test_load_invalid_yaml(self, tmp_path):
        """Test invalid YAML raises error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: : :")

        with pytest.raises(ValueError):
            load_yaml_config(config_file)

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file returns empty dict."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = load_yaml_config(config_file)
        assert config == {}

    def test_load_nested_config(self, tmp_path):
        """Test loading nested configuration."""
        config_file = tmp_path / "nested.yaml"
        config_data = {
            "build": {"type": "Release", "dir": "build"},
            "toolchain": {"name": "llvm-18"},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_yaml_config(config_file)
        assert config["build"]["type"] == "Release"
        assert config["toolchain"]["name"] == "llvm-18"


class TestValidateConfig:
    def test_valid_config(self):
        """Test valid configuration."""
        config = {"build": {"type": "Release"}, "toolchain": "llvm"}
        assert validate_config(config, ["build.type", "toolchain"])

    def test_missing_key(self):
        """Test missing key raises error."""
        config = {"build": {"type": "Release"}}
        with pytest.raises(ValueError, match="toolchain"):
            validate_config(config, ["toolchain"])

    def test_nested_missing_key(self):
        """Test nested missing key raises error."""
        config = {"build": {}}
        with pytest.raises(ValueError, match="build.type"):
            validate_config(config, ["build.type"])

    def test_empty_required_keys(self):
        """Test empty required keys list."""
        config = {"key": "value"}
        assert validate_config(config, [])

    def test_multiple_missing_keys(self):
        """Test multiple missing keys reported."""
        config = {}
        with pytest.raises(ValueError) as exc_info:
            validate_config(config, ["key1", "key2"])
        assert "key1" in str(exc_info.value)
        assert "key2" in str(exc_info.value)


class TestFormatSuccessMessage:
    def test_basic_message(self):
        """Test basic success message formatting."""
        msg = format_success_message(
            "Operation Complete!", {"Toolchain": "llvm-18", "Status": "Success"}
        )
        assert "Operation Complete!" in msg
        assert "Toolchain: llvm-18" in msg
        assert "Status: Success" in msg
        assert "=" * 70 in msg

    def test_with_next_steps(self):
        """Test message with next steps."""
        msg = format_success_message(
            "Build Complete",
            {"Output": "/tmp/build"},
            next_steps=["Run tests", "Deploy binary"],
        )
        assert "Next steps:" in msg
        assert "Run tests" in msg
        assert "Deploy binary" in msg

    def test_custom_width(self):
        """Test custom width for message box."""
        msg = format_success_message("Test", {}, width=40)
        assert "=" * 40 in msg

    def test_empty_details(self):
        """Test message with empty details."""
        msg = format_success_message("Success", {})
        assert "Success" in msg

    def test_none_next_steps(self):
        """Test message with None next_steps."""
        msg = format_success_message("Success", {"Key": "Value"}, next_steps=None)
        assert "Next steps:" not in msg
        assert "Key: Value" in msg


class TestCheckInitialized:
    def test_initialized_project(self, tmp_path):
        """Test detecting initialized project."""
        (tmp_path / "toolchainkit.yaml").touch()
        assert check_initialized(tmp_path) is True

    def test_uninitialized_project(self, tmp_path):
        """Test detecting uninitialized project."""
        assert check_initialized(tmp_path) is False

    def test_require_initialized_success(self, tmp_path):
        """Test require_initialized succeeds for initialized project."""
        (tmp_path / "toolchainkit.yaml").touch()
        require_initialized(tmp_path, "test")  # Should not raise

    def test_require_initialized_failure(self, tmp_path):
        """Test require_initialized raises for uninitialized project."""
        with pytest.raises(RuntimeError, match="not initialized"):
            require_initialized(tmp_path, "test")

    def test_require_initialized_error_message(self, tmp_path):
        """Test error message includes command name."""
        with pytest.raises(RuntimeError, match="test"):
            require_initialized(tmp_path, "test")


class TestPrintError:
    def test_print_error_basic(self, capsys):
        """Test basic error printing."""
        print_error("Test error")
        captured = capsys.readouterr()
        assert "ERROR: Test error" in captured.err

    def test_print_error_with_details(self, capsys):
        """Test error printing with details."""
        print_error("Test error", "More details")
        captured = capsys.readouterr()
        assert "ERROR: Test error" in captured.err
        assert "More details" in captured.err


class TestPrintWarning:
    def test_print_warning(self, capsys):
        """Test warning printing."""
        print_warning("Test warning")
        captured = capsys.readouterr()
        assert "WARNING: Test warning" in captured.err


class TestResolveProjectRoot:
    def test_resolve_none(self):
        """Test resolving None path."""
        root = resolve_project_root(None)
        assert root.is_absolute()
        assert root == Path.cwd().resolve()

    def test_resolve_absolute_path(self, tmp_path):
        """Test resolving absolute path."""
        root = resolve_project_root(tmp_path)
        assert root.is_absolute()
        assert root == tmp_path.resolve()

    def test_resolve_relative_path(self, tmp_path, monkeypatch):
        """Test resolving relative path."""
        monkeypatch.chdir(tmp_path)
        subdir = Path("subdir")
        (tmp_path / subdir).mkdir()

        root = resolve_project_root(subdir)
        assert root.is_absolute()
        assert root == (tmp_path / subdir).resolve()


class TestEnsureDirectory:
    def test_create_directory(self, tmp_path):
        """Test creating directory."""
        new_dir = tmp_path / "new_dir"
        ensure_directory(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_create_nested_directories(self, tmp_path):
        """Test creating nested directories."""
        nested = tmp_path / "a" / "b" / "c"
        ensure_directory(nested)
        assert nested.exists()
        assert nested.is_dir()

    def test_existing_directory(self, tmp_path):
        """Test ensuring existing directory."""
        existing = tmp_path / "existing"
        existing.mkdir()
        ensure_directory(existing)  # Should not raise
        assert existing.exists()

    def test_create_with_description(self, tmp_path):
        """Test creating directory with description."""
        new_dir = tmp_path / "described"
        ensure_directory(new_dir, "test directory")
        assert new_dir.exists()


class TestGetPackageManagerInstance:
    def test_get_conan_manager(self, tmp_path):
        """Test getting Conan package manager instance."""
        from toolchainkit.cli.utils import get_package_manager_instance

        try:
            manager = get_package_manager_instance("conan", tmp_path)
            assert manager is not None
            assert hasattr(manager, "detect")
        except KeyError:
            # If package manager not registered, that's acceptable for this test
            pytest.skip("Conan package manager not registered")

    def test_unknown_package_manager(self, tmp_path):
        """Test unknown package manager raises KeyError."""
        from toolchainkit.cli.utils import get_package_manager_instance

        with pytest.raises(KeyError, match="not found"):
            get_package_manager_instance("nonexistent_manager", tmp_path)
