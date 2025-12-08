"""
Tests for plugin metadata parser and validation.
"""

import pytest
from pathlib import Path
from toolchainkit.plugins import (
    PluginMetadata,
    PluginMetadataParser,
    PluginValidationError,
)


# ============================================================================
# Test: PluginMetadata Class
# ============================================================================


class TestPluginMetadata:
    """Test PluginMetadata dataclass functionality."""

    def test_minimal_metadata(self):
        """Test creating metadata with only required fields."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            type="compiler",
            description="A test plugin",
            author="Test Author",
            entry_point="test_module.TestClass",
        )

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.type == "compiler"
        assert metadata.description == "A test plugin"
        assert metadata.author == "Test Author"
        assert metadata.entry_point == "test_module.TestClass"

        # Optional fields should have defaults
        assert metadata.homepage is None
        assert metadata.license is None
        assert metadata.requires == []
        assert metadata.platforms == []
        assert metadata.tags == []
        assert metadata.permissions == []
        assert metadata.plugin_dir is None

    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = PluginMetadata(
            name="zig-compiler",
            version="1.2.3",
            type="compiler",
            description="Zig compiler support",
            author="ToolchainKit Team",
            entry_point="zig_plugin.ZigCompiler",
            homepage="https://github.com/example/zig-plugin",
            license="MIT",
            requires=["base-utils >= 1.0"],
            min_toolchainkit_version="1.0.0",
            max_toolchainkit_version="2.0.0",
            platforms=["linux-x64", "windows-x64"],
            tags=["compiler", "zig"],
            permissions=["filesystem", "network"],
            plugin_dir=Path("/path/to/plugin"),
        )

        assert metadata.name == "zig-compiler"
        assert metadata.homepage == "https://github.com/example/zig-plugin"
        assert metadata.license == "MIT"
        assert metadata.requires == ["base-utils >= 1.0"]
        assert metadata.min_toolchainkit_version == "1.0.0"
        assert metadata.max_toolchainkit_version == "2.0.0"
        assert metadata.platforms == ["linux-x64", "windows-x64"]
        assert metadata.tags == ["compiler", "zig"]
        assert metadata.permissions == ["filesystem", "network"]
        assert metadata.plugin_dir == Path("/path/to/plugin")

    def test_is_compatible_with_toolchainkit_no_constraints(self):
        """Test version compatibility with no version constraints."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
        )

        # No constraints = compatible with any version
        assert metadata.is_compatible_with_toolchainkit("0.5.0")
        assert metadata.is_compatible_with_toolchainkit("1.0.0")
        assert metadata.is_compatible_with_toolchainkit("2.0.0")

    def test_is_compatible_with_toolchainkit_min_version(self):
        """Test version compatibility with min version constraint."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
            min_toolchainkit_version="1.0.0",
        )

        assert not metadata.is_compatible_with_toolchainkit("0.9.0")
        assert metadata.is_compatible_with_toolchainkit("1.0.0")
        assert metadata.is_compatible_with_toolchainkit("1.5.0")
        assert metadata.is_compatible_with_toolchainkit("2.0.0")

    def test_is_compatible_with_toolchainkit_max_version(self):
        """Test version compatibility with max version constraint."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
            max_toolchainkit_version="2.0.0",
        )

        assert metadata.is_compatible_with_toolchainkit("0.5.0")
        assert metadata.is_compatible_with_toolchainkit("1.0.0")
        assert metadata.is_compatible_with_toolchainkit("1.9.0")
        assert not metadata.is_compatible_with_toolchainkit("2.0.0")
        assert not metadata.is_compatible_with_toolchainkit("2.5.0")

    def test_is_compatible_with_toolchainkit_both_constraints(self):
        """Test version compatibility with min and max constraints."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
            min_toolchainkit_version="1.0.0",
            max_toolchainkit_version="2.0.0",
        )

        assert not metadata.is_compatible_with_toolchainkit("0.9.0")
        assert metadata.is_compatible_with_toolchainkit("1.0.0")
        assert metadata.is_compatible_with_toolchainkit("1.5.0")
        assert not metadata.is_compatible_with_toolchainkit("2.0.0")

    def test_is_compatible_with_toolchainkit_invalid_version(self):
        """Test version compatibility with invalid version string."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
            min_toolchainkit_version="1.0.0",
        )

        # Invalid version should return False
        assert not metadata.is_compatible_with_toolchainkit("invalid")

    def test_is_compatible_with_platform_all_platforms(self):
        """Test platform compatibility with empty platforms list."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
        )

        # Empty platforms = all platforms supported
        assert metadata.is_compatible_with_platform("linux-x64")
        assert metadata.is_compatible_with_platform("windows-x64")
        assert metadata.is_compatible_with_platform("macos-arm64")

    def test_is_compatible_with_platform_specific_platforms(self):
        """Test platform compatibility with specific platforms."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="test.Test",
            platforms=["linux-x64", "windows-x64"],
        )

        assert metadata.is_compatible_with_platform("linux-x64")
        assert metadata.is_compatible_with_platform("windows-x64")
        assert not metadata.is_compatible_with_platform("macos-arm64")

    def test_get_module_name(self):
        """Test extracting module name from entry_point."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="zig_plugin.ZigCompiler",
        )

        assert metadata.get_module_name() == "zig_plugin"

    def test_get_module_name_nested(self):
        """Test extracting module name from nested entry_point."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="my_plugins.compilers.ZigCompiler",
        )

        assert metadata.get_module_name() == "my_plugins.compilers"

    def test_get_class_name(self):
        """Test extracting class name from entry_point."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="zig_plugin.ZigCompiler",
        )

        assert metadata.get_class_name() == "ZigCompiler"

    def test_get_class_name_nested(self):
        """Test extracting class name from nested entry_point."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="compiler",
            description="Test",
            author="Test",
            entry_point="my_plugins.compilers.ZigCompiler",
        )

        assert metadata.get_class_name() == "ZigCompiler"


