"""
Integration tests for filesystem utilities.

Tests real-world scenarios and interactions between multiple filesystem operations.
These tests use actual files and directories to verify end-to-end functionality.
"""

import json
import zipfile
import tarfile
import pytest

from toolchainkit.core.filesystem import (
    create_link,
    extract_archive,
    atomic_write,
    safe_rmtree,
    recursive_copy,
    compute_file_hash,
    directory_size,
    temporary_directory,
    ensure_directory,
    IS_WINDOWS,
)


# ============================================================================
# Integration Test Scenarios
# ============================================================================


class TestToolchainWorkflow:
    """Test a complete toolchain download and setup workflow."""

    def test_download_extract_link_workflow(self, mock_llvm_toolchain):
        """
        Simulate complete workflow using mock toolchain fixture.

        This test demonstrates the value of fixtures by replacing ~40 lines
        of toolchain setup code with a single fixture parameter.

        Workflow:
        1. Use pre-built toolchain structure (via fixture)
        2. Create link in project-local directory
        3. Verify access through link
        """
        with temporary_directory() as workspace:
            # Step 1: Toolchain already created by mock_llvm_toolchain fixture
            # (Previously required ~30 lines of setup code)

            # Step 2: Create link in project-local directory
            project_dir = workspace / "my_project"
            project_toolchains = project_dir / ".toolchainkit" / "toolchains"
            project_toolchains.mkdir(parents=True)

            link_path = project_toolchains / "llvm"
            create_link(mock_llvm_toolchain, link_path, link_type="auto")

            # Step 3: Verify access through link
            # Use platform-appropriate executable names
            import platform as plat

            exe_ext = ".exe" if plat.system() == "Windows" else ""

            assert link_path.exists()
            assert (link_path / "bin" / f"clang{exe_ext}").exists()
            # Verify link points to fixture's toolchain
            assert (link_path / "lib" / "libc++.a").exists()
            assert (link_path / "include" / "c++" / "v1").is_dir()


class TestMultipleArchiveFormats:
    """Test extraction of different archive formats."""

    def test_extract_various_formats(self):
        """Test extracting .zip, .tar.gz, .tar.xz, .tar.bz2 archives."""
        with temporary_directory() as workspace:
            # Prepare sample content
            sample_content = {
                "file1.txt": "Content 1",
                "subdir/file2.txt": "Content 2",
                "subdir/nested/file3.txt": "Content 3",
            }

            # Test each format
            formats = [
                ("sample.zip", "zip"),
                ("sample.tar.gz", "tar.gz"),
                ("sample.tar.xz", "tar.xz"),
                ("sample.tar.bz2", "tar.bz2"),
            ]

            for archive_name, format_type in formats:
                archive_path = workspace / archive_name

                # Create archive
                if format_type == "zip":
                    with zipfile.ZipFile(archive_path, "w") as zf:
                        for name, content in sample_content.items():
                            zf.writestr(name, content)

                elif format_type.startswith("tar"):
                    # Determine compression
                    if format_type == "tar.gz":
                        mode = "w:gz"
                    elif format_type == "tar.xz":
                        mode = "w:xz"
                    elif format_type == "tar.bz2":
                        mode = "w:bz2"
                    else:
                        mode = "w"

                    with tarfile.open(archive_path, mode) as tar:
                        for name, content in sample_content.items():
                            # Create temp file
                            temp_file = workspace / f'temp_{name.replace("/", "_")}'
                            temp_file.parent.mkdir(parents=True, exist_ok=True)
                            temp_file.write_text(content)
                            tar.add(temp_file, arcname=name)
                            temp_file.unlink()

                # Extract archive
                extract_dir = workspace / f'extracted_{format_type.replace(".", "_")}'
                extract_archive(archive_path, extract_dir)

                # Verify extraction
                for name, expected_content in sample_content.items():
                    extracted_file = extract_dir / name
                    assert extracted_file.exists(), f"{archive_name}: {name} not found"
                    assert extracted_file.read_text() == expected_content


class TestLinkChainResolution:
    """Test creating and following chains of links."""

    @pytest.mark.skipif(IS_WINDOWS, reason="Complex symlink test, requires Unix")
    def test_symlink_chain(self):
        """Test creating a chain of symlinks and resolving them."""
        with temporary_directory() as workspace:
            # Create actual directory
            actual = workspace / "actual"
            actual.mkdir()
            (actual / "file.txt").write_text("content")

            # Create chain: link1 -> link2 -> actual
            link1 = workspace / "link1"
            link2 = workspace / "link2"

            create_link(actual, link2, link_type="symlink")
            create_link(link2, link1, link_type="symlink")

            # Access through chain
            assert (link1 / "file.txt").exists()
            assert (link1 / "file.txt").read_text() == "content"


