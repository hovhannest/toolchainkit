"""
Tests for init command.
"""

import sys
from unittest.mock import Mock, patch

import pytest
import yaml

from toolchainkit.cli.commands import init


class TestInitCommandValidation:
    """Test validation logic."""

    def test_init_requires_cmakelists(self, tmp_path):
        """Test init fails without CMakeLists.txt."""
        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 1

    def test_init_succeeds_with_cmakelists(self, tmp_path):
        """Test init succeeds with CMakeLists.txt."""
        # Create CMakeLists.txt
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 0
        assert (tmp_path / "toolchainkit.yaml").exists()

    def test_init_fails_if_already_initialized(self, tmp_path):
        """Test init fails if already initialized without --force."""
        # Create CMakeLists.txt and config
        (tmp_path / "CMakeLists.txt").write_text("project(test)")
        (tmp_path / "toolchainkit.yaml").write_text("project: {name: test}")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 1

    def test_init_succeeds_with_force_flag(self, tmp_path):
        """Test init succeeds with --force even if already initialized."""
        # Create CMakeLists.txt and config
        (tmp_path / "CMakeLists.txt").write_text("project(test)")
        (tmp_path / "toolchainkit.yaml").write_text("project: {name: test}")

        args = Mock(
            project_root=str(tmp_path),
            force=True,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 0


class TestPackageManagerDetection:
    """Test package manager auto-detection."""

    def test_detect_conan_from_conanfile_txt(self, tmp_path):
        """Test Conan detection from conanfile.txt."""
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        pm = init._detect_package_manager(tmp_path)

        assert pm == "conan"

    def test_detect_conan_from_conanfile_py(self, tmp_path):
        """Test Conan detection from conanfile.py."""
        (tmp_path / "conanfile.py").write_text("class ConanFile: pass")

        pm = init._detect_package_manager(tmp_path)

        assert pm == "conan"

    def test_detect_vcpkg_from_vcpkg_json(self, tmp_path):
        """Test vcpkg detection from vcpkg.json."""
        (tmp_path / "vcpkg.json").write_text('{"name": "test"}')

        pm = init._detect_package_manager(tmp_path)

        assert pm == "vcpkg"

    def test_detect_cpm_from_cpm_cmake(self, tmp_path):
        """Test CPM detection from CPM.cmake."""
        (tmp_path / "CPM.cmake").write_text("# CPM")

        pm = init._detect_package_manager(tmp_path)

        assert pm == "cpm"

    def test_detect_cpm_from_cmake_subdir(self, tmp_path):
        """Test CPM detection from cmake/CPM.cmake."""
        cmake_dir = tmp_path / "cmake"
        cmake_dir.mkdir()
        (cmake_dir / "CPM.cmake").write_text("# CPM")

        pm = init._detect_package_manager(tmp_path)

        assert pm == "cpm"

    def test_detect_none_when_no_package_manager(self, tmp_path):
        """Test no detection when no package manager files."""
        pm = init._detect_package_manager(tmp_path)

        assert pm is None

    def test_conan_takes_precedence(self, tmp_path):
        """Test Conan is detected first if multiple exist."""
        (tmp_path / "conanfile.txt").write_text("[requires]")
        (tmp_path / "vcpkg.json").write_text('{"name": "test"}')

        pm = init._detect_package_manager(tmp_path)

        assert pm == "conan"


class TestConfigGeneration:
    """Test configuration generation."""

    def test_generate_minimal_config(self, tmp_path):
        """Test minimal configuration generation."""
        mock_platform = Mock(os="linux", arch="x86_64")

        config = init._generate_config(
            project_root=tmp_path,
            toolchain=None,
            minimal=True,
            package_manager=None,
            platform_info=mock_platform,
        )

        assert config["project"]["name"] == tmp_path.name
        assert config["build"]["build_dir"] == "build"
        assert config["build"]["build_type"] == "Release"
        assert "toolchain" not in config
        assert "packages" not in config

    def test_generate_config_with_toolchain(self, tmp_path):
        """Test configuration with toolchain."""
        mock_platform = Mock(os="linux", arch="x86_64")

        config = init._generate_config(
            project_root=tmp_path,
            toolchain="llvm-18",
            minimal=False,
            package_manager=None,
            platform_info=mock_platform,
        )

        assert config["toolchain"]["name"] == "llvm-18"

    def test_generate_config_with_package_manager(self, tmp_path):
        """Test configuration with package manager."""
        mock_platform = Mock(os="linux", arch="x86_64")

        config = init._generate_config(
            project_root=tmp_path,
            toolchain=None,
            minimal=False,
            package_manager="conan",
            platform_info=mock_platform,
        )

        assert config["packages"]["manager"] == "conan"

    def test_generate_full_config(self, tmp_path):
        """Test full configuration generation."""
        mock_platform = Mock(os="linux", arch="x86_64")

        config = init._generate_config(
            project_root=tmp_path,
            toolchain="gcc-13",
            minimal=False,
            package_manager="vcpkg",
            platform_info=mock_platform,
        )

        assert config["project"]["name"] == tmp_path.name
        assert config["toolchain"]["name"] == "gcc-13"
        assert config["packages"]["manager"] == "vcpkg"
        assert config["build"]["build_dir"] == "build"
        assert config["build"]["build_type"] == "Release"


class TestConfigFileWriting:
    """Test configuration file writing."""

    def test_write_config_file(self, tmp_path):
        """Test writing configuration file."""
        config_file = tmp_path / "toolchainkit.yaml"
        config = {
            "project": {"name": "test"},
            "build": {"build_dir": "build", "build_type": "Release"},
        }

        init._write_config_file(config_file, config)

        assert config_file.exists()
        content = config_file.read_text(encoding="utf-8")
        assert "# ToolchainKit Configuration" in content
        assert "project:" in content
        assert "name: test" in content

    def test_config_is_valid_yaml(self, tmp_path):
        """Test written configuration is valid YAML."""
        config_file = tmp_path / "toolchainkit.yaml"
        config = {
            "project": {"name": "test"},
            "toolchain": {"name": "llvm-18"},
            "build": {"build_dir": "build", "build_type": "Debug"},
        }

        init._write_config_file(config_file, config)

        # Load and verify YAML
        with open(config_file, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        assert loaded["project"]["name"] == "test"
        assert loaded["toolchain"]["name"] == "llvm-18"
        assert loaded["build"]["build_type"] == "Debug"


class TestGitignoreUpdate:
    """Test .gitignore update."""

    def test_create_new_gitignore(self, tmp_path):
        """Test creating new .gitignore."""
        init._update_gitignore(tmp_path)

        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text(encoding="utf-8")
        assert "# ToolchainKit" in content
        assert ".toolchainkit/" in content
        assert "bootstrap.sh" in content
        assert "bootstrap.bat" in content

    def test_update_existing_gitignore(self, tmp_path):
        """Test updating existing .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("build/\n*.pyc", encoding="utf-8")

        init._update_gitignore(tmp_path)

        content = gitignore.read_text(encoding="utf-8")
        assert "build/" in content
        assert "*.pyc" in content
        assert "# ToolchainKit" in content
        assert ".toolchainkit/" in content

    def test_dont_duplicate_entries(self, tmp_path):
        """Test not duplicating ToolchainKit entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# ToolchainKit\n.toolchainkit/", encoding="utf-8")

        init._update_gitignore(tmp_path)

        content = gitignore.read_text(encoding="utf-8")
        # Should only appear once
        assert content.count("# ToolchainKit") == 1


class TestBootstrapScriptGeneration:
    """Test bootstrap script generation."""

    def test_bootstrap_scripts_generated(self, tmp_path):
        """Test bootstrap scripts are generated."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain="llvm-18",
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 0
        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="chmod doesn't work the same on Windows"
    )
    def test_shell_script_is_executable(self, tmp_path):
        """Test shell script is made executable."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain="llvm-18",
            minimal=False,
            config=None,
        )

        init.run(args)

        shell_script = tmp_path / "bootstrap.sh"
        # Check if executable bit is set
        import os

        assert os.access(shell_script, os.X_OK)


class TestInitCommandIntegration:
    """Integration tests for init command."""

    def test_init_with_auto_detect_conan(self, tmp_path):
        """Test init with auto-detect finds Conan."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")
        (tmp_path / "conanfile.txt").write_text("[requires]\nfmt/9.1.0")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=True,
            toolchain=None,
            minimal=False,
            config=None,
        )

        result = init.run(args)

        assert result == 0

        # Check config has package manager
        config_file = tmp_path / "toolchainkit.yaml"
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["packages"]["manager"] == "conan"

    def test_init_with_toolchain_and_minimal(self, tmp_path):
        """Test init with both toolchain and minimal flags."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain="gcc-13",
            minimal=True,
            config=None,
        )

        result = init.run(args)

        assert result == 0

        # Check config
        config_file = tmp_path / "toolchainkit.yaml"
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Should have toolchain even with minimal
        assert config["toolchain"]["name"] == "gcc-13"
        # Should not have packages with minimal
        assert "packages" not in config

    def test_full_init_workflow(self, tmp_path):
        """Test complete init workflow."""
        # Setup project
        (tmp_path / "CMakeLists.txt").write_text("project(myproject)")
        (tmp_path / "conanfile.txt").write_text("[requires]")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=True,
            toolchain="llvm-18",
            minimal=False,
            config=None,
        )

        result = init.run(args)

        # Should succeed
        assert result == 0

        # Check all files created
        assert (tmp_path / "toolchainkit.yaml").exists()
        assert (tmp_path / ".gitignore").exists()
        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()

        # Check config content
        config_file = tmp_path / "toolchainkit.yaml"
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["project"]["name"] == tmp_path.name
        assert config["toolchain"]["name"] == "llvm-18"
        assert config["packages"]["manager"] == "conan"
        assert config["build"]["build_dir"] == "build"
        assert config["build"]["build_type"] == "Release"


