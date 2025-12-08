"""
Tests for VSCode integration.
"""

import json
import pytest
from pathlib import Path
from toolchainkit.ide.vscode import VSCodeIntegrator


class TestVSCodeIntegratorInit:
    """Test VSCodeIntegrator initialization."""

    def test_init_creates_correct_paths(self, tmp_path):
        """Test that initialization creates correct paths."""
        integrator = VSCodeIntegrator(tmp_path)

        assert integrator.project_root == tmp_path
        assert integrator.vscode_dir == tmp_path / ".vscode"

    def test_init_with_str_path(self, tmp_path):
        """Test initialization with string path."""
        integrator = VSCodeIntegrator(str(tmp_path))

        assert integrator.project_root == tmp_path
        assert isinstance(integrator.project_root, Path)


class TestGenerateSettings:
    """Test generate_settings method."""

    def test_generate_settings_creates_vscode_dir(self, tmp_path):
        """Test that generate_settings creates .vscode directory."""
        integrator = VSCodeIntegrator(tmp_path)

        integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
        )

        assert (tmp_path / ".vscode").exists()
        assert (tmp_path / ".vscode").is_dir()

    def test_generate_settings_creates_settings_json(self, tmp_path):
        """Test that generate_settings creates settings.json."""
        integrator = VSCodeIntegrator(tmp_path)

        settings_file = integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
        )

        assert settings_file.exists()
        assert settings_file.name == "settings.json"

    def test_generate_settings_with_defaults(self, tmp_path):
        """Test generate_settings with default parameters."""
        integrator = VSCodeIntegrator(tmp_path)

        settings_file = integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        assert "cmake.configureSettings" in settings
        assert "CMAKE_TOOLCHAIN_FILE" in settings["cmake.configureSettings"]
        assert (
            settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
        )

        # Compiler path should be stored as string (may have backslashes on Windows)
        assert settings["C_Cpp.default.compilerPath"] == str(Path("/usr/bin/clang"))
        assert settings["cmake.buildDirectory"] == "${workspaceFolder}/build"
        assert settings["cmake.generator"] == "Ninja"
        assert settings["cmake.exportCompileCommandsFile"] is True

    def test_generate_settings_with_clang_tools(self, tmp_path):
        """Test generate_settings with Clang Format and Clang Tidy paths."""
        integrator = VSCodeIntegrator(tmp_path)

        settings_file = integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
            clang_format_path=Path("/usr/bin/clang-format"),
            clang_tidy_path=Path("/usr/bin/clang-tidy"),
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        assert "cmake.configureSettings" in settings
        assert "CMAKE_TOOLCHAIN_FILE" in settings["cmake.configureSettings"]
        assert (
            settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
        )
        assert settings["C_Cpp.default.compilerPath"] == str(Path("/usr/bin/clang"))

        # Check Clang Tools settings
        assert settings["C_Cpp.clang_format_path"] == str(Path("/usr/bin/clang-format"))
        assert settings["editor.formatOnSave"] is True
        assert settings["editor.formatOnSaveMode"] == "modifications"
        assert settings["C_Cpp.codeAnalysis.clangTidy.enabled"] is True
        assert settings["C_Cpp.codeAnalysis.clangTidy.path"] == str(
            Path("/usr/bin/clang-tidy")
        )

    def test_generate_settings_with_custom_parameters(self, tmp_path):
        """Test generate_settings with custom parameters."""
        integrator = VSCodeIntegrator(tmp_path)

        settings_file = integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain-gcc.cmake"),
            compiler_path=Path("/usr/bin/gcc"),
            build_dir="build-release",
            generator="Unix Makefiles",
            export_compile_commands=False,
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        assert (
            settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/.toolchainkit/cmake/toolchain-gcc.cmake"
        )
        assert settings["C_Cpp.default.compilerPath"] == str(Path("/usr/bin/gcc"))
        assert settings["cmake.buildDirectory"] == "${workspaceFolder}/build-release"
        assert settings["cmake.generator"] == "Unix Makefiles"
        assert "cmake.exportCompileCommandsFile" not in settings

    def test_generate_settings_with_absolute_toolchain_path(self, tmp_path):
        """Test generate_settings with absolute toolchain path."""
        integrator = VSCodeIntegrator(tmp_path)

        # Create absolute toolchain path inside project
        toolchain_dir = tmp_path / ".toolchainkit" / "cmake"
        toolchain_dir.mkdir(parents=True)
        toolchain_file = toolchain_dir / "toolchain.cmake"
        toolchain_file.touch()

        settings_file = integrator.generate_settings(
            toolchain_file=toolchain_file,  # Absolute path
            compiler_path=Path("/usr/bin/clang"),
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # Should be converted to relative path
        assert (
            settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
        )

    def test_generate_settings_with_absolute_toolchain_outside_project(self, tmp_path):
        """Test generate_settings with absolute toolchain path outside project."""
        integrator = VSCodeIntegrator(tmp_path)

        # Use absolute path outside project
        toolchain_file = Path("/opt/toolchains/custom/toolchain.cmake")

        settings_file = integrator.generate_settings(
            toolchain_file=toolchain_file, compiler_path=Path("/usr/bin/clang")
        )

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # Should keep path as posix format (toolchain_file.as_posix() is used)
        # On Windows: /opt/... becomes ${workspaceFolder}//opt/...
        # On Unix: /opt/... becomes ${workspaceFolder}/opt/...
        expected = f"${{workspaceFolder}}/{toolchain_file.as_posix()}"
        assert settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"] == expected


class TestLoadExistingSettings:
    """Test _load_existing_settings method."""

    def test_load_existing_settings_no_file(self, tmp_path):
        """Test loading when settings.json doesn't exist."""
        integrator = VSCodeIntegrator(tmp_path)
        settings_file = tmp_path / ".vscode" / "settings.json"

        settings = integrator._load_existing_settings(settings_file)

        assert settings == {}

    def test_load_existing_settings_valid_json(self, tmp_path):
        """Test loading existing valid settings.json."""
        integrator = VSCodeIntegrator(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        existing = {"editor.formatOnSave": True, "files.trimTrailingWhitespace": True}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        settings = integrator._load_existing_settings(settings_file)

        assert settings == existing

    def test_load_existing_settings_invalid_json(self, tmp_path):
        """Test loading existing invalid settings.json."""
        integrator = VSCodeIntegrator(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        # Write invalid JSON
        with open(settings_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        settings = integrator._load_existing_settings(settings_file)

        # Should return empty dict on parse error
        assert settings == {}


class TestMergeSettings:
    """Test _merge_settings method."""

    def test_merge_settings_empty_existing(self, tmp_path):
        """Test merging with empty existing settings."""
        integrator = VSCodeIntegrator(tmp_path)

        existing = {}
        new = {
            "cmake.generator": "Ninja",
            "C_Cpp.default.compilerPath": "/usr/bin/clang",
        }

        merged = integrator._merge_settings(existing, new)

        assert merged == new

    def test_merge_settings_preserves_existing(self, tmp_path):
        """Test that merge preserves existing user settings."""
        integrator = VSCodeIntegrator(tmp_path)

        existing = {"editor.formatOnSave": True, "files.trimTrailingWhitespace": True}
        new = {
            "cmake.generator": "Ninja",
            "C_Cpp.default.compilerPath": "/usr/bin/clang",
        }

        merged = integrator._merge_settings(existing, new)

        assert merged["editor.formatOnSave"] is True
        assert merged["files.trimTrailingWhitespace"] is True
        assert merged["cmake.generator"] == "Ninja"
        assert merged["C_Cpp.default.compilerPath"] == "/usr/bin/clang"

    def test_merge_settings_overwrites_toolchainkit_keys(self, tmp_path):
        """Test that merge overwrites ToolchainKit-specific keys."""
        integrator = VSCodeIntegrator(tmp_path)

        existing = {
            "cmake.generator": "Unix Makefiles",
            "C_Cpp.default.compilerPath": "/usr/bin/gcc",
        }
        new = {
            "cmake.generator": "Ninja",
            "C_Cpp.default.compilerPath": "/usr/bin/clang",
        }

        merged = integrator._merge_settings(existing, new)

        assert merged["cmake.generator"] == "Ninja"
        assert merged["C_Cpp.default.compilerPath"] == "/usr/bin/clang"

    def test_merge_settings_merges_cmake_configure_settings(self, tmp_path):
        """Test that merge properly handles nested cmake.configureSettings."""
        integrator = VSCodeIntegrator(tmp_path)

        existing = {
            "cmake.configureSettings": {
                "CMAKE_BUILD_TYPE": "Debug",
                "BUILD_SHARED_LIBS": "ON",
            }
        }
        new = {
            "cmake.configureSettings": {
                "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/toolchain.cmake"
            }
        }

        merged = integrator._merge_settings(existing, new)

        # Should merge nested settings
        assert merged["cmake.configureSettings"]["CMAKE_BUILD_TYPE"] == "Debug"
        assert merged["cmake.configureSettings"]["BUILD_SHARED_LIBS"] == "ON"
        assert (
            merged["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/toolchain.cmake"
        )

    def test_merge_settings_overwrites_cmake_configure_settings_non_dict(
        self, tmp_path
    ):
        """Test merge when cmake.configureSettings is not a dict."""
        integrator = VSCodeIntegrator(tmp_path)

        existing = {"cmake.configureSettings": "invalid"}
        new = {
            "cmake.configureSettings": {
                "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/toolchain.cmake"
            }
        }

        merged = integrator._merge_settings(existing, new)

        # Should overwrite invalid value
        assert isinstance(merged["cmake.configureSettings"], dict)
        assert (
            merged["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/toolchain.cmake"
        )


class TestWriteSettings:
    """Test _write_settings method."""

    def test_write_settings_creates_file(self, tmp_path):
        """Test that write_settings creates file."""
        integrator = VSCodeIntegrator(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        settings = {"cmake.generator": "Ninja"}
        integrator._write_settings(settings_file, settings)

        assert settings_file.exists()

    def test_write_settings_valid_json(self, tmp_path):
        """Test that write_settings creates valid JSON."""
        integrator = VSCodeIntegrator(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        settings = {
            "cmake.generator": "Ninja",
            "C_Cpp.default.compilerPath": "/usr/bin/clang",
        }
        integrator._write_settings(settings_file, settings)

        with open(settings_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == settings

    def test_write_settings_pretty_formatted(self, tmp_path):
        """Test that write_settings uses pretty formatting."""
        integrator = VSCodeIntegrator(tmp_path)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        settings = {"cmake.generator": "Ninja"}
        integrator._write_settings(settings_file, settings)

        with open(settings_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Should have indentation
        assert "    " in content
        # Should have newline at end
        assert content.endswith("\n")


class TestIntegration:
    """Test full integration scenarios."""

    def test_generate_preserves_existing_user_settings(self, tmp_path):
        """Test that generating settings preserves existing user settings."""
        integrator = VSCodeIntegrator(tmp_path)

        # Create existing settings
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        existing = {
            "editor.formatOnSave": True,
            "files.trimTrailingWhitespace": True,
            "python.linting.enabled": True,
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        # Generate ToolchainKit settings
        integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
        )

        # Read merged settings
        with open(settings_file, "r", encoding="utf-8") as f:
            merged = json.load(f)

        # User settings should be preserved
        assert merged["editor.formatOnSave"] is True
        assert merged["files.trimTrailingWhitespace"] is True
        assert merged["python.linting.enabled"] is True

        # ToolchainKit settings should be added
        assert "cmake.configureSettings" in merged
        assert "C_Cpp.default.compilerPath" in merged
        assert "cmake.buildDirectory" in merged

    def test_generate_updates_toolchainkit_settings(self, tmp_path):
        """Test that generating settings updates existing ToolchainKit settings."""
        integrator = VSCodeIntegrator(tmp_path)

        # Create existing settings with old ToolchainKit config
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"

        existing = {
            "cmake.configureSettings": {
                "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/old-toolchain.cmake"
            },
            "C_Cpp.default.compilerPath": "/usr/bin/gcc",
            "cmake.generator": "Unix Makefiles",
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        # Generate with new toolchain
        integrator.generate_settings(
            toolchain_file=Path(".toolchainkit/cmake/new-toolchain.cmake"),
            compiler_path=Path("/usr/bin/clang"),
            generator="Ninja",
        )

        # Read updated settings
        with open(settings_file, "r", encoding="utf-8") as f:
            updated = json.load(f)

        # ToolchainKit settings should be updated
        assert (
            updated["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
            == "${workspaceFolder}/.toolchainkit/cmake/new-toolchain.cmake"
        )
        assert updated["C_Cpp.default.compilerPath"] == str(Path("/usr/bin/clang"))
        assert updated["cmake.generator"] == "Ninja"


class TestRecommendedExtensions:
    """Test recommended extensions functionality."""

    def test_get_recommended_extensions(self, tmp_path):
        """Test getting recommended extensions list."""
        integrator = VSCodeIntegrator(tmp_path)

        extensions = integrator.get_recommended_extensions()

        assert isinstance(extensions, list)
        assert len(extensions) > 0
        assert "ms-vscode.cpptools" in extensions
        assert "ms-vscode.cmake-tools" in extensions

    def test_generate_extensions_json(self, tmp_path):
        """Test generating extensions.json."""
        integrator = VSCodeIntegrator(tmp_path)

        extensions_file = integrator.generate_extensions_json()

        assert extensions_file.exists()
        assert extensions_file.name == "extensions.json"

        with open(extensions_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert "ms-vscode.cpptools" in data["recommendations"]


class TestVSCodeExceptionHandling:
    """Test exception handling in VSCodeIntegrator."""

    def test_load_existing_settings_generic_exception(self, tmp_path):
        """Test _load_existing_settings generic exception handling."""
        from unittest.mock import patch

        integrator = VSCodeIntegrator(tmp_path)
        settings_file = tmp_path / ".vscode" / "settings.json"
        settings_file.parent.mkdir()
        settings_file.touch()

        # Mock open to raise exception (not JSONDecodeError)
        with patch("builtins.open", side_effect=IOError("Read failed")):
            settings = integrator._load_existing_settings(settings_file)
            assert settings == {}

    def test_create_toolchainkit_settings_absolute_path_error(self, tmp_path):
        """Test _create_toolchainkit_settings with path error."""
        from unittest.mock import patch

        integrator = VSCodeIntegrator(tmp_path)

        # Create a path that cannot be relative to project root
        toolchain_file = Path("/opt/toolchain.cmake")

        with patch.object(Path, "relative_to", side_effect=ValueError("Not relative")):
            settings = integrator._create_toolchainkit_settings(
                toolchain_file=toolchain_file,
                compiler_path=Path("/usr/bin/clang"),
                build_dir="build",
                generator="Ninja",
                export_compile_commands=True,
                clang_tidy_path=Path("/usr/bin/clang-tidy"),
            )

            # Should fall back to absolute path
            assert (
                settings["cmake.configureSettings"]["CMAKE_TOOLCHAIN_FILE"]
                == f"${{workspaceFolder}}/{toolchain_file.as_posix()}"
            )
            assert settings["C_Cpp.codeAnalysis.clangTidy.path"] == str(
                Path("/usr/bin/clang-tidy")
            )

    def test_generate_tasks_with_clang_tools(self, tmp_path):
        """Test generating tasks with Clang tools."""
        integrator = VSCodeIntegrator(tmp_path)

        tasks_file = integrator.generate_tasks_config(
            clang_format_path=Path("/usr/bin/clang-format"),
            clang_tidy_path=Path("/usr/bin/clang-tidy"),
        )

        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)

        tasks = tasks_data.get("tasks", [])

        # Check Format Task
        format_task = next(
            (t for t in tasks if t["label"] == "Clang Format: All Files"), None
        )
        assert format_task is not None
        assert "clang-format" in format_task["command"]

        # Check Tidy Check Task
        tidy_check = next((t for t in tasks if t["label"] == "Clang Tidy: Check"), None)
        assert tidy_check is not None
        assert "clang-tidy" in tidy_check["command"]
        assert "-p build" in tidy_check["command"]

        # Check Tidy Fix Task
        tidy_fix = next((t for t in tasks if t["label"] == "Clang Tidy: Fix"), None)
        assert tidy_fix is not None
        assert "--fix" in tidy_fix["command"]

    def test_write_settings_exception(self, tmp_path):
        """Test _write_settings exception handling."""
        from unittest.mock import patch

        integrator = VSCodeIntegrator(tmp_path)
        settings_file = tmp_path / "settings.json"

        with patch("builtins.open", side_effect=IOError("Write failed")):
            with pytest.raises(IOError, match="Write failed"):
                integrator._write_settings(settings_file, {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