# ============================================================================
# Test: PluginMetadataParser - Valid Files
# ============================================================================


class TestPluginMetadataParserValid:
    """Test parsing valid plugin.yaml files."""

    def test_parse_minimal_valid_yaml(self, tmp_path):
        """Test parsing minimal valid plugin.yaml."""
        yaml_content = """
name: test-plugin
version: 1.0.0
type: compiler
description: A test plugin
author: Test Author
entry_point: test_module.TestClass
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.type == "compiler"
        assert metadata.description == "A test plugin"
        assert metadata.author == "Test Author"
        assert metadata.entry_point == "test_module.TestClass"
        assert metadata.plugin_dir == tmp_path

    def test_parse_full_valid_yaml(self, tmp_path):
        """Test parsing full valid plugin.yaml."""
        yaml_content = """
name: zig-compiler
version: 1.2.3
type: compiler
description: Zig compiler support for ToolchainKit
author: ToolchainKit Team
entry_point: zig_plugin.ZigCompiler
homepage: https://github.com/example/zig-plugin
license: MIT
requires:
  - base-utils >= 1.0
  - compiler-helpers ~> 2.0
min_toolchainkit_version: 1.0.0
max_toolchainkit_version: 2.0.0
platforms:
  - linux-x64
  - windows-x64
  - macos-arm64
tags:
  - compiler
  - zig
  - cross-platform
permissions:
  - filesystem
  - network
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.name == "zig-compiler"
        assert metadata.version == "1.2.3"
        assert metadata.homepage == "https://github.com/example/zig-plugin"
        assert metadata.license == "MIT"
        assert metadata.requires == ["base-utils >= 1.0", "compiler-helpers ~> 2.0"]
        assert metadata.min_toolchainkit_version == "1.0.0"
        assert metadata.max_toolchainkit_version == "2.0.0"
        assert metadata.platforms == ["linux-x64", "windows-x64", "macos-arm64"]
        assert metadata.tags == ["compiler", "zig", "cross-platform"]
        assert metadata.permissions == ["filesystem", "network"]

    def test_parse_package_manager_type(self, tmp_path):
        """Test parsing package_manager type."""
        yaml_content = """
name: hunter-package-manager
version: 1.0.0
type: package_manager
description: Hunter package manager integration
author: Test Author
entry_point: hunter_plugin.HunterPackageManager
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.type == "package_manager"

    def test_parse_backend_type(self, tmp_path):
        """Test parsing backend type."""
        yaml_content = """
name: meson-backend
version: 1.0.0
type: backend
description: Meson build backend
author: Test Author
entry_point: meson_plugin.MesonBackend
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.type == "backend"


# ============================================================================
# Test: PluginMetadataParser - Invalid Files
# ============================================================================


class TestPluginMetadataParserInvalid:
    """Test parsing invalid plugin.yaml files."""

    def test_parse_file_not_found(self, tmp_path):
        """Test parsing non-existent file."""
        yaml_file = tmp_path / "nonexistent.yaml"

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "File not found" in str(exc_info.value)

    def test_parse_invalid_yaml_syntax(self, tmp_path):
        """Test parsing file with invalid YAML syntax."""
        yaml_content = """
name: test
version: 1.0.0
invalid yaml syntax: [unclosed bracket
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_parse_non_dict_root(self, tmp_path):
        """Test parsing file with non-dictionary root."""
        yaml_content = """
- item1
- item2
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Root element must be a dictionary" in str(exc_info.value)

    def test_parse_missing_required_field(self, tmp_path):
        """Test parsing file with missing required field."""
        yaml_content = """
name: test-plugin
version: 1.0.0
# Missing type, description, author, entry_point
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        error_msg = str(exc_info.value)
        assert "Missing required field: type" in error_msg
        assert "Missing required field: description" in error_msg
        assert "Missing required field: author" in error_msg
        assert "Missing required field: entry_point" in error_msg

    def test_parse_invalid_type(self, tmp_path):
        """Test parsing file with invalid plugin type."""
        yaml_content = """