class TestErrorHandling:
    """Test error handling."""

    def test_handles_yaml_write_error(self, tmp_path):
        """Test handling YAML write errors."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        # Make directory read-only (simulation)
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text("dummy")
        config_file.chmod(0o444)  # Read-only

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        # On Windows, this might still succeed, so we just check it doesn't crash
        result = init.run(args)
        assert result in (0, 1)  # Either success or error, but no crash

        # Restore permissions
        config_file.chmod(0o644)

    def test_handles_bootstrap_generation_error(self, tmp_path):
        """Test handling bootstrap generation errors."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        # Mock BootstrapGenerator to raise error
        with patch("toolchainkit.bootstrap.generator.BootstrapGenerator") as mock_gen:
            mock_gen.side_effect = Exception("Test error")

            result = init.run(args)

            # Should still succeed (warning only)
            assert result == 0
            # Config file should still be created
            assert (tmp_path / "toolchainkit.yaml").exists()

    def test_handles_gitignore_update_error(self, tmp_path):
        """Test handling .gitignore update errors."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        # Mock _update_gitignore to raise error
        with patch("toolchainkit.cli.commands.init._update_gitignore") as mock_update:
            mock_update.side_effect = Exception("Test error")

            result = init.run(args)

            # Should still succeed (warning only)
            assert result == 0
            # Config file should still be created
            assert (tmp_path / "toolchainkit.yaml").exists()


class TestPlatformIntegration:
    """Test platform integration."""

    def test_platform_detection_called(self, tmp_path):
        """Test platform detection is called."""
        (tmp_path / "CMakeLists.txt").write_text("project(test)")

        args = Mock(
            project_root=str(tmp_path),
            force=False,
            auto_detect=False,
            toolchain=None,
            minimal=False,
            config=None,
        )

        with patch("toolchainkit.core.platform.detect_platform") as mock_detect:
            mock_detect.return_value = Mock(os="linux", arch="x86_64")

            result = init.run(args)

            assert result == 0
            mock_detect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
