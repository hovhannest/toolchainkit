"""
Base package manager abstraction for ToolchainKit.

This module provides the abstract base class and infrastructure for
integrating C++ package managers (Conan, vcpkg, CPM, etc.) with
ToolchainKit's toolchain management system.

Classes:
    PackageManagerConfig: Configuration data for package managers
    PackageManager: Abstract base class for package manager implementations
    PackageManagerDetector: Detect and manage package manager instances

Exceptions:
    PackageManagerError: Base exception for package manager errors
    PackageManagerNotFoundError: Package manager not found
    PackageManagerDetectionError: Error during package manager detection
    PackageManagerInstallError: Error during dependency installation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from toolchainkit.core.exceptions import (
    PackageManagerDetectionError,
)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class PackageManagerConfig:
    """
    Configuration data for a package manager.

    Attributes:
        name: Package manager name (e.g., 'conan', 'vcpkg')
        manifest_file: Path to package manager manifest file
        toolchain_file: Optional path to generated toolchain file

    Example:
        config = PackageManagerConfig(
            name='conan',
            manifest_file=Path('/project/conanfile.txt'),
            toolchain_file=Path('/project/build/conan_toolchain.cmake')
        )
    """

    name: str
    manifest_file: Path
    toolchain_file: Optional[Path] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Package manager name cannot be empty")
        if not isinstance(self.manifest_file, Path):
            raise TypeError(
                f"manifest_file must be Path, got {type(self.manifest_file)}"
            )
        if self.toolchain_file is not None and not isinstance(
            self.toolchain_file, Path
        ):
            raise TypeError(
                f"toolchain_file must be Path or None, got {type(self.toolchain_file)}"
            )


# =============================================================================
# Abstract Package Manager
# =============================================================================


class PackageManager(ABC):
    """
    Abstract base class for package manager implementations.

    All package manager integrations (Conan, vcpkg, CPM, etc.) must
    inherit from this class and implement the required methods.

    Attributes:
        project_root: Root directory of the project using the package manager

    Abstract Methods:
        detect(): Detect if this package manager is used in the project
        install_dependencies(): Install project dependencies
        generate_toolchain_integration(): Generate CMake integration file
        get_name(): Get the package manager name

    Example:
        class MyPackageManager(PackageManager):
            def detect(self) -> bool:
                return (self.project_root / 'mypm.json').exists()

            def install_dependencies(self):
                # Run package manager install
                pass

            def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
                # Generate CMake integration
                pass

            def get_name(self) -> str:
                return 'mypm'
    """

    def __init__(self, project_root: Path):
        """
        Initialize package manager.

        Args:
            project_root: Root directory of the project

        Raises:
            TypeError: If project_root is not a Path
            ValueError: If project_root doesn't exist
        """
        if not isinstance(project_root, Path):
            raise TypeError(f"project_root must be Path, got {type(project_root)}")
        if not project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        self.project_root = project_root

    @abstractmethod
    def detect(self) -> bool:
        """
        Detect if this package manager is used in the project.

        This method should check for the presence of package manager
        manifest files (e.g., conanfile.txt, vcpkg.json) to determine
        if the package manager is being used.

        Returns:
            True if package manager is detected, False otherwise

        Example:
            def detect(self) -> bool:
                return (self.project_root / 'conanfile.txt').exists()
        """
        pass

    @abstractmethod
    def install_dependencies(self, **kwargs) -> None:
        """
        Install project dependencies using the package manager.

        This method should run the package manager's install command
        to fetch and install all dependencies specified in the manifest.

        Args:
            **kwargs: Additional arguments for installation (e.g., platform, build_type)

        Raises:
            PackageManagerInstallError: If installation fails

        Example:
            def install_dependencies(self, **kwargs):
                result = subprocess.run(['conan', 'install', '.'])
                if result.returncode != 0:
                    raise PackageManagerInstallError("Conan install failed")
        """
        pass

    @abstractmethod
    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        """
        Generate CMake integration file for the package manager.

        This method should create a CMake file that integrates the
        package manager's toolchain with ToolchainKit's toolchain.

        Args:
            toolchain_file: Path to ToolchainKit's toolchain file

        Returns:
            Path to generated integration file

        Raises:
            PackageManagerError: If generation fails

        Example:
            def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
                integration_file = toolchain_file.parent / 'conan-integration.cmake'
                integration_file.write_text('include(${CMAKE_BINARY_DIR}/conan_toolchain.cmake)')
                return integration_file
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the package manager name.

        Returns:
            Package manager name (e.g., 'conan', 'vcpkg')

        Example:
            def get_name(self) -> str:
                return 'conan'
        """
        pass


# =============================================================================
# Package Manager Detector
# =============================================================================


class PackageManagerDetector:
    """
    Detect and manage package manager instances.

    This class maintains a registry of available package managers
    and provides methods to detect which ones are used in a project.

    Attributes:
        project_root: Root directory of the project
        managers: List of registered package manager instances

    Example:
        from pathlib import Path
        from toolchainkit.packages import PackageManagerDetector
        from toolchainkit.packages.conan import ConanIntegration
        from toolchainkit.packages.vcpkg import VcpkgIntegration

        # Create detector
        detector = PackageManagerDetector(Path('/project'))

        # Register managers
        detector.register(ConanIntegration(Path('/project')))
        detector.register(VcpkgIntegration(Path('/project')))

        # Detect which are used
        managers = detector.detect_all()
        for manager in managers:
            print(f"Found: {manager.get_name()}")
    """

    def __init__(self, project_root: Path):
        """
        Initialize package manager detector.

        Args:
            project_root: Root directory of the project

        Raises:
            TypeError: If project_root is not a Path
            ValueError: If project_root doesn't exist
        """
        if not isinstance(project_root, Path):
            raise TypeError(f"project_root must be Path, got {type(project_root)}")
        if not project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        self.project_root = project_root
        self.managers: List[PackageManager] = []

    def register(self, manager: PackageManager) -> None:
        """
        Register a package manager implementation.

        Args:
            manager: Package manager instance to register

        Raises:
            TypeError: If manager is not a PackageManager instance
            ValueError: If manager's project_root doesn't match detector's

        Example:
            detector.register(ConanIntegration(project_root))
        """
        if not isinstance(manager, PackageManager):
            raise TypeError(
                f"manager must be PackageManager instance, got {type(manager)}"
            )
        if manager.project_root != self.project_root:
            raise ValueError(
                f"Manager project_root ({manager.project_root}) "
                f"doesn't match detector project_root ({self.project_root})"
            )

        self.managers.append(manager)

    def detect_all(self) -> List[PackageManager]:
        """
        Detect all package managers in use.

        Returns:
            List of detected package manager instances (may be empty)

        Raises:
            PackageManagerDetectionError: If detection fails

        Example:
            managers = detector.detect_all()
            if managers:
                print(f"Found {len(managers)} package managers")
            else:
                print("No package managers detected")
        """
        detected = []

        for manager in self.managers:
            try:
                if manager.detect():
                    detected.append(manager)
            except Exception as e:
                raise PackageManagerDetectionError(
                    f"Error detecting {manager.get_name()}: {e}"
                ) from e

        return detected

    def detect_primary(self) -> Optional[PackageManager]:
        """
        Detect primary package manager.

        Returns the first detected package manager, or None if no
        package managers are detected. When multiple managers are
        detected, the first one registered is considered primary.

        Returns:
            Primary package manager instance, or None if none detected

        Raises:
            PackageManagerDetectionError: If detection fails

        Example:
            manager = detector.detect_primary()
            if manager:
                print(f"Primary package manager: {manager.get_name()}")
            else:
                print("No package manager found")
        """
        detected = self.detect_all()
        return detected[0] if detected else None

    def get_registered_managers(self) -> List[PackageManager]:
        """
        Get list of all registered managers.

        Returns:
            List of registered package manager instances

        Example:
            all_managers = detector.get_registered_managers()
            print(f"Registered: {[m.get_name() for m in all_managers]}")
        """
        return self.managers.copy()

    def clear(self) -> None:
        """
        Clear all registered managers.

        Example:
            detector.clear()  # Remove all registered managers
        """
        self.managers.clear()
