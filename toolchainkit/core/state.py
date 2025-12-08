"""
State management for ToolchainKit projects.

This module provides state tracking for project configuration, active toolchains,
and build status. State is persisted to `.toolchainkit/state.json` and used to
detect when reconfiguration is needed.

Example:
    >>> from pathlib import Path
    >>> from toolchainkit.core.state import StateManager
    >>>
    >>> # Initialize state manager
    >>> project_root = Path('/path/to/project')
    >>> state_manager = StateManager(project_root)
    >>>
    >>> # Load and update state
    >>> state = state_manager.load()
    >>> state_manager.update_toolchain('llvm-18.1.8-linux-x64', 'sha256:abc123...')
    >>>
    >>> # Check if reconfiguration needed
    >>> if state_manager.needs_reconfigure(current_config_hash):
    >>>     print("Configuration changed, reconfigure required")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from toolchainkit.core.filesystem import atomic_write

logger = logging.getLogger(__name__)


class StateError(Exception):
    """Base exception for state management errors."""

    pass


class StateValidationError(StateError):
    """Raised when state validation fails."""

    pass


@dataclass
class CachingState:
    """Build caching state configuration."""

    enabled: bool = False
    tool: Optional[str] = None
    configured: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "enabled": self.enabled,
            "tool": self.tool,
            "configured": self.configured,
        }


@dataclass
class ProjectState:
    """
    Project state tracking.

    Tracks the current state of a ToolchainKit project including active toolchain,
    configuration hash, and build status.

    Attributes:
        version: State file format version
        active_toolchain: ID of currently active toolchain
        toolchain_hash: SHA256 hash of active toolchain
        config_hash: SHA256 hash of toolchainkit.yaml
        cmake_configured: Whether CMake has been configured
        last_bootstrap: ISO 8601 timestamp of last bootstrap
        last_configure: ISO 8601 timestamp of last configure
        package_manager: Active package manager (conan, vcpkg, etc.)
        package_manager_configured: Whether package manager is configured
        build_directory: CMake build directory path
        caching: Build caching configuration
        modules: List of active modules
    """

    version: int = 1
    active_toolchain: Optional[str] = None
    toolchain_hash: Optional[str] = None
    config_hash: Optional[str] = None
    cmake_configured: bool = False
    last_bootstrap: Optional[str] = None
    last_configure: Optional[str] = None
    package_manager: Optional[str] = None
    package_manager_configured: bool = False
    build_directory: str = "build"
    caching: CachingState = field(default_factory=CachingState)
    modules: list[str] = field(default_factory=lambda: ["core", "cmake"])

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "active_toolchain": self.active_toolchain,
            "toolchain_hash": self.toolchain_hash,
            "config_hash": self.config_hash,
            "cmake_configured": self.cmake_configured,
            "last_bootstrap": self.last_bootstrap,
            "last_configure": self.last_configure,
            "package_manager": self.package_manager,
            "package_manager_configured": self.package_manager_configured,
            "build_directory": self.build_directory,
            "caching": self.caching.to_dict(),
            "modules": self.modules,
        }


class StateManager:
    """
    Manages project state persistence and operations.

    StateManager provides a high-level API for tracking project state including
    active toolchain, configuration, and build status. State is persisted to
    `.toolchainkit/state.json` with atomic writes.

    Example:
        >>> from pathlib import Path
        >>> from toolchainkit.core.state import StateManager
        >>>
        >>> # Initialize
        >>> manager = StateManager(Path('/path/to/project'))
        >>>
        >>> # Update toolchain
        >>> manager.update_toolchain('llvm-18.1.8-linux-x64', 'sha256:abc123...')
        >>>
        >>> # Check if reconfiguration needed
        >>> needs_reconfig = manager.needs_reconfigure('sha256:current_hash')

    Attributes:
        project_root: Project root directory
        state_file: Path to state.json file
    """

    def __init__(self, project_root: Path):
        """
        Initialize state manager.

        Args:
            project_root: Project root directory

        Raises:
            StateError: If project_root is not a directory
        """
        if not isinstance(project_root, Path):
            project_root = Path(project_root)

        if not project_root.exists():
            raise StateError(
                f"Project root does not exist: {project_root}. "
                f"Ensure the directory exists before initializing StateManager."
            )

        if not project_root.is_dir():
            raise StateError(
                f"Project root is not a directory: {project_root}. "
                f"Expected a valid directory path."
            )

        self.project_root = project_root.resolve()
        self.state_file = self.project_root / ".toolchainkit" / "state.json"
        self._state: Optional[ProjectState] = None

    def load(self) -> ProjectState:
        """
        Load state from disk.

        If state file doesn't exist, returns a new default ProjectState.
        If state file is corrupted, logs warning and returns default state.

        Returns:
            Current project state

        Example:
            >>> state = manager.load()
            >>> print(f"Active toolchain: {state.active_toolchain}")
        """
        # Return cached state if available
        if self._state is not None:
            return self._state

        # State file doesn't exist - first run
        if not self.state_file.exists():
            logger.debug(f"State file not found, creating new state: {self.state_file}")
            self._state = ProjectState()
            return self._state

        # Load from file
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle version migration
            if data.get("version", 1) != 1:
                logger.warning(
                    f"State version {data.get('version')} not supported, using v1"
                )
                data = self._migrate_state(data)

            # Parse caching state
            caching_data = data.pop("caching", {})
            caching = CachingState(
                enabled=caching_data.get("enabled", False),
                tool=caching_data.get("tool"),
                configured=caching_data.get("configured", False),
            )

            # Parse modules list
            modules = data.pop("modules", ["core", "cmake"])

            # Create ProjectState
            self._state = ProjectState(
                version=data.get("version", 1),
                active_toolchain=data.get("active_toolchain"),
                toolchain_hash=data.get("toolchain_hash"),
                config_hash=data.get("config_hash"),
                cmake_configured=data.get("cmake_configured", False),
                last_bootstrap=data.get("last_bootstrap"),
                last_configure=data.get("last_configure"),
                package_manager=data.get("package_manager"),
                package_manager_configured=data.get(
                    "package_manager_configured", False
                ),
                build_directory=data.get("build_directory", "build"),
                caching=caching,
                modules=modules,
            )

            logger.debug(f"Loaded state from {self.state_file}")

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(
                f"Invalid state file {self.state_file}, resetting to default: {e}"
            )
            self._state = ProjectState()

        return self._state

    def save(self, state: Optional[ProjectState] = None):
        """
        Save state to disk atomically.

        Uses atomic write to prevent corruption. Creates .toolchainkit directory
        if it doesn't exist.

        Args:
            state: State to save (uses current if None)

        Example:
            >>> state = manager.load()
            >>> state.active_toolchain = 'llvm-18.1.8'
            >>> manager.save(state)
        """
        if state is None:
            state = self._state

        if state is None:
            logger.warning("No state to save")
            return

        self._state = state

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and write atomically
        state_dict = state.to_dict()
        json_content = json.dumps(state_dict, indent=2)

        atomic_write(self.state_file, json_content)
        logger.debug(f"Saved state to {self.state_file}")

    def update_toolchain(self, toolchain_id: str, toolchain_hash: str):
        """
        Update active toolchain information.

        Updates the active toolchain ID and hash, and records the current
        timestamp as last_configure time.

        Args:
            toolchain_id: Toolchain identifier (e.g., 'llvm-18.1.8-linux-x64')
            toolchain_hash: SHA256 hash of toolchain

        Example:
            >>> manager.update_toolchain(
            ...     'llvm-18.1.8-linux-x64',
            ...     'sha256:abc123def456...'
            ... )
        """
        state = self.load()
        state.active_toolchain = toolchain_id
        state.toolchain_hash = toolchain_hash
        state.last_configure = datetime.now().isoformat()
        self.save(state)
        logger.info(f"Updated active toolchain: {toolchain_id}")

    def update_config_hash(self, config_hash: str):
        """
        Update configuration hash.

        Records the hash of toolchainkit.yaml for change detection.

        Args:
            config_hash: SHA256 hash of toolchainkit.yaml

        Example:
            >>> from toolchainkit.core.verification import compute_file_hash
            >>> config_hash = compute_file_hash(config_file, 'sha256')
            >>> manager.update_config_hash(f"sha256:{config_hash}")
        """
        state = self.load()
        state.config_hash = config_hash
        self.save(state)
        logger.debug(f"Updated config hash: {config_hash[:16]}...")

    def update_build_config(
        self, build_dir: str = "build", build_type: str = "Release"
    ):
        """
        Update build configuration.

        Updates the build directory and marks CMake as configured.

        Args:
            build_dir: CMake build directory (relative to project root)
            build_type: Build type (Debug, Release, etc.)

        Example:
            >>> manager.update_build_config('build', 'Release')
        """
        state = self.load()
        state.cmake_configured = True
        state.build_directory = build_dir
        state.last_configure = datetime.now().isoformat()
        self.save(state)
        logger.info(
            f"Updated build config (build_dir: {build_dir}, type: {build_type})"
        )

    def mark_bootstrap_complete(self):
        """
        Mark bootstrap operation as completed.

        Records current timestamp as last_bootstrap time.

        Example:
            >>> manager.mark_bootstrap_complete()
        """
        state = self.load()
        state.last_bootstrap = datetime.now().isoformat()
        self.save(state)
        logger.info("Marked bootstrap complete")

    def mark_cmake_configured(self, build_dir: str = "build"):
        """
        Mark CMake as configured.

        Records that CMake configuration is complete and stores the build
        directory path.

        Args:
            build_dir: CMake build directory (relative to project root)

        Example:
            >>> manager.mark_cmake_configured('build')
        """
        state = self.load()
        state.cmake_configured = True
        state.build_directory = build_dir
        state.last_configure = datetime.now().isoformat()
        self.save(state)
        logger.info(f"Marked CMake configured (build_dir: {build_dir})")

    def mark_package_manager_configured(self, manager: str):
        """
        Mark package manager as configured.

        Records which package manager is configured (conan, vcpkg, cpm).

        Args:
            manager: Package manager name

        Example:
            >>> manager.mark_package_manager_configured('conan')
        """
        state = self.load()
        state.package_manager = manager
        state.package_manager_configured = True
        self.save(state)
        logger.info(f"Marked package manager configured: {manager}")

    def update_caching(self, enabled: bool, tool: Optional[str] = None):
        """
        Update caching configuration.

        Records build caching settings (sccache, ccache, etc.).

        Args:
            enabled: Whether caching is enabled
            tool: Caching tool name (e.g., 'sccache', 'ccache')

        Example:
            >>> manager.update_caching(enabled=True, tool='sccache')
        """
        state = self.load()
        state.caching.enabled = enabled
        state.caching.tool = tool
        state.caching.configured = True
        self.save(state)
        logger.info(f"Updated caching: enabled={enabled}, tool={tool}")

    def needs_reconfigure(self, current_config_hash: str) -> bool:
        """
        Check if reconfiguration is needed.

        Reconfiguration is needed if:
        - No previous configuration exists
        - Configuration hash changed
        - CMake not configured
        - Build directory doesn't exist

        Args:
            current_config_hash: Current configuration file hash

        Returns:
            True if reconfiguration needed, False otherwise

        Example:
            >>> from toolchainkit.core.verification import compute_file_hash
            >>> config_file = project_root / 'toolchainkit.yaml'
            >>> current_hash = compute_file_hash(config_file, 'sha256')
            >>> if manager.needs_reconfigure(f"sha256:{current_hash}"):
            ...     print("Reconfiguration required")
        """
        state = self.load()

        # No previous configuration
        if state.config_hash is None:
            logger.debug("Reconfigure needed: no previous configuration")
            return True

        # Configuration changed
        if state.config_hash != current_config_hash:
            logger.debug(
                f"Reconfigure needed: config changed "
                f"(old={state.config_hash[:16]}..., new={current_config_hash[:16]}...)"
            )
            return True

        # CMake not configured
        if not state.cmake_configured:
            logger.debug("Reconfigure needed: CMake not configured")
            return True

        # Build directory doesn't exist
        build_dir = self.project_root / state.build_directory
        if not build_dir.exists():
            logger.debug(f"Reconfigure needed: build directory missing ({build_dir})")
            return True

        logger.debug("No reconfiguration needed")
        return False

    def validate(self) -> list[str]:
        """
        Validate current state consistency.

        Checks that:
        - Active toolchain still exists (if set)
        - Build directory exists (if CMake configured)

        Returns:
            List of validation issues (empty if valid)

        Example:
            >>> issues = manager.validate()
            >>> if issues:
            ...     for issue in issues:
            ...         print(f"⚠ {issue}")
        """
        state = self.load()
        issues = []

        # Check toolchain exists
        if state.active_toolchain:
            try:
                from toolchainkit.core.cache_registry import ToolchainCacheRegistry
                from toolchainkit.core.directory import get_global_cache_dir

                cache_dir = get_global_cache_dir()
                registry_file = cache_dir / "registry.json"
                registry = ToolchainCacheRegistry(registry_file)

                toolchain_info = registry.get_toolchain_info(state.active_toolchain)
                if not toolchain_info:
                    issues.append(
                        f"Active toolchain not found in registry: {state.active_toolchain}. "
                        f"The toolchain may have been removed or never installed."
                    )
                elif not Path(toolchain_info["path"]).exists():
                    issues.append(
                        f"Active toolchain path does not exist: {toolchain_info['path']}. "
                        f"The toolchain directory may have been deleted."
                    )
            except ImportError:
                # Registry module not available, skip validation
                logger.debug(
                    "Registry module not available, skipping toolchain validation"
                )
            except Exception as e:
                logger.warning(f"Error validating toolchain: {e}")

        # Check build directory
        if state.cmake_configured:
            build_dir = self.project_root / state.build_directory
            if not build_dir.exists():
                issues.append(
                    f"Build directory not found: {build_dir}. "
                    f"CMake was marked as configured, but the build directory is missing. "
                    f"Run configuration again to recreate it."
                )

        return issues

    def clear(self):
        """
        Clear state (reset to initial).

        Resets all state to default values and saves.

        Example:
            >>> manager.clear()
            >>> state = manager.load()
            >>> assert state.active_toolchain is None
        """
        self._state = ProjectState()
        self.save()
        logger.info("Cleared state to initial values")

    def _migrate_state(self, old_data: dict) -> dict:
        """
        Migrate state from old version.

        Future versions can implement migration logic here.

        Args:
            old_data: Old state data

        Returns:
            Migrated state data (v1 format)
        """
        logger.warning("State version migration not yet implemented")
        # For now, just reset to v1
        old_data["version"] = 1
        return old_data


def compute_config_hash(config_path: Path) -> str:
    """
    Compute hash of configuration file.

    Args:
        config_path: Path to toolchainkit.yaml

    Returns:
        SHA256 hash of configuration with 'sha256:' prefix

    Example:
        >>> from pathlib import Path
        >>> config_file = Path('/path/to/toolchainkit.yaml')
        >>> hash_str = compute_config_hash(config_file)
        >>> print(hash_str)  # "sha256:abc123..."
    """
    if not config_path.exists():
        return "sha256:no-config"

    from toolchainkit.core.verification import compute_file_hash

    hash_value = compute_file_hash(config_path, algorithm="sha256")
    return f"sha256:{hash_value}"
