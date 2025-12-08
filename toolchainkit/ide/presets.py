"""
CMakePresets.json Generator

This module generates CMakePresets.json for IDEs like CLion, Qt Creator, and Visual Studio.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CMakePresetsGenerator:
    """
    Generate CMakePresets.json for ToolchainKit projects.

    CMakePresets.json provides IDE integration for CLion, Qt Creator, Visual Studio,
    and other modern IDEs that support CMake presets version 3+.

    Example:
        >>> from pathlib import Path
        >>> generator = CMakePresetsGenerator(Path('/projects/myapp'))
        >>> presets_file = generator.generate_presets('llvm-18')
    """

    def __init__(self, project_root: Path):
        """
        Initialize CMakePresets generator.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)
        self.presets_file = self.project_root / "CMakePresets.json"
        logger.debug(f"Initialized CMakePresets generator for {self.project_root}")

    def generate_presets(
        self,
        toolchain_name: str,
        build_types: Optional[List[str]] = None,
        generator: str = "Ninja",
        additional_cache_vars: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Generate CMakePresets.json for IDE integration.

        Args:
            toolchain_name: Name of the toolchain (used in preset names)
            build_types: List of build types (default: ['Debug', 'Release'])
            generator: CMake generator (default: 'Ninja')
            additional_cache_vars: Additional CMake cache variables (optional)

        Returns:
            Path to generated CMakePresets.json file

        Example:
            >>> presets_file = generator.generate_presets(
            ...     'llvm-18',
            ...     build_types=['Debug', 'Release', 'RelWithDebInfo'],
            ...     generator='Ninja',
            ...     additional_cache_vars={'BUILD_TESTING': 'ON'}
            ... )
        """
        if build_types is None:
            build_types = ["Debug", "Release"]

        if additional_cache_vars is None:
            additional_cache_vars = {}

        logger.debug(f"Generating CMakePresets.json for toolchain: {toolchain_name}")
        logger.debug(f"Build types: {build_types}")
        logger.debug(f"Generator: {generator}")

        # Create presets structure
        presets = {
            "version": 3,
            "configurePresets": self._create_configure_presets(
                toolchain_name=toolchain_name,
                build_types=build_types,
                generator=generator,
                additional_cache_vars=additional_cache_vars,
            ),
            "buildPresets": self._create_build_presets(
                toolchain_name=toolchain_name, build_types=build_types
            ),
        }

        # Write presets
        self._write_presets(presets)
        logger.info(f"Generated CMakePresets.json: {self.presets_file}")

        return self.presets_file

    def _create_configure_presets(
        self,
        toolchain_name: str,
        build_types: List[str],
        generator: str,
        additional_cache_vars: Dict[str, str],
    ) -> List[Dict]:
        """
        Create configure presets for each build type.

        Args:
            toolchain_name: Toolchain name for preset naming
            build_types: List of build types
            generator: CMake generator
            additional_cache_vars: Additional cache variables

        Returns:
            List of configure preset dictionaries
        """
        configure_presets = []

        for build_type in build_types:
            preset_name = f"{toolchain_name}-{build_type.lower()}"

            # Base cache variables
            cache_variables = {
                "CMAKE_BUILD_TYPE": build_type,
                "CMAKE_TOOLCHAIN_FILE": "${sourceDir}/.toolchainkit/cmake/toolchain.cmake",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
            }

            # Add additional cache variables
            cache_variables.update(additional_cache_vars)

            preset = {
                "name": preset_name,
                "displayName": f"{toolchain_name} {build_type}",
                "description": f"{build_type} build with {toolchain_name} toolchain",
                "binaryDir": "${sourceDir}/build/${presetName}",
                "generator": generator,
                "cacheVariables": cache_variables,
            }

            configure_presets.append(preset)
            logger.debug(f"Created configure preset: {preset_name}")

        return configure_presets

    def _create_build_presets(
        self, toolchain_name: str, build_types: List[str]
    ) -> List[Dict]:
        """
        Create build presets linked to configure presets.

        Args:
            toolchain_name: Toolchain name for preset naming
            build_types: List of build types

        Returns:
            List of build preset dictionaries
        """
        build_presets = []

        for build_type in build_types:
            preset_name = f"{toolchain_name}-{build_type.lower()}"

            preset = {
                "name": preset_name,
                "displayName": f"{toolchain_name} {build_type} Build",
                "configurePreset": preset_name,
            }

            build_presets.append(preset)
            logger.debug(f"Created build preset: {preset_name}")

        return build_presets

    def _write_presets(self, presets: Dict):
        """
        Write presets to CMakePresets.json file.

        Args:
            presets: Presets dictionary to write
        """
        try:
            with open(self.presets_file, "w", encoding="utf-8") as f:
                json.dump(presets, f, indent=2, ensure_ascii=False)
                # Add newline at end of file
                f.write("\n")
            logger.debug(f"Wrote presets to {self.presets_file}")
        except Exception as e:
            logger.error(f"Failed to write CMakePresets.json: {e}")
            raise

    def _load_existing_presets(self) -> Optional[Dict]:
        """
        Load existing CMakePresets.json if it exists.

        Returns:
            Dictionary of existing presets, or None if file doesn't exist
        """
        if not self.presets_file.exists():
            logger.debug("No existing CMakePresets.json found")
            return None

        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                presets = json.load(f)
            logger.debug(f"Loaded existing presets from {self.presets_file}")
            return presets
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse existing CMakePresets.json: {e}")
            logger.warning("Creating new presets file")
            return None
        except Exception as e:
            logger.warning(f"Error reading CMakePresets.json: {e}")
            return None

    def has_user_presets(self) -> bool:
        """
        Check if CMakeUserPresets.json exists.

        CMakeUserPresets.json is for user-specific presets and should be
        in .gitignore. This method checks if it exists.

        Returns:
            True if CMakeUserPresets.json exists
        """
        user_presets = self.project_root / "CMakeUserPresets.json"
        return user_presets.exists()
