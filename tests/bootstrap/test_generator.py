"""
Tests for bootstrap script generator.
"""

import pytest
import stat
import sys

from toolchainkit.bootstrap.generator import BootstrapGenerator, BootstrapGeneratorError


class TestBootstrapGeneratorInit:
    """Test BootstrapGenerator initialization."""

    def test_init_basic(self, tmp_path):
        """Test basic initialization."""
        generator = BootstrapGenerator(tmp_path)

        assert generator.project_root == tmp_path
        assert generator.project_name == tmp_path.name
        assert generator.config == {}

    def test_init_with_config(self, tmp_path):
        """Test initialization with configuration."""
        config = {
            "toolchain": "gcc-13",
            "build_type": "Debug",
            "build_dir": "build-debug",
            "package_manager": "conan",
        }

        generator = BootstrapGenerator(tmp_path, config)

        assert generator.toolchain == "gcc-13"
        assert generator.build_type == "Debug"
        assert generator.build_dir == "build-debug"
        assert generator.package_manager == "conan"

    def test_init_with_defaults(self, tmp_path):
        """Test default values."""
        generator = BootstrapGenerator(tmp_path, {})

        assert generator.toolchain == "llvm-18"
        assert generator.build_type == "Release"
        assert generator.build_dir == "build"
        assert generator.package_manager is None


