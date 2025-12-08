"""
Tests for CMakePresets.json generation.
"""

import json
import pytest
from pathlib import Path
from toolchainkit.ide.presets import CMakePresetsGenerator


class TestCMakePresetsGeneratorInit:
    """Test CMakePresetsGenerator initialization."""

    def test_init_creates_correct_paths(self, tmp_path):
        """Test that initialization creates correct paths."""
        generator = CMakePresetsGenerator(tmp_path)

        assert generator.project_root == tmp_path
        assert generator.presets_file == tmp_path / "CMakePresets.json"

    def test_init_with_str_path(self, tmp_path):
        """Test initialization with string path."""
        generator = CMakePresetsGenerator(str(tmp_path))

        assert generator.project_root == tmp_path
        assert isinstance(generator.project_root, Path)


class TestGeneratePresets:
    """Test generate_presets method."""

    def test_generate_presets_creates_file(self, tmp_path):
        """Test that generate_presets creates CMakePresets.json."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        assert presets_file.exists()
        assert presets_file.name == "CMakePresets.json"

    def test_generate_presets_default_build_types(self, tmp_path):
        """Test generate_presets with default build types."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        # Should have Debug and Release by default
        assert len(presets["configurePresets"]) == 2
        assert len(presets["buildPresets"]) == 2

        preset_names = [p["name"] for p in presets["configurePresets"]]
        assert "llvm-18-debug" in preset_names
        assert "llvm-18-release" in preset_names

    def test_generate_presets_custom_build_types(self, tmp_path):
        """Test generate_presets with custom build types."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets(
            "gcc-13", build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"]
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        assert len(presets["configurePresets"]) == 4
        assert len(presets["buildPresets"]) == 4

        preset_names = [p["name"] for p in presets["configurePresets"]]
        assert "gcc-13-debug" in preset_names
        assert "gcc-13-release" in preset_names
        assert "gcc-13-relwithdebinfo" in preset_names
        assert "gcc-13-minsizerel" in preset_names

    def test_generate_presets_custom_generator(self, tmp_path):
        """Test generate_presets with custom generator."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18", generator="Unix Makefiles")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        # All presets should use the custom generator
        for preset in presets["configurePresets"]:
            assert preset["generator"] == "Unix Makefiles"

    def test_generate_presets_additional_cache_vars(self, tmp_path):
        """Test generate_presets with additional cache variables."""
        generator = CMakePresetsGenerator(tmp_path)

        additional_vars = {
            "BUILD_TESTING": "ON",
            "CMAKE_CXX_STANDARD": "20",
            "CUSTOM_OPTION": "value",
        }

        presets_file = generator.generate_presets(
            "llvm-18", additional_cache_vars=additional_vars
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        # Check that additional vars are present in all presets
        for preset in presets["configurePresets"]:
            cache_vars = preset["cacheVariables"]
            assert cache_vars["BUILD_TESTING"] == "ON"
            assert cache_vars["CMAKE_CXX_STANDARD"] == "20"
            assert cache_vars["CUSTOM_OPTION"] == "value"


class TestPresetsStructure:
    """Test structure of generated presets."""

    def test_presets_version(self, tmp_path):
        """Test that presets use version 3."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        assert presets["version"] == 3

    def test_configure_preset_structure(self, tmp_path):
        """Test structure of configure presets."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["configurePresets"]:
            assert "name" in preset
            assert "displayName" in preset
            assert "description" in preset
            assert "binaryDir" in preset
            assert "generator" in preset
            assert "cacheVariables" in preset

    def test_build_preset_structure(self, tmp_path):
        """Test structure of build presets."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["buildPresets"]:
            assert "name" in preset
            assert "displayName" in preset
            assert "configurePreset" in preset

    def test_build_presets_link_to_configure(self, tmp_path):
        """Test that build presets correctly link to configure presets."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        configure_names = {p["name"] for p in presets["configurePresets"]}

        for build_preset in presets["buildPresets"]:
            # Build preset should reference a valid configure preset
            assert build_preset["configurePreset"] in configure_names
            # Build preset name should match configure preset name
            assert build_preset["name"] == build_preset["configurePreset"]


class TestPresetsContent:
    """Test content of generated presets."""

    def test_toolchain_file_reference(self, tmp_path):
        """Test that toolchain file is correctly referenced."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["configurePresets"]:
            cache_vars = preset["cacheVariables"]
            assert "CMAKE_TOOLCHAIN_FILE" in cache_vars
            assert (
                cache_vars["CMAKE_TOOLCHAIN_FILE"]
                == "${sourceDir}/.toolchainkit/cmake/toolchain.cmake"
            )

    def test_binary_directory_structure(self, tmp_path):
        """Test binary directory uses preset name."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["configurePresets"]:
            assert preset["binaryDir"] == "${sourceDir}/build/${presetName}"

    def test_build_type_cache_variable(self, tmp_path):
        """Test that CMAKE_BUILD_TYPE is set correctly."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets(
            "llvm-18", build_types=["Debug", "Release"]
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        debug_preset = next(
            p for p in presets["configurePresets"] if p["name"] == "llvm-18-debug"
        )
        assert debug_preset["cacheVariables"]["CMAKE_BUILD_TYPE"] == "Debug"

        release_preset = next(
            p for p in presets["configurePresets"] if p["name"] == "llvm-18-release"
        )
        assert release_preset["cacheVariables"]["CMAKE_BUILD_TYPE"] == "Release"

    def test_export_compile_commands(self, tmp_path):
        """Test that CMAKE_EXPORT_COMPILE_COMMANDS is enabled."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["configurePresets"]:
            cache_vars = preset["cacheVariables"]
            assert cache_vars["CMAKE_EXPORT_COMPILE_COMMANDS"] == "ON"


class TestPresetsNames:
    """Test preset naming conventions."""

    def test_configure_preset_names(self, tmp_path):
        """Test configure preset naming format."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets(
            "llvm-18", build_types=["Debug", "Release"]
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        names = [p["name"] for p in presets["configurePresets"]]
        assert "llvm-18-debug" in names
        assert "llvm-18-release" in names

    def test_display_names(self, tmp_path):
        """Test preset display names."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("gcc-13")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        debug_preset = next(
            p for p in presets["configurePresets"] if p["name"] == "gcc-13-debug"
        )
        assert debug_preset["displayName"] == "gcc-13 Debug"

        release_preset = next(
            p for p in presets["configurePresets"] if p["name"] == "gcc-13-release"
        )
        assert release_preset["displayName"] == "gcc-13 Release"

    def test_descriptions(self, tmp_path):
        """Test preset descriptions."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        for preset in presets["configurePresets"]:
            assert "description" in preset
            assert "toolchain" in preset["description"].lower()


class TestPresetsWriting:
    """Test preset file writing."""

    def test_write_creates_file(self, tmp_path):
        """Test that writing creates the file."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        assert presets_file.exists()

    def test_write_valid_json(self, tmp_path):
        """Test that written file is valid JSON."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        # Should be able to load the JSON
        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        assert isinstance(presets, dict)

    def test_write_formatted_json(self, tmp_path):
        """Test that JSON is pretty-formatted."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets("llvm-18")

        with open(presets_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have indentation
        assert "  " in content
        # Should have newline at end
        assert content.endswith("\n")


class TestPresetsLoading:
    """Test loading existing presets."""

    def test_load_existing_presets_no_file(self, tmp_path):
        """Test loading when CMakePresets.json doesn't exist."""
        generator = CMakePresetsGenerator(tmp_path)

        presets = generator._load_existing_presets()

        assert presets is None

    def test_load_existing_presets_valid_json(self, tmp_path):
        """Test loading existing valid CMakePresets.json."""
        generator = CMakePresetsGenerator(tmp_path)

        # Create existing presets
        existing = {"version": 3, "configurePresets": [{"name": "old-preset"}]}
        with open(tmp_path / "CMakePresets.json", "w", encoding="utf-8") as f:
            json.dump(existing, f)

        presets = generator._load_existing_presets()

        assert presets == existing

    def test_load_existing_presets_invalid_json(self, tmp_path):
        """Test loading existing invalid CMakePresets.json."""
        generator = CMakePresetsGenerator(tmp_path)

        # Write invalid JSON
        with open(tmp_path / "CMakePresets.json", "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        presets = generator._load_existing_presets()

        # Should return None on parse error
        assert presets is None


class TestUserPresets:
    """Test CMakeUserPresets.json detection."""

    def test_has_user_presets_false(self, tmp_path):
        """Test when CMakeUserPresets.json doesn't exist."""
        generator = CMakePresetsGenerator(tmp_path)

        assert generator.has_user_presets() is False

    def test_has_user_presets_true(self, tmp_path):
        """Test when CMakeUserPresets.json exists."""
        generator = CMakePresetsGenerator(tmp_path)

        # Create user presets file
        user_presets = tmp_path / "CMakeUserPresets.json"
        user_presets.write_text("{}")

        assert generator.has_user_presets() is True


class TestIntegration:
    """Test integration scenarios."""

    def test_multiple_build_types_workflow(self, tmp_path):
        """Test workflow with multiple build types."""
        generator = CMakePresetsGenerator(tmp_path)

        presets_file = generator.generate_presets(
            "llvm-18", build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"]
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        # Should have 4 configure and 4 build presets
        assert len(presets["configurePresets"]) == 4
        assert len(presets["buildPresets"]) == 4

        # Each build type should have matching configure and build preset
        for build_type in ["Debug", "Release", "RelWithDebInfo", "MinSizeRel"]:
            preset_name = f"llvm-18-{build_type.lower()}"

            # Find configure preset
            configure = next(
                (p for p in presets["configurePresets"] if p["name"] == preset_name),
                None,
            )
            assert configure is not None
            assert configure["cacheVariables"]["CMAKE_BUILD_TYPE"] == build_type

            # Find build preset
            build = next(
                (p for p in presets["buildPresets"] if p["name"] == preset_name), None
            )
            assert build is not None
            assert build["configurePreset"] == preset_name

    def test_cross_compilation_preset(self, tmp_path):
        """Test preset generation for cross-compilation."""
        generator = CMakePresetsGenerator(tmp_path)

        # Simulate cross-compilation with custom toolchain file
        presets_file = generator.generate_presets(
            "arm64-linux-gcc", build_types=["Debug", "Release"]
        )

        with open(presets_file, "r", encoding="utf-8") as f:
            presets = json.load(f)

        # Toolchain file should still point to ToolchainKit's location
        for preset in presets["configurePresets"]:
            assert (
                preset["cacheVariables"]["CMAKE_TOOLCHAIN_FILE"]
                == "${sourceDir}/.toolchainkit/cmake/toolchain.cmake"
            )


class TestPresetsExceptionHandling:
    """Test exception handling in CMakePresetsGenerator."""

    def test_write_presets_exception(self, tmp_path):
        """Test _write_presets exception handling."""
        from unittest.mock import patch

        generator = CMakePresetsGenerator(tmp_path)

        # Mock open to raise exception
        with patch("builtins.open", side_effect=IOError("Write failed")):
            with pytest.raises(IOError, match="Write failed"):
                generator._write_presets({})

    def test_load_existing_presets_generic_exception(self, tmp_path):
        """Test _load_existing_presets generic exception handling."""
        from unittest.mock import patch

        generator = CMakePresetsGenerator(tmp_path)
        (tmp_path / "CMakePresets.json").touch()

        # Mock open to raise exception (not JSONDecodeError)
        with patch("builtins.open", side_effect=IOError("Read failed")):
            presets = generator._load_existing_presets()
            assert presets is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
