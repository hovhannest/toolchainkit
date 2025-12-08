"""
Tests for CI/CD template generation.
"""

import pytest
import yaml
from toolchainkit.ci.templates import CITemplateGenerator


class TestCITemplateGeneratorInit:
    """Test CITemplateGenerator initialization."""

    def test_init_with_path_object(self, tmp_path):
        """Test initialization with Path object."""
        generator = CITemplateGenerator(tmp_path)
        assert generator.project_root == tmp_path

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        generator = CITemplateGenerator(str(tmp_path))
        assert generator.project_root == tmp_path


class TestGitHubActionsGeneration:
    """Test GitHub Actions workflow generation."""

    def test_generate_github_actions_creates_file(self, tmp_path):
        """Test that generate_github_actions creates a workflow file."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions()

        assert workflow_file.exists()
        assert workflow_file.name == "build.yml"
        assert workflow_file.parent.name == "workflows"

    def test_generate_github_actions_creates_directory(self, tmp_path):
        """Test that .github/workflows directory is created."""
        generator = CITemplateGenerator(tmp_path)
        generator.generate_github_actions()

        workflows_dir = tmp_path / ".github" / "workflows"
        assert workflows_dir.exists()
        assert workflows_dir.is_dir()

    def test_generate_github_actions_default_values(self, tmp_path):
        """Test generation with default values."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions()

        content = workflow_file.read_text()

        # Check for default OS matrix
        assert "ubuntu-latest" in content
        assert "macos-latest" in content
        assert "windows-latest" in content

        # Check for default build types
        assert "Debug" in content
        assert "Release" in content

    def test_generate_github_actions_custom_os_matrix(self, tmp_path):
        """Test generation with custom OS matrix."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(
            os_matrix=["ubuntu-latest", "ubuntu-20.04"]
        )

        content = workflow_file.read_text()

        assert "ubuntu-latest" in content
        assert "ubuntu-20.04" in content
        assert "windows-latest" not in content

    def test_generate_github_actions_custom_build_types(self, tmp_path):
        """Test generation with custom build types."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(
            build_types=["Release", "MinSizeRel"]
        )

        content = workflow_file.read_text()

        assert "Release" in content
        assert "MinSizeRel" in content
        assert "Debug" not in content

    def test_generate_github_actions_with_caching(self, tmp_path):
        """Test that caching is included when enabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_caching=True)

        content = workflow_file.read_text()

        assert "cache@v3" in content.lower()
        assert ".toolchainkit" in content

    def test_generate_github_actions_without_caching(self, tmp_path):
        """Test that caching is excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_caching=False)

        content = workflow_file.read_text()

        assert "cache@v3" not in content.lower()

    def test_generate_github_actions_with_tests(self, tmp_path):
        """Test that test execution is included when enabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_tests=True)

        content = workflow_file.read_text()

        assert "ctest" in content.lower()
        assert "Run tests" in content

    def test_generate_github_actions_without_tests(self, tmp_path):
        """Test that test execution is excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_tests=False)

        content = workflow_file.read_text()

        assert "ctest" not in content.lower()

    def test_generate_github_actions_with_artifacts(self, tmp_path):
        """Test that artifact uploads are included when enabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_artifacts=True)

        content = workflow_file.read_text()

        assert "upload-artifact@v3" in content.lower()
        assert "Upload build artifacts" in content

    def test_generate_github_actions_without_artifacts(self, tmp_path):
        """Test that artifact uploads are excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(enable_artifacts=False)

        content = workflow_file.read_text()

        assert "upload-artifact" not in content.lower()

    def test_generate_github_actions_valid_yaml(self, tmp_path):
        """Test that generated workflow is valid YAML."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions()

        content = workflow_file.read_text()

        # Should parse without errors
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "name" in parsed
        assert "jobs" in parsed

    def test_generate_github_actions_has_required_steps(self, tmp_path):
        """Test that workflow has all required steps."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions()

        content = workflow_file.read_text()

        # Check for essential steps
        assert "Checkout code" in content
        assert "Set up Python" in content
        assert "Install ToolchainKit" in content
        assert "Bootstrap project" in content
        assert "Configure CMake" in content
        assert "Build" in content


