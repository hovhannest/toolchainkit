"""
Unit tests for package manager base infrastructure.

Tests the abstract base class, configuration, and detection system
for package manager integrations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from toolchainkit.packages.base import (
    PackageManager,
    PackageManagerConfig,
    PackageManagerDetector,
)
from toolchainkit.core.exceptions import (
    PackageManagerError,
    PackageManagerNotFoundError,
    PackageManagerDetectionError,
    PackageManagerInstallError,
)


# =============================================================================
# Test PackageManagerConfig
# =============================================================================


class TestPackageManagerConfig:
    """Test PackageManagerConfig dataclass."""

    def test_create_config(self, tmp_path):
        """Test creating a basic configuration."""
        manifest = tmp_path / "manifest.txt"
        manifest.touch()

        config = PackageManagerConfig(name="test", manifest_file=manifest)

        assert config.name == "test"
        assert config.manifest_file == manifest
        assert config.toolchain_file is None

    def test_create_config_with_toolchain(self, tmp_path):
        """Test creating configuration with toolchain file."""
        manifest = tmp_path / "manifest.txt"
        toolchain = tmp_path / "toolchain.cmake"
        manifest.touch()
        toolchain.touch()

        config = PackageManagerConfig(
            name="test", manifest_file=manifest, toolchain_file=toolchain
        )

        assert config.name == "test"
        assert config.manifest_file == manifest
        assert config.toolchain_file == toolchain

    def test_config_is_immutable(self, tmp_path):
        """Test that configuration is immutable (frozen)."""
        manifest = tmp_path / "manifest.txt"
        manifest.touch()

        config = PackageManagerConfig(name="test", manifest_file=manifest)

        with pytest.raises(AttributeError):
            config.name = "modified"

    def test_config_validates_name(self, tmp_path):
        """Test that empty name is rejected."""
        manifest = tmp_path / "manifest.txt"
        manifest.touch()

        with pytest.raises(ValueError, match="name cannot be empty"):
            PackageManagerConfig(name="", manifest_file=manifest)

    def test_config_validates_manifest_type(self):
        """Test that manifest_file must be Path."""
        with pytest.raises(TypeError, match="manifest_file must be Path"):
            PackageManagerConfig(name="test", manifest_file="not/a/path")

    def test_config_validates_toolchain_type(self, tmp_path):
        """Test that toolchain_file must be Path or None."""
        manifest = tmp_path / "manifest.txt"
        manifest.touch()

        with pytest.raises(TypeError, match="toolchain_file must be Path or None"):
            PackageManagerConfig(
                name="test", manifest_file=manifest, toolchain_file="not/a/path"
            )


# =============================================================================
# Mock Package Manager for Testing
# =============================================================================


class MockPackageManager(PackageManager):
    """Mock package manager implementation for testing."""

    def __init__(self, project_root: Path, name: str = "mock", detectable: bool = True):
        super().__init__(project_root)
        self._name = name
        self._detectable = detectable
        self.install_called = False
        self.generate_called = False

    def detect(self) -> bool:
        return self._detectable

    def install_dependencies(self) -> None:
        self.install_called = True

    def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
        self.generate_called = True
        return toolchain_file.parent / f"{self._name}-integration.cmake"

    def get_name(self) -> str:
        return self._name


# =============================================================================
# Test PackageManager Abstract Base Class
# =============================================================================


class TestPackageManager:
    """Test PackageManager abstract base class."""

    def test_cannot_instantiate_abstract_class(self, tmp_path):
        """Test that abstract class cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PackageManager(tmp_path)

    def test_constructor_validates_project_root_type(self):
        """Test that project_root must be Path."""
        with pytest.raises(TypeError, match="project_root must be Path"):
            MockPackageManager("not/a/path")

    def test_constructor_validates_project_root_exists(self, tmp_path):
        """Test that project_root must exist."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Project root does not exist"):
            MockPackageManager(nonexistent)

    def test_implementation_stores_project_root(self, tmp_path):
        """Test that implementation stores project_root."""
        manager = MockPackageManager(tmp_path)
        assert manager.project_root == tmp_path

    def test_implementation_must_implement_detect(self, tmp_path):
        """Test that implementations must implement detect()."""

        class IncompleteManager(PackageManager):
            def install_dependencies(self):
                pass

            def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
                return toolchain_file

            def get_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteManager(tmp_path)

    def test_implementation_must_implement_install(self, tmp_path):
        """Test that implementations must implement install_dependencies()."""

        class IncompleteManager(PackageManager):
            def detect(self) -> bool:
                return True

            def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
                return toolchain_file

            def get_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteManager(tmp_path)

    def test_implementation_must_implement_generate(self, tmp_path):
        """Test that implementations must implement generate_toolchain_integration()."""

        class IncompleteManager(PackageManager):
            def detect(self) -> bool:
                return True

            def install_dependencies(self):
                pass

            def get_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteManager(tmp_path)

    def test_implementation_must_implement_get_name(self, tmp_path):
        """Test that implementations must implement get_name()."""

        class IncompleteManager(PackageManager):
            def detect(self) -> bool:
                return True

            def install_dependencies(self):
                pass

            def generate_toolchain_integration(self, toolchain_file: Path) -> Path:
                return toolchain_file

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteManager(tmp_path)

    def test_mock_implementation_works(self, tmp_path):
        """Test that our mock implementation works correctly."""
        manager = MockPackageManager(tmp_path, name="test")

        assert manager.detect() is True
        assert manager.get_name() == "test"

        manager.install_dependencies()
        assert manager.install_called is True

        toolchain = tmp_path / "toolchain.cmake"
        result = manager.generate_toolchain_integration(toolchain)
        assert manager.generate_called is True
        assert result == tmp_path / "test-integration.cmake"


# =============================================================================
# Test PackageManagerDetector
# =============================================================================


class TestPackageManagerDetector:
    """Test PackageManagerDetector class."""

    def test_create_detector(self, tmp_path):
        """Test creating a detector."""
        detector = PackageManagerDetector(tmp_path)

        assert detector.project_root == tmp_path
        assert len(detector.managers) == 0

    def test_detector_validates_project_root_type(self):
        """Test that project_root must be Path."""
        with pytest.raises(TypeError, match="project_root must be Path"):
            PackageManagerDetector("not/a/path")

    def test_detector_validates_project_root_exists(self, tmp_path):
        """Test that project_root must exist."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Project root does not exist"):
            PackageManagerDetector(nonexistent)

    def test_register_manager(self, tmp_path):
        """Test registering a package manager."""
        detector = PackageManagerDetector(tmp_path)
        manager = MockPackageManager(tmp_path)

        detector.register(manager)

        assert len(detector.managers) == 1
        assert detector.managers[0] is manager

    def test_register_multiple_managers(self, tmp_path):
        """Test registering multiple package managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="manager1")
        manager2 = MockPackageManager(tmp_path, name="manager2")

        detector.register(manager1)
        detector.register(manager2)

        assert len(detector.managers) == 2
        assert detector.managers[0] is manager1
        assert detector.managers[1] is manager2

    def test_register_validates_type(self, tmp_path):
        """Test that register validates manager type."""
        detector = PackageManagerDetector(tmp_path)

        with pytest.raises(TypeError, match="manager must be PackageManager instance"):
            detector.register("not a manager")

    def test_register_validates_project_root_match(self, tmp_path):
        """Test that register validates project_root matches."""
        detector = PackageManagerDetector(tmp_path)
        other_path = tmp_path / "other"
        other_path.mkdir()
        manager = MockPackageManager(other_path)

        with pytest.raises(ValueError, match="doesn't match detector project_root"):
            detector.register(manager)

    def test_detect_all_empty(self, tmp_path):
        """Test detect_all with no managers registered."""
        detector = PackageManagerDetector(tmp_path)

        detected = detector.detect_all()

        assert detected == []

    def test_detect_all_single_detected(self, tmp_path):
        """Test detect_all with single detectable manager."""
        detector = PackageManagerDetector(tmp_path)
        manager = MockPackageManager(tmp_path, detectable=True)
        detector.register(manager)

        detected = detector.detect_all()

        assert len(detected) == 1
        assert detected[0] is manager

    def test_detect_all_single_not_detected(self, tmp_path):
        """Test detect_all with single non-detectable manager."""
        detector = PackageManagerDetector(tmp_path)
        manager = MockPackageManager(tmp_path, detectable=False)
        detector.register(manager)

        detected = detector.detect_all()

        assert detected == []

    def test_detect_all_multiple_all_detected(self, tmp_path):
        """Test detect_all with multiple detectable managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="manager1", detectable=True)
        manager2 = MockPackageManager(tmp_path, name="manager2", detectable=True)
        detector.register(manager1)
        detector.register(manager2)

        detected = detector.detect_all()

        assert len(detected) == 2
        assert manager1 in detected
        assert manager2 in detected

    def test_detect_all_multiple_partial_detected(self, tmp_path):
        """Test detect_all with some detectable managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="manager1", detectable=True)
        manager2 = MockPackageManager(tmp_path, name="manager2", detectable=False)
        manager3 = MockPackageManager(tmp_path, name="manager3", detectable=True)
        detector.register(manager1)
        detector.register(manager2)
        detector.register(manager3)

        detected = detector.detect_all()

        assert len(detected) == 2
        assert manager1 in detected
        assert manager2 not in detected
        assert manager3 in detected

    def test_detect_all_handles_exception(self, tmp_path):
        """Test detect_all handles exceptions from detect()."""
        detector = PackageManagerDetector(tmp_path)

        # Create manager that raises exception
        manager = MockPackageManager(tmp_path)
        manager.detect = Mock(side_effect=RuntimeError("Detection failed"))
        detector.register(manager)

        with pytest.raises(PackageManagerDetectionError, match="Error detecting mock"):
            detector.detect_all()

    def test_detect_primary_none(self, tmp_path):
        """Test detect_primary with no managers."""
        detector = PackageManagerDetector(tmp_path)

        primary = detector.detect_primary()

        assert primary is None

    def test_detect_primary_single(self, tmp_path):
        """Test detect_primary with single manager."""
        detector = PackageManagerDetector(tmp_path)
        manager = MockPackageManager(tmp_path)
        detector.register(manager)

        primary = detector.detect_primary()

        assert primary is manager

    def test_detect_primary_multiple(self, tmp_path):
        """Test detect_primary returns first detected manager."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="first")
        manager2 = MockPackageManager(tmp_path, name="second")
        detector.register(manager1)
        detector.register(manager2)

        primary = detector.detect_primary()

        assert primary is manager1

    def test_detect_primary_skips_non_detected(self, tmp_path):
        """Test detect_primary skips non-detected managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="first", detectable=False)
        manager2 = MockPackageManager(tmp_path, name="second", detectable=True)
        detector.register(manager1)
        detector.register(manager2)

        primary = detector.detect_primary()

        assert primary is manager2

    def test_get_registered_managers(self, tmp_path):
        """Test getting all registered managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="manager1")
        manager2 = MockPackageManager(tmp_path, name="manager2")
        detector.register(manager1)
        detector.register(manager2)

        registered = detector.get_registered_managers()

        assert len(registered) == 2
        assert manager1 in registered
        assert manager2 in registered

    def test_get_registered_managers_returns_copy(self, tmp_path):
        """Test that get_registered_managers returns a copy."""
        detector = PackageManagerDetector(tmp_path)
        manager = MockPackageManager(tmp_path)
        detector.register(manager)

        registered = detector.get_registered_managers()
        registered.clear()

        # Original should still have the manager
        assert len(detector.managers) == 1

    def test_clear(self, tmp_path):
        """Test clearing all managers."""
        detector = PackageManagerDetector(tmp_path)
        manager1 = MockPackageManager(tmp_path, name="manager1")
        manager2 = MockPackageManager(tmp_path, name="manager2")
        detector.register(manager1)
        detector.register(manager2)

        detector.clear()

        assert len(detector.managers) == 0
        assert detector.detect_all() == []


