"""
CMake File API interaction helper.

This module provides functionality to interact with the CMake File API
to query information about the project structure, targets, and configurations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CMakeFileAPI:
    """
    Interface to CMake File API.

    Allows querying the CMake build system for targets, configurations,
    and project structure.
    """

    def __init__(self, build_dir: Path):
        """
        Initialize CMake File API wrapper.

        Args:
            build_dir: Path to CMake build directory
        """
        self.build_dir = Path(build_dir)
        self.api_dir = self.build_dir / ".cmake" / "api" / "v1"
        self.query_dir = self.api_dir / "query"
        self.reply_dir = self.api_dir / "reply"

    def prepare_query(self):
        """
        Create query files to request information from CMake.
        Must be called BEFORE running CMake configuration.
        """
        self.query_dir.mkdir(parents=True, exist_ok=True)

        # Request codemodel-v2
        codemodel_query = self.query_dir / "codemodel-v2"
        codemodel_query.touch()
        logger.debug(f"Created CMake API query: {codemodel_query}")

    def read_reply(self) -> Optional[Dict]:
        """
        Read the reply from CMake after configuration.

        Returns:
            Dictionary containing codemodel data or None if not found
        """
        if not self.reply_dir.exists():
            logger.warning(f"CMake API reply directory not found: {self.reply_dir}")
            return None

        # Find the latest codemodel reply file
        # Format: codemodel-v2-<hash>.json
        try:
            reply_files = list(self.reply_dir.glob("codemodel-v2-*.json"))
            if not reply_files:
                logger.warning("No codemodel reply found")
                return None

            # Sort by modification time, newest first
            reply_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_reply = reply_files[0]

            with open(latest_reply, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.debug(f"Loaded CMake API reply from {latest_reply.name}")
            return data

        except Exception as e:
            logger.error(f"Failed to read CMake API reply: {e}")
            return None

    def get_executables(self) -> List[Dict[str, str]]:
        """
        Get list of executable targets from the project.

        Returns:
            List of dictionaries with 'name', 'path', and 'config' keys.
        """
        data = self.read_reply()
        if not data:
            return []

        executables = []

        try:
            configurations = data.get("configurations", [])
            for config in configurations:
                config_name = config.get("name", "")

                for target in config.get("targets", []):
                    # We need to look up the target definition in the referenced json file
                    # The codemodel file only contains references to target files
                    target_json_file = self.reply_dir / target.get("jsonFile", "")

                    if not target_json_file.exists():
                        continue

                    try:
                        with open(target_json_file, "r", encoding="utf-8") as f:
                            target_data = json.load(f)

                        # Check if it's an executable
                        if target_data.get("type") == "EXECUTABLE":
                            name = target_data.get("name")

                            # Get the path to the executable artifact
                            artifacts = target_data.get("artifacts", [])
                            if artifacts:
                                path = artifacts[0].get("path")
                                # Path is relative to build directory
                                abs_path = (self.build_dir / path).resolve()

                                executables.append(
                                    {
                                        "name": name,
                                        "path": str(abs_path),
                                        "config": config_name,
                                    }
                                )
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse target file {target_json_file}: {e}"
                        )
                        continue

        except Exception as e:
            logger.error(f"Error parsing CMake codemodel: {e}")

        return executables
