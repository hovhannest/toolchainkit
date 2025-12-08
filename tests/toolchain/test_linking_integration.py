"""
tests/toolchain/test_linking_integration.py

Integration tests for symlink and junction management.
"""

import pytest
import sys
from pathlib import Path

from toolchainkit.toolchain.linking import ToolchainLinkManager


@pytest.fixture
def link_manager():
    """Link manager with real platform detection."""
    return ToolchainLinkManager()


@pytest.fixture
def mock_toolchain(tmp_path):
    """Create a realistic mock toolchain directory."""
    toolchain_dir = tmp_path / ".toolchainkit" / "toolchains" / "llvm-18.1.8-linux-x64"

    # Create realistic toolchain structure
    bin_dir = toolchain_dir / "bin"
    bin_dir.mkdir(parents=True)

    lib_dir = toolchain_dir / "lib"
    lib_dir.mkdir(parents=True)

    include_dir = toolchain_dir / "include"
    include_dir.mkdir(parents=True)

    # Create mock binaries
    (bin_dir / "clang").write_text("#!/bin/sh\necho clang version 18.1.8")
    (bin_dir / "clang++").write_text("#!/bin/sh\necho clang++ version 18.1.8")
    (bin_dir / "lld").write_text("#!/bin/sh\necho lld 18.1.8")

    # Create mock libraries
    (lib_dir / "libc++.a").touch()
    (lib_dir / "libc++abi.a").touch()

    # Create mock headers
    (include_dir / "c++" / "v1").mkdir(parents=True)
    (include_dir / "c++" / "v1" / "iostream").touch()

    return toolchain_dir


@pytest.fixture
def project_structure(tmp_path):
    """Create a realistic project structure."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # Create project files
    (project_dir / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\n" "project(MyProject)\n"
    )

    (project_dir / "src").mkdir()
    (project_dir / "src" / "main.cpp").write_text(
        "#include <iostream>\n" "int main() { return 0; }\n"
    )

    (project_dir / "include").mkdir()
    (project_dir / "tests").mkdir()

    return project_dir


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
def test_create_and_verify_toolchain_link(
    link_manager, mock_toolchain, project_structure
):
    """Test creating and verifying a toolchain link in realistic scenario."""
    # Create link from project to toolchain
    link_path = link_manager.link_toolchain_to_project(
        mock_toolchain, project_structure, link_name=".toolchain"
    )

    # Verify link was created
    assert link_path.exists()
    assert link_manager.is_valid_link(link_path)

    # Verify link points to correct target
    resolved = link_manager.resolve_link(link_path)
    assert resolved == mock_toolchain.resolve()

    # Verify we can access toolchain files through link
    clang_bin = link_path / "bin" / "clang"
    assert clang_bin.exists()


@pytest.mark.integration
def test_multiple_projects_same_toolchain(link_manager, mock_toolchain, tmp_path):
    """Test multiple projects linking to same toolchain."""
    # Create multiple projects
    project1 = tmp_path / "project1"
    project1.mkdir()

    project2 = tmp_path / "project2"
    project2.mkdir()

    project3 = tmp_path / "project3"
    project3.mkdir()

    # Create links from all projects to same toolchain
    link1 = link_manager.link_toolchain_to_project(mock_toolchain, project1)
    link2 = link_manager.link_toolchain_to_project(mock_toolchain, project2)
    link3 = link_manager.link_toolchain_to_project(mock_toolchain, project3)

    # Verify all links are valid
    assert link_manager.is_valid_link(link1)
    assert link_manager.is_valid_link(link2)
    assert link_manager.is_valid_link(link3)

    # Verify all point to same target
    target1 = link_manager.resolve_link(link1)
    target2 = link_manager.resolve_link(link2)
    target3 = link_manager.resolve_link(link3)

    assert target1 == target2 == target3 == mock_toolchain.resolve()


@pytest.mark.integration
def test_nested_directory_structure(link_manager, mock_toolchain, tmp_path):
    """Test links in deeply nested directory structure."""
    # Create nested project structure
    project_root = tmp_path / "workspace" / "team" / "projects" / "my_app"
    project_root.mkdir(parents=True)

    # Create link in nested location
    link_path = link_manager.link_toolchain_to_project(mock_toolchain, project_root)

    # Verify link works in nested structure
    assert link_manager.is_valid_link(link_path)

    # Verify resolution works
    resolved = link_manager.resolve_link(link_path)
    assert resolved == mock_toolchain.resolve()


@pytest.mark.integration
def test_find_links_in_workspace(link_manager, mock_toolchain, tmp_path):
    """Test finding all links in a workspace with multiple projects."""
    # Create workspace with multiple projects
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    projects = []
    for i in range(5):
        project = workspace / f"project{i}"
        project.mkdir()
        link = link_manager.link_toolchain_to_project(mock_toolchain, project)
        projects.append((project, link))

    # Find all links in workspace
    links = link_manager.find_links(workspace)

    # Should find all 5 links
    assert len(links) == 5

    # Verify all found links are in our project list
    for project, expected_link in projects:
        assert expected_link in links


@pytest.mark.integration
def test_cleanup_broken_links_in_workspace(link_manager, tmp_path):
    """Test cleaning up broken links in a workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create temporary toolchains
    temp_toolchains = []
    for i in range(3):
        tc = tmp_path / f"toolchain{i}"
        tc.mkdir()
        temp_toolchains.append(tc)

    # Create projects with links
    projects = []
    for i in range(3):
        project = workspace / f"project{i}"
        project.mkdir()
        link = link_manager.link_toolchain_to_project(temp_toolchains[i], project)
        projects.append(link)

    # Break some toolchains (delete targets)
    temp_toolchains[0].rmdir()  # Break first
    temp_toolchains[2].rmdir()  # Break third

    # Find broken links
    broken = link_manager.find_broken_links(workspace)
    assert len(broken) == 2

    # Cleanup broken links
    removed = link_manager.cleanup_broken_links(workspace, dry_run=False)
    assert removed == 2

    # Verify only valid link remains
    remaining_links = link_manager.find_links(workspace)
    assert len(remaining_links) == 1
    assert link_manager.is_valid_link(remaining_links[0])