# =============================================================================
# Test Exception Hierarchy
# =============================================================================


class TestExceptions:
    """Test exception classes."""

    def test_package_manager_error_is_exception(self):
        """Test PackageManagerError is an Exception."""
        assert issubclass(PackageManagerError, Exception)

    def test_not_found_error_is_package_manager_error(self):
        """Test PackageManagerNotFoundError inherits from PackageManagerError."""
        assert issubclass(PackageManagerNotFoundError, PackageManagerError)

    def test_detection_error_is_package_manager_error(self):
        """Test PackageManagerDetectionError inherits from PackageManagerError."""
        assert issubclass(PackageManagerDetectionError, PackageManagerError)

    def test_install_error_is_package_manager_error(self):
        """Test PackageManagerInstallError inherits from PackageManagerError."""
        assert issubclass(PackageManagerInstallError, PackageManagerError)

    def test_can_raise_and_catch_base_error(self):
        """Test raising and catching base error."""
        with pytest.raises(PackageManagerError, match="test error"):
            raise PackageManagerError("test error")

    def test_can_raise_and_catch_specific_errors(self):
        """Test raising and catching specific errors."""
        with pytest.raises(PackageManagerNotFoundError):
            raise PackageManagerNotFoundError("not found")

        with pytest.raises(PackageManagerDetectionError):
            raise PackageManagerDetectionError("detection failed")

        with pytest.raises(PackageManagerInstallError):
            raise PackageManagerInstallError("install failed")

    def test_specific_errors_caught_by_base(self):
        """Test that specific errors are caught by base exception."""
        try:
            raise PackageManagerInstallError("install failed")
        except PackageManagerError as e:
            assert isinstance(e, PackageManagerInstallError)
            assert str(e) == "install failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
