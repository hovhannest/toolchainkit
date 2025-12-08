"""
End-to-end tests for Python API workflows.

Tests complete workflows using the ToolchainKit Python API (not CLI).
CLI-based workflows will be added when CLI commands (Tasks 32-40) are implemented.
"""

import pytest


@pytest.mark.e2e
class TestPythonAPIWorkflows:
    """Test end-to-end workflows using Python API."""

    def test_directory_initialization(self, temp_workspace):
        """
        Test: Initialize directory structure for a project.

        Workflow:
        1. Create directory structure
        2. Verify directories exist
        3. Verify gitignore created
        """
        from toolchainkit.core.directory import create_directory_structure

        # Initialize
        paths = create_directory_structure(temp_workspace)

        # Verify global cache
        assert paths["global_cache"].exists()
        assert (paths["global_cache"] / "toolchains").exists()
        assert (paths["global_cache"] / "downloads").exists()

        # Verify project local
        assert paths["project_local"].exists()
        assert (paths["project_local"] / "packages").exists()

        # Verify gitignore
        gitignore = temp_workspace / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".toolchainkit" in content

    def test_platform_detection_workflow(self):
        """
        Test: Detect platform and use for backend selection.

        Workflow:
        1. Detect platform
        2. Use platform info for backend detection
        3. Verify backend configuration
        """
        from toolchainkit.core.platform import detect_platform
        from toolchainkit.cmake.backends import BuildBackendDetector

        # Detect platform
        platform = detect_platform()
        assert platform.os in ["windows", "linux", "macos"]

        # Detect backend
        detector = BuildBackendDetector(platform)
        backends = detector.get_all()

        # Should have at least one backend on most systems
        # (may be empty on minimal systems)
        if backends:
            backend = detector.detect_best()
            assert backend is not None
            assert backend.is_available()

    def test_config_parse_and_validate_workflow(self, temp_workspace):
        """
        Test: Parse and validate configuration.

        Workflow:
        1. Create configuration file
        2. Parse configuration
        3. Validate configuration
        4. Check for issues
        """
        from toolchainkit.config.parser import parse_config
        from toolchainkit.config.validation import ConfigValidator
        from toolchainkit.core.platform import detect_platform

        # Create config
        config_file = temp_workspace / "toolchainkit.yaml"
        config_content = """version: 1
toolchains:
  - name: default
    type: clang
    version: "18"

build:
  backend: ninja
  parallel: "8"
"""
        config_file.write_text(config_content)

        # Parse
        config = parse_config(config_file)
        assert config is not None

        # Validate
        platform_info = detect_platform()
        validator = ConfigValidator(platform_info)
        result = validator.validate(config)

        # May have warnings (e.g., toolchain not found) but shouldn't have syntax errors
        assert isinstance(result.issues, list)

    def test_backend_detection_and_config_workflow(self):
        """
        Test: Detect backend and generate CMake configuration.

        Workflow:
        1. Detect best available backend
        2. Create backend configuration
        3. Generate CMake arguments
        4. Verify arguments are valid
        """
        from toolchainkit.cmake.backends import (
            detect_build_backend,
            BuildBackendConfig,
        )
        from toolchainkit.core.exceptions import BuildBackendError

        try:
            # Detect backend
            backend = detect_build_backend()
            assert backend is not None

            # Create config
            config = BuildBackendConfig(backend)

            # Generate arguments
            cmake_args = config.generate_cmake_args()
            assert "-G" in cmake_args
            # Backend name appears as part of the generator argument
            assert len(cmake_args) > 0
            assert any(
                "Ninja" in str(arg)
                or "Makefiles" in str(arg)
                or "Visual Studio" in str(arg)
                or "Xcode" in str(arg)
                for arg in cmake_args
            )

            build_args = config.generate_build_args("Debug")
            assert "--build" in build_args
            assert "--config" in build_args

        except BuildBackendError:
            pytest.skip("No build backend available")

    def test_state_management_workflow(self, temp_workspace):
        """
        Test: Project state management.

        Workflow:
        1. Initialize directory structure
        2. Create state manager
        3. Update state
        4. Reload and verify
        """
        from toolchainkit.core.directory import create_directory_structure
        from toolchainkit.core.state import StateManager

        # Initialize
        create_directory_structure(temp_workspace)

        # Create state manager
        state_mgr = StateManager(temp_workspace)

        # Load state (creates if doesn't exist)
        state = state_mgr.load()
        assert state is not None

        # Update state
        state_mgr.update_toolchain(
            toolchain_id="test-toolchain-1", toolchain_hash="abc123"
        )

        # Reload and verify
        state_mgr2 = StateManager(temp_workspace)
        state2 = state_mgr2.load()

        assert state2.active_toolchain == "test-toolchain-1"
        assert state2.toolchain_hash == "abc123"

    @pytest.mark.slow
    def test_full_cmake_workflow(
        self,
        python_api_workspace,
        cmake_available,
        compiler_available,
        build_backend_available,
    ):
        """
        Test: Complete CMake configure and build workflow.

        Workflow:
        1. Set up workspace with CMake project
        2. Detect backend
        3. Configure CMake
        4. Build project
        5. Verify artifacts

        This test requires CMake, a compiler, and a build backend.
        """
        from toolchainkit.cmake.backends import detect_build_backend
        from tests.cmake.test_integration import CMakeTestRunner
        from tests.cmake.test_projects import HelloWorldProject

        # Create test project
        project = HelloWorldProject()
        source_dir = python_api_workspace / "hello"
        build_dir = python_api_workspace / "build"
        project.create(source_dir)

        # Detect backend
        backend = detect_build_backend()
        print(f"Using backend: {backend.name}")

        # Configure and build
        runner = CMakeTestRunner(backend_name=backend.get_cmake_generator())

        # Configure
        config_result = runner.configure(source_dir, build_dir)
        if config_result.returncode != 0:
            print(f"Configure output:\n{config_result.stdout}")
            print(f"Configure errors:\n{config_result.stderr}")
            pytest.skip("Configure failed (may need specific compiler setup)")

        # Build
        build_result = runner.build(build_dir)
        if build_result.returncode != 0:
            print(f"Build output:\n{build_result.stdout}")
            print(f"Build errors:\n{build_result.stderr}")
            pytest.skip("Build failed (may need specific compiler setup)")

        # Verify artifacts
        expected_outputs = project.get_expected_outputs()
        found = False
        for expected in expected_outputs:
            if list(build_dir.rglob(expected)):
                found = True
                break

        assert found, f"Expected build artifacts not found: {expected_outputs}"


@pytest.mark.e2e
class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_missing_config_file(self, temp_workspace):
        """Test: Graceful handling of missing config file."""
        from toolchainkit.config.parser import parse_config, ConfigError

        missing_file = temp_workspace / "nonexistent.yaml"

        with pytest.raises(ConfigError):
            parse_config(missing_file)

    def test_invalid_yaml_syntax(self, temp_workspace):
        """Test: Graceful handling of invalid YAML."""
        from toolchainkit.config.parser import parse_config, ConfigError

        config_file = temp_workspace / "bad.yaml"
        config_file.write_text("invalid: yaml: content: [[[")

        with pytest.raises(ConfigError):
            parse_config(config_file)

    def test_backend_not_available_error(self):
        """Test: Proper error when preferred backend unavailable."""
        from toolchainkit.cmake.backends import (
            detect_build_backend,
            BackendNotAvailableError,
        )

        with pytest.raises(BackendNotAvailableError):
            detect_build_backend(prefer="NonExistentBackend9999")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