class TestSafeOperationsWithFailures:
    """Test safe operations handle failures correctly."""

    def test_atomic_write_failure_cleanup(self):
        """Test that temp files are cleaned up on write failure."""
        with temporary_directory() as workspace:
            file_path = workspace / "test.txt"

            # Simulate write failure by using invalid content type
            # (This should be caught during development, but we test recovery)
            try:
                # Try to write with wrong encoding
                atomic_write(file_path, b"binary", encoding="utf-8")
            except Exception:
                pass  # Expected to fail

            # Verify no temp files left behind
            temp_files = list(workspace.glob(".test.txt.*.tmp"))
            assert len(temp_files) == 0

    def test_safe_rmtree_concurrent_deletion(self):
        """Test safe deletion when directory is already being deleted."""
        with temporary_directory() as workspace:
            target = workspace / "to_delete"
            target.mkdir()
            (target / "file.txt").write_text("content")

            # Delete directory
            safe_rmtree(target)

            # Try to delete again (should not raise)
            safe_rmtree(target)


class TestCopyAndVerify:
    """Test copying with verification."""

    def test_copy_and_verify_hash(self):
        """Test copying a directory and verifying integrity."""
        with temporary_directory() as workspace:
            # Create source directory with various files
            source = workspace / "source"
            source.mkdir()

            files_data = {
                "file1.txt": "Content 1",
                "file2.bin": b"\x00\x01\x02\x03",
                "subdir/file3.txt": "Content 3",
            }

            file_hashes = {}

            # Create files and compute hashes
            for path, content in files_data.items():
                file_path = source / path
                file_path.parent.mkdir(parents=True, exist_ok=True)

                if isinstance(content, bytes):
                    file_path.write_bytes(content)
                else:
                    file_path.write_text(content)

                file_hashes[path] = compute_file_hash(file_path)

            # Copy directory
            dest = workspace / "dest"
            recursive_copy(source, dest)

            # Verify hashes match
            for path, expected_hash in file_hashes.items():
                dest_file = dest / path
                assert dest_file.exists()
                actual_hash = compute_file_hash(dest_file)
                assert actual_hash == expected_hash


class TestConfigurationPersistence:
    """Test saving and loading configuration files."""

    def test_config_update_cycle(self):
        """Test updating configuration multiple times."""
        with temporary_directory() as workspace:
            config_file = workspace / "config.json"

            # Initial configuration
            config_v1 = {
                "version": 1,
                "toolchain": {
                    "name": "llvm",
                    "version": "14.0.0",
                },
                "build_type": "Debug",
            }

            atomic_write(config_file, json.dumps(config_v1, indent=2))

            # Update 1: Change toolchain version
            config = json.loads(config_file.read_text())
            config["version"] = 2
            config["toolchain"]["version"] = "15.0.0"
            atomic_write(config_file, json.dumps(config, indent=2))

            # Update 2: Change build type
            config = json.loads(config_file.read_text())
            config["version"] = 3
            config["build_type"] = "Release"
            atomic_write(config_file, json.dumps(config, indent=2))

            # Verify final state
            final_config = json.loads(config_file.read_text())
            assert final_config["version"] == 3
            assert final_config["toolchain"]["version"] == "15.0.0"
            assert final_config["build_type"] == "Release"


class TestCacheManagement:
    """Test cache directory management scenarios."""

    def test_cache_size_calculation(self):
        """Test calculating cache size with multiple toolchains."""
        with temporary_directory() as workspace:
            cache_dir = workspace / "cache" / "toolchains"
            cache_dir.mkdir(parents=True)

            # Create multiple toolchain directories
            toolchains = {
                "llvm-14": {
                    "bin/clang": "x" * 1000,
                    "lib/libclang.so": "y" * 2000,
                },
                "llvm-15": {
                    "bin/clang": "z" * 1500,
                    "lib/libclang.so": "w" * 2500,
                },
            }

            expected_total_size = 0

            for toolchain_name, files in toolchains.items():
                toolchain_dir = cache_dir / toolchain_name
                toolchain_dir.mkdir()

                for file_path, content in files.items():
                    full_path = toolchain_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    expected_total_size += len(content)

            # Calculate total cache size
            total_size = directory_size(cache_dir)
            assert total_size == expected_total_size

    def test_selective_cache_cleanup(self):
        """Test cleaning up specific cache entries."""
        with temporary_directory() as workspace:
            cache_dir = workspace / "cache" / "toolchains"
            cache_dir.mkdir(parents=True)

            # Create old and new toolchains
            old_toolchain = cache_dir / "llvm-13"
            old_toolchain.mkdir()
            (old_toolchain / "bin").mkdir()
            (old_toolchain / "bin" / "clang").write_text("old version")

            new_toolchain = cache_dir / "llvm-15"
            new_toolchain.mkdir()
            (new_toolchain / "bin").mkdir()
            (new_toolchain / "bin" / "clang").write_text("new version")

            # Remove old toolchain
            safe_rmtree(old_toolchain, require_prefix=cache_dir)

            # Verify selective deletion
            assert not old_toolchain.exists()
            assert new_toolchain.exists()
            assert (new_toolchain / "bin" / "clang").read_text() == "new version"


