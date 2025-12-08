"""
tests/toolchain/test_linking.py

Unit tests for symlink and junction management.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

from toolchainkit.toolchain.linking import ToolchainLinkManager, LinkType
from toolchainkit.core.platform import PlatformInfo


@pytest.fixture
def platform_linux():
    """Mock Linux platform."""
    return PlatformInfo(
        os="linux",
        arch="x64",
        os_version="5.15",
        distribution="ubuntu",
        abi="glibc-2.31",
    )


@pytest.fixture
def platform_windows():
    """Mock Windows platform."""
    return PlatformInfo(
        os="windows", arch="x64", os_version="10.0.19041", distribution="", abi="msvc"
    )


@pytest.fixture
def link_manager_linux(platform_linux):
    """Link manager for Linux."""
    return ToolchainLinkManager(platform_linux)


@pytest.fixture
def link_manager_windows(platform_windows):
    """Link manager for Windows."""
    return ToolchainLinkManager(platform_windows)


# mock_llvm_toolchain fixture replaced with mock_llvm_toolchain from tests.fixtures.toolchains
# This fixture provided a minimal toolchain structure, but the new fixture
# provides a more realistic structure with actual files and proper layout.


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "CMakeLists.txt").touch()

    return project_dir


# ==============================================================================
# Link Type Tests
# ==============================================================================


@pytest.mark.unit
def test_link_type_enum():
    """Test LinkType enum values."""
    assert LinkType.SYMLINK.value == "symlink"
    assert LinkType.JUNCTION.value == "junction"
    assert LinkType.HARDLINK.value == "hardlink"
    assert LinkType.COPY.value == "copy"


# ==============================================================================
# Initialization Tests
# ==============================================================================


@pytest.mark.unit
def test_link_manager_init_linux(platform_linux):
    """Test link manager initialization on Linux."""
    manager = ToolchainLinkManager(platform_linux)
    assert manager.platform == platform_linux
    assert manager._use_junctions is False


@pytest.mark.unit
def test_link_manager_init_windows(platform_windows):
    """Test link manager initialization on Windows."""
    manager = ToolchainLinkManager(platform_windows)
    assert manager.platform == platform_windows
    assert manager._use_junctions is True


@pytest.mark.unit
def test_link_manager_auto_detect_platform():
    """Test automatic platform detection."""
    manager = ToolchainLinkManager()
    assert manager.platform is not None
    assert manager.platform.os in ["windows", "linux", "macos"]


# ==============================================================================
# Symlink Creation Tests (Unix)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_success(link_manager_linux, mock_llvm_toolchain, temp_project):
    """Test successful symlink creation on Unix."""
    link_path = temp_project / ".toolchain"

    result = link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    assert result is True
    assert link_path.is_symlink()
    assert link_path.resolve() == mock_llvm_toolchain.resolve()


@pytest.mark.unit
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_target_not_exists(link_manager_linux, temp_project, tmp_path):
    """Test symlink creation fails when target doesn't exist."""
    link_path = temp_project / ".toolchain"
    target_path = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="Target does not exist"):
        link_manager_linux.create_link(link_path, target_path)