class TestGitLabCIGeneration:
    """Test GitLab CI configuration generation."""

    def test_generate_gitlab_ci_creates_file(self, tmp_path):
        """Test that generate_gitlab_ci creates a config file."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci()

        assert config_file.exists()
        assert config_file.name == ".gitlab-ci.yml"

    def test_generate_gitlab_ci_with_caching(self, tmp_path):
        """Test that caching is included when enabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_caching=True)

        content = config_file.read_text()

        assert "cache:" in content
        assert ".toolchainkit" in content

    def test_generate_gitlab_ci_without_caching(self, tmp_path):
        """Test that caching is excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_caching=False)

        content = config_file.read_text()

        assert "cache:" not in content

    def test_generate_gitlab_ci_with_tests(self, tmp_path):
        """Test that test job is included when enabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_tests=True)

        content = config_file.read_text()

        assert "test:" in content
        assert "ctest" in content.lower()

    def test_generate_gitlab_ci_without_tests(self, tmp_path):
        """Test that test job is excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_tests=False)

        content = config_file.read_text()

        assert "test:" not in content or "stage: test" not in content

    def test_generate_gitlab_ci_with_artifacts(self, tmp_path):
        """Test that artifacts are configured when enabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_artifacts=True)

        content = config_file.read_text()

        assert "artifacts:" in content

    def test_generate_gitlab_ci_without_artifacts(self, tmp_path):
        """Test that artifacts are excluded when disabled."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci(enable_artifacts=False)

        content = config_file.read_text()

        assert "artifacts:" not in content

    def test_generate_gitlab_ci_valid_yaml(self, tmp_path):
        """Test that generated configuration is valid YAML."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci()

        content = config_file.read_text()

        # Should parse without errors
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "stages" in parsed

    def test_generate_gitlab_ci_has_required_sections(self, tmp_path):
        """Test that configuration has all required sections."""
        generator = CITemplateGenerator(tmp_path)
        config_file = generator.generate_gitlab_ci()

        content = config_file.read_text()

        # Check for essential sections
        assert "image:" in content
        assert "stages:" in content
        assert "before_script:" in content
        assert "build:debug" in content
        assert "build:release" in content


class TestGenerateAll:
    """Test generation of all CI/CD configurations."""

    def test_generate_all_creates_both_files(self, tmp_path):
        """Test that generate_all creates both GitHub and GitLab files."""
        generator = CITemplateGenerator(tmp_path)
        results = generator.generate_all()

        assert "github_actions" in results
        assert "gitlab_ci" in results
        assert results["github_actions"].exists()
        assert results["gitlab_ci"].exists()

    def test_generate_all_with_custom_options(self, tmp_path):
        """Test generate_all with custom options."""
        generator = CITemplateGenerator(tmp_path)
        results = generator.generate_all(
            os_matrix=["ubuntu-latest"],
            build_types=["Release"],
            enable_caching=False,
            enable_tests=False,
            enable_artifacts=False,
        )

        assert len(results) == 2

        # Check GitHub Actions
        github_content = results["github_actions"].read_text()
        assert "ubuntu-latest" in github_content
        assert "Release" in github_content
        assert "cache@v3" not in github_content.lower()

        # Check GitLab CI
        gitlab_content = results["gitlab_ci"].read_text()
        assert "cache:" not in gitlab_content
        assert "artifacts:" not in gitlab_content


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_existing_workflow_file_is_overwritten(self, tmp_path):
        """Test that existing workflow file is overwritten."""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        workflow_file = workflows_dir / "build.yml"
        workflow_file.write_text("old content")

        generator = CITemplateGenerator(tmp_path)
        new_file = generator.generate_github_actions()

        assert new_file.read_text() != "old content"
        assert "name: Build" in new_file.read_text()

    def test_existing_gitlab_config_is_overwritten(self, tmp_path):
        """Test that existing GitLab config is overwritten."""
        config_file = tmp_path / ".gitlab-ci.yml"
        config_file.write_text("old content")

        generator = CITemplateGenerator(tmp_path)
        new_file = generator.generate_gitlab_ci()

        assert new_file.read_text() != "old content"
        assert "image:" in new_file.read_text()

    def test_empty_os_matrix(self, tmp_path):
        """Test with empty OS matrix list."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(os_matrix=[])

        content = workflow_file.read_text()
        # Should still generate valid YAML
        parsed = yaml.safe_load(content)
        assert parsed is not None

    def test_single_os(self, tmp_path):
        """Test with single OS in matrix."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(os_matrix=["ubuntu-latest"])

        content = workflow_file.read_text()
        assert "ubuntu-latest" in content

    def test_single_build_type(self, tmp_path):
        """Test with single build type."""
        generator = CITemplateGenerator(tmp_path)
        workflow_file = generator.generate_github_actions(build_types=["Release"])

        content = workflow_file.read_text()
        assert "Release" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