name: test-plugin
version: 1.0.0
type: invalid_type
description: Test
author: Test Author
entry_point: test.Test
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Invalid type 'invalid_type'" in str(exc_info.value)

    def test_parse_invalid_version(self, tmp_path):
        """Test parsing file with invalid semantic version."""
        yaml_content = """
name: test-plugin
version: not-a-version
type: compiler
description: Test
author: Test Author
entry_point: test.Test
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Invalid semantic version" in str(exc_info.value)

    def test_parse_invalid_entry_point(self, tmp_path):
        """Test parsing file with invalid entry_point format."""
        yaml_content = """
name: test-plugin
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: InvalidNoModule
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "must be in format 'module.ClassName'" in str(exc_info.value)

    def test_parse_wrong_field_type_name(self, tmp_path):
        """Test parsing file with wrong type for name field."""
        yaml_content = """
name: 123
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Field 'name' must be a string" in str(exc_info.value)

    def test_parse_empty_name(self, tmp_path):
        """Test parsing file with empty name field."""
        yaml_content = """
name: ""
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Field 'name' cannot be empty" in str(exc_info.value)

    def test_parse_wrong_type_for_list_field(self, tmp_path):
        """Test parsing file with wrong type for list field."""
        yaml_content = """
name: test
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
requires: not-a-list
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "Field 'requires' must be a list" in str(exc_info.value)

    def test_parse_non_string_items_in_list(self, tmp_path):
        """Test parsing file with non-string items in list."""
        yaml_content = """
name: test
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
tags:
  - valid-tag
  - 123
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        with pytest.raises(PluginValidationError) as exc_info:
            parser.parse_file(yaml_file)

        assert "All items in 'tags' must be strings" in str(exc_info.value)


# ============================================================================
# Test: PluginMetadataParser - Edge Cases
# ============================================================================


class TestPluginMetadataParserEdgeCases:
    """Test edge cases in metadata parsing."""

    def test_parse_empty_optional_lists(self, tmp_path):
        """Test parsing with explicitly empty optional lists."""
        yaml_content = """
name: test
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
requires: []
platforms: []
tags: []
permissions: []
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.requires == []
        assert metadata.platforms == []
        assert metadata.tags == []
        assert metadata.permissions == []

    def test_parse_null_optional_fields(self, tmp_path):
        """Test parsing with null optional fields."""
        yaml_content = """
name: test
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
homepage: null
license: null
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        metadata = parser.parse_file(yaml_file)

        assert metadata.homepage is None
        assert metadata.license is None

    def test_parse_with_extra_fields(self, tmp_path):
        """Test parsing with extra unknown fields (should be ignored)."""
        yaml_content = """
name: test
version: 1.0.0
type: compiler
description: Test
author: Test Author
entry_point: test.Test
unknown_field: some_value
another_unknown: 123
"""
        yaml_file = tmp_path / "plugin.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = PluginMetadataParser()
        # Should succeed - unknown fields are ignored
        metadata = parser.parse_file(yaml_file)

        assert metadata.name == "test"


# ============================================================================
# Test: PluginMetadataParser API
# ============================================================================


class TestPluginMetadataParserAPI:
    """Test PluginMetadataParser class API."""

    def test_parser_can_be_instantiated(self):
        """Test creating parser instance."""
        parser = PluginMetadataParser()
        assert isinstance(parser, PluginMetadataParser)

    def test_parser_has_required_fields_constant(self):
        """Test parser has REQUIRED_FIELDS constant."""
        assert hasattr(PluginMetadataParser, "REQUIRED_FIELDS")
        assert isinstance(PluginMetadataParser.REQUIRED_FIELDS, list)
        assert "name" in PluginMetadataParser.REQUIRED_FIELDS
        assert "version" in PluginMetadataParser.REQUIRED_FIELDS

    def test_parser_has_valid_types_constant(self):
        """Test parser has VALID_TYPES constant."""
        assert hasattr(PluginMetadataParser, "VALID_TYPES")
        assert isinstance(PluginMetadataParser.VALID_TYPES, list)
        assert "compiler" in PluginMetadataParser.VALID_TYPES
        assert "package_manager" in PluginMetadataParser.VALID_TYPES
        assert "backend" in PluginMetadataParser.VALID_TYPES


# ============================================================================
# Test: Module Exports
# ============================================================================


class TestMetadataModuleExports:
    """Test module exports correct API."""

    def test_plugin_metadata_exported(self):
        """Test PluginMetadata is exported."""
        from toolchainkit.plugins.metadata import PluginMetadata as DirectImport
        from toolchainkit.plugins import PluginMetadata as PackageImport

        assert DirectImport is PackageImport

    def test_plugin_metadata_parser_exported(self):
        """Test PluginMetadataParser is exported."""
        from toolchainkit.plugins.metadata import PluginMetadataParser as DirectImport
        from toolchainkit.plugins import PluginMetadataParser as PackageImport

        assert DirectImport is PackageImport


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