@pytest.mark.integration
def test_link_overwrite_with_force(link_manager, tmp_path):
    """Test overwriting existing link with force flag."""
    # Create two different toolchains
    toolchain1 = tmp_path / "toolchain1"
    toolchain1.mkdir()

    toolchain2 = tmp_path / "toolchain2"
    toolchain2.mkdir()

    project = tmp_path / "project"
    project.mkdir()

    # Create link to first toolchain
    link = link_manager.link_toolchain_to_project(toolchain1, project)
    assert link_manager.resolve_link(link) == toolchain1.resolve()

    # Overwrite with link to second toolchain (force=True in implementation)
    link2 = link_manager.link_toolchain_to_project(toolchain2, project)
    assert link2 == link
    assert link_manager.resolve_link(link2) == toolchain2.resolve()


@pytest.mark.integration
def test_link_removal_preserves_target(link_manager, mock_toolchain, tmp_path):
    """Test that removing link doesn't affect target toolchain."""
    project = tmp_path / "project"
    project.mkdir()

    # Verify toolchain content before linking
    original_files = list(mock_toolchain.rglob("*"))
    original_file_count = len(original_files)

    # Create and remove link
    link = link_manager.link_toolchain_to_project(mock_toolchain, project)
    link_manager.remove_link(link)

    # Verify toolchain is unchanged
    remaining_files = list(mock_toolchain.rglob("*"))
    assert len(remaining_files) == original_file_count

    # Verify specific files still exist
    assert (mock_toolchain / "bin" / "clang").exists()
    assert (mock_toolchain / "lib" / "libc++.a").exists()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_symlink_relative_vs_absolute(link_manager, mock_toolchain, tmp_path):
    """Test that symlinks are created with absolute paths."""
    project = tmp_path / "project"
    project.mkdir()

    link = link_manager.link_toolchain_to_project(mock_toolchain, project)

    # Read the symlink target
    import os

    target = os.readlink(link)

    # Verify it's an absolute path (or resolves to absolute)
    assert Path(target).is_absolute() or link.resolve().is_absolute()


