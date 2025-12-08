"""
CI/CD template generation for ToolchainKit.

This module generates configuration files for popular CI/CD platforms,
enabling automated builds of projects using ToolchainKit.
"""

from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class CITemplateGenerator:
    """Generate CI/CD configuration files for various platforms."""

    def __init__(self, project_root: Path):
        """
        Initialize the CI template generator.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        logger.info(f"Initialized CITemplateGenerator for {project_root}")

    def generate_github_actions(
        self,
        os_matrix: Optional[List[str]] = None,
        build_types: Optional[List[str]] = None,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> Path:
        """
        Generate GitHub Actions workflow file.

        Args:
            os_matrix: List of operating systems to build on (default: ubuntu-latest, macos-latest, windows-latest)
            build_types: List of build types (default: Debug, Release)
            enable_caching: Enable caching for toolchains and builds
            enable_tests: Enable test execution
            enable_artifacts: Enable artifact uploads

        Returns:
            Path to the generated workflow file
        """
        if os_matrix is None:
            os_matrix = ["ubuntu-latest", "macos-latest", "windows-latest"]

        if build_types is None:
            build_types = ["Debug", "Release"]

        logger.info("Generating GitHub Actions workflow")
        logger.debug(f"OS matrix: {os_matrix}")
        logger.debug(f"Build types: {build_types}")

        # Generate workflow content
        workflow = self._generate_github_actions_yaml(
            os_matrix=os_matrix,
            build_types=build_types,
            enable_caching=enable_caching,
            enable_tests=enable_tests,
            enable_artifacts=enable_artifacts,
        )

        # Create .github/workflows directory
        workflow_dir = self.project_root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        # Write workflow file
        workflow_file = workflow_dir / "build.yml"
        workflow_file.write_text(workflow, encoding="utf-8")

        logger.info(f"GitHub Actions workflow created at {workflow_file}")
        return workflow_file

    def _generate_github_actions_yaml(
        self,
        os_matrix: List[str],
        build_types: List[str],
        enable_caching: bool,
        enable_tests: bool,
        enable_artifacts: bool,
    ) -> str:
        """Generate the YAML content for GitHub Actions workflow."""

        # Build OS matrix string
        os_matrix_str = ", ".join(os_matrix)

        # Build type matrix string
        build_type_matrix_str = ", ".join(build_types)

        # Caching step
        cache_step = ""
        if enable_caching:
            cache_step = """
      - name: Cache ToolchainKit toolchains
        uses: actions/cache@v3
        with:
          path: ~/.toolchainkit
          key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.yaml', 'toolchainkit.lock') }}
          restore-keys: |
            ${{ runner.os }}-toolchainkit-
"""

        # Test step
        test_step = ""
        if enable_tests:
            test_step = """
      - name: Run tests
        run: ctest --test-dir build/${{ matrix.build_type }} --output-on-failure
        shell: bash
"""

        # Artifact upload step
        artifact_step = ""
        if enable_artifacts:
            artifact_step = """
      - name: Upload build artifacts
        if: success()
        uses: actions/upload-artifact@v3
        with:
          name: build-${{ matrix.os }}-${{ matrix.build_type }}
          path: build/${{ matrix.build_type }}/
          retention-days: 7
