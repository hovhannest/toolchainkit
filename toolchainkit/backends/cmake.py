"""
CMake build backend.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from toolchainkit.backends.base import BuildBackend
from toolchainkit.cmake.toolchain_generator import (
    CMakeToolchainGenerator,
    ToolchainFileConfig,
)

logger = logging.getLogger(__name__)


class CMakeBackend(BuildBackend):
    """
    CMake build backend implementation.
    """

    def configure(
        self,
        project_root: Path,
        build_dir: Path,
        toolchain_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        """
        Configure the build using CMake.
        """
        # 1. Generate toolchain file
        toolchain_file = self._generate_toolchain(project_root, toolchain_data, config)

        # 2. Run CMake
        self._run_cmake(project_root, build_dir, toolchain_file, config)

    def _generate_toolchain(
        self, project_root: Path, toolchain_data: Dict[str, Any], config: Dict[str, Any]
    ) -> Path:
        """Generate CMake toolchain file."""
        generator = CMakeToolchainGenerator(project_root)

        # Extract configuration
        toolchain_id = toolchain_data.get("id")
        toolchain_path = toolchain_data.get("path")
        toolchain_name = toolchain_data.get("name", "unknown")

        # Determine compiler type
        # This logic was in configure.py, moving it here or relying on config
        # Ideally, toolchain_data should have this info, but for now we infer
        compiler_type = config.get("compiler_type")
        if not compiler_type:
            if "llvm" in toolchain_name.lower() or "clang" in toolchain_name.lower():
                compiler_type = "clang"
            elif "gcc" in toolchain_name.lower():
                compiler_type = "gcc"
            elif "msvc" in toolchain_name.lower():
                compiler_type = "msvc"
            else:
                compiler_type = "clang"  # default

        # Cross compilation
        cross_compile = config.get("cross_compile")

        config_obj = ToolchainFileConfig(
            toolchain_id=toolchain_id,
            toolchain_path=Path(toolchain_path) if toolchain_path else None,
            compiler_type=compiler_type,
            stdlib=config.get("stdlib"),
            linker=config.get("linker"),
            cross_compile=cross_compile,
        )

        if toolchain_path:
            return generator.generate(config_obj)
        else:
            # Placeholder generation logic could go here, but for now assume path exists
            # or handle it gracefully.
            # In configure.py there was a fallback. Let's replicate simple fallback if needed.
            # But really, we should expect a valid toolchain for the backend to work well.
            # If no toolchain path, we might be using system compiler.
            return generator.generate(config_obj)

    def _run_cmake(
        self,
        project_root: Path,
        build_dir: Path,
        toolchain_file: Path,
        config: Dict[str, Any],
    ) -> None:
        """Run CMake configuration command."""
        build_type = config.get("build_type", "Debug")

        logger.info("Running CMake configuration")
        print("Configuring CMake...")
        print()

        cmake_args = [
            "cmake",
            "-B",
            str(build_dir),
            "-S",
            str(project_root),
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
        ]

        # Add additional cmake args
        if config.get("cmake_args"):
            cmake_args.extend(config["cmake_args"])

        logger.debug(f"CMake command: {' '.join(cmake_args)}")

        try:
            cmake_result = subprocess.run(cmake_args, cwd=project_root)
            if cmake_result.returncode != 0:
                logger.error("CMake configuration failed")
                print(
                    f"ERROR: CMake configuration failed with exit code {cmake_result.returncode}",
                    file=sys.stderr,
                )
                raise RuntimeError("CMake configuration failed")
        except FileNotFoundError:
            logger.error("CMake not found in PATH")
            print("ERROR: CMake not found in PATH", file=sys.stderr)
            print(
                "  Please install CMake: https://cmake.org/download/", file=sys.stderr
            )
            raise RuntimeError("CMake not found")
        except Exception as e:
            logger.error(f"CMake execution failed: {e}")
            print(f"ERROR: CMake execution failed: {e}", file=sys.stderr)
            raise e