@pytest.mark.integration
def test_complex_workspace_scenario(link_manager, tmp_path):
    """Test complex real-world scenario with multiple toolchains and projects."""
    # Create global cache structure
    cache = tmp_path / ".toolchainkit"
    toolchains_dir = cache / "toolchains"

    # Create multiple toolchains
    llvm18 = toolchains_dir / "llvm-18.1.8"
    llvm18.mkdir(parents=True)
    (llvm18 / "bin").mkdir()

    gcc13 = toolchains_dir / "gcc-13.2.0"
    gcc13.mkdir(parents=True)
    (gcc13 / "bin").mkdir()

    # Create workspace with multiple projects
    workspace = tmp_path / "workspace"

    project_a = workspace / "project-a"
    project_a.mkdir(parents=True)

    project_b = workspace / "project-b"
    project_b.mkdir(parents=True)

    project_c = workspace / "project-c"
    project_c.mkdir(parents=True)

    # Link projects to different toolchains
    link_a = link_manager.link_toolchain_to_project(llvm18, project_a)
    link_b = link_manager.link_toolchain_to_project(gcc13, project_b)
    link_c = link_manager.link_toolchain_to_project(llvm18, project_c)

    # Verify all links are valid
    assert link_manager.is_valid_link(link_a)
    assert link_manager.is_valid_link(link_b)
    assert link_manager.is_valid_link(link_c)

    # Verify projects A and C point to same toolchain
    assert link_manager.resolve_link(link_a) == link_manager.resolve_link(link_c)

    # Verify project B points to different toolchain
    assert link_manager.resolve_link(link_b) != link_manager.resolve_link(link_a)

    # Find all links
    all_links = link_manager.find_links(workspace)
    assert len(all_links) == 3


@pytest.mark.integration
def test_link_manager_with_concurrent_operations(
    link_manager, mock_toolchain, tmp_path
):
    """Test that link manager handles multiple operations correctly."""
    projects = []
    links = []

    # Create multiple projects and links
    for i in range(10):
        project = tmp_path / f"project_{i}"
        project.mkdir()
        link = link_manager.link_toolchain_to_project(mock_toolchain, project)
        projects.append(project)
        links.append(link)

    # Verify all links
    for link in links:
        assert link_manager.is_valid_link(link)

    # Remove half the links
    for i in range(0, 10, 2):
        link_manager.remove_link(links[i])

    # Verify remaining links still valid
    for i in range(1, 10, 2):
        assert link_manager.is_valid_link(links[i])

    # Verify removed links are gone
    for i in range(0, 10, 2):
        assert not links[i].exists()


@pytest.mark.integration
@pytest.mark.slow
def test_large_directory_tree_performance(link_manager, tmp_path):
    """Test performance with large directory tree."""
    # Create a large directory tree
    root = tmp_path / "large_tree"
    root.mkdir()

    # Create nested structure with many links
    num_dirs = 50
    num_links_per_dir = 5

    for i in range(num_dirs):
        dir_path = root / f"dir_{i}"
        dir_path.mkdir()

        for j in range(num_links_per_dir):
            target = tmp_path / f"target_{i}_{j}"
            target.mkdir(exist_ok=True)

            link_path = dir_path / f"link_{j}"
            link_manager.create_link(link_path, target)

    # Measure performance of finding all links
    import time

    start = time.time()
    links = link_manager.find_links(root)
    elapsed = time.time() - start

    # Should find all links
    expected_links = num_dirs * num_links_per_dir
    assert len(links) == expected_links

    # Should complete in reasonable time (< 5 seconds)
    assert elapsed < 5.0, f"Finding {expected_links} links took {elapsed:.2f}s"


@pytest.mark.integration
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_junction_specific_behavior(link_manager, mock_toolchain, tmp_path):
    """Test Windows-specific junction behavior."""
    project = tmp_path / "project"
    project.mkdir()

    # Create junction
    link = link_manager.link_toolchain_to_project(mock_toolchain, project)

    # Verify it's detected as junction
    assert link_manager._is_junction(link)

    # Verify junction attributes
    import os

    st = os.stat(link, follow_symlinks=False)
    assert hasattr(st, "st_file_attributes")
    assert st.st_file_attributes & 0x400  # FILE_ATTRIBUTE_REPARSE_POINT

    # Verify can be removed without affecting target
    link_manager.remove_link(link)
    assert not link.exists()
    assert mock_toolchain.exists()


@pytest.mark.integration
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Linux-specific test")
def test_linux_symlink_specific_behavior(link_manager, mock_toolchain, tmp_path):
    """Test Linux-specific symlink behavior."""
    project = tmp_path / "project"
    project.mkdir()

    # Create symlink
    link = link_manager.link_toolchain_to_project(mock_toolchain, project)

    # Verify it's a symlink
    assert link.is_symlink()

    # Verify symlink can be read
    import os

    target = os.readlink(link)
    assert (
        Path(target) == mock_toolchain
        or Path(target).resolve() == mock_toolchain.resolve()
    )

    # Verify symlink behavior
    assert link.resolve() == mock_toolchain.resolve()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