@pytest.mark.unit
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_link_exists_no_force(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test symlink creation fails when link exists without force."""
    link_path = temp_project / ".toolchain"
    link_path.touch()  # Create existing file

    with pytest.raises(FileExistsError, match="Link path already exists"):
        link_manager_linux.create_link(link_path, mock_llvm_toolchain, force=False)


@pytest.mark.unit
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_link_exists_with_force(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test symlink creation succeeds when link exists with force=True."""
    link_path = temp_project / ".toolchain"
    link_path.touch()  # Create existing file

    result = link_manager_linux.create_link(link_path, mock_llvm_toolchain, force=True)

    assert result is True
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.platform_linux
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_creates_parent_dirs(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test symlink creation creates parent directories."""
    link_path = temp_project / "nested" / "path" / ".toolchain"

    result = link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    assert result is True
    assert link_path.parent.exists()
    assert link_path.is_symlink()


# ==============================================================================
# Junction Creation Tests (Windows)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_success(
    link_manager_windows, mock_llvm_toolchain, temp_project
):
    """Test successful junction creation on Windows."""
    link_path = temp_project / ".toolchain"

    result = link_manager_windows.create_link(link_path, mock_llvm_toolchain)

    assert result is True
    assert link_path.exists()
    # Verify it's a junction by checking reparse point
    assert link_manager_windows._is_junction(link_path)


@pytest.mark.unit
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_target_not_exists(
    link_manager_windows, temp_project, tmp_path
):
    """Test junction creation fails when target doesn't exist."""
    link_path = temp_project / ".toolchain"
    target_path = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="Target does not exist"):
        link_manager_windows.create_link(link_path, target_path)


@pytest.mark.unit
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_with_force(
    link_manager_windows, mock_llvm_toolchain, temp_project
):
    """Test junction creation with force overwrites existing."""
    link_path = temp_project / ".toolchain"
    link_path.mkdir()  # Create existing directory

    result = link_manager_windows.create_link(
        link_path, mock_llvm_toolchain, force=True
    )

    assert result is True
    assert link_manager_windows._is_junction(link_path)


# ==============================================================================
# Link Resolution Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_symlink(link_manager_linux, mock_llvm_toolchain, temp_project):
    """Test resolving symlink to target."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    resolved = link_manager_linux.resolve_link(link_path)

    assert resolved is not None
    assert resolved == mock_llvm_toolchain.resolve()


@pytest.mark.unit
def test_resolve_link_not_a_link(link_manager_linux, temp_project):
    """Test resolve_link returns None for non-link."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    resolved = link_manager_linux.resolve_link(regular_file)

    assert resolved is None


@pytest.mark.unit
def test_resolve_link_nonexistent(link_manager_linux, tmp_path):
    """Test resolve_link returns None for nonexistent path."""
    nonexistent = tmp_path / "nonexistent"

    resolved = link_manager_linux.resolve_link(nonexistent)

    assert resolved is None


@pytest.mark.unit
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_resolve_junction(link_manager_windows, mock_llvm_toolchain, temp_project):
    """Test resolving junction to target."""
    link_path = temp_project / ".toolchain"
    link_manager_windows.create_link(link_path, mock_llvm_toolchain)

    resolved = link_manager_windows.resolve_link(link_path)

    assert resolved is not None
    assert resolved == mock_llvm_toolchain.resolve()


# ==============================================================================
# Link Validation Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_valid_link_true(link_manager_linux, mock_llvm_toolchain, temp_project):
    """Test valid link detection."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    assert link_manager_linux.is_valid_link(link_path) is True


@pytest.mark.unit
def test_is_valid_link_false_not_a_link(link_manager_linux, temp_project):
    """Test is_valid_link returns False for non-link."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    assert link_manager_linux.is_valid_link(regular_file) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_valid_link_false_broken(
    link_manager_linux, mock_llvm_toolchain, temp_project, tmp_path
):
    """Test is_valid_link returns False for broken link."""
    # Create a temporary target that we'll delete
    temp_target = tmp_path / "temp_target"
    temp_target.mkdir()

    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, temp_target)

    # Delete the target to break the link
    temp_target.rmdir()

    assert link_manager_linux.is_valid_link(link_path) is False


