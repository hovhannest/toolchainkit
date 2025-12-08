"""
VSCode Settings Generator

This module generates .vscode/settings.json for VSCode integration with ToolchainKit.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from toolchainkit.cmake.api import CMakeFileAPI


logger = logging.getLogger(__name__)


class VSCodeIntegrator:
    """
    Generate VSCode configuration for ToolchainKit projects.

    This class creates or updates .vscode/settings.json with CMake toolchain file,
    compiler paths for IntelliSense, and build directory settings.

    Example:
        >>> from pathlib import Path
        >>> integrator = VSCodeIntegrator(Path('/projects/myapp'))
        >>> settings_file = integrator.generate_settings(
        ...     toolchain_file=Path('.toolchainkit/cmake/toolchain.cmake'),
        ...     compiler_path=Path('/usr/bin/clang')
        ... )
    """

    def __init__(self, project_root: Path):
        """
        Initialize VSCode integrator.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)
        self.vscode_dir = self.project_root / ".vscode"
        logger.debug(f"Initialized VSCode integrator for {self.project_root}")

    def generate_settings(
        self,
        toolchain_file: Path,
        compiler_path: Path,
        build_dir: str = "build",
        generator: str = "Ninja",
        export_compile_commands: bool = True,
        clang_tidy_path: Optional[Path] = None,
        clang_format_path: Optional[Path] = None,
    ) -> Path:
        """
        Generate .vscode/settings.json with ToolchainKit configuration.

        Args:
            toolchain_file: Path to CMake toolchain file (relative to project root)
            compiler_path: Path to C/C++ compiler for IntelliSense
            build_dir: Build directory path (default: "build")
            generator: CMake generator (default: "Ninja")
            export_compile_commands: Export compile_commands.json (default: True)
            clang_tidy_path: Path to clang-tidy executable
            clang_format_path: Path to clang-format executable

        Returns:
            Path to generated settings.json file

        Example:
            >>> settings_file = integrator.generate_settings(
            ...     toolchain_file=Path('.toolchainkit/cmake/toolchain.cmake'),
            ...     compiler_path=Path('/usr/bin/clang'),
            ...     build_dir='build-release',
            ...     generator='Unix Makefiles'
            ... )
        """
        # Create .vscode directory if it doesn't exist
        self.vscode_dir.mkdir(exist_ok=True)
        logger.debug(f"VSCode directory: {self.vscode_dir}")

        settings_file = self.vscode_dir / "settings.json"

        # Load existing settings
        existing_settings = self._load_existing_settings(settings_file)
        logger.debug(f"Loaded {len(existing_settings)} existing settings")

        # Create new ToolchainKit settings
        toolchainkit_settings = self._create_toolchainkit_settings(
            toolchain_file=toolchain_file,
            compiler_path=compiler_path,
            build_dir=build_dir,
            generator=generator,
            export_compile_commands=export_compile_commands,
            clang_tidy_path=clang_tidy_path,
            clang_format_path=clang_format_path,
        )

        # Merge settings
        merged_settings = self._merge_settings(existing_settings, toolchainkit_settings)

        # Write settings
        self._write_settings(settings_file, merged_settings)
        logger.info(f"Generated VSCode settings: {settings_file}")

        return settings_file

    def _load_existing_settings(self, settings_file: Path) -> Dict:
        """
        Load existing .vscode/settings.json if it exists.

        Args:
            settings_file: Path to settings.json

        Returns:
            Dictionary of existing settings, or empty dict if file doesn't exist
        """
        if not settings_file.exists():
            logger.debug("No existing settings.json found")
            return {}

        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            logger.debug(f"Loaded existing settings from {settings_file}")
            return settings
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse existing settings.json: {e}")
            logger.warning("Creating new settings file")
            return {}
        except Exception as e:
            logger.warning(f"Error reading settings.json: {e}")
            return {}

    def _create_toolchainkit_settings(
        self,
        toolchain_file: Path,
        compiler_path: Path,
        build_dir: str,
        generator: str,
        export_compile_commands: bool,
        clang_tidy_path: Optional[Path] = None,
        clang_format_path: Optional[Path] = None,
    ) -> Dict:
        """
        Create ToolchainKit-specific settings dictionary.

        Args:
            toolchain_file: Path to CMake toolchain file
            compiler_path: Path to compiler
            build_dir: Build directory
            generator: CMake generator
            export_compile_commands: Export compile commands flag
            clang_tidy_path: Path to clang-tidy executable
            clang_format_path: Path to clang-format executable

        Returns:
            Dictionary of ToolchainKit settings
        """
        # Convert toolchain file to relative path if absolute
        if toolchain_file.is_absolute():
            try:
                toolchain_file = toolchain_file.relative_to(self.project_root)
            except ValueError:
                # Path is not relative to project root, keep as is
                pass

        # Create settings with VSCode variables
        settings: Dict[str, Any] = {
            "cmake.configureSettings": {
                "CMAKE_TOOLCHAIN_FILE": f"${{workspaceFolder}}/{toolchain_file.as_posix()}"
            },
            "C_Cpp.default.compilerPath": str(compiler_path),
            "cmake.buildDirectory": f"${{workspaceFolder}}/{build_dir}",
            "cmake.generator": generator,
        }

        if export_compile_commands:
            settings["cmake.exportCompileCommandsFile"] = True  # type: ignore[assignment]

        if clang_format_path:
            settings["C_Cpp.clang_format_path"] = str(clang_format_path)
            settings["editor.formatOnSave"] = True
            settings["editor.formatOnSaveMode"] = "modifications"

        if clang_tidy_path:
            settings["C_Cpp.codeAnalysis.clangTidy.enabled"] = True
            settings["C_Cpp.codeAnalysis.clangTidy.path"] = str(clang_tidy_path)

        logger.debug(f"Created ToolchainKit settings: {len(settings)} keys")
        return settings

    def _merge_settings(self, existing: Dict, new: Dict) -> Dict:
        """
        Merge new ToolchainKit settings with existing settings.

        ToolchainKit settings take precedence for ToolchainKit-specific keys,
        but all other user settings are preserved.

        Args:
            existing: Existing settings dictionary
            new: New ToolchainKit settings dictionary

        Returns:
            Merged settings dictionary
        """
        merged = existing.copy()

        # Update with new settings (nested merge for cmake.configureSettings)
        for key, value in new.items():
            if key == "cmake.configureSettings" and key in merged:
                # Merge cmake.configureSettings
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key].update(value)
                else:
                    merged[key] = value
            else:
                merged[key] = value

        logger.debug(f"Merged settings: {len(merged)} total keys")
        return merged

    def _write_settings(self, settings_file: Path, settings: Dict):
        """
        Write settings to settings.json file.

        Args:
            settings_file: Path to settings.json
            settings: Settings dictionary to write
        """
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
                # Add newline at end of file
                f.write("\n")
            logger.debug(f"Wrote settings to {settings_file}")
        except Exception as e:
            logger.error(f"Failed to write settings.json: {e}")
            raise

    def get_recommended_extensions(self) -> list:
        """
        Get list of recommended VSCode extensions for ToolchainKit projects.

        Returns:
            List of extension IDs
        """
        return [
            "ms-vscode.cpptools",  # C/C++ extension
            "ms-vscode.cmake-tools",  # CMake Tools extension
            "twxs.cmake",  # CMake language support
        ]

    def generate_extensions_json(self) -> Path:
        """
        Generate .vscode/extensions.json with recommended extensions.

        Returns:
            Path to generated extensions.json file
        """
        self.vscode_dir.mkdir(exist_ok=True)
        extensions_file = self.vscode_dir / "extensions.json"

        extensions_data = {"recommendations": self.get_recommended_extensions()}

        with open(extensions_file, "w", encoding="utf-8") as f:
            json.dump(extensions_data, f, indent=4)
            f.write("\n")

        logger.info(f"Generated VSCode extensions.json: {extensions_file}")
        return extensions_file

    def generate_launch_config(
        self,
        targets: List[Dict[str, str]],
        debugger_path: Optional[str] = None,
    ) -> Path:
        """
        Generate .vscode/launch.json for executable targets.

        Args:
            targets: List of executable targets from CMake API
            debugger_path: Path to debugger (lldb/gdb)

        Returns:
            Path to generated launch.json
        """
        configurations = []

        for target in targets:
            name = target["name"]
            path = target["path"]

            # Use relative path if possible for cleaner config
            try:
                exe_path = Path(path)
                if exe_path.is_relative_to(self.project_root):
                    program = f"${{workspaceFolder}}/{exe_path.relative_to(self.project_root).as_posix()}"
                else:
                    program = str(path)
            except ValueError:
                program = str(path)

            config = {
                "name": f"Debug {name}",
                "type": "cppdbg",
                "request": "launch",
                "program": program,
                "args": [],
                "stopAtEntry": False,
                "cwd": "${workspaceFolder}",
                "environment": [],
                "externalConsole": False,
                "MIMode": "lldb"
                if debugger_path and "lldb" in str(debugger_path).lower()
                else "gdb",
            }

            if debugger_path:
                config["miDebuggerPath"] = str(debugger_path)

            configurations.append(config)

        launch_data = {
            "version": "0.2.0",
            "configurations": configurations,
        }

        self.vscode_dir.mkdir(exist_ok=True)
        launch_file = self.vscode_dir / "launch.json"

        # Merge with existing configurations if file exists
        if launch_file.exists():
            try:
                with open(launch_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)

                # Create map of existing configs by name
                existing_configs = {
                    c["name"]: c for c in existing_data.get("configurations", [])
                }

                # Update/Add new configs
                for config in configurations:
                    existing_configs[config["name"]] = config

                launch_data["configurations"] = list(existing_configs.values())
            except Exception as e:
                logger.warning(f"Failed to merge existing launch.json: {e}")

        with open(launch_file, "w", encoding="utf-8") as f:
            json.dump(launch_data, f, indent=4)
            f.write("\n")

        logger.info(f"Generated VSCode launch.json: {launch_file}")
        return launch_file

    def generate_tasks_config(
        self,
        clang_tidy_path: Optional[Path] = None,
        clang_format_path: Optional[Path] = None,
    ) -> Path:
        """
        Generate .vscode/tasks.json for building the project.

        Returns:
            Path to generated tasks.json
        """
        tasks_data: Dict[str, Any] = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "Build All",
                    "type": "shell",
                    "command": "cmake --build build",
                    "group": {"kind": "build", "isDefault": True},
                    "problemMatcher": ["$gcc"],
                },
                {
                    "label": "Configure Project",
                    "type": "shell",
                    "command": "toolchainkit configure",
                    "problemMatcher": [],
                },
            ],
        }

        if clang_format_path:
            tasks_data["tasks"].append(
                {
                    "label": "Clang Format: All Files",
                    "type": "shell",
                    "command": f'"{clang_format_path}" -i src/**/*.cpp src/**/*.h',
                    "problemMatcher": [],
                    "group": "none",
                }
            )

        if clang_tidy_path:
            tasks_data["tasks"].append(
                {
                    "label": "Clang Tidy: Check",
                    "type": "shell",
                    "command": f'"{clang_tidy_path}" -p build src/**/*.cpp',
                    "problemMatcher": [],
                    "group": "none",
                }
            )
            tasks_data["tasks"].append(
                {
                    "label": "Clang Tidy: Fix",
                    "type": "shell",
                    "command": f'"{clang_tidy_path}" -p build --fix src/**/*.cpp',
                    "problemMatcher": [],
                    "group": "none",
                }
            )

        self.vscode_dir.mkdir(exist_ok=True)
        tasks_file = self.vscode_dir / "tasks.json"

        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks_data, f, indent=4)
            f.write("\n")

        logger.info(f"Generated VSCode tasks.json: {tasks_file}")
        return tasks_file

    def configure_workspace(
        self,
        toolchain_file: Path,
        compiler_path: Path,
        build_dir: str = "build",
        build_type: str = "Debug",
        generator: str = "Ninja",
        debugger_path: Optional[str] = None,
        clang_tidy_path: Optional[Path] = None,
        clang_format_path: Optional[Path] = None,
    ):
        """
        Configure the entire workspace for VS Code.

        Args:
            toolchain_file: Path to toolchain file
            compiler_path: Path to compiler
            build_dir: Build directory
            build_type: Build type
            generator: CMake generator
            debugger_path: Path to debugger
            clang_tidy_path: Path to clang-tidy (optional)
            clang_format_path: Path to clang-format (optional)
        """
        # 1. Generate settings.json
        self.generate_settings(
            toolchain_file=toolchain_file,
            compiler_path=compiler_path,
            build_dir=build_dir,
            generator=generator,
            clang_tidy_path=clang_tidy_path,
            clang_format_path=clang_format_path,
        )

        # 2. Generate extensions.json
        self.generate_extensions_json()

        # 3. Generate tasks.json
        self.generate_tasks_config(
            clang_tidy_path=clang_tidy_path,
            clang_format_path=clang_format_path,
        )

        # 4. Generate launch.json (requires identifying targets)
        # Try to use CMake API to find targets
        try:
            build_path = self.project_root / build_dir
            api = CMakeFileAPI(build_path)

            # Prepare API query
            api.prepare_query()

            # We need to run CMake configure to populate the reply
            # Use 'cmake .' since build dir is already configured or we want to configure it
            logger.info("Running CMake to query targets for VS Code...")

            import subprocess

            cmd = ["cmake", ".", f"-DCMAKE_BUILD_TYPE={build_type}"]

            # Ensure build dir exists
            build_path.mkdir(exist_ok=True)

            subprocess.run(
                cmd,
                cwd=build_path,
                check=False,  # Don't crash if cmake fails, just skip launch.json
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            targets = api.get_executables()
            if targets:
                self.generate_launch_config(targets, debugger_path)
                logger.info(
                    f"Generated launch configurations for {len(targets)} targets"
                )
            else:
                logger.warning("No executable targets found via CMake API")

        except Exception as e:
            logger.warning(f"Failed to generate launch configurations: {e}")
