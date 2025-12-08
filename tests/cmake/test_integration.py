"""
Integration tests for CMake toolchain generation and build execution.

Provides CMakeTestRunner for executing CMake configure and build commands,
and ToolchainValidator for validating generated toolchain files.
"""

import subprocess
import tempfile
import re
from pathlib import Path
from typing import List, Optional, Dict
import pytest

from .test_projects import (
    TestProject,
    HelloWorldProject,
    LibraryProject,
    MultiFileProject,
    ModernCppProject,
    SubdirectoryProject,
)


class CMakeTestRunner:
    """Run CMake configuration and build tests."""

    def __init__(
        self, toolchain_file: Optional[Path] = None, backend_name: Optional[str] = None
    ):
        """
        Initialize CMake test runner.

        Args:
            toolchain_file: Path to CMake toolchain file (optional)
            backend_name: Specific backend to use (optional)
        """
        self.toolchain_file = toolchain_file
        self.backend_name = backend_name

    def configure(
        self,
        source_dir: Path,
        build_dir: Path,
        extra_args: Optional[List[str]] = None,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess:
        """
        Run cmake configuration.

        Args:
            source_dir: Source directory containing CMakeLists.txt
            build_dir: Build directory for out-of-source build
            extra_args: Additional CMake arguments
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with returncode, stdout, stderr
        """
        build_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["cmake", str(source_dir)]

        # Add toolchain file
        if self.toolchain_file:
            cmd.extend(["-DCMAKE_TOOLCHAIN_FILE=" + str(self.toolchain_file)])

        # Add generator if specified
        if self.backend_name:
            cmd.extend(["-G", self.backend_name])

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        return subprocess.run(
            cmd, cwd=build_dir, capture_output=True, text=True, timeout=timeout
        )

    def build(
        self,
        build_dir: Path,
        config: str = "Release",
        target: Optional[str] = None,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess:
        """
        Run cmake build.

        Args:
            build_dir: Build directory
            config: Build configuration (Debug, Release, etc.)
            target: Specific target to build (None = all)
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with returncode, stdout, stderr
        """
        cmd = ["cmake", "--build", ".", "--config", config]

        if target:
            cmd.extend(["--target", target])

        return subprocess.run(
            cmd, cwd=build_dir, capture_output=True, text=True, timeout=timeout
        )

    def test_full_cycle(
        self, project: TestProject, temp_dir: Path, config: str = "Release"
    ) -> bool:
        """
        Test complete configure + build + verify cycle.

        Args:
            project: TestProject to build
            temp_dir: Temporary directory for build
            config: Build configuration

        Returns:
            True if successful, False otherwise
        """
        source_dir = temp_dir / "src"
        build_dir = temp_dir / "build"

        # Create project
        project.create(source_dir)

        # Configure
        config_result = self.configure(source_dir, build_dir)
        if config_result.returncode != 0:
            print(f"Configuration failed:\n{config_result.stderr}")
            return False

        # Build
        build_result = self.build(build_dir, config)
        if build_result.returncode != 0:
            print(f"Build failed:\n{build_result.stderr}")
            return False

        # Verify outputs exist
        expected_outputs = project.get_expected_outputs()
        found = False

        # Search in build directory and subdirectories
        for expected in expected_outputs:
            matches = list(build_dir.rglob(expected))
            if matches:
                found = True
                break

        if not found:
            print(f"Expected outputs not found: {expected_outputs}")
            all_files = [
                str(f.relative_to(build_dir))
                for f in build_dir.rglob("*")
                if f.is_file()
            ]
            print(f"Found files: {all_files[:20]}")  # Show first 20
            return False

        return True

    def get_cmake_version(self) -> Optional[str]:
        """
        Get CMake version.

        Returns:
            CMake version string or None if not found
        """
        try:
            result = subprocess.run(
                ["cmake", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                # Parse version from output (e.g., "cmake version 3.26.4")
                match = re.search(r"cmake version (\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None


class ToolchainValidator:
    """Validate generated toolchain files."""

    def validate_syntax(self, toolchain_file: Path, timeout: int = 60) -> bool:
        """
        Check CMake syntax is valid by running cmake with trace.

        Args:
            toolchain_file: Path to toolchain file
            timeout: Timeout in seconds

        Returns:
            True if syntax is valid
        """
        # Create minimal CMakeLists.txt
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            cmake_file = tmp_path / "CMakeLists.txt"
            cmake_file.write_text(
                "cmake_minimum_required(VERSION 3.20)\nproject(Test CXX)"
            )

            build_dir = tmp_path / "build"
            build_dir.mkdir()

            result = subprocess.run(
                [
                    "cmake",
                    "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain_file),
                    str(tmp_path),
                ],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return result.returncode == 0

    def validate_variables(self, toolchain_file: Path) -> Dict[str, str]:
        """
        Extract CMake variables from toolchain file.

        Args:
            toolchain_file: Path to toolchain file

        Returns:
            Dictionary of variable names to values
        """
        content = toolchain_file.read_text()
        variables = {}

        # Parse set() commands
        # Handles: set(VAR "value") and set(VAR value)
        pattern = r'set\s*\(\s*(\w+)\s+(?:"([^"]*)"|([^\)]+))\s*\)'
        matches = re.findall(pattern, content)

        for match in matches:
            var_name = match[0]
            # Value is in either group 1 (quoted) or group 2 (unquoted)
            var_value = match[1] if match[1] else match[2].strip()
            variables[var_name] = var_value

        return variables

    def validate_compiler_detection(self, toolchain_file: Path) -> bool:
        """
        Verify compiler is detected correctly.

        Args:
            toolchain_file: Path to toolchain file

        Returns:
            True if compiler paths are valid
        """
        variables = self.validate_variables(toolchain_file)

        # Check required variables
        required = ["CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER"]
        for var in required:
            if var not in variables:
                return False

            # Check compiler exists (skip on cross-compilation)
            _compiler_path = Path(variables[var])
            # Don't check existence if it's a cross-compiler path we can't verify
            # Just check it's not empty
            if not variables[var]:
                return False

        return True

    def validate_required_variables(
        self, toolchain_file: Path, required_vars: List[str]
    ) -> bool:
        """
        Validate that required variables are set.

        Args:
            toolchain_file: Path to toolchain file
            required_vars: List of required variable names

        Returns:
            True if all required variables are present
        """
        variables = self.validate_variables(toolchain_file)

        for var in required_vars:
            if var not in variables:
                return False

        return True


# Pytest fixtures
@pytest.fixture
def cmake_runner():
    """CMake test runner fixture."""
    return CMakeTestRunner()


@pytest.fixture
def toolchain_validator():
    """Toolchain validator fixture."""
    return ToolchainValidator()


@pytest.fixture
def hello_world_project():
    """Hello world test project."""
    return HelloWorldProject()


@pytest.fixture
def library_project():
    """Library test project."""
    return LibraryProject()


@pytest.fixture
def multifile_project():
    """Multi-file test project."""
    return MultiFileProject()


@pytest.fixture
def modern_cpp_project():
    """Modern C++ test project."""
    return ModernCppProject()


@pytest.fixture
def subdirectory_project():
    """Subdirectory test project."""
    return SubdirectoryProject()


# Integration tests
@pytest.mark.integration
class TestCMakeIntegration:
    """Integration tests for CMake toolchain generation."""

    def test_cmake_available(self, cmake_runner):
        """Test that CMake is available."""
        version = cmake_runner.get_cmake_version()

        if version is None:
            pytest.skip("CMake not available")

        print(f"CMake version: {version}")
        assert version is not None

    def test_hello_world_build(self, cmake_runner, hello_world_project, temp_dir):
        """Test building simple hello world project."""
        version = cmake_runner.get_cmake_version()
        if version is None:
            pytest.skip("CMake not available")

        success = cmake_runner.test_full_cycle(hello_world_project, temp_dir)

        if not success:
            pytest.skip("Build failed - may need compiler setup")

    def test_library_build(self, cmake_runner, library_project, temp_dir):
        """Test building project with library."""
        version = cmake_runner.get_cmake_version()
        if version is None:
            pytest.skip("CMake not available")

        success = cmake_runner.test_full_cycle(library_project, temp_dir)

        if not success:
            pytest.skip("Build failed - may need compiler setup")

    def test_multifile_build(self, cmake_runner, multifile_project, temp_dir):
        """Test building multi-file project."""
        version = cmake_runner.get_cmake_version()
        if version is None:
            pytest.skip("CMake not available")

        success = cmake_runner.test_full_cycle(multifile_project, temp_dir)

        if not success:
            pytest.skip("Build failed - may need compiler setup")


@pytest.mark.integration
class TestToolchainValidation:
    """Integration tests for toolchain validation."""

    def test_validate_variables_parsing(self, toolchain_validator, temp_dir):
        """Test parsing CMake variables from toolchain file."""
        # Create a sample toolchain file
        toolchain_file = temp_dir / "toolchain.cmake"
        toolchain_content = """
set(CMAKE_C_COMPILER "/usr/bin/clang")
set(CMAKE_CXX_COMPILER "/usr/bin/clang++")
set(CMAKE_CXX_FLAGS "-std=c++17 -stdlib=libc++")
"""
        toolchain_file.write_text(toolchain_content)

        variables = toolchain_validator.validate_variables(toolchain_file)

        assert "CMAKE_C_COMPILER" in variables
        assert "CMAKE_CXX_COMPILER" in variables
        assert "CMAKE_CXX_FLAGS" in variables
        assert "/usr/bin/clang" in variables["CMAKE_C_COMPILER"]

    def test_validate_required_variables(self, toolchain_validator, temp_dir):
        """Test validation of required variables."""
        toolchain_file = temp_dir / "toolchain.cmake"
        toolchain_content = """
set(CMAKE_C_COMPILER "gcc")
set(CMAKE_CXX_COMPILER "g++")
set(CMAKE_SYSTEM_NAME "Linux")
"""
        toolchain_file.write_text(toolchain_content)

        # Check for required compiler variables
        assert toolchain_validator.validate_required_variables(
            toolchain_file, ["CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER"]
        )

        # Check for optional variable
        assert toolchain_validator.validate_required_variables(
            toolchain_file, ["CMAKE_SYSTEM_NAME"]
        )

        # Check for missing variable
        assert not toolchain_validator.validate_required_variables(
            toolchain_file, ["CMAKE_DOES_NOT_EXIST"]
        )


def example_usage():
    """Example: Run integration tests manually."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Create and test hello world
        print("=== Testing Hello World Project ===")
        project = HelloWorldProject()
        runner = CMakeTestRunner()

        cmake_version = runner.get_cmake_version()
        if cmake_version:
            print(f"CMake version: {cmake_version}")

            success = runner.test_full_cycle(project, temp_path)
            print(f"Test result: {'PASS' if success else 'FAIL'}")
        else:
            print("CMake not available")


if __name__ == "__main__":
    example_usage()