class TestCrossProjectSharing:
    """Test sharing toolchains between multiple projects."""

    def test_multiple_projects_same_toolchain(self):
        """Test multiple projects linking to the same toolchain."""
        with temporary_directory() as workspace:
            # Create global toolchain
            global_cache = workspace / "global" / "toolchains"
            toolchain_dir = global_cache / "llvm-15"
            toolchain_dir.mkdir(parents=True)
            (toolchain_dir / "bin").mkdir()
            (toolchain_dir / "bin" / "clang").write_text("clang executable")

            # Create multiple projects
            projects = ["project_a", "project_b", "project_c"]

            for project_name in projects:
                project_dir = workspace / project_name
                project_toolchains = project_dir / ".toolchainkit" / "toolchains"
                project_toolchains.mkdir(parents=True)

                # Create link to global toolchain
                link = project_toolchains / "llvm"
                create_link(toolchain_dir, link, link_type="auto")

                # Verify access
                assert (link / "bin" / "clang").exists()
                assert (link / "bin" / "clang").read_text() == "clang executable"

            # All projects can access the same toolchain
            for project_name in projects:
                link = (
                    workspace / project_name / ".toolchainkit" / "toolchains" / "llvm"
                )
                assert link.exists()


class TestLongPathHandling:
    """Test handling of long paths (especially on Windows)."""

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific long path test")
    def test_deeply_nested_extraction(self):
        """Test extracting archives with deeply nested paths on Windows."""
        with temporary_directory() as workspace:
            # Create an archive with nested structure
            archive_path = workspace / "nested.zip"

            with zipfile.ZipFile(archive_path, "w") as zf:
                # Create increasingly nested paths
                for i in range(10):
                    path = "/".join([f"dir{j}" for j in range(i + 1)])
                    path += "/file.txt"
                    zf.writestr(path, f"Content at depth {i}")

            # Extract to a location that might push paths over 260 chars
            extract_dir = workspace / "extracted" / "with" / "long" / "base" / "path"
            extract_archive(archive_path, extract_dir)

            # Verify deepest file exists
            deepest = (
                extract_dir
                / "dir0"
                / "dir1"
                / "dir2"
                / "dir3"
                / "dir4"
                / "dir5"
                / "dir6"
                / "dir7"
                / "dir8"
                / "dir9"
                / "file.txt"
            )
            assert deepest.exists()


class TestErrorRecovery:
    """Test recovery from various error conditions."""

    def test_extraction_with_insufficient_space(self):
        """Test behavior when extraction might fail due to space issues."""
        # Note: This is a conceptual test; actual space exhaustion is hard to simulate
        with temporary_directory() as workspace:
            archive_path = workspace / "test.zip"

            with zipfile.ZipFile(archive_path, "w") as zf:
                zf.writestr("file.txt", "content")

            dest = workspace / "extracted"

            # Normal extraction should work
            extract_archive(archive_path, dest)
            assert (dest / "file.txt").exists()

    def test_hash_verification_failure_simulation(self):
        """Test detecting hash mismatches (simulated)."""
        with temporary_directory() as workspace:
            # Create a file
            file1 = workspace / "original.bin"
            file1.write_bytes(b"original content")

            hash1 = compute_file_hash(file1)

            # Modify file
            file1.write_bytes(b"modified content")

            hash2 = compute_file_hash(file1)

            # Hashes should differ
            assert hash1 != hash2


class TestRealWorldScenarios:
    """Test realistic end-to-end scenarios."""

    def test_complete_project_setup(self):
        """Test complete project setup workflow."""
        with temporary_directory() as workspace:
            # 1. Create global cache structure
            global_cache = workspace / ".toolchainkit"
            toolchains_dir = global_cache / "toolchains"
            ensure_directory(toolchains_dir)

            # 2. "Download" and extract toolchain
            archive_path = workspace / "downloads" / "llvm-15.tar.gz"
            archive_path.parent.mkdir(parents=True)

            with tarfile.open(archive_path, "w:gz") as tar:
                temp_file = workspace / "temp_clang"
                temp_file.write_text("#!/bin/sh\nclang")
                tar.add(temp_file, arcname="bin/clang")
                temp_file.unlink()

            toolchain_dir = toolchains_dir / "llvm-15.0.0"
            extract_archive(archive_path, toolchain_dir)

            # 3. Create project structure
            project_dir = workspace / "my_project"
            project_local = project_dir / ".toolchainkit"
            project_toolchains = project_local / "toolchains"
            ensure_directory(project_toolchains)

            # 4. Link toolchain
            link = project_toolchains / "llvm"
            create_link(toolchain_dir, link)

            # 5. Create configuration
            config = {
                "toolchain": "llvm",
                "version": "15.0.0",
                "build_dir": "build",
            }
            config_file = project_local / "config.json"
            atomic_write(config_file, json.dumps(config, indent=2))

            # 6. Verify complete setup
            assert (link / "bin" / "clang").exists()
            assert config_file.exists()

            loaded_config = json.loads(config_file.read_text())
            assert loaded_config["toolchain"] == "llvm"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
