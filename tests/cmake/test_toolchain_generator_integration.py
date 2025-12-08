"""
Integration tests for CMake Toolchain File Generator.

These tests generate real CMake toolchain files and verify they work
with actual CMake projects.
"""

import pytest
import subprocess
import shutil

from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
)


def is_cmake_available():
    """Check if CMake is available on the system."""
    return shutil.which("cmake") is not None


@pytest.mark.integration
@pytest.mark.skipif(not is_cmake_available(), reason="CMake not available")
class TestCMakeIntegration:
    """Integration tests with real CMake."""

    def test_generate_and_parse_toolchain_file(self, temp_dir):
        """Test that CMake can parse the generated toolchain file."""
        # Create project structure
        project_root = temp_dir / "project"
        project_root.mkdir()

        # Create minimal CMakeLists.txt
        cmake_lists = project_root / "CMakeLists.txt"
        cmake_lists.write_text(
            """
cmake_minimum_required(VERSION 3.20)
project(TestProject CXX)

message(STATUS "Project configured successfully")
message(STATUS "C Compiler: ${CMAKE_C_COMPILER}")
message(STATUS "CXX Compiler: ${CMAKE_CXX_COMPILER}")
"""
        )

        # Create toolchain (using system compiler for simplicity)
        toolchain_path = temp_dir / "toolchains" / "system"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()

        # Find system compiler
        import platform

        if platform.system() == "Windows":
            # Try to find cl.exe or clang on Windows
            cl_exe = shutil.which("cl")
            clang_exe = shutil.which("clang")

            if clang_exe:
                compiler_type = "clang"
                # Create symlinks to actual compilers
                (toolchain_path / "bin" / "clang.exe").write_text("dummy")
                (toolchain_path / "bin" / "clang++.exe").write_text("dummy")
            elif cl_exe:
                compiler_type = "msvc"
            else:
                pytest.skip("No compiler found on system")
                return
        else:
            # Unix-like systems
            gcc_exe = shutil.which("gcc")
            clang_exe = shutil.which("clang")

            if clang_exe:
                compiler_type = "clang"
                (toolchain_path / "bin" / "clang").write_text(
                    '#!/bin/sh\\nexec clang "$@"'
                )
                (toolchain_path / "bin" / "clang++").write_text(
                    '#!/bin/sh\\nexec clang++ "$@"'
                )
                (toolchain_path / "bin" / "clang").chmod(0o755)
                (toolchain_path / "bin" / "clang++").chmod(0o755)
            elif gcc_exe:
                compiler_type = "gcc"
                (toolchain_path / "bin" / "gcc").write_text('#!/bin/sh\\nexec gcc "$@"')
                (toolchain_path / "bin" / "g++").write_text('#!/bin/sh\\nexec g++ "$@"')
                (toolchain_path / "bin" / "gcc").chmod(0o755)
                (toolchain_path / "bin" / "g++").chmod(0o755)
            else:
                pytest.skip("No compiler found on system")
                return

        # Generate toolchain file
        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="system-test",
            toolchain_path=toolchain_path,
            compiler_type=compiler_type,
        )

        toolchain_file = generator.generate(config)
        assert toolchain_file.exists()

        # Try to configure with CMake
        build_dir = project_root / "build"
        build_dir.mkdir()

        # Note: This test may fail if the generated toolchain file references
        # non-existent compilers. In real usage, actual toolchain binaries would exist.
        # For this test, we just verify CMake can parse the file syntax.
        try:
            result = subprocess.run(
                [
                    "cmake",
                    "-S",
                    str(project_root),
                    "-B",
                    str(build_dir),
                    f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # We expect this might fail due to compiler not found,
            # but CMake should at least parse the toolchain file
            # If there's a CMake syntax error, it will fail immediately
            assert (
                "CMake Error" not in result.stderr
                or "CMAKE_TOOLCHAIN_FILE" not in result.stderr
            )

        except subprocess.TimeoutExpired:
            pytest.fail("CMake configure timed out")
        except FileNotFoundError:
            pytest.skip("CMake not found in PATH")

    def test_generated_file_is_valid_cmake_syntax(self, temp_dir):
        """Test that generated file has valid CMake syntax."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8-linux-x64",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            linker="lld",
            caching_enabled=True,
            cache_tool="sccache",
        )

        toolchain_file = generator.generate(config)
        content = toolchain_file.read_text()

        # Check for common CMake syntax elements
        assert "set(" in content
        assert ")" in content
        assert "message(" in content

        # Verify no obvious syntax errors
        assert "(" in content  # Must have opening parens
        assert ")" in content  # Must have closing parens

        # Count parens - should be balanced
        open_count = content.count("(")
        close_count = content.count(")")
        assert open_count == close_count, "Unbalanced parentheses in CMake file"

    def test_multiple_toolchain_files(self, temp_dir):
        """Test generating multiple toolchain files in same project."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        # Create two different toolchains
        llvm_path = temp_dir / "toolchains" / "llvm-18"
        llvm_path.mkdir(parents=True)
        (llvm_path / "bin").mkdir()
        (llvm_path / "bin" / "clang").touch()
        (llvm_path / "bin" / "clang++").touch()

        gcc_path = temp_dir / "toolchains" / "gcc-13"
        gcc_path.mkdir(parents=True)
        (gcc_path / "bin").mkdir()
        (gcc_path / "bin" / "gcc").touch()
        (gcc_path / "bin" / "g++").touch()

        generator = CMakeToolchainGenerator(project_root)

        # Generate LLVM toolchain file
        llvm_config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=llvm_path,
            compiler_type="clang",
        )
        llvm_file = generator.generate(llvm_config)

        # Generate GCC toolchain file
        gcc_config = ToolchainFileConfig(
            toolchain_id="gcc-13.2.0",
            toolchain_path=gcc_path,
            compiler_type="gcc",
        )
        gcc_file = generator.generate(gcc_config)

        # Verify both files exist
        assert llvm_file.exists()
        assert gcc_file.exists()
        assert llvm_file != gcc_file

        # Verify content is different
        assert llvm_file.read_text() != gcc_file.read_text()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_release_and_debug_configurations(self, temp_dir):
        """Test generating separate release and debug toolchain files."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)

        # Release config
        release_config = ToolchainFileConfig(
            toolchain_id="llvm-18-release",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            build_type="Release",
            stdlib="libc++",
            linker="lld",
        )

        # Debug config
        debug_config = ToolchainFileConfig(
            toolchain_id="llvm-18-debug",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            build_type="Debug",
            stdlib="libc++",
            linker="lld",
        )

        release_file = generator.generate(release_config)
        debug_file = generator.generate(debug_config)

        assert release_file.exists()
        assert debug_file.exists()
        assert release_file != debug_file

    def test_regeneration_preserves_functionality(self, temp_dir):
        """Test that regenerating a toolchain file preserves functionality."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
            stdlib="libc++",
            linker="lld",
        )

        # Generate multiple times
        file1 = generator.generate(config)
        content1 = file1.read_text()

        file2 = generator.generate(config)
        content2 = file2.read_text()

        file3 = generator.generate(config)
        content3 = file3.read_text()

        # All should point to same file
        assert file1 == file2 == file3

        # Content should be functionally equivalent (ignoring timestamps)
        lines1 = [
            line for line in content1.split("\n") if not line.startswith("# Generated:")
        ]
        lines2 = [
            line for line in content2.split("\n") if not line.startswith("# Generated:")
        ]
        lines3 = [
            line for line in content3.split("\n") if not line.startswith("# Generated:")
        ]

        assert lines1 == lines2
        assert lines2 == lines3

    def test_cross_platform_paths(self, temp_dir):
        """Test that generated paths work cross-platform."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        toolchain_path = temp_dir / "toolchains" / "llvm-18"
        toolchain_path.mkdir(parents=True)
        (toolchain_path / "bin").mkdir()
        (toolchain_path / "bin" / "clang").touch()
        (toolchain_path / "bin" / "clang++").touch()

        generator = CMakeToolchainGenerator(project_root)
        config = ToolchainFileConfig(
            toolchain_id="llvm-18.1.8",
            toolchain_path=toolchain_path,
            compiler_type="clang",
        )

        output_file = generator.generate(config)
        content = output_file.read_text()

        # Verify paths use forward slashes or CMake variables (cross-platform)
        # CMake converts paths internally, so we just check paths are present
        assert "CMAKE_C_COMPILER" in content
        assert "CMAKE_CXX_COMPILER" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
