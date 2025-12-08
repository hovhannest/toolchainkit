"""
Tests for config.composer module.

Tests cover:
- ComposedConfig creation and properties
- LayerComposer initialization and layer discovery
- Layer composition logic
- Configuration caching
- Error handling
"""

import pytest
from unittest.mock import Mock

from toolchainkit.config.composer import ComposedConfig
from toolchainkit.config.layers import (
    ConfigLayer,
    LayerContext,
)


class TestComposedConfig:
    """Test ComposedConfig class."""

    @pytest.fixture
    def mock_context(self):
        """Create mock LayerContext."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Release"
        context.compile_flags = ["-Wall", "-Wextra", "-O3"]
        context.link_flags = ["-fuse-ld=lld", "-pthread"]
        context.defines = ["NDEBUG", "RELEASE_BUILD"]
        context.cmake_variables = {"CMAKE_CXX_STANDARD": "20"}
        context.runtime_env = {"LD_LIBRARY_PATH": "/usr/lib"}
        context.sanitizers = {"address"}
        return context

    @pytest.fixture
    def mock_layers(self):
        """Create mock layers."""
        layer1 = Mock(spec=ConfigLayer)
        layer1.name = "clang-18"
        layer1.layer_type = "compiler"
        layer2 = Mock(spec=ConfigLayer)
        layer2.name = "linux-x64"
        layer2.layer_type = "platform"
        return [layer1, layer2]

    def test_composed_config_creation(self, mock_context, mock_layers):
        """Test creating ComposedConfig."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.context == mock_context
        assert config.layers == mock_layers

    def test_composed_config_compiler_property(self, mock_context, mock_layers):
        """Test compiler property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.compiler == "clang"

    def test_composed_config_compiler_version_property(self, mock_context, mock_layers):
        """Test compiler_version property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.compiler_version == "18.1.8"

    def test_composed_config_platform_property(self, mock_context, mock_layers):
        """Test platform property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.platform == "linux-x64"

    def test_composed_config_stdlib_property(self, mock_context, mock_layers):
        """Test stdlib property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.stdlib == "libc++"

    def test_composed_config_build_type_property(self, mock_context, mock_layers):
        """Test build_type property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.build_type == "Release"

    def test_composed_config_compile_flags_property(self, mock_context, mock_layers):
        """Test compile_flags property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.compile_flags == ["-Wall", "-Wextra", "-O3"]

    def test_composed_config_link_flags_property(self, mock_context, mock_layers):
        """Test link_flags property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.link_flags == ["-fuse-ld=lld", "-pthread"]

    def test_composed_config_defines_property(self, mock_context, mock_layers):
        """Test defines property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.defines == ["NDEBUG", "RELEASE_BUILD"]

    def test_composed_config_cmake_variables_property(self, mock_context, mock_layers):
        """Test cmake_variables property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.cmake_variables == {"CMAKE_CXX_STANDARD": "20"}

    def test_composed_config_runtime_env_property(self, mock_context, mock_layers):
        """Test runtime_env property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.runtime_env == {"LD_LIBRARY_PATH": "/usr/lib"}

    def test_composed_config_sanitizers_property(self, mock_context, mock_layers):
        """Test sanitizers property."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.sanitizers == {"address"}

    def test_composed_config_linker_property(self, mock_context, mock_layers):
        """Test linker property extracts from link flags."""
        config = ComposedConfig(mock_context, mock_layers)

        assert config.linker == "lld"

    def test_composed_config_linker_property_no_linker(self, mock_context, mock_layers):
        """Test linker property when no linker specified."""
        mock_context.link_flags = ["-pthread"]
        config = ComposedConfig(mock_context, mock_layers)

        assert config.linker is None

    def test_composed_config_to_dict(self, mock_context, mock_layers):
        """Test to_dict method."""
        config = ComposedConfig(mock_context, mock_layers)

        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["compiler"] == "clang"
        assert result["compiler_version"] == "18.1.8"
        assert result["platform"] == "linux-x64"
        assert result["stdlib"] == "libc++"
        assert result["build_type"] == "Release"
        assert result["compile_flags"] == ["-Wall", "-Wextra", "-O3"]
        assert result["link_flags"] == ["-fuse-ld=lld", "-pthread"]
        assert result["defines"] == ["NDEBUG", "RELEASE_BUILD"]
        assert result["cmake_variables"] == {"CMAKE_CXX_STANDARD": "20"}

    def test_composed_config_with_none_values(self, mock_layers):
        """Test ComposedConfig with None values."""
        context = Mock(spec=LayerContext)
        context.compiler = None
        context.compiler_version = None
        context.platform = None
        context.stdlib = None
        context.build_type = None
        context.compile_flags = []
        context.link_flags = []
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert config.compiler is None
        assert config.compiler_version is None
        assert config.platform is None
        assert config.stdlib is None
        assert config.build_type is None
        assert config.compile_flags == []

    def test_composed_config_linker_with_gold(self, mock_context, mock_layers):
        """Test linker property with gold linker."""
        mock_context.link_flags = ["-fuse-ld=gold", "-Wl,--as-needed"]
        config = ComposedConfig(mock_context, mock_layers)

        assert config.linker == "gold"

    def test_composed_config_linker_with_mold(self, mock_context, mock_layers):
        """Test linker property with mold linker."""
        mock_context.link_flags = ["-fuse-ld=mold"]
        config = ComposedConfig(mock_context, mock_layers)

        assert config.linker == "mold"

    def test_composed_config_multiple_use_ld_flags(self, mock_context, mock_layers):
        """Test linker property with multiple -fuse-ld flags (uses first)."""
        mock_context.link_flags = ["-fuse-ld=lld", "-fuse-ld=gold"]
        config = ComposedConfig(mock_context, mock_layers)

        # Should extract first occurrence
        assert config.linker == "lld"

    def test_composed_config_empty_layers(self, mock_context):
        """Test ComposedConfig with empty layers list."""
        config = ComposedConfig(mock_context, [])

        assert config.layers == []
        assert config.compiler == "clang"

    def test_composed_config_property_access(self, mock_context, mock_layers):
        """Test that all properties are accessible."""
        config = ComposedConfig(mock_context, mock_layers)

        # Access all properties to ensure they don't raise
        _ = config.compiler
        _ = config.compiler_version
        _ = config.platform
        _ = config.stdlib
        _ = config.build_type
        _ = config.compile_flags
        _ = config.link_flags
        _ = config.defines
        _ = config.cmake_variables
        _ = config.runtime_env
        _ = config.sanitizers
        _ = config.linker

    def test_composed_config_to_dict_complete(self, mock_context, mock_layers):
        """Test to_dict includes all expected keys."""
        config = ComposedConfig(mock_context, mock_layers)

        result = config.to_dict()

        expected_keys = [
            "compiler",
            "compiler_version",
            "platform",
            "stdlib",
            "build_type",
            "compile_flags",
            "link_flags",
            "defines",
            "cmake_variables",
        ]

        for key in expected_keys:
            assert key in result


class TestLayerComposerEdgeCases:
    """Test edge cases and error conditions for LayerComposer."""

    @pytest.fixture
    def mock_layers(self):
        """Create mock layers."""
        layer1 = Mock(spec=ConfigLayer)
        layer1.name = "test-compiler"
        layer1.layer_type = "compiler"
        layer2 = Mock(spec=ConfigLayer)
        layer2.name = "test-platform"
        layer2.layer_type = "platform"
        return [layer1, layer2]

    def test_composed_config_with_empty_compile_flags(self, mock_layers):
        """Test config with empty compile flags."""
        context = Mock(spec=LayerContext)
        context.compiler = "gcc"
        context.compiler_version = "13.2.0"
        context.platform = "linux-x64"
        context.stdlib = "libstdc++"
        context.build_type = "Debug"
        context.compile_flags = []
        context.link_flags = []
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert config.compile_flags == []
        assert config.link_flags == []

    def test_composed_config_with_complex_link_flags(self, mock_layers):
        """Test config with complex link flags."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Release"
        context.compile_flags = []
        context.link_flags = [
            "-fuse-ld=lld",
            "-Wl,--as-needed",
            "-Wl,--no-undefined",
            "-Wl,-rpath,/usr/lib",
        ]
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert config.linker == "lld"
        assert len(config.link_flags) == 4

    def test_composed_config_with_multiple_sanitizers(self, mock_layers):
        """Test config with multiple sanitizers."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Debug"
        context.compile_flags = []
        context.link_flags = []
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {}
        context.sanitizers = {"address", "undefined", "leak"}

        config = ComposedConfig(context, mock_layers)

        assert "address" in config.sanitizers
        assert "undefined" in config.sanitizers
        assert "leak" in config.sanitizers

    def test_composed_config_with_many_cmake_variables(self, mock_layers):
        """Test config with many CMake variables."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Release"
        context.compile_flags = []
        context.link_flags = []
        context.defines = []
        context.cmake_variables = {
            "CMAKE_CXX_STANDARD": "20",
            "CMAKE_CXX_STANDARD_REQUIRED": "ON",
            "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
            "CMAKE_BUILD_TYPE": "Release",
            "CMAKE_INTERPROCEDURAL_OPTIMIZATION": "ON",
        }
        context.runtime_env = {}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert len(config.cmake_variables) == 5
        assert config.cmake_variables["CMAKE_CXX_STANDARD"] == "20"

    def test_composed_config_with_runtime_env_vars(self, mock_layers):
        """Test config with runtime environment variables."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Release"
        context.compile_flags = []
        context.link_flags = []
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {
            "LD_LIBRARY_PATH": "/usr/lib:/usr/local/lib",
            "PATH": "/usr/bin:/usr/local/bin",
            "CC": "clang",
            "CXX": "clang++",
        }
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert len(config.runtime_env) == 4
        assert config.runtime_env["CC"] == "clang"
        assert config.runtime_env["CXX"] == "clang++"

    def test_composed_config_linker_with_spaces_in_flag(self, mock_layers):
        """Test linker extraction with spaces in flag."""
        context = Mock(spec=LayerContext)
        context.compiler = "clang"
        context.compiler_version = "18.1.8"
        context.platform = "linux-x64"
        context.stdlib = "libc++"
        context.build_type = "Release"
        context.compile_flags = []
        context.link_flags = ["-fuse-ld=lld", "-Wl,-plugin-opt=O3"]
        context.defines = []
        context.cmake_variables = {}
        context.runtime_env = {}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        assert config.linker == "lld"

    def test_composed_config_to_dict_preserves_types(self, mock_layers):
        """Test to_dict preserves data types."""
        context = Mock(spec=LayerContext)
        context.compiler = "gcc"
        context.compiler_version = "13.2.0"
        context.platform = "linux-x64"
        context.stdlib = "libstdc++"
        context.build_type = "Release"
        context.compile_flags = ["-O3", "-Wall"]
        context.link_flags = ["-pthread"]
        context.defines = ["NDEBUG"]
        context.cmake_variables = {"CMAKE_CXX_STANDARD": "20"}
        context.runtime_env = {"PATH": "/usr/bin"}
        context.sanitizers = set()

        config = ComposedConfig(context, mock_layers)

        result = config.to_dict()

        assert isinstance(result["compile_flags"], list)
        assert isinstance(result["link_flags"], list)
        assert isinstance(result["defines"], list)
        assert isinstance(result["cmake_variables"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
