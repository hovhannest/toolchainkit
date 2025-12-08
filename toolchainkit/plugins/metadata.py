"""
Plugin metadata parser and validation.

This module handles parsing and validating plugin.yaml files according to the
plugin metadata schema.
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from toolchainkit.plugins import PluginValidationError


@dataclass
class PluginMetadata:
    """
    Parsed and validated plugin metadata from plugin.yaml.

    This class represents the metadata for a plugin after parsing and
    validation. It contains all required and optional fields from the
    plugin.yaml file.
    """

    # Required fields
    name: str
    version: str
    type: str  # 'compiler', 'package_manager', 'backend'
    description: str
    author: str
    entry_point: str

    # Optional fields
    homepage: Optional[str] = None
    license: Optional[str] = None
    requires: List[str] = field(default_factory=list)
    min_toolchainkit_version: Optional[str] = None
    max_toolchainkit_version: Optional[str] = None
    platforms: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

    # Set by parser
    plugin_dir: Optional[Path] = None

    def is_compatible_with_toolchainkit(self, tk_version: str) -> bool:
        """
        Check if plugin is compatible with ToolchainKit version.

        Args:
            tk_version: ToolchainKit version string (semantic version)

        Returns:
            True if compatible, False otherwise

        Example:
            >>> metadata.is_compatible_with_toolchainkit("1.5.0")
            True
        """
        try:
            from packaging import version

            tk_ver = version.parse(tk_version)

            if self.min_toolchainkit_version:
                if tk_ver < version.parse(self.min_toolchainkit_version):
                    return False

            if self.max_toolchainkit_version:
                if tk_ver >= version.parse(self.max_toolchainkit_version):
                    return False

            return True
        except Exception:
            return False

    def is_compatible_with_platform(self, platform_str: str) -> bool:
        """
        Check if plugin supports given platform.

        Args:
            platform_str: Platform string (e.g., "linux-x64", "windows-x64")

        Returns:
            True if supported, False otherwise
            Note: Empty platforms list means all platforms supported

        Example:
            >>> metadata.is_compatible_with_platform("linux-x64")
            True
        """
        if not self.platforms:  # Empty means all platforms
            return True
        return platform_str in self.platforms

    def get_module_name(self) -> str:
        """
        Extract module name from entry_point.

        Returns:
            Module name (e.g., "zig_plugin" from "zig_plugin.ZigCompiler")

        Example:
            >>> metadata.get_module_name()
            'zig_plugin'
        """
        return self.entry_point.rsplit(".", 1)[0]

    def get_class_name(self) -> str:
        """
        Extract class name from entry_point.

        Returns:
            Class name (e.g., "ZigCompiler" from "zig_plugin.ZigCompiler")

        Example:
            >>> metadata.get_class_name()
            'ZigCompiler'
        """
        return self.entry_point.rsplit(".", 1)[1]


class PluginMetadataParser:
    """
    Parse and validate plugin.yaml files.

    This parser reads plugin.yaml files, validates the schema and
    semantic rules, and returns PluginMetadata instances.
    """

    REQUIRED_FIELDS = [
        "name",
        "version",
        "type",
        "description",
        "author",
        "entry_point",
    ]

    VALID_TYPES = ["compiler", "package_manager", "backend"]

    def parse_file(self, yaml_path: Path) -> PluginMetadata:
        """
        Parse plugin.yaml file.

        Args:
            yaml_path: Path to plugin.yaml file

        Returns:
            PluginMetadata instance with parsed and validated data

        Raises:
            PluginValidationError: If parsing or validation fails

        Example:
            parser = PluginMetadataParser()
            metadata = parser.parse_file(Path("plugin/plugin.yaml"))
            print(f"Plugin: {metadata.name} v{metadata.version}")
        """
        if not yaml_path.exists():
            raise PluginValidationError(
                str(yaml_path), [f"File not found: {yaml_path}"]
            )

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PluginValidationError(str(yaml_path), [f"Invalid YAML syntax: {e}"])
        except Exception as e:
            raise PluginValidationError(str(yaml_path), [f"Error reading file: {e}"])

        if not isinstance(data, dict):
            raise PluginValidationError(
                str(yaml_path), ["Root element must be a dictionary"]
            )

        # Validate
        issues = self._validate_schema(data)
        if issues:
            raise PluginValidationError(str(yaml_path), issues)

        # Create metadata
        metadata = PluginMetadata(
            name=data["name"],
            version=data["version"],
            type=data["type"],
            description=data["description"],
            author=data["author"],
            entry_point=data["entry_point"],
            homepage=data.get("homepage"),
            license=data.get("license"),
            requires=data.get("requires", []),
            min_toolchainkit_version=data.get("min_toolchainkit_version"),
            max_toolchainkit_version=data.get("max_toolchainkit_version"),
            platforms=data.get("platforms", []),
            tags=data.get("tags", []),
            permissions=data.get("permissions", []),
            plugin_dir=yaml_path.parent,
        )

        return metadata

    def _validate_schema(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate plugin metadata schema.

        Args:
            data: Parsed YAML data

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data:
                issues.append(f"Missing required field: {field_name}")

        # Validate types and formats
        if "name" in data:
            if not isinstance(data["name"], str):
                issues.append("Field 'name' must be a string")
            elif not data["name"]:
                issues.append("Field 'name' cannot be empty")

        if "version" in data:
            if not isinstance(data["version"], str):
                issues.append("Field 'version' must be a string")
            elif not self._is_valid_semver(data["version"]):
                issues.append(f"Invalid semantic version: {data['version']}")

        if "type" in data:
            if not isinstance(data["type"], str):
                issues.append("Field 'type' must be a string")
            elif data["type"] not in self.VALID_TYPES:
                issues.append(
                    f"Invalid type '{data['type']}'. "
                    f"Must be one of: {', '.join(self.VALID_TYPES)}"
                )

        if "description" in data and not isinstance(data["description"], str):
            issues.append("Field 'description' must be a string")

        if "author" in data and not isinstance(data["author"], str):
            issues.append("Field 'author' must be a string")

        if "entry_point" in data:
            if not isinstance(data["entry_point"], str):
                issues.append("Field 'entry_point' must be a string")
            elif "." not in data["entry_point"]:
                issues.append(
                    "Field 'entry_point' must be in format 'module.ClassName'"
                )

        # Validate optional string fields
        for field_name in [
            "homepage",
            "license",
            "min_toolchainkit_version",
            "max_toolchainkit_version",
        ]:
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], str):
                    issues.append(f"Field '{field_name}' must be a string")

        # Validate optional list fields
        for field_name in ["requires", "platforms", "tags", "permissions"]:
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], list):
                    issues.append(f"Field '{field_name}' must be a list")
                elif not all(isinstance(item, str) for item in data[field_name]):
                    issues.append(f"All items in '{field_name}' must be strings")

        return issues

    def _is_valid_semver(self, version_str: str) -> bool:
        """
        Check if version is valid semantic version.

        Args:
            version_str: Version string to validate

        Returns:
            True if valid semantic version, False otherwise
        """
        try:
            from packaging import version

            version.parse(version_str)
            return True
        except Exception:
            return False


__all__ = ["PluginMetadata", "PluginMetadataParser"]
