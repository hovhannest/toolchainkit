"""
Tests for bootstrap command.
"""

from unittest.mock import Mock

import yaml

from toolchainkit.cli.commands import bootstrap


def create_mock_args(**kwargs):
    """
    Create a Mock args object with default Phase 2 attributes set to None.

    This ensures backward compatibility with existing tests while supporting
    new Phase 2 advanced configuration features.
    """
    defaults = {
        "cmake_args": None,
        "env": None,
        "pre_configure_hook": None,
        "post_configure_hook": None,
        "config": None,
        "validate": False,
    }
    # Update with provided kwargs
    defaults.update(kwargs)
    return Mock(**defaults)


class TestBootstrapCommandValidation:
    """Test validation logic."""

    def test_bootstrap_requires_initialization(self, tmp_path):
        """Test bootstrap fails if project not initialized."""
        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 1

    def test_bootstrap_succeeds_when_initialized(self, tmp_path):
        """Test bootstrap succeeds with valid configuration."""
        # Create toolchainkit.yaml
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release", "build_dir": "build"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()

    def test_bootstrap_fails_if_scripts_exist_without_force(self, tmp_path):
        """Test bootstrap fails if scripts exist without --force."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        # Create existing scripts
        (tmp_path / "bootstrap.sh").write_text("#!/bin/bash")
        (tmp_path / "bootstrap.bat").write_text("@echo off")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 1

    def test_bootstrap_succeeds_with_force_flag(self, tmp_path):
        """Test bootstrap succeeds with --force even if scripts exist."""
        # Create toolchainkit.yaml - use llvm which is supported on all platforms
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        # Create existing scripts
        (tmp_path / "bootstrap.sh").write_text("#!/bin/bash\nold content")
        (tmp_path / "bootstrap.bat").write_text("@echo off\nold content")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=True,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        # Verify new content
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-18" in shell_content
        assert "old content" not in shell_content


class TestDryRunMode:
    """Test dry-run functionality."""

    def test_dry_run_does_not_create_files(self, tmp_path, capsys):
        """Test --dry-run doesn't create files."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=True,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert not (tmp_path / "bootstrap.sh").exists()
        assert not (tmp_path / "bootstrap.bat").exists()

        # Check preview output
        captured = capsys.readouterr()
        assert "PREVIEW" in captured.out
        assert "bootstrap.sh" in captured.out
        assert "bootstrap.bat" in captured.out

    def test_dry_run_shows_script_content(self, tmp_path, capsys):
        """Test --dry-run displays script content."""
        # Create toolchainkit.yaml - use llvm which is supported on all platforms
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=True,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "llvm-18" in captured.out
        assert "#!/bin/bash" in captured.out

    def test_dry_run_bypasses_existing_check(self, tmp_path):
        """Test --dry-run works even if scripts exist."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        # Create existing scripts
        (tmp_path / "bootstrap.sh").write_text("#!/bin/bash\nold content")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=True,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0


class TestPlatformSelection:
    """Test platform-specific script generation."""

    def test_platform_unix_only(self, tmp_path):
        """Test --platform unix generates only shell script."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert (tmp_path / "bootstrap.sh").exists()
        assert not (tmp_path / "bootstrap.bat").exists()

    def test_platform_windows_only(self, tmp_path):
        """Test --platform windows generates only batch script."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="windows",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert not (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()

    def test_platform_all_generates_both(self, tmp_path):
        """Test --platform all generates both scripts."""
        # Create toolchainkit.yaml
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()


class TestCLIOverrides:
    """Test CLI argument overrides."""

    def test_toolchain_override(self, tmp_path):
        """Test --toolchain overrides config value."""
        # Create toolchainkit.yaml with default toolchain
        config = {"toolchain": {"name": "llvm-18"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain="llvm-19",  # Override to different llvm version
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-19" in shell_content
        assert "llvm-18" not in shell_content

    def test_build_type_override(self, tmp_path):
        """Test --build-type overrides config value."""
        # Create toolchainkit.yaml with default build type
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type="Debug",  # Override
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "Debug" in shell_content

    def test_both_overrides(self, tmp_path):
        """Test multiple CLI overrides work together."""
        # Create toolchainkit.yaml
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain="llvm-19",
            build_type="Debug",
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-19" in shell_content
        assert "Debug" in shell_content


class TestConfigurationFormats:
    """Test different configuration formats."""

    def test_nested_toolchain_config(self, tmp_path):
        """Test nested toolchain configuration."""
        config = {"toolchain": {"name": "llvm-18", "version": "18.1.0"}}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-18" in shell_content

    def test_string_toolchain_config(self, tmp_path):
        """Test simple string toolchain configuration."""
        config = {"toolchain": "llvm-18"}
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-18" in shell_content

    def test_custom_config_path(self, tmp_path):
        """Test --config option for custom config path."""
        # Create custom config in subdirectory
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config = {"toolchain": {"name": "llvm-19"}}
        custom_config = config_dir / "custom.yaml"
        custom_config.write_text(yaml.safe_dump(config), encoding="utf-8")

        # Also create default config to verify it's not used
        default_config = tmp_path / "toolchainkit.yaml"
        default_config.write_text(
            yaml.safe_dump({"toolchain": {"name": "llvm-18"}}), encoding="utf-8"
        )

        args = create_mock_args(
            project_root=str(tmp_path),
            config=custom_config,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "llvm-19" in shell_content
        assert "gcc-13" not in shell_content


class TestPackageManagerIntegration:
    """Test package manager configuration in scripts."""

    def test_conan_package_manager(self, tmp_path):
        """Test Conan package manager in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "packages": {"manager": "conan"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_content = (tmp_path / "bootstrap.sh").read_text()
        assert "conan" in shell_content.lower()

    def test_vcpkg_package_manager(self, tmp_path):
        """Test vcpkg package manager in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "packages": {"manager": "vcpkg"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="windows",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        batch_content = (tmp_path / "bootstrap.bat").read_text()
        assert "vcpkg" in batch_content.lower()


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML."""
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text("invalid: yaml: content: :", encoding="utf-8")

        args = create_mock_args(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 1

    def test_missing_config_file(self, tmp_path):
        """Test error when config file doesn't exist."""
        args = create_mock_args(
            project_root=str(tmp_path),
            config=tmp_path / "nonexistent.yaml",
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
        )

        result = bootstrap.run(args)

        assert result == 1


class TestFlattenConfig:
    """Test configuration flattening."""

    def test_flatten_nested_config(self):
        """Test flattening nested configuration."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release", "build_dir": "build"},
            "packages": {"manager": "conan"},
        }

        flat = bootstrap._flatten_config(config)

        assert flat["toolchain"] == "llvm-18"
        assert flat["build_type"] == "Release"
        assert flat["build_dir"] == "build"
        assert flat["package_manager"] == "conan"

    def test_flatten_empty_config(self):
        """Test flattening empty configuration."""
        flat = bootstrap._flatten_config({})

        # Empty config should return defaults
        assert flat["toolchain"] == "llvm-18"
        assert flat["build_type"] == "Release"
        assert flat["build_dir"] == "build"
        assert "package_manager" not in flat

    def test_flatten_partial_config(self):
        """Test flattening partial configuration."""
        config = {"toolchain": {"name": "gcc-13"}}

        flat = bootstrap._flatten_config(config)

        assert flat["toolchain"] == "gcc-13"
        # Partial config should still provide defaults for missing values
        assert flat["build_type"] == "Release"
        assert flat["build_dir"] == "build"
        assert "package_manager" not in flat


class TestAdvancedConfiguration:
    """Test Phase 2: Advanced configuration options."""

    def test_cmake_args_in_generated_script(self, tmp_path):
        """Test additional CMake arguments appear in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=["-DENABLE_TESTS=ON", "-DBUILD_SHARED_LIBS=ON"],
            env=None,
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_script = tmp_path / "bootstrap.sh"
        assert shell_script.exists()
        content = shell_script.read_text(encoding="utf-8")
        assert "-DENABLE_TESTS=ON" in content
        assert "-DBUILD_SHARED_LIBS=ON" in content

    def test_environment_variables_in_generated_script(self, tmp_path):
        """Test environment variables appear in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=[["CC", "clang"], ["CXX", "clang++"]],
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_script = tmp_path / "bootstrap.sh"
        assert shell_script.exists()
        content = shell_script.read_text(encoding="utf-8")
        assert "export CC=" in content or "CC=" in content
        assert "export CXX=" in content or "CXX=" in content
        assert "clang" in content
        assert "clang++" in content

    def test_pre_configure_hook_in_generated_script(self, tmp_path):
        """Test pre-configure hook appears in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook="./scripts/setup.sh",
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_script = tmp_path / "bootstrap.sh"
        assert shell_script.exists()
        content = shell_script.read_text(encoding="utf-8")
        assert "./scripts/setup.sh" in content
        assert "pre_configure hook" in content.lower()

    def test_post_configure_hook_in_generated_script(self, tmp_path):
        """Test post-configure hook appears in generated scripts."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook=None,
            post_configure_hook="./scripts/cleanup.sh",
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_script = tmp_path / "bootstrap.sh"
        assert shell_script.exists()
        content = shell_script.read_text(encoding="utf-8")
        assert "./scripts/cleanup.sh" in content
        assert "post_configure hook" in content.lower()

    def test_all_advanced_options_combined(self, tmp_path):
        """Test all advanced options work together."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="unix",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=["-DENABLE_TESTS=ON"],
            env=[["CC", "clang"]],
            pre_configure_hook="./scripts/setup.sh",
            post_configure_hook="./scripts/cleanup.sh",
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        shell_script = tmp_path / "bootstrap.sh"
        assert shell_script.exists()
        content = shell_script.read_text(encoding="utf-8")
        # Verify all options are present
        assert "-DENABLE_TESTS=ON" in content
        assert "CC=" in content or "export CC=" in content
        assert "./scripts/setup.sh" in content
        assert "./scripts/cleanup.sh" in content


class TestPowerShellSupport:
    """Test Phase 5: PowerShell support."""

    def test_generate_powershell_script(self, tmp_path):
        """Test PowerShell script generation."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="powershell",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        powershell_script = tmp_path / "bootstrap.ps1"
        assert powershell_script.exists()
        content = powershell_script.read_text(encoding="utf-8")
        # Check PowerShell syntax
        assert "Write-Host" in content
        assert "$LASTEXITCODE" in content
        assert "cmake" in content.lower()

    def test_powershell_included_in_all_platform(self, tmp_path):
        """Test PowerShell script is generated with --platform all."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="all",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()
        assert (tmp_path / "bootstrap.ps1").exists()

    def test_powershell_with_environment_variables(self, tmp_path):
        """Test PowerShell script with environment variables."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="powershell",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=[["MY_VAR", "value123"]],
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        powershell_script = tmp_path / "bootstrap.ps1"
        assert powershell_script.exists()
        content = powershell_script.read_text(encoding="utf-8")
        assert "$env:MY_VAR" in content
        assert "value123" in content

    def test_powershell_with_hooks(self, tmp_path):
        """Test PowerShell script with pre/post configure hooks."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=False,
            platform="powershell",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook=".\\scripts\\setup.ps1",
            post_configure_hook=".\\scripts\\cleanup.ps1",
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        powershell_script = tmp_path / "bootstrap.ps1"
        assert powershell_script.exists()
        content = powershell_script.read_text(encoding="utf-8")
        assert ".\\scripts\\setup.ps1" in content or "./scripts/setup.ps1" in content
        assert (
            ".\\scripts\\cleanup.ps1" in content or "./scripts/cleanup.ps1" in content
        )

    def test_powershell_dry_run(self, tmp_path, capsys):
        """Test PowerShell script preview in dry-run mode."""
        config = {
            "toolchain": {"name": "llvm-18"},
            "build": {"build_type": "Release"},
        }
        config_file = tmp_path / "toolchainkit.yaml"
        config_file.write_text(yaml.safe_dump(config), encoding="utf-8")

        args = Mock(
            project_root=str(tmp_path),
            config=None,
            force=False,
            dry_run=True,
            platform="powershell",
            toolchain=None,
            build_type=None,
            verbose=False,
            cmake_args=None,
            env=None,
            pre_configure_hook=None,
            post_configure_hook=None,
            validate=False,
        )

        result = bootstrap.run(args)

        assert result == 0
        # Verify no files created
        assert not (tmp_path / "bootstrap.ps1").exists()
        # Verify preview output
        captured = capsys.readouterr()
        assert "bootstrap.ps1" in captured.out
        assert "PowerShell" in captured.out
        assert "Write-Host" in captured.out