"""

        workflow = f"""name: Build

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build:
    name: Build on ${{{{ matrix.os }}}} - ${{{{ matrix.build_type }}}}
    runs-on: ${{{{ matrix.os }}}}

    strategy:
      fail-fast: false
      matrix:
        os: [{os_matrix_str}]
        build_type: [{build_type_matrix_str}]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3
{cache_step}
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install ToolchainKit
        run: pip install toolchainkit
        shell: bash

      - name: Bootstrap project
        run: |
          if [ "${{{{ runner.os }}}}" == "Windows" ]; then
            ./bootstrap.bat
          else
            ./bootstrap.sh
          fi
        shell: bash

      - name: Configure CMake
        run: cmake --preset tkgen-${{{{ matrix.build_type }}}} || cmake -B build/${{{{ matrix.build_type }}}} -DCMAKE_BUILD_TYPE=${{{{ matrix.build_type }}}} -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
        shell: bash

      - name: Build
        run: cmake --build build/${{{{ matrix.build_type }}}} --config ${{{{ matrix.build_type }}}}
        shell: bash
{test_step}{artifact_step}"""

        return workflow

    def generate_gitlab_ci(
        self,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> Path:
        """
        Generate GitLab CI configuration file.

        Args:
            enable_caching: Enable caching for toolchains and builds
            enable_tests: Enable test execution
            enable_artifacts: Enable artifact uploads

        Returns:
            Path to the generated .gitlab-ci.yml file
        """
        logger.info("Generating GitLab CI configuration")

        # Generate configuration content
        config = self._generate_gitlab_ci_yaml(
            enable_caching=enable_caching,
            enable_tests=enable_tests,
            enable_artifacts=enable_artifacts,
        )

        # Write configuration file
        config_file = self.project_root / ".gitlab-ci.yml"
        config_file.write_text(config, encoding="utf-8")

        logger.info(f"GitLab CI configuration created at {config_file}")
        return config_file

    def _generate_gitlab_ci_yaml(
        self, enable_caching: bool, enable_tests: bool, enable_artifacts: bool
    ) -> str:
        """Generate the YAML content for GitLab CI."""

        # Cache configuration
        cache_config = ""
        if enable_caching:
            cache_config = """
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .toolchainkit/
    - ~/.toolchainkit/
"""

        # Test job
        test_job = ""
        if enable_tests:
            test_job = """
test:
  stage: test
  script:
    - cd build/Debug
    - ctest --output-on-failure
  dependencies:
    - build:debug
"""

        # Artifact configuration for build jobs
        artifacts_config = ""
        if enable_artifacts:
            artifacts_config = """
  artifacts:
    paths:
      - build/
    expire_in: 1 week
"""

        config = f"""image: ubuntu:22.04

stages:
  - build
  - test

before_script:
  - apt-get update && apt-get install -y python3 python3-pip cmake ninja-build build-essential
  - pip3 install toolchainkit
  - ./bootstrap.sh
{cache_config}
build:debug:
  stage: build
  script:
    - cmake -B build/Debug -DCMAKE_BUILD_TYPE=Debug -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
    - cmake --build build/Debug
{artifacts_config}
build:release:
  stage: build
  script:
    - cmake -B build/Release -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
    - cmake --build build/Release
{artifacts_config}{test_job}"""

        return config

    def generate_all(
        self,
        os_matrix: Optional[List[str]] = None,
        build_types: Optional[List[str]] = None,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> dict:
        """
        Generate configuration files for all supported CI/CD platforms.

        Args:
            os_matrix: List of operating systems for GitHub Actions
            build_types: List of build types
            enable_caching: Enable caching
            enable_tests: Enable test execution
            enable_artifacts: Enable artifact uploads

        Returns:
            Dictionary mapping platform name to generated file path
        """
        logger.info("Generating CI/CD configurations for all platforms")

        results = {}

        # Generate GitHub Actions
        try:
            github_file = self.generate_github_actions(
                os_matrix=os_matrix,
                build_types=build_types,
                enable_caching=enable_caching,
                enable_tests=enable_tests,
                enable_artifacts=enable_artifacts,
            )
            results["github_actions"] = github_file
        except Exception as e:
            logger.error(f"Failed to generate GitHub Actions workflow: {e}")

        # Generate GitLab CI
        try:
            gitlab_file = self.generate_gitlab_ci(
                enable_caching=enable_caching,
                enable_tests=enable_tests,
                enable_artifacts=enable_artifacts,
            )
            results["gitlab_ci"] = gitlab_file
        except Exception as e:
            logger.error(f"Failed to generate GitLab CI configuration: {e}")

        logger.info(f"Generated {len(results)} CI/CD configurations")
        return results