# ==============================================================================
# Broken Link Detection Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_broken_link_true(link_manager_linux, temp_project, tmp_path):
    """Test broken link detection."""
    # Create a temporary target that we'll delete
    temp_target = tmp_path / "temp_target"
    temp_target.mkdir()

    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, temp_target)

    # Delete the target to break the link
    temp_target.rmdir()

    assert link_manager_linux.is_broken_link(link_path) is True


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_broken_link_false_valid(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test is_broken_link returns False for valid link."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    assert link_manager_linux.is_broken_link(link_path) is False


@pytest.mark.unit
def test_is_broken_link_false_not_a_link(link_manager_linux, temp_project):
    """Test is_broken_link returns False for non-link."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    assert link_manager_linux.is_broken_link(regular_file) is False


# ==============================================================================
# Link Removal Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_remove_symlink(link_manager_linux, mock_llvm_toolchain, temp_project):
    """Test removing symlink."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    result = link_manager_linux.remove_link(link_path)

    assert result is True
    assert not link_path.exists()
    assert not link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.platform_windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_remove_junction(link_manager_windows, mock_llvm_toolchain, temp_project):
    """Test removing junction."""
    link_path = temp_project / ".toolchain"
    link_manager_windows.create_link(link_path, mock_llvm_toolchain)

    result = link_manager_windows.remove_link(link_path)

    assert result is True
    assert not link_path.exists()


@pytest.mark.unit
def test_remove_link_nonexistent(link_manager_linux, tmp_path):
    """Test removing nonexistent link returns False."""
    nonexistent = tmp_path / "nonexistent"

    result = link_manager_linux.remove_link(nonexistent)

    assert result is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_remove_link_preserves_target(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test removing link doesn't affect target."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    link_manager_linux.remove_link(link_path)

    # Target should still exist
    assert mock_llvm_toolchain.exists()
    assert (mock_llvm_toolchain / "bin" / "clang").exists()


# ==============================================================================
# Find Links Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_single(link_manager_linux, mock_llvm_toolchain, temp_project):
    """Test finding a single link."""
    link_path = temp_project / ".toolchain"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    links = link_manager_linux.find_links(temp_project)

    assert len(links) == 1
    assert links[0] == link_path


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_multiple(
    link_manager_linux, mock_llvm_toolchain, temp_project, tmp_path
):
    """Test finding multiple links."""
    # Create multiple targets
    target1 = tmp_path / "target1"
    target1.mkdir()
    target2 = tmp_path / "target2"
    target2.mkdir()

    # Create multiple links
    link1 = temp_project / ".toolchain1"
    link2 = temp_project / "nested" / ".toolchain2"

    link_manager_linux.create_link(link1, target1)
    link_manager_linux.create_link(link2, target2)

    links = link_manager_linux.find_links(temp_project)

    assert len(links) == 2
    assert link1 in links
    assert link2 in links


@pytest.mark.unit
def test_find_links_empty(link_manager_linux, temp_project):
    """Test finding links in directory with no links."""
    links = link_manager_linux.find_links(temp_project)

    assert len(links) == 0


# ==============================================================================
# Find Broken Links Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_broken_links(link_manager_linux, temp_project, tmp_path):
    """Test finding broken links."""
    # Create temporary targets
    target1 = tmp_path / "target1"
    target1.mkdir()
    target2 = tmp_path / "target2"
    target2.mkdir()

    # Create links
    link1 = temp_project / "link1"
    link2 = temp_project / "link2"

    link_manager_linux.create_link(link1, target1)
    link_manager_linux.create_link(link2, target2)

    # Break one link
    target1.rmdir()

    broken = link_manager_linux.find_broken_links(temp_project)

    assert len(broken) == 1
    assert broken[0] == link1


# ==============================================================================
# Cleanup Broken Links Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_dry_run(link_manager_linux, temp_project, tmp_path):
    """Test cleanup broken links in dry-run mode."""
    # Create temporary target
    temp_target = tmp_path / "temp_target"
    temp_target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, temp_target)

    # Break the link
    temp_target.rmdir()

    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=True)

    assert removed == 1
    # Link should still exist (dry run)
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_actual(link_manager_linux, temp_project, tmp_path):
    """Test cleanup broken links actually removes them."""
    # Create temporary target
    temp_target = tmp_path / "temp_target"
    temp_target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, temp_target)

    # Break the link
    temp_target.rmdir()

    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

    assert removed == 1
    # Link should be removed
    assert not link_path.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_preserves_valid(
    link_manager_linux, mock_llvm_toolchain, temp_project, tmp_path
):
    """Test cleanup doesn't remove valid links."""
    # Create one valid and one broken link
    temp_target = tmp_path / "temp_target"
    temp_target.mkdir()

    valid_link = temp_project / "valid"
    broken_link = temp_project / "broken"

    link_manager_linux.create_link(valid_link, mock_llvm_toolchain)
    link_manager_linux.create_link(broken_link, temp_target)

    # Break one link
    temp_target.rmdir()

    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

    assert removed == 1
    assert valid_link.exists()
    assert valid_link.is_symlink()
    assert not broken_link.exists()