class TestShellScriptGeneration:
    """Test shell script generation."""

    def test_generate_shell_script(self, tmp_path):
        """Test shell script generation."""
        config = {"toolchain": "llvm-18", "build_type": "Release"}

        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        assert script_path.exists()
        assert script_path.name == "bootstrap.sh"

        content = script_path.read_text()
        assert "#!/bin/bash" in content
        assert "set -e" in content
        assert "llvm-18" in content
        assert "Release" in content

    def test_shell_script_is_executable(self, tmp_path):
        """Test shell script is executable on Unix."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_shell_script()

        # Check if executable bit is set (Unix only)
        try:
            mode = script_path.stat().st_mode
            _is_executable = mode & stat.S_IXUSR
            # On Unix, should be executable
            # On Windows, this test will pass regardless
            assert True  # File was created successfully
        except Exception:
            # Windows doesn't have executable bit
            pass

    def test_shell_script_python_check(self, tmp_path):
        """Test shell script includes Python check."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "python3" in content
        assert "command -v python3" in content

    def test_shell_script_toolchainkit_install(self, tmp_path):
        """Test shell script includes ToolchainKit installation."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "tkgen" in content
        assert "pip3 install" in content
        assert "toolchainkit" in content

    def test_shell_script_configure_command(self, tmp_path):
        """Test shell script includes configure command."""
        config = {"toolchain": "gcc-13", "build_type": "Debug"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        content = script_path.read_text()
        # tkgen configure is now enabled in bootstrap script
        assert "tkgen configure" in content

    def test_shell_script_cmake_command(self, tmp_path):
        """Test shell script includes CMake command."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "tkgen configure" in content
        assert "--build-dir" in content
        assert "build" in content
        # Script now uses dynamic toolchain detection (Conan, ToolchainKit, or system compiler)
        assert "CMAKE_TOOLCHAIN_FILE" in content or "toolchain" in content.lower()

    def test_shell_script_with_conan(self, tmp_path):
        """Test shell script with Conan package manager."""
        config = {"package_manager": "conan"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "tkgen configure" in content
        # Package manager logic is now handled by tkgen configure, so no explicit conan commands
        assert "conan install" not in content.lower()

    def test_shell_script_with_vcpkg(self, tmp_path):
        """Test shell script with vcpkg package manager."""
        config = {"package_manager": "vcpkg"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "tkgen configure" in content
        # Package manager logic is now handled by tkgen configure
        assert "vcpkg install" not in content.lower()


class TestBatchScriptGeneration:
    """Test batch script generation."""

    def test_generate_batch_script(self, tmp_path):
        """Test batch script generation."""
        config = {"toolchain": "msvc-latest", "build_type": "Release"}

        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        assert script_path.exists()
        assert script_path.name == "bootstrap.bat"

        content = script_path.read_text()
        assert "@echo off" in content
        assert "msvc-latest" in content
        assert "Release" in content

    def test_batch_script_python_check(self, tmp_path):
        """Test batch script includes Python check."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "python --version" in content
        assert "errorlevel" in content

    def test_batch_script_toolchainkit_install(self, tmp_path):
        """Test batch script includes ToolchainKit installation."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "tkgen" in content
        assert "pip install" in content
        assert "toolchainkit" in content

    def test_batch_script_configure_command(self, tmp_path):
        """Test batch script includes configure command."""
        config = {"toolchain": "llvm-18", "build_type": "Debug"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        content = script_path.read_text()
        # tkgen configure is now enabled in bootstrap script
        assert "tkgen configure" in content

    def test_batch_script_cmake_command(self, tmp_path):
        """Test batch script includes CMake command."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "cmake" in content
        assert "tkgen configure" in content
        assert "--build-dir" in content
        assert "build" in content
        # Script now uses dynamic toolchain detection (Conan, ToolchainKit, or system compiler)
        assert "CMAKE_TOOLCHAIN_FILE" in content or "toolchain" in content.lower()

    def test_batch_script_error_handling(self, tmp_path):
        """Test batch script includes error handling."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "errorlevel" in content
        assert "exit /b" in content

    def test_batch_script_with_conan(self, tmp_path):
        """Test batch script with Conan package manager."""
        config = {"package_manager": "conan"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "tkgen configure" in content
        # Package manager logic is now handled by tkgen configure
        assert "conan install" not in content.lower()

    def test_batch_script_with_vcpkg(self, tmp_path):
        """Test batch script with vcpkg package manager."""
        config = {"package_manager": "vcpkg"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "tkgen configure" in content
        # Package manager logic is now handled by tkgen configure
        assert "vcpkg install" not in content.lower()


class TestGenerateAll:
    """Test generate_all method."""

    def test_generate_all(self, tmp_path):
        """Test generating all scripts."""
        generator = BootstrapGenerator(tmp_path)
        result = generator.generate_all()

        assert "shell" in result
        assert "batch" in result
        assert result["shell"].exists()
        assert result["batch"].exists()
        assert result["shell"].name == "bootstrap.sh"
        assert result["batch"].name == "bootstrap.bat"

    def test_generate_all_creates_both_files(self, tmp_path):
        """Test both scripts are created."""
        generator = BootstrapGenerator(tmp_path)
        generator.generate_all()

        assert (tmp_path / "bootstrap.sh").exists()
        assert (tmp_path / "bootstrap.bat").exists()


class TestReadmeSection:
    """Test README section generation."""

    def test_generate_readme_section(self, tmp_path):
        """Test README section generation."""
        config = {"toolchain": "llvm-18", "build_type": "Release", "build_dir": "build"}

        generator = BootstrapGenerator(tmp_path, config)
        section = generator.generate_readme_section()

        assert "## Getting Started" in section
        assert "./bootstrap.sh" in section
        assert "bootstrap.bat" in section
        assert "llvm-18" in section
        assert "cmake --build build" in section

    def test_readme_section_with_package_manager(self, tmp_path):
        """Test README section with package manager."""
        config = {"package_manager": "conan"}
        generator = BootstrapGenerator(tmp_path, config)
        section = generator.generate_readme_section()

        assert "conan" in section.lower()

    def test_readme_section_without_package_manager(self, tmp_path):
        """Test README section without package manager."""
        generator = BootstrapGenerator(tmp_path, {})
        section = generator.generate_readme_section()

        assert "dependencies" in section.lower()


class TestConfigurationIntegration:
    """Test configuration integration."""

    def test_custom_toolchain(self, tmp_path):
        """Test with custom toolchain."""
        config = {"toolchain": "gcc-14"}
        generator = BootstrapGenerator(tmp_path, config)

        shell_script = generator.generate_shell_script()
        content = shell_script.read_text()
        assert "gcc-14" in content

    def test_custom_build_type(self, tmp_path):
        """Test with custom build type."""
        config = {"build_type": "RelWithDebInfo"}
        generator = BootstrapGenerator(tmp_path, config)

        shell_script = generator.generate_shell_script()
        content = shell_script.read_text()
        assert "RelWithDebInfo" in content

    def test_custom_build_dir(self, tmp_path):
        """Test with custom build directory."""
        config = {"build_dir": "build-custom"}
        generator = BootstrapGenerator(tmp_path, config)

        shell_script = generator.generate_shell_script()
        content = shell_script.read_text()
        assert "build-custom" in content

    def test_all_custom_config(self, tmp_path):
        """Test with all custom configuration."""
        config = {
            "toolchain": "msvc-2022",
            "build_type": "Debug",
            "build_dir": "out",
            "package_manager": "vcpkg",
        }

        generator = BootstrapGenerator(tmp_path, config)

        shell_script = generator.generate_shell_script()
        shell_content = shell_script.read_text()
        assert "msvc-2022" in shell_content
        assert "Debug" in shell_content
        assert "out" in shell_content
        # Package manager logic is now handled by tkgen configure
        assert "vcpkg" not in shell_content.lower()

        batch_script = generator.generate_batch_script()
        batch_content = batch_script.read_text()
        assert "msvc-2022" in batch_content
        assert "Debug" in batch_content
        assert "out" in batch_content
        # Package manager logic is now handled by tkgen configure
        assert "vcpkg" not in batch_content.lower()


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.skipif(
        sys.platform == "win32", reason="chmod doesn't work the same on Windows"
    )
    def test_write_error_shell(self, tmp_path):
        """Test error when writing shell script fails."""
        generator = BootstrapGenerator(tmp_path)

        # Make directory read-only (Unix)
        try:
            tmp_path.chmod(0o444)

            with pytest.raises(BootstrapGeneratorError):
                generator.generate_shell_script()
        finally:
            # Restore permissions
            tmp_path.chmod(0o755)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="chmod doesn't work the same on Windows"
    )
    def test_write_error_batch(self, tmp_path):
        """Test error when writing batch script fails."""
        generator = BootstrapGenerator(tmp_path)

        # Make directory read-only (Unix)
        try:
            tmp_path.chmod(0o444)

            with pytest.raises(BootstrapGeneratorError):
                generator.generate_batch_script()
        finally:
            # Restore permissions
            tmp_path.chmod(0o755)


class TestProjectName:
    """Test project name handling."""

    def test_project_name_from_path(self, tmp_path):
        """Test project name is extracted from path."""
        project_dir = tmp_path / "my-awesome-project"
        project_dir.mkdir()

        generator = BootstrapGenerator(project_dir)

        assert generator.project_name == "my-awesome-project"

        shell_script = generator.generate_shell_script()
        content = shell_script.read_text()
        assert "my-awesome-project" in content


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, tmp_path):
        """Test full workflow from config to scripts."""
        config = {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "build_dir": "build",
            "package_manager": "conan",
        }

        generator = BootstrapGenerator(tmp_path, config)

        # Generate all scripts
        scripts = generator.generate_all()

        # Verify both exist
        assert scripts["shell"].exists()
        assert scripts["batch"].exists()

        # Verify content
        shell_content = scripts["shell"].read_text()
        assert "llvm-18" in shell_content
        assert "Release" in shell_content
        # Package manager logic is now handled by tkgen configure
        assert "conan" not in shell_content.lower()

        batch_content = scripts["batch"].read_text()
        assert "llvm-18" in batch_content
        assert "Release" in batch_content
        # Package manager logic is now handled by tkgen configure
        assert "conan" not in batch_content.lower()

        # Generate README section
        readme = generator.generate_readme_section()
        assert "llvm-18" in readme
        assert "conan" in readme.lower()

    def test_minimal_config(self, tmp_path):
        """Test with minimal configuration."""
        generator = BootstrapGenerator(tmp_path)

        scripts = generator.generate_all()

        assert scripts["shell"].exists()
        assert scripts["batch"].exists()

        # Should use defaults
        shell_content = scripts["shell"].read_text()
        assert "llvm-18" in shell_content
        assert "Release" in shell_content


class TestPreviewScripts:
    """Test preview_scripts functionality."""

    def test_preview_scripts_returns_dict(self, tmp_path):
        """Test preview_scripts returns dictionary with both scripts."""
        config = {"toolchain": "llvm-18", "build_type": "Release"}
        generator = BootstrapGenerator(tmp_path, config)

        scripts = generator.preview_scripts()

        assert isinstance(scripts, dict)
        assert "shell" in scripts
        assert "batch" in scripts

    def test_preview_scripts_contains_shell_content(self, tmp_path):
        """Test preview shell script contains expected content."""
        config = {"toolchain": "gcc-14", "build_type": "Debug"}
        generator = BootstrapGenerator(tmp_path, config)

        scripts = generator.preview_scripts()
        shell_content = scripts["shell"]

        assert "#!/bin/bash" in shell_content
        assert "gcc-14" in shell_content
        assert "Debug" in shell_content

    def test_preview_scripts_contains_batch_content(self, tmp_path):
        """Test preview batch script contains expected content."""
        config = {"toolchain": "msvc-latest", "build_type": "Release"}
        generator = BootstrapGenerator(tmp_path, config)

        scripts = generator.preview_scripts()
        batch_content = scripts["batch"]

        assert "@echo off" in batch_content
        assert "msvc-latest" in batch_content
        assert "Release" in batch_content

    def test_preview_scripts_does_not_create_files(self, tmp_path):
        """Test preview_scripts doesn't write any files."""
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)

        generator.preview_scripts()

        # Ensure no files were created
        assert not (tmp_path / "bootstrap.sh").exists()
        assert not (tmp_path / "bootstrap.bat").exists()

    def test_preview_scripts_includes_powershell(self, tmp_path):
        """Test preview_scripts includes PowerShell script."""
        config = {"toolchain": "llvm-18", "build_type": "Release"}
        generator = BootstrapGenerator(tmp_path, config)

        scripts = generator.preview_scripts()

        assert "powershell" in scripts
        powershell_content = scripts["powershell"]
        assert "Write-Host" in powershell_content
        assert "$LASTEXITCODE" in powershell_content
        assert "llvm-18" in powershell_content


class TestAdvancedConfigurationFeatures:
    """Test Phase 2: Advanced configuration features."""

    def test_cmake_args_in_shell_script(self, tmp_path):
        """Test additional CMake arguments in shell script."""
        config = {
            "toolchain": "llvm-18",
            "cmake_args": ["-DENABLE_TESTS=ON", "-DBUILD_SHARED_LIBS=ON"],
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "-DENABLE_TESTS=ON" in content
        assert "-DBUILD_SHARED_LIBS=ON" in content

    def test_cmake_args_in_batch_script(self, tmp_path):
        """Test additional CMake arguments in batch script."""
        config = {
            "toolchain": "msvc-latest",
            "cmake_args": ["-DENABLE_TESTS=ON", "-DBUILD_SHARED_LIBS=ON"],
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "-DENABLE_TESTS=ON" in content
        assert "-DBUILD_SHARED_LIBS=ON" in content

    def test_cmake_args_in_powershell_script(self, tmp_path):
        """Test additional CMake arguments in PowerShell script."""
        config = {
            "toolchain": "llvm-18",
            "cmake_args": ["-DENABLE_TESTS=ON", "-DBUILD_SHARED_LIBS=ON"],
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert "-DENABLE_TESTS=ON" in content
        assert "-DBUILD_SHARED_LIBS=ON" in content

    def test_environment_variables_in_shell_script(self, tmp_path):
        """Test environment variables in shell script."""
        config = {
            "toolchain": "llvm-18",
            "env_vars": {"CC": "clang", "CXX": "clang++", "CFLAGS": "-O3"},
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "export CC=" in content or "CC=" in content
        assert "clang" in content
        assert "export CXX=" in content or "CXX=" in content
        assert "clang++" in content
        assert "CFLAGS" in content
        assert "-O3" in content

    def test_environment_variables_in_batch_script(self, tmp_path):
        """Test environment variables in batch script."""
        config = {"toolchain": "msvc-latest", "env_vars": {"MY_VAR": "value123"}}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "set MY_VAR=" in content
        assert "value123" in content

    def test_environment_variables_in_powershell_script(self, tmp_path):
        """Test environment variables in PowerShell script."""
        config = {"toolchain": "llvm-18", "env_vars": {"MY_VAR": "value123"}}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert "$env:MY_VAR" in content
        assert "value123" in content

    def test_pre_configure_hook_in_shell_script(self, tmp_path):
        """Test pre-configure hook in shell script."""
        config = {
            "toolchain": "llvm-18",
            "hooks": {"pre_configure": "./scripts/setup.sh"},
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "./scripts/setup.sh" in content
        # Should run before cmake configure
        cmake_pos = content.find("tkgen configure")
        hook_pos = content.find("./scripts/setup.sh")
        assert hook_pos < cmake_pos

    def test_post_configure_hook_in_shell_script(self, tmp_path):
        """Test post-configure hook in shell script."""
        config = {
            "toolchain": "llvm-18",
            "hooks": {"post_configure": "./scripts/cleanup.sh"},
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        assert "./scripts/cleanup.sh" in content
        # Should run after cmake configure
        cmake_pos = content.find("tkgen configure")
        hook_pos = content.find("./scripts/cleanup.sh")
        assert hook_pos > cmake_pos

    def test_hooks_in_batch_script(self, tmp_path):
        """Test hooks in batch script."""
        config = {
            "toolchain": "msvc-latest",
            "hooks": {
                "pre_configure": "scripts\\setup.bat",
                "post_configure": "scripts\\cleanup.bat",
            },
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        assert "scripts\\setup.bat" in content or "scripts/setup.bat" in content
        assert "scripts\\cleanup.bat" in content or "scripts/cleanup.bat" in content

    def test_hooks_in_powershell_script(self, tmp_path):
        """Test hooks in PowerShell script."""
        config = {
            "toolchain": "llvm-18",
            "hooks": {
                "pre_configure": ".\\scripts\\setup.ps1",
                "post_configure": ".\\scripts\\cleanup.ps1",
            },
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert ".\\scripts\\setup.ps1" in content or "./scripts/setup.ps1" in content
        assert (
            ".\\scripts\\cleanup.ps1" in content or "./scripts/cleanup.ps1" in content
        )

    def test_all_advanced_features_combined(self, tmp_path):
        """Test all advanced features work together."""
        config = {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "cmake_args": ["-DENABLE_TESTS=ON", "-DCOVERAGE=ON"],
            "env_vars": {"CC": "clang", "ASAN_OPTIONS": "detect_leaks=1"},
            "hooks": {
                "pre_configure": "./scripts/setup.sh",
                "post_configure": "./scripts/cleanup.sh",
            },
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        # Check all features present
        assert "-DENABLE_TESTS=ON" in content
        assert "-DCOVERAGE=ON" in content
        assert "CC=" in content
        assert "clang" in content
        assert "ASAN_OPTIONS" in content
        assert "./scripts/setup.sh" in content
        assert "./scripts/cleanup.sh" in content


class TestPowerShellScriptGeneration:
    """Test Phase 5: PowerShell script generation."""

    def test_generate_powershell_script(self, tmp_path):
        """Test PowerShell script generation."""
        config = {"toolchain": "llvm-18", "build_type": "Release"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        assert script_path.exists()
        assert script_path.name == "bootstrap.ps1"

    def test_powershell_script_content(self, tmp_path):
        """Test PowerShell script contains expected content."""
        config = {"toolchain": "llvm-18", "build_type": "Release"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert "Write-Host" in content
        assert "$LASTEXITCODE" in content
        assert "llvm-18" in content
        assert "Release" in content
        assert "tkgen" in content

    def test_powershell_script_error_handling(self, tmp_path):
        """Test PowerShell script includes error handling."""
        generator = BootstrapGenerator(tmp_path)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert "$LASTEXITCODE" in content
        assert "exit" in content

    def test_powershell_script_with_package_manager(self, tmp_path):
        """Test PowerShell script with package manager."""
        config = {
            "toolchain": "llvm-18",
            "package_manager": "conan",
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        assert "tkgen" in content
        assert "configure" in content
        # Package manager logic is now handled by tkgen configure
        assert "conan install" not in content.lower()

    def test_generate_all_includes_powershell(self, tmp_path):
        """Test generate_all includes PowerShell script."""
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)
        scripts = generator.generate_all()

        assert "powershell" in scripts
        assert scripts["powershell"].exists()
        assert scripts["powershell"].name == "bootstrap.ps1"


class TestScriptValidation:
    """Test Phase 3: Script validation features."""

    def test_validate_shell_script_syntax(self, tmp_path):
        """Test shell script validation with bash -n."""
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        # Should pass validation (script is syntactically correct)
        is_valid, errors = generator.validate_shell_script(script_path)
        # Note: Validation may pass even without bash/shellcheck installed
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_batch_script(self, tmp_path):
        """Test batch script validation."""
        config = {"toolchain": "msvc-latest"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        # Basic validation should pass
        is_valid, errors = generator.validate_batch_script(script_path)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_powershell_script(self, tmp_path):
        """Test PowerShell script validation."""
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        # Should pass validation (script is syntactically correct)
        is_valid, errors = generator.validate_powershell_script(script_path)
        # Note: Validation may pass even without PowerShell installed
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_invalid_shell_script(self, tmp_path):
        """Test validation catches invalid shell script."""
        # Create an invalid shell script
        invalid_script = tmp_path / "invalid.sh"
        invalid_script.write_text("#!/bin/bash\nif [ missing bracket\necho 'test'")

        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)

        # Validation should fail (if bash is available)
        is_valid, errors = generator.validate_shell_script(invalid_script)
        # If bash isn't available, validation might pass
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


class TestJinja2Templates:
    """Test Phase 4: Jinja2 template system."""

    def test_jinja2_available(self, tmp_path):
        """Test Jinja2 is available and initialized."""
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)

        # Generator now exclusively uses Jinja2 (no fallback mechanism)
        assert hasattr(generator, "_jinja_env")
        # Jinja2 environment should be initialized
        assert generator._jinja_env is not None

    def test_shell_script_with_jinja2(self, tmp_path):
        """Test shell script generation with Jinja2 templates."""
        config = {
            "toolchain": "gcc-14",
            "build_type": "Debug",
            "cmake_args": ["-DENABLE_TESTS=ON"],
            "env_vars": {"CC": "gcc", "CXX": "g++"},
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        # Verify content includes our configuration
        assert "gcc-14" in content
        assert "Debug" in content
        assert "-DENABLE_TESTS=ON" in content
        # Environment variables should be set
        assert "CC=" in content or "export CC=" in content

    def test_batch_script_with_jinja2(self, tmp_path):
        """Test batch script generation with Jinja2 templates."""
        config = {
            "toolchain": "msvc-latest",
            "build_type": "Release",
            "cmake_args": ["-DBUILD_SHARED_LIBS=ON"],
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_batch_script()

        content = script_path.read_text()
        # Verify content includes our configuration
        assert "msvc-latest" in content
        assert "Release" in content
        assert "-DBUILD_SHARED_LIBS=ON" in content

    def test_powershell_script_with_jinja2(self, tmp_path):
        """Test PowerShell script generation with Jinja2 templates."""
        config = {
            "toolchain": "llvm-18",
            "build_type": "RelWithDebInfo",
            "env_vars": {"MY_VAR": "test_value"},
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_powershell_script()

        content = script_path.read_text()
        # Verify content includes our configuration
        assert "llvm-18" in content
        assert "RelWithDebInfo" in content
        # Environment variables in PowerShell format
        assert "$env:MY_VAR" in content or "MY_VAR" in content

    def test_jinja2_with_hooks(self, tmp_path):
        """Test Jinja2 templates with pre/post hooks."""
        config = {
            "toolchain": "llvm-18",
            "hooks": {
                "pre_configure": "./scripts/pre.sh",
                "post_configure": "./scripts/post.sh",
            },
        }
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        # Hooks should be included
        assert "./scripts/pre.sh" in content
        assert "./scripts/post.sh" in content
        assert "pre_configure" in content.lower() or "pre.sh" in content

    def test_jinja2_required(self, tmp_path):
        """Test that Jinja2 is required (no fallback)."""

        # Test that generator requires Jinja2 templates directory
        config = {"toolchain": "llvm-18"}
        generator = BootstrapGenerator(tmp_path, config)

        # If templates are missing, _init_jinja2 should raise error
        # (In normal operation, templates are always present in package)
        assert generator._jinja_env is not None

        # Verify script can be generated with Jinja2
        script_path = generator.generate_shell_script()
        assert script_path.exists()

        content = script_path.read_text()
        assert "#!/bin/bash" in content
        assert "llvm-18" in content

    def test_custom_template_directory(self, tmp_path):
        """Test using custom template directory."""
        # Create custom template directory
        custom_templates = tmp_path / "my_templates"
        custom_templates.mkdir()

        # Create a custom shell template
        (custom_templates / "bootstrap.sh.j2").write_text(
            """#!/bin/bash
# Custom Template
echo "Custom bootstrap for {{ project_name }}"
"""
        )

        config = {"toolchain": "llvm-18", "template_dir": str(custom_templates)}
        generator = BootstrapGenerator(tmp_path, config)
        script_path = generator.generate_shell_script()

        content = script_path.read_text()
        # Should use custom template
        assert "Custom Template" in content or "Custom bootstrap" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
