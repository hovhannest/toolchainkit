"""
Integration tests for configuration layer system.

Tests the layer system end-to-end using built-in layers.
"""

import pytest

from toolchainkit.config import LayerComposer
from toolchainkit.cmake.toolchain_generator import CMakeToolchainGenerator


class TestLayerSystemBasics:
    """Basic layer system functionality tests."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project root."""
        root = tmp_path / "test_project"
        root.mkdir()
        return root

    @pytest.fixture
    def composer(self, project_root):
        """Create layer composer."""
        return LayerComposer(project_root=project_root)

    def test_compose_basic_configuration(self, composer):
        """Test composing a basic release configuration."""
        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "buildtype", "name": "release"},
        ]

        config = composer.compose(layer_specs)

        assert config.compiler == "clang"
        assert config.platform == "linux-x64"
        assert config.build_type == "release"
        assert len(config.layers) == 3
        assert "-O3" in config.compile_flags
        assert "NDEBUG" in config.defines

    def test_compose_with_stdlib(self, composer):
        """Test composition with stdlib layer."""
        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "stdlib", "name": "libc++"},
            {"type": "buildtype", "name": "debug"},
        ]

        config = composer.compose(layer_specs)

        assert config.stdlib == "libc++"
        assert "-stdlib=libc++" in config.compile_flags
        assert "-lc++" in config.link_flags

    def test_compose_with_optimization(self, composer):
        """Test composition with optimization layer."""
        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "buildtype", "name": "release"},
            {"type": "optimization", "name": "lto-thin"},
        ]

        config = composer.compose(layer_specs)

        assert "-flto=thin" in config.compile_flags
        assert "-flto=thin" in config.link_flags
        assert "LTO_ENABLED=1" in config.defines

    def test_list_builtin_layers(self, composer):
        """Test listing built-in layers."""
        layers = composer.list_layers("base")

        assert len(layers) > 0
        assert any("clang-18" in layer for layer in layers)

    def test_list_all_layers(self, composer):
        """Test listing all layer types."""
        all_layers = composer.list_layers()

        assert len(all_layers) >= 22  # We have 22+ built-in layers
        assert any("base/" in layer for layer in all_layers)
        assert any("platform/" in layer for layer in all_layers)
        assert any("buildtype/" in layer for layer in all_layers)


class TestLayerValidation:
    """Test layer validation logic."""

    @pytest.fixture
    def composer(self, tmp_path):
        """Create layer composer."""
        root = tmp_path / "project"
        root.mkdir()
        return LayerComposer(project_root=root)

    def test_missing_required_base_layer(self, composer):
        """Test that missing base layer causes validation error."""
        from toolchainkit.config.layers import LayerValidationError

        layer_specs = [
            {"type": "platform", "name": "linux-x64"},
            {"type": "buildtype", "name": "release"},
        ]

        with pytest.raises(LayerValidationError, match="base"):
            composer.compose(layer_specs)

    def test_missing_required_platform_layer(self, composer):
        """Test that missing platform layer causes validation error."""
        from toolchainkit.config.layers import LayerValidationError

        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "buildtype", "name": "release"},
        ]

        with pytest.raises(LayerValidationError, match="platform"):
            composer.compose(layer_specs)

    def test_missing_required_buildtype_layer(self, composer):
        """Test that missing buildtype layer causes validation error."""
        from toolchainkit.config.layers import LayerValidationError

        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
        ]

        with pytest.raises(LayerValidationError, match="buildtype"):
            composer.compose(layer_specs)

    def test_stdlib_compiler_requirement(self, composer, tmp_path):
        """Test that stdlib validates compiler requirement."""
        from toolchainkit.config.layers import LayerRequirementError
        import yaml

        # Create GCC base layer
        gcc_dir = tmp_path / "project" / ".toolchainkit" / "layers" / "base"
        gcc_dir.mkdir(parents=True, exist_ok=True)

        gcc_layer = {
            "type": "base",
            "name": "gcc-test",
            "description": "Test GCC",
            "compiler": "gcc",
            "compiler_version": "13.0.0",
            "flags": {},
        }

        with open(gcc_dir / "gcc-test.yaml", "w") as f:
            yaml.dump(gcc_layer, f)

        # Try to use libc++ (requires Clang) with GCC
        layer_specs = [
            {"type": "base", "name": "gcc-test"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "stdlib", "name": "libc++"},  # Requires Clang!
            {"type": "buildtype", "name": "release"},
        ]

        with pytest.raises(LayerRequirementError, match="compiler"):
            composer.compose(layer_specs)


class TestCMakeIntegration:
    """Test CMake toolchain generation from layers."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create CMake toolchain generator."""
        root = tmp_path / "project"
        root.mkdir()
        return CMakeToolchainGenerator(root)

    def test_generate_toolchain_from_layers(self, generator):
        """Test generating CMake toolchain file from layers."""
        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "buildtype", "name": "release"},
        ]

        toolchain_file = generator.generate_from_layers(
            layer_specs, toolchain_name="test-config"
        )

        assert toolchain_file.exists()
        assert toolchain_file.name == "toolchain-test-config.cmake"

        content = toolchain_file.read_text()
        assert "Generated by ToolchainKit" in content
        assert "clang-18" in content
        assert "linux-x64" in content
        assert "-O3" in content

    def test_generate_toolchain_with_optimization(self, generator):
        """Test generating toolchain with LTO."""
        layer_specs = [
            {"type": "base", "name": "clang-18"},
            {"type": "platform", "name": "linux-x64"},
            {"type": "buildtype", "name": "release"},
            {"type": "optimization", "name": "lto-thin"},
        ]

        toolchain_file = generator.generate_from_layers(
            layer_specs, toolchain_name="lto-config"
        )

        content = toolchain_file.read_text()
        assert "-flto=thin" in content
        assert "LTO_ENABLED" in content


class TestComposedConfig:
    """Test ComposedConfig interface."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a composed configuration."""
        root = tmp_path / "project"
        root.mkdir()
        composer = LayerComposer(project_root=root)

        return composer.compose(
            [
                {"type": "base", "name": "clang-18"},
                {"type": "platform", "name": "linux-x64"},
                {"type": "buildtype", "name": "release"},
            ]
        )

    def test_config_properties(self, config):
        """Test configuration property accessors."""
        assert config.compiler == "clang"
        assert config.platform == "linux-x64"
        assert config.build_type == "release"
        assert isinstance(config.compile_flags, list)
        assert isinstance(config.link_flags, list)
        assert isinstance(config.defines, list)

    def test_config_to_dict(self, config):
        """Test converting config to dictionary."""
        config_dict = config.to_dict()

        assert config_dict["compiler"] == "clang"
        assert config_dict["platform"] == "linux-x64"
        assert isinstance(config_dict["compile_flags"], list)
        assert isinstance(config_dict["layers"], list)

    def test_config_layer_info(self, config):
        """Test getting layer information."""
        layer_info = config.layer_info()

        assert len(layer_info) == 3
        assert all("type" in info for info in layer_info)
        assert all("name" in info for info in layer_info)
        assert all("description" in info for info in layer_info)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