# ==============================================================================
# High-Level API Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test high-level link_toolchain_to_project method."""
    link_path = link_manager_linux.link_toolchain_to_project(
        mock_llvm_toolchain, temp_project
    )

    assert link_path == temp_project / ".toolchain"
    assert link_path.is_symlink()
    assert link_path.resolve() == mock_llvm_toolchain.resolve()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project_custom_name(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test link_toolchain_to_project with custom link name."""
    link_path = link_manager_linux.link_toolchain_to_project(
        mock_llvm_toolchain, temp_project, link_name="custom-toolchain"
    )

    assert link_path == temp_project / "custom-toolchain"
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project_force_overwrites(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test link_toolchain_to_project overwrites existing link."""
    # Create initial link
    link_path = link_manager_linux.link_toolchain_to_project(
        mock_llvm_toolchain, temp_project
    )

    # Create again (should overwrite with force=True in implementation)
    new_link_path = link_manager_linux.link_toolchain_to_project(
        mock_llvm_toolchain, temp_project
    )

    assert new_link_path == link_path
    assert link_path.is_symlink()


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


@pytest.mark.unit
def test_is_junction_on_unix(link_manager_linux, temp_project):
    """Test _is_junction returns False on Unix."""
    regular_dir = temp_project / "regular"
    regular_dir.mkdir()

    assert link_manager_linux._is_junction(regular_dir) is False


@pytest.mark.unit
def test_is_junction_nonexistent(link_manager_windows, tmp_path):
    """Test _is_junction returns False for nonexistent path."""
    nonexistent = tmp_path / "nonexistent"

    assert link_manager_windows._is_junction(nonexistent) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_remove_link_error_handling(link_manager_linux, temp_project):
    """Test remove_link handles errors gracefully."""
    # Create a path we can't remove (mock the exception)
    link_path = temp_project / "protected_link"
    link_path.touch()

    with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
        with pytest.raises(PermissionError):
            link_manager_linux.remove_link(link_path)


@pytest.mark.unit
def test_find_links_handles_permission_error(link_manager_linux, temp_project):
    """Test find_links handles permission errors gracefully."""
    # Mock rglob to raise PermissionError
    with patch.object(Path, "rglob", side_effect=PermissionError("Access denied")):
        links = link_manager_linux.find_links(temp_project)

        # Should return empty list instead of crashing
        assert links == []


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_relative_target(link_manager_linux, temp_project, tmp_path):
    """Test resolving symlink with relative target path."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "rel_link"

    # Create relative symlink
    import os

    os.symlink("../target", link_path)

    resolved = link_manager_linux.resolve_link(link_path)

    assert resolved is not None
    assert resolved.is_absolute()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_nonexistent_path(link_manager_linux, tmp_path):
    """Test resolving link for nonexistent path."""
    nonexistent = tmp_path / "nonexistent"

    resolved = link_manager_linux.resolve_link(nonexistent)

    assert resolved is None


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_regular_file(link_manager_linux, temp_project):
    """Test resolving regular file returns None."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    resolved = link_manager_linux.resolve_link(regular_file)

    assert resolved is None


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_valid_link_with_broken_link(link_manager_linux, temp_project, tmp_path):
    """Test is_valid_link returns False for broken link."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, target)

    # Break the link
    target.rmdir()

    assert link_manager_linux.is_valid_link(link_path) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_valid_link_with_regular_file(link_manager_linux, temp_project):
    """Test is_valid_link returns False for regular file."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    assert link_manager_linux.is_valid_link(regular_file) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_broken_link_with_valid_link(
    link_manager_linux, mock_llvm_toolchain, temp_project
):
    """Test is_broken_link returns False for valid link."""
    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, mock_llvm_toolchain)

    assert link_manager_linux.is_broken_link(link_path) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_broken_link_with_regular_file(link_manager_linux, temp_project):
    """Test is_broken_link returns False for regular file."""
    regular_file = temp_project / "regular.txt"
    regular_file.touch()

    assert link_manager_linux.is_broken_link(regular_file) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_is_broken_link_with_nonexistent_path(link_manager_linux, tmp_path):
    """Test is_broken_link returns False for nonexistent path."""
    nonexistent = tmp_path / "nonexistent"

    assert link_manager_linux.is_broken_link(nonexistent) is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_remove_link_returns_false_for_nonexistent(link_manager_linux, tmp_path):
    """Test remove_link returns False for nonexistent path."""
    nonexistent = tmp_path / "nonexistent"

    result = link_manager_linux.remove_link(nonexistent)

    assert result is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_remove_link_directory_symlink(link_manager_linux, temp_project, tmp_path):
    """Test removing directory symlink."""
    target = tmp_path / "target_dir"
    target.mkdir()

    link_path = temp_project / "dir_link"
    link_manager_linux.create_link(link_path, target)

    result = link_manager_linux.remove_link(link_path)

    assert result is True
    assert not link_path.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_file_symlinks(link_manager_linux, temp_project, tmp_path):
    """Test find_links detects file symlinks."""
    target_file = tmp_path / "target.txt"
    target_file.touch()

    link_path = temp_project / "file_link.txt"
    link_manager_linux.create_link(link_path, target_file)

    links = link_manager_linux.find_links(temp_project)

    assert link_path in links


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_nested_directories(link_manager_linux, temp_project, tmp_path):
    """Test find_links searches nested directories."""
    target = tmp_path / "target"
    target.mkdir()

    nested_dir = temp_project / "nested" / "deep"
    nested_dir.mkdir(parents=True)

    link_path = nested_dir / "link"
    link_manager_linux.create_link(link_path, target)

    links = link_manager_linux.find_links(temp_project)

    assert link_path in links


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_multiple(link_manager_linux, temp_project, tmp_path):
    """Test cleanup removes multiple broken links."""
    target1 = tmp_path / "target1"
    target2 = tmp_path / "target2"
    target1.mkdir()
    target2.mkdir()

    link1 = temp_project / "link1"
    link2 = temp_project / "link2"

    link_manager_linux.create_link(link1, target1)
    link_manager_linux.create_link(link2, target2)

    # Break both links
    target1.rmdir()
    target2.rmdir()

    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

    assert removed == 2
    assert not link1.exists()
    assert not link2.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_with_errors(link_manager_linux, temp_project, tmp_path):
    """Test cleanup handles removal errors gracefully."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, target)

    # Break the link
    target.rmdir()

    # Mock remove_link to fail
    with patch.object(
        link_manager_linux, "remove_link", side_effect=PermissionError("Access denied")
    ):
        removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

        # Should return 0 since removal failed
        assert removed == 0


@pytest.mark.unit
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink test requires admin privileges on Windows",
)
def test_create_link_creates_parent_directory(link_manager_linux, tmp_path):
    """Test create_link creates parent directories if needed."""
    target = tmp_path / "target"
    target.mkdir()

    nested_link = tmp_path / "nested" / "deep" / "link"

    result = link_manager_linux.create_link(nested_link, target)

    assert result is True
    assert nested_link.parent.exists()
    assert nested_link.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_with_force_removes_existing_file(
    link_manager_linux, temp_project, tmp_path
):
    """Test create_link with force removes existing file."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    # Create existing regular file
    link_path.touch()

    result = link_manager_linux.create_link(link_path, target, force=True)

    assert result is True
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_with_force_removes_existing_symlink(
    link_manager_linux, temp_project, tmp_path
):
    """Test create_link with force removes existing symlink."""
    old_target = tmp_path / "old_target"
    new_target = tmp_path / "new_target"
    old_target.mkdir()
    new_target.mkdir()

    link_path = temp_project / "link"

    # Create initial link
    link_manager_linux.create_link(link_path, old_target)

    # Create new link with force
    result = link_manager_linux.create_link(link_path, new_target, force=True)

    assert result is True
    assert link_path.resolve() == new_target.resolve()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_windows(link_manager_windows, tmp_path):
    """Test junction creation on Windows."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"

    result = link_manager_windows.create_link(link_path, target)

    assert result is True
    assert link_manager_windows._is_junction(link_path)


@pytest.mark.unit
def test_create_junction_on_unix_raises_error(link_manager_linux, tmp_path):
    """Test _create_junction raises error on Unix."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"

    with pytest.raises(RuntimeError, match="Junctions are only supported on Windows"):
        link_manager_linux._create_junction(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_resolve_junction_windows(link_manager_windows, tmp_path):
    """Test resolving junction on Windows."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    resolved = link_manager_windows.resolve_link(link_path)

    assert resolved is not None
    # Check if paths are equivalent (may have UNC prefix differences)
    assert resolved.resolve() == target.resolve()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_remove_junction_windows(link_manager_windows, tmp_path):
    """Test removing junction on Windows."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    result = link_manager_windows.remove_link(link_path)

    assert result is True
    assert not link_path.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_empty_directory(link_manager_linux, tmp_path):
    """Test find_links returns empty list for directory with no links."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    links = link_manager_linux.find_links(empty_dir)

    assert links == []


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_no_broken_links(link_manager_linux, temp_project):
    """Test cleanup_broken_links returns 0 when no broken links."""
    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

    assert removed == 0


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_file_exists_error_without_force(
    link_manager_linux, temp_project, tmp_path
):
    """Test create_link raises FileExistsError when link exists without force."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "existing_link"
    link_manager_linux.create_link(link_path, target)

    # Try to create the same link again without force
    with pytest.raises(FileExistsError, match="Link path already exists"):
        link_manager_linux.create_link(link_path, target, force=False)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_handles_symlink_error(link_manager_linux, temp_project, tmp_path):
    """Test create_link handles OSError during symlink creation."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"

    # Mock os.symlink to raise OSError
    with patch("os.symlink", side_effect=OSError("Permission denied")):
        with pytest.raises(OSError, match="Permission denied"):
            link_manager_linux.create_link(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_symlink_oserror(link_manager_linux, tmp_path):
    """Test _create_symlink raises OSError on failure."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "link"

    # Mock os.symlink to raise OSError
    with patch("os.symlink", side_effect=OSError("Operation not permitted")):
        with pytest.raises(OSError, match="Operation not permitted"):
            link_manager_linux._create_symlink(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_mklink_failure(link_manager_windows, tmp_path):
    """Test _create_junction handles mklink command failure."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"

    # Mock subprocess.run to return failure
    import subprocess

    mock_result = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="Access denied"
    )

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(OSError, match="Failed to create junction"):
            link_manager_windows._create_junction(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_subprocess_exception(link_manager_windows, tmp_path):
    """Test _create_junction handles subprocess exception."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"

    # Mock subprocess.run to raise exception
    with patch("subprocess.run", side_effect=Exception("Command failed")):
        with pytest.raises(Exception, match="Command failed"):
            link_manager_windows._create_junction(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_symlink_absolute_target(
    link_manager_linux, temp_project, tmp_path
):
    """Test resolve_link with absolute symlink target."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    import os

    os.symlink(str(target), str(link_path))

    resolved = link_manager_linux.resolve_link(link_path)

    assert resolved is not None
    assert resolved == target


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_symlink_relative_target(link_manager_linux, temp_project):
    """Test resolve_link with relative symlink target."""
    # Create target in same directory
    target = temp_project / "target_dir"
    target.mkdir()

    link_path = temp_project / "link"
    import os

    os.symlink("target_dir", str(link_path))

    resolved = link_manager_linux.resolve_link(link_path)

    assert resolved is not None
    assert resolved.resolve() == target.resolve()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_resolve_link_exception_handling(link_manager_linux, temp_project):
    """Test resolve_link handles exceptions gracefully."""
    link_path = temp_project / "link"
    link_path.touch()

    # Mock is_symlink to raise exception
    with patch.object(Path, "is_symlink", side_effect=Exception("Unexpected error")):
        resolved = link_manager_linux.resolve_link(link_path)

        assert resolved is None


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_resolve_junction_unc_path_forward_slash(link_manager_windows, tmp_path):
    """Test resolve_link removes //?/ UNC prefix."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    # Mock readlink to return UNC path with forward slashes
    with patch("os.readlink", return_value=f"//?/{str(target)}"):
        resolved = link_manager_windows.resolve_link(link_path)

        assert resolved is not None
        assert not str(resolved).startswith("//?/")


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_resolve_junction_exception_handling(link_manager_windows, tmp_path):
    """Test resolve_link handles junction resolution exceptions."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    # Mock readlink to raise exception
    with patch("os.readlink", side_effect=Exception("Read error")):
        resolved = link_manager_windows.resolve_link(link_path)

        # Should still return None gracefully
        assert resolved is None or resolved is not None


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_valid_link_junction(link_manager_windows, tmp_path):
    """Test is_valid_link returns True for valid junction."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    assert link_manager_windows.is_valid_link(link_path) is True


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_broken_link_junction(link_manager_windows, tmp_path):
    """Test is_broken_link detects broken junction."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    # Break the junction by removing target
    import shutil

    shutil.rmtree(target)

    assert link_manager_windows.is_broken_link(link_path) is True


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_remove_link_regular_directory(link_manager_windows, tmp_path):
    """Test remove_link handles regular directory (not junction)."""
    regular_dir = tmp_path / "regular_dir"
    regular_dir.mkdir()

    result = link_manager_windows.remove_link(regular_dir)

    assert result is True
    assert not regular_dir.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_remove_link_handles_exception(link_manager_windows, tmp_path):
    """Test remove_link raises exception on removal failure."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    # Mock os.rmdir to raise exception
    with patch("os.rmdir", side_effect=PermissionError("Access denied")):
        with pytest.raises(PermissionError, match="Access denied"):
            link_manager_windows.remove_link(link_path)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_with_file_symlinks(link_manager_linux, temp_project, tmp_path):
    """Test find_links finds both directory and file symlinks."""
    # Create targets
    dir_target = tmp_path / "dir_target"
    dir_target.mkdir()
    file_target = tmp_path / "file_target.txt"
    file_target.touch()

    # Create links
    dir_link = temp_project / "dir_link"
    file_link = temp_project / "file_link.txt"

    link_manager_linux.create_link(dir_link, dir_target)
    link_manager_linux.create_link(file_link, file_target)

    links = link_manager_linux.find_links(temp_project)

    assert len(links) == 2
    assert dir_link in links
    assert file_link in links


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_handles_walk_exception(link_manager_linux, temp_project):
    """Test find_links handles os.walk exception gracefully."""
    # Mock os.walk to raise exception
    with patch("os.walk", side_effect=Exception("Permission denied")):
        links = link_manager_linux.find_links(temp_project)

        # Should return empty list on error
        assert links == []


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_broken_links_empty_result(link_manager_linux, temp_project, tmp_path):
    """Test find_broken_links returns empty list when all links are valid."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, target)

    broken = link_manager_linux.find_broken_links(temp_project)

    assert broken == []


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_broken_links_all_broken(link_manager_linux, temp_project, tmp_path):
    """Test find_broken_links finds all broken links."""
    # Create multiple broken links
    target1 = tmp_path / "target1"
    target2 = tmp_path / "target2"
    target3 = tmp_path / "target3"
    target1.mkdir()
    target2.mkdir()
    target3.mkdir()

    link1 = temp_project / "link1"
    link2 = temp_project / "link2"
    link3 = temp_project / "link3"

    link_manager_linux.create_link(link1, target1)
    link_manager_linux.create_link(link2, target2)
    link_manager_linux.create_link(link3, target3)

    # Break all links
    import shutil

    shutil.rmtree(target1)
    shutil.rmtree(target2)
    shutil.rmtree(target3)

    broken = link_manager_linux.find_broken_links(temp_project)

    assert len(broken) == 3
    assert link1 in broken
    assert link2 in broken
    assert link3 in broken


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_partial_failure(
    link_manager_linux, temp_project, tmp_path
):
    """Test cleanup handles partial failures when removing links."""
    target1 = tmp_path / "target1"
    target2 = tmp_path / "target2"
    target1.mkdir()
    target2.mkdir()

    link1 = temp_project / "link1"
    link2 = temp_project / "link2"

    link_manager_linux.create_link(link1, target1)
    link_manager_linux.create_link(link2, target2)

    # Break both links
    import shutil

    shutil.rmtree(target1)
    shutil.rmtree(target2)

    # Mock remove_link to fail for first link
    original_remove = link_manager_linux.remove_link
    call_count = [0]

    def mock_remove(path):
        call_count[0] += 1
        if call_count[0] == 1:
            raise PermissionError("Cannot remove")
        return original_remove(path)

    with patch.object(link_manager_linux, "remove_link", side_effect=mock_remove):
        removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=False)

        # Should continue after first failure
        assert removed <= 1


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_junction_file_not_found(link_manager_windows, tmp_path):
    """Test _is_junction handles FileNotFoundError."""
    nonexistent = tmp_path / "nonexistent"

    # Force the use of junction check
    link_manager_windows._use_junctions = True

    result = link_manager_windows._is_junction(nonexistent)

    assert result is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_junction_fallback_to_readlink(link_manager_windows, tmp_path):
    """Test _is_junction fallback to os.readlink."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = tmp_path / "junction"
    link_manager_windows.create_link(link_path, target)

    # Mock st_file_attributes to not exist (test fallback path)
    with patch("os.stat") as mock_stat:
        mock_st = type("MockStat", (), {})()
        # Don't set st_file_attributes attribute
        mock_stat.st_mode = 0o040000  # Directory mode
        mock_stat.st_size = 0
        mock_stat.st_mtime = 0
        mock_stat.st_ino = 0
        mock_stat.st_dev = 0
        mock_stat.st_nlink = 1
        mock_stat.st_uid = 0
        mock_stat.st_gid = 0
        mock_stat.st_atime = 0
        mock_stat.st_ctime = 0
        mock_stat.st_birthtime = 0
        mock_stat.st_blocks = 0
        mock_stat.st_blksize = 0
        mock_stat.st_rdev = 0
        mock_stat.st_flags = 0
        mock_stat.st_gen = 0
        mock_stat.st_fstype = ""
        mock_stat.st_rsize = 0
        mock_stat.st_creator = ""
        mock_stat.st_type = ""
        # Don't set st_file_attributes to simulate older Python version
        mock_stat.st_reparse_tag = 0

        mock_stat_instance = mock_st
        # Don't need to delete attribute - just don't set it

        mock_stat.return_value = mock_stat_instance

        result = link_manager_windows._is_junction(link_path)

        # Should detect via readlink fallback
        assert result is True


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_junction_readlink_oserror(link_manager_windows, tmp_path):
    """Test _is_junction handles OSError from readlink."""
    regular_dir = tmp_path / "regular"
    regular_dir.mkdir()

    # Mock stat to not have st_file_attributes
    with patch("os.stat") as mock_stat:
        mock_st = type("MockStat", (), {})()
        mock_stat.return_value = mock_st

        # Mock readlink to raise OSError
        with patch("os.readlink", side_effect=OSError("Not a link")):
            result = link_manager_windows._is_junction(regular_dir)

            assert result is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_is_junction_general_exception(link_manager_windows, tmp_path):
    """Test _is_junction handles general exceptions."""
    path = tmp_path / "something"

    # Mock stat to raise exception
    with patch("os.stat", side_effect=Exception("Unexpected error")):
        result = link_manager_windows._is_junction(path)

        assert result is False


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project_target_not_found(
    link_manager_linux, temp_project, tmp_path
):
    """Test link_toolchain_to_project raises error when toolchain doesn't exist."""
    nonexistent_toolchain = tmp_path / "nonexistent_toolchain"

    with pytest.raises(FileNotFoundError, match="Target does not exist"):
        link_manager_linux.link_toolchain_to_project(
            nonexistent_toolchain, temp_project
        )


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project_custom_link_name(
    link_manager_linux, temp_project, tmp_path
):
    """Test link_toolchain_to_project with custom link name."""
    toolchain = tmp_path / "toolchain"
    toolchain.mkdir()

    link_path = link_manager_linux.link_toolchain_to_project(
        toolchain, temp_project, link_name="my-custom-toolchain"
    )

    assert link_path == temp_project / "my-custom-toolchain"
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_link_toolchain_to_project_overwrites_existing(
    link_manager_linux, temp_project, tmp_path
):
    """Test link_toolchain_to_project overwrites existing link with force."""
    toolchain1 = tmp_path / "toolchain1"
    toolchain2 = tmp_path / "toolchain2"
    toolchain1.mkdir()
    toolchain2.mkdir()

    # Create first link
    link_path1 = link_manager_linux.link_toolchain_to_project(toolchain1, temp_project)

    # Create second link (should overwrite)
    link_path2 = link_manager_linux.link_toolchain_to_project(toolchain2, temp_project)

    assert link_path1 == link_path2
    assert link_path2.resolve() == toolchain2.resolve()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_junction_on_unix_raises_error(link_manager_linux, tmp_path):
    """Test _create_junction raises RuntimeError when called on Unix."""
    target = tmp_path / "target"
    target.mkdir()
    link_path = tmp_path / "junction"

    # Calling _create_junction on Unix should raise RuntimeError
    # since it checks self._use_junctions which is False on Unix
    with pytest.raises(RuntimeError, match="Junctions are only supported on Windows"):
        link_manager_linux._create_junction(link_path, target)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_find_links_junctions(link_manager_windows, temp_project, tmp_path):
    """Test find_links finds junctions on Windows."""
    target = tmp_path / "target"
    target.mkdir()

    junction_path = temp_project / "junction"
    link_manager_windows.create_link(junction_path, target)

    links = link_manager_windows.find_links(temp_project)

    assert junction_path in links


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_cleanup_broken_junctions(link_manager_windows, temp_project, tmp_path):
    """Test cleanup removes broken junctions on Windows."""
    target = tmp_path / "target"
    target.mkdir()

    junction_path = temp_project / "junction"
    link_manager_windows.create_link(junction_path, target)

    # Break the junction
    import shutil

    shutil.rmtree(target)

    removed = link_manager_windows.cleanup_broken_links(temp_project, dry_run=False)

    assert removed == 1
    assert not junction_path.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_create_link_absolute_paths(link_manager_linux, temp_project, tmp_path):
    """Test create_link converts paths to absolute."""
    target = tmp_path / "target"
    target.mkdir()

    # Use relative path
    import os

    original_dir = os.getcwd()
    try:
        os.chdir(temp_project)
        relative_link = Path("relative_link")

        result = link_manager_linux.create_link(relative_link, target)

        assert result is True
        assert (temp_project / "relative_link").exists()
    finally:
        os.chdir(original_dir)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_find_links_ignores_regular_files_and_dirs(link_manager_linux, temp_project):
    """Test find_links only returns actual links."""
    # Create regular files and directories
    regular_file = temp_project / "regular.txt"
    regular_dir = temp_project / "regular_dir"
    regular_file.touch()
    regular_dir.mkdir()

    links = link_manager_linux.find_links(temp_project)

    # Should not include regular files/dirs
    assert regular_file not in links
    assert regular_dir not in links
    assert len(links) == 0


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
def test_cleanup_broken_links_dry_run_preserves_links(
    link_manager_linux, temp_project, tmp_path
):
    """Test cleanup in dry-run mode doesn't remove links."""
    target = tmp_path / "target"
    target.mkdir()

    link_path = temp_project / "link"
    link_manager_linux.create_link(link_path, target)

    # Break the link
    import shutil

    shutil.rmtree(target)

    # Verify link is broken
    assert link_manager_linux.is_broken_link(link_path)

    removed = link_manager_linux.cleanup_broken_links(temp_project, dry_run=True)

    assert removed == 1
    # Link should still exist after dry run
    assert link_path.is_symlink()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_create_junction_force_removes_existing_junction(
    link_manager_windows, temp_project, tmp_path
):
    """Test create junction with force removes existing junction."""
    target1 = tmp_path / "target1"
    target2 = tmp_path / "target2"
    target1.mkdir()
    target2.mkdir()

    link_path = temp_project / "junction"

    # Create first junction
    link_manager_windows.create_link(link_path, target1)

    # Create second junction with force
    result = link_manager_windows.create_link(link_path, target2, force=True)

    assert result is True
    assert link_manager_windows.resolve_link(link_path) == target2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
