"""
Unit tests for filesystem utilities.

Tests cross-platform file operations including:
- Path utilities and normalization
- Symlink/junction creation
- Archive extraction
- Safe file operations
- File hashing
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import tarfile
import pytest
from pathlib import Path

# Import module under test
from toolchainkit.core.filesystem import (
    # Exceptions
    FilesystemError,
    LinkCreationError,
    ArchiveExtractionError,
    UnsupportedArchiveFormat,
    InsecureArchiveError,
    # Path utilities
    normalize_path,
    make_long_path_safe,
    is_relative_to,
    resolve_link,
    find_executable,
    # Link creation
    create_link,
    # Archive extraction
    extract_archive,
    # Safe file operations
    atomic_write,
    safe_rmtree,
    recursive_copy,
    ensure_directory,
    is_empty_directory,
    directory_size,
    # Hashing
    compute_file_hash,
    # Temporary files
    temporary_directory,
    # Platform detection
    IS_WINDOWS,
    IS_UNIX,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory(prefix="test_filesystem_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Hello, World!")
    return file_path


@pytest.fixture
def sample_directory(temp_dir):
    """Create a sample directory structure for testing."""
    base = temp_dir / "sample_dir"
    base.mkdir()

    # Create some files
    (base / "file1.txt").write_text("Content 1")
    (base / "file2.txt").write_text("Content 2")

    # Create a subdirectory
    subdir = base / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("Content 3")

    return base


@pytest.fixture
def sample_zip_archive(temp_dir):
    """Create a sample ZIP archive for testing."""
    archive_path = temp_dir / "sample.zip"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("file1.txt", "Content 1")
        zf.writestr("subdir/file2.txt", "Content 2")

    return archive_path


@pytest.fixture
def sample_tar_gz_archive(temp_dir):
    """Create a sample tar.gz archive for testing."""
    archive_path = temp_dir / "sample.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        # Create temp files to add to archive
        temp_file1 = temp_dir / "temp1.txt"
        temp_file1.write_text("Content 1")
        tar.add(temp_file1, arcname="file1.txt")

        temp_file2 = temp_dir / "temp2.txt"
        temp_file2.write_text("Content 2")
        tar.add(temp_file2, arcname="subdir/file2.txt")

        # Clean up temp files
        temp_file1.unlink()
        temp_file2.unlink()

    return archive_path


@pytest.fixture
def malicious_zip_archive(temp_dir):
    """Create a ZIP archive with directory traversal attempt."""
    archive_path = temp_dir / "malicious.zip"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../../../etc/passwd", "malicious content")

    return archive_path


# ============================================================================
# Path Utilities Tests
# ============================================================================


class TestPathUtilities:
    """Tests for path utility functions."""

    def test_normalize_path_absolute(self, temp_dir):
        """Test normalizing an absolute path."""
        result = normalize_path(temp_dir)
        assert result.is_absolute()
        assert result == temp_dir.resolve()

    def test_normalize_path_relative(self, temp_dir):
        """Test normalizing a relative path."""
        # Change to temp dir and test relative path
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            result = normalize_path(".")
            assert result.is_absolute()
            assert result == temp_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_normalize_path_with_dotdot(self, temp_dir):
        """Test normalizing a path with .. components."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        path = subdir / ".." / "file.txt"
        result = normalize_path(path)

        assert ".." not in str(result)
        assert result.resolve() == (temp_dir / "file.txt").resolve()

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_make_long_path_safe_short_path(self, temp_dir):
        """Test that short paths are not modified on Windows."""
        result = make_long_path_safe(temp_dir)
        assert not result.startswith("\\\\?\\")

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_make_long_path_safe_long_path(self):
        """Test that long paths get \\\\?\\ prefix on Windows."""
        # Create a path longer than 260 characters
        long_path = "C:\\" + "a" * 260
        result = make_long_path_safe(long_path)
        assert result.startswith("\\\\?\\")
        assert "C:\\" in result

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-specific test")
    def test_make_long_path_safe_unix(self, temp_dir):
        """Test that Unix paths are never modified."""
        # Even very long paths shouldn't be modified on Unix
        long_path = temp_dir / ("a" * 500)
        result = make_long_path_safe(long_path)
        assert not result.startswith("\\\\?\\")

    def test_is_relative_to_true(self, temp_dir):
        """Test is_relative_to with path under parent."""
        child = temp_dir / "subdir" / "file.txt"
        assert is_relative_to(child, temp_dir)

    def test_is_relative_to_false(self, temp_dir):
        """Test is_relative_to with path not under parent."""
        other_path = Path("/completely/different/path")
        assert not is_relative_to(other_path, temp_dir)

    def test_is_relative_to_same_path(self, temp_dir):
        """Test is_relative_to with identical paths."""
        assert is_relative_to(temp_dir, temp_dir)

    def test_find_executable_python(self):
        """Test finding Python executable in PATH."""
        # Python should be in PATH (we're running it!)
        _python_name = "python" if not IS_WINDOWS else "python.exe"

        # Try variations
        for name in ["python", "python3", sys.executable]:
            result = find_executable(Path(name).stem)
            if result:
                assert result.exists()
                break
        else:
            pytest.skip("Could not find any Python executable")

    def test_find_executable_nonexistent(self):
        """Test finding nonexistent executable."""
        result = find_executable("nonexistent_command_xyz123")
        assert result is None

    def test_find_executable_custom_paths(self, temp_dir):
        """Test finding executable in custom search paths."""
        # Create a fake executable
        exe_name = "test_exe.exe" if IS_WINDOWS else "test_exe"
        exe_path = temp_dir / exe_name
        exe_path.write_text("#!/bin/sh\necho test")
        exe_path.chmod(0o755)

        result = find_executable("test_exe", search_paths=[temp_dir])
        assert result == exe_path


# ============================================================================
# Link Creation Tests
# ============================================================================


class TestLinkCreation:
    """Tests for symbolic link and junction creation."""

    def test_create_symlink_unix(self, temp_dir, sample_directory):
        """Test creating a symlink on Unix-like systems."""
        if IS_WINDOWS:
            pytest.skip("Unix-specific test")

        link_path = temp_dir / "link_to_dir"
        create_link(sample_directory, link_path, link_type="symlink")

        assert link_path.is_symlink()
        assert link_path.resolve() == sample_directory.resolve()

        # Verify we can read through the link
        assert (link_path / "file1.txt").read_text() == "Content 1"

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_create_junction_windows(self, temp_dir, sample_directory):
        """Test creating a junction on Windows."""
        link_path = temp_dir / "junction_to_dir"
        create_link(sample_directory, link_path, link_type="junction")

        # Junction should be treated as a link
        assert link_path.exists()

        # Verify we can read through the junction
        assert (link_path / "file1.txt").read_text() == "Content 1"

    def test_create_link_auto_type(self, temp_dir, sample_directory):
        """Test creating a link with auto type detection."""
        link_path = temp_dir / "auto_link"
        create_link(sample_directory, link_path, link_type="auto")

        # Should create appropriate link type for platform
        assert link_path.exists()
        assert (link_path / "file1.txt").read_text() == "Content 1"

    def test_create_link_target_exists_file(self, temp_dir, sample_directory):
        """Test that creating a link removes existing file at target."""
        # Create a file at target location
        target = temp_dir / "target"
        target.write_text("existing file")

        # Creating a link should remove the file first
        create_link(sample_directory, target)

        # Now target should be a link (or reference on Windows fallback)
        assert target.exists() or (target.with_suffix(".link_reference")).exists()

    def test_create_link_target_exists_directory(self, temp_dir, sample_directory):
        """Test that creating a link fails if target exists as directory."""
        # Create a directory at target location
        target = temp_dir / "target"
        target.mkdir()

        # Should raise an error
        with pytest.raises(LinkCreationError, match="exists as a directory"):
            create_link(sample_directory, target)

    def test_create_link_creates_parent_directories(self, temp_dir, sample_directory):
        """Test that parent directories are created automatically."""
        link_path = temp_dir / "deep" / "nested" / "link"
        create_link(sample_directory, link_path)

        assert link_path.exists()
        assert link_path.parent.exists()

    def test_create_link_source_not_exists(self, temp_dir):
        """Test creating a link to nonexistent source."""
        source = temp_dir / "nonexistent"
        target = temp_dir / "link"

        # On Unix, symlinks can point to nonexistent targets
        # On Windows with junctions, this requires existing directory
        # With allow_fallback=True (default), should create reference
        if IS_UNIX:
            create_link(source, target, link_type="symlink")
            assert target.is_symlink()
        else:
            # On Windows, junctions require existing directories
            # With fallback enabled, should create reference
            create_link(source, target, link_type="junction")
            # Should create reference file instead
            reference_file = target.with_suffix(".link_reference")
            assert reference_file.exists()

            # Without fallback, should raise error
            target2 = temp_dir / "link2"
            with pytest.raises(LinkCreationError):
                create_link(source, target2, link_type="junction", allow_fallback=False)

    def test_create_reference_fallback(self, temp_dir, sample_directory):
        """Test fallback to reference tracking."""
        link_path = temp_dir / "reference_link"
        create_link(sample_directory, link_path, link_type="reference")

        # Should create a .link_reference file
        reference_file = link_path.with_suffix(".link_reference")
        assert reference_file.exists()

        # Verify reference data
        with open(reference_file, "r") as f:
            data = json.load(f)

        assert "source" in data
        assert "target" in data
        assert data["type"] == "reference"

    def test_resolve_link(self, temp_dir, sample_directory):
        """Test resolving a symbolic link."""
        if IS_WINDOWS:
            pytest.skip("Symlink resolution test requires Unix or Windows admin")

        link_path = temp_dir / "link"
        create_link(sample_directory, link_path, link_type="symlink")

        resolved = resolve_link(link_path)
        assert resolved == sample_directory.resolve()

    def test_resolve_link_not_a_link(self, temp_dir, sample_file):
        """Test resolving a non-link raises error."""
        with pytest.raises(ValueError, match="not a symbolic link"):
            resolve_link(sample_file)


# ============================================================================
# Archive Extraction Tests
# ============================================================================


class TestArchiveExtraction:
    """Tests for archive extraction."""

    def test_extract_zip(self, temp_dir, sample_zip_archive):
        """Test extracting a ZIP archive."""
        dest = temp_dir / "extracted"
        extract_archive(sample_zip_archive, dest)

        assert (dest / "file1.txt").exists()
        assert (dest / "file1.txt").read_text() == "Content 1"
        assert (dest / "subdir" / "file2.txt").exists()
        assert (dest / "subdir" / "file2.txt").read_text() == "Content 2"

    def test_extract_tar_gz(self, temp_dir, sample_tar_gz_archive):
        """Test extracting a tar.gz archive."""
        dest = temp_dir / "extracted"
        extract_archive(sample_tar_gz_archive, dest)

        assert (dest / "file1.txt").exists()
        assert (dest / "file1.txt").read_text() == "Content 1"
        assert (dest / "subdir" / "file2.txt").exists()
        assert (dest / "subdir" / "file2.txt").read_text() == "Content 2"

    def test_extract_archive_creates_destination(self, temp_dir, sample_zip_archive):
        """Test that destination directory is created if needed."""
        dest = temp_dir / "new_dir" / "extracted"
        extract_archive(sample_zip_archive, dest)

        assert dest.exists()
        assert (dest / "file1.txt").exists()

    def test_extract_archive_with_progress(self, temp_dir, sample_zip_archive):
        """Test extraction with progress callback."""
        dest = temp_dir / "extracted"
        progress_calls = []

        def progress(current, total):
            progress_calls.append((current, total))

        extract_archive(sample_zip_archive, dest, progress_callback=progress)

        assert len(progress_calls) > 0
        # Last call should have current == total
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_extract_malicious_archive(self, temp_dir, malicious_zip_archive):
        """Test that malicious archives are rejected."""
        dest = temp_dir / "extracted"

        with pytest.raises(InsecureArchiveError, match="directory traversal"):
            extract_archive(malicious_zip_archive, dest)

    def test_extract_unsupported_format(self, temp_dir):
        """Test that unsupported archive formats are rejected."""
        # Create a file with unsupported extension
        archive = temp_dir / "file.rar"
        archive.write_text("not really an archive")

        dest = temp_dir / "extracted"

        with pytest.raises(
            UnsupportedArchiveFormat, match="Unsupported archive format"
        ):
            extract_archive(archive, dest)

    def test_extract_nonexistent_archive(self, temp_dir):
        """Test extracting nonexistent archive."""
        archive = temp_dir / "nonexistent.zip"
        dest = temp_dir / "extracted"

        with pytest.raises(ArchiveExtractionError, match="not found"):
            extract_archive(archive, dest)

    def test_extract_tar_xz(self, temp_dir):
        """Test extracting a tar.xz archive."""
        # Create a tar.xz archive
        archive_path = temp_dir / "sample.tar.xz"

        with tarfile.open(archive_path, "w:xz") as tar:
            temp_file = temp_dir / "temp.txt"
            temp_file.write_text("Content")
            tar.add(temp_file, arcname="file.txt")
            temp_file.unlink()

        dest = temp_dir / "extracted"
        extract_archive(archive_path, dest)

        assert (dest / "file.txt").exists()
        assert (dest / "file.txt").read_text() == "Content"

    def test_extract_tar_bz2(self, temp_dir):
        """Test extracting a tar.bz2 archive."""
        # Create a tar.bz2 archive
        archive_path = temp_dir / "sample.tar.bz2"

        with tarfile.open(archive_path, "w:bz2") as tar:
            temp_file = temp_dir / "temp.txt"
            temp_file.write_text("Content")
            tar.add(temp_file, arcname="file.txt")
            temp_file.unlink()

        dest = temp_dir / "extracted"
        extract_archive(archive_path, dest)

        assert (dest / "file.txt").exists()
        assert (dest / "file.txt").read_text() == "Content"


# ============================================================================
# Safe File Operations Tests
# ============================================================================


class TestSafeFileOperations:
    """Tests for safe file operations."""

    def test_atomic_write_text(self, temp_dir):
        """Test atomic write with text content."""
        file_path = temp_dir / "test.txt"
        content = "Hello, World!"

        atomic_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == content

    def test_atomic_write_binary(self, temp_dir):
        """Test atomic write with binary content."""
        file_path = temp_dir / "test.bin"
        content = b"\x00\x01\x02\x03"

        atomic_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() == content

    def test_atomic_write_creates_parent(self, temp_dir):
        """Test that parent directories are created."""
        file_path = temp_dir / "deep" / "nested" / "file.txt"

        atomic_write(file_path, "content")

        assert file_path.exists()
        assert file_path.read_text() == "content"

    def test_atomic_write_overwrites_existing(self, temp_dir):
        """Test that atomic write overwrites existing file."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("old content")

        atomic_write(file_path, "new content")

        assert file_path.read_text() == "new content"

    def test_safe_rmtree_removes_directory(self, temp_dir, sample_directory):
        """Test removing a directory tree."""
        assert sample_directory.exists()

        safe_rmtree(sample_directory)

        assert not sample_directory.exists()

    def test_safe_rmtree_nonexistent(self, temp_dir):
        """Test removing nonexistent directory (should not raise)."""
        path = temp_dir / "nonexistent"
        safe_rmtree(path)  # Should not raise

    def test_safe_rmtree_with_prefix_valid(self, temp_dir):
        """Test safe deletion with valid prefix."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        safe_rmtree(subdir, require_prefix=temp_dir)

        assert not subdir.exists()

    def test_safe_rmtree_with_prefix_invalid(self, temp_dir):
        """Test safe deletion rejects path outside prefix."""
        other_dir = Path(tempfile.gettempdir()) / "other"

        with pytest.raises(ValueError, match="not under required prefix"):
            safe_rmtree(other_dir, require_prefix=temp_dir)

    def test_safe_rmtree_not_a_directory(self, temp_dir, sample_file):
        """Test that safe_rmtree rejects non-directories."""
        with pytest.raises(FilesystemError, match="not a directory"):
            safe_rmtree(sample_file)

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_safe_rmtree_readonly_windows(self, temp_dir):
        """Test removing read-only files on Windows."""
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()

        readonly_file = readonly_dir / "file.txt"
        readonly_file.write_text("content")

        # Make file read-only
        readonly_file.chmod(0o444)

        # Should still be able to delete
        safe_rmtree(readonly_dir)

        assert not readonly_dir.exists()

    def test_recursive_copy(self, temp_dir, sample_directory):
        """Test recursive copy of directory tree."""
        dest = temp_dir / "copy"

        recursive_copy(sample_directory, dest)

        # Verify all files were copied
        assert (dest / "file1.txt").exists()
        assert (dest / "file2.txt").exists()
        assert (dest / "subdir" / "file3.txt").exists()

        # Verify content
        assert (dest / "file1.txt").read_text() == "Content 1"
        assert (dest / "subdir" / "file3.txt").read_text() == "Content 3"

    def test_recursive_copy_with_progress(self, temp_dir, sample_directory):
        """Test recursive copy with progress callback."""
        dest = temp_dir / "copy"
        copied_files = []

        def progress(path):
            copied_files.append(path)

        recursive_copy(sample_directory, dest, progress_callback=progress)

        assert len(copied_files) > 0

    def test_recursive_copy_source_not_exists(self, temp_dir):
        """Test copying nonexistent source."""
        source = temp_dir / "nonexistent"
        dest = temp_dir / "dest"

        with pytest.raises(FilesystemError, match="does not exist"):
            recursive_copy(source, dest)

    def test_recursive_copy_source_not_directory(self, temp_dir, sample_file):
        """Test copying a file (not directory)."""
        dest = temp_dir / "dest"

        with pytest.raises(FilesystemError, match="not a directory"):
            recursive_copy(sample_file, dest)

    def test_ensure_directory_creates_new(self, temp_dir):
        """Test creating a new directory."""
        new_dir = temp_dir / "new_dir"

        result = ensure_directory(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir.resolve()

    def test_ensure_directory_existing(self, temp_dir):
        """Test ensuring an existing directory."""
        existing = temp_dir / "existing"
        existing.mkdir()

        result = ensure_directory(existing)

        assert existing.exists()
        assert result == existing.resolve()

    def test_ensure_directory_creates_parents(self, temp_dir):
        """Test creating nested directories."""
        nested = temp_dir / "a" / "b" / "c"

        result = ensure_directory(nested)

        assert nested.exists()
        assert result == nested.resolve()

    def test_is_empty_directory_empty(self, temp_dir):
        """Test checking an empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        assert is_empty_directory(empty_dir)

    def test_is_empty_directory_not_empty(self, temp_dir, sample_directory):
        """Test checking a non-empty directory."""
        assert not is_empty_directory(sample_directory)

    def test_is_empty_directory_not_exists(self, temp_dir):
        """Test checking nonexistent directory."""
        nonexistent = temp_dir / "nonexistent"

        assert not is_empty_directory(nonexistent)

    def test_is_empty_directory_not_a_directory(self, temp_dir, sample_file):
        """Test checking a file (not directory)."""
        assert not is_empty_directory(sample_file)

    def test_directory_size(self, temp_dir, sample_directory):
        """Test calculating directory size."""
        size = directory_size(sample_directory)

        # Should be sum of all file sizes
        expected = len("Content 1") + len("Content 2") + len("Content 3")

        assert size == expected

    def test_directory_size_empty(self, temp_dir):
        """Test size of empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        size = directory_size(empty_dir)

        assert size == 0


# ============================================================================
# File Hashing Tests
# ============================================================================


class TestFileHashing:
    """Tests for file hashing."""

    def test_compute_file_hash_sha256(self, temp_dir):
        """Test computing SHA256 hash."""
        file_path = temp_dir / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content)

        hash_value = compute_file_hash(file_path, algorithm="sha256")

        # Verify it's a valid hex string
        assert len(hash_value) == 64  # SHA256 is 256 bits = 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_value)

        # Verify consistency
        hash_value2 = compute_file_hash(file_path, algorithm="sha256")
        assert hash_value == hash_value2

    def test_compute_file_hash_md5(self, temp_dir):
        """Test computing MD5 hash."""
        file_path = temp_dir / "test.txt"
        content = "Test content"
        file_path.write_text(content)

        hash_value = compute_file_hash(file_path, algorithm="md5")

        # Verify it's a valid hex string
        assert len(hash_value) == 32  # MD5 is 128 bits = 32 hex chars
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_file_hash_different_content(self, temp_dir):
        """Test that different content produces different hashes."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2

    def test_compute_file_hash_same_content(self, temp_dir):
        """Test that same content produces same hash."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"

        content = "Same content"
        file1.write_text(content)
        file2.write_text(content)

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 == hash2

    def test_compute_file_hash_binary(self, temp_dir):
        """Test hashing binary files."""
        file_path = temp_dir / "binary.bin"
        content = bytes(range(256))
        file_path.write_bytes(content)

        hash_value = compute_file_hash(file_path)

        assert len(hash_value) == 64  # SHA256

    def test_compute_file_hash_nonexistent(self, temp_dir):
        """Test hashing nonexistent file."""
        file_path = temp_dir / "nonexistent.txt"

        with pytest.raises(FilesystemError, match="not found"):
            compute_file_hash(file_path)

    def test_compute_file_hash_invalid_algorithm(self, temp_dir, sample_file):
        """Test using invalid hash algorithm."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            compute_file_hash(sample_file, algorithm="invalid_algo")

    def test_compute_file_hash_large_file(self, temp_dir):
        """Test hashing a large file (tests chunked reading)."""
        file_path = temp_dir / "large.bin"

        # Create a file larger than default chunk size (8KB)
        content = b"x" * (10 * 1024)  # 10KB
        file_path.write_bytes(content)

        hash_value = compute_file_hash(file_path, chunk_size=1024)

        # Verify consistency with different chunk size
        hash_value2 = compute_file_hash(file_path, chunk_size=4096)
        assert hash_value == hash_value2


# ============================================================================
# Temporary Directory Tests
# ============================================================================


class TestTemporaryDirectory:
    """Tests for temporary directory context manager."""

    def test_temporary_directory_created(self):
        """Test that temporary directory is created."""
        with temporary_directory() as tmp:
            assert tmp.exists()
            assert tmp.is_dir()

    def test_temporary_directory_cleaned_up(self):
        """Test that temporary directory is cleaned up."""
        with temporary_directory() as tmp:
            temp_path = tmp
            # Create some files
            (tmp / "file.txt").write_text("content")

        # After exiting context, directory should be gone
        assert not temp_path.exists()

    def test_temporary_directory_custom_prefix(self):
        """Test temporary directory with custom prefix."""
        with temporary_directory(prefix="custom_") as tmp:
            assert "custom_" in tmp.name

    def test_temporary_directory_no_cleanup(self):
        """Test temporary directory without cleanup."""
        with temporary_directory(cleanup=False) as tmp:
            temp_path = tmp
            (tmp / "file.txt").write_text("content")

        # Directory should still exist
        assert temp_path.exists()

        # Clean up manually
        safe_rmtree(temp_path)

    def test_temporary_directory_can_write(self):
        """Test that we can write to temporary directory."""
        with temporary_directory() as tmp:
            file_path = tmp / "test.txt"
            file_path.write_text("Hello")

            assert file_path.read_text() == "Hello"

    def test_temporary_directory_exception_cleanup(self):
        """Test that directory is cleaned up even on exception."""
        temp_path = None

        try:
            with temporary_directory() as tmp:
                temp_path = tmp
                (tmp / "file.txt").write_text("content")
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Directory should be cleaned up despite exception
        assert not temp_path.exists()


# ============================================================================
# Platform-Specific Tests
# ============================================================================


class TestPlatformSpecific:
    """Platform-specific behavior tests."""

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_windows_junction_no_admin(self, temp_dir, sample_directory):
        """Test that Windows junctions work without admin privileges."""
        link_path = temp_dir / "junction"

        # This should work without admin rights
        create_link(sample_directory, link_path, link_type="junction")

        assert link_path.exists()
        assert (link_path / "file1.txt").exists()

    @pytest.mark.skipif(not IS_UNIX, reason="Unix-specific test")
    def test_unix_symlink_permissions(self, temp_dir):
        """Test Unix symlink creation and permissions."""
        source = temp_dir / "source"
        source.mkdir()

        link = temp_dir / "link"
        create_link(source, link, link_type="symlink")

        assert link.is_symlink()
        # Symlinks themselves don't have meaningful permissions
        assert link.exists()

    @pytest.mark.skipif(not IS_UNIX, reason="Unix-specific test")
    def test_unix_symlink_to_file(self, temp_dir, sample_file):
        """Test creating symlink to a file on Unix."""
        link = temp_dir / "link"
        create_link(sample_file, link, link_type="symlink")

        assert link.is_symlink()
        assert link.read_text() == sample_file.read_text()


# ============================================================================
# Integration-Like Tests
# ============================================================================


class TestIntegrationScenarios:
    """Tests that simulate real-world usage scenarios."""

    def test_toolchain_extraction_and_linking(self, temp_dir, sample_tar_gz_archive):
        """Simulate extracting a toolchain and creating a link."""
        # Extract archive
        extract_dir = temp_dir / "toolchains" / "llvm-15"
        extract_archive(sample_tar_gz_archive, extract_dir)

        # Create a link in project-local directory
        project_local = temp_dir / "project" / ".toolchainkit" / "toolchains"
        project_local.mkdir(parents=True)
        link = project_local / "llvm-15"

        create_link(extract_dir, link)

        # Verify we can access through link
        assert (link / "file1.txt").exists()

    def test_safe_config_update(self, temp_dir):
        """Simulate safely updating a configuration file."""
        config_file = temp_dir / "config.json"

        # Initial config
        initial_config = {"version": 1, "toolchain": "llvm-14"}
        atomic_write(config_file, json.dumps(initial_config, indent=2))

        # Update config
        updated_config = {"version": 2, "toolchain": "llvm-15"}
        atomic_write(config_file, json.dumps(updated_config, indent=2))

        # Verify update
        loaded = json.loads(config_file.read_text())
        assert loaded["version"] == 2
        assert loaded["toolchain"] == "llvm-15"

    def test_verify_downloaded_archive(self, temp_dir, sample_zip_archive):
        """Simulate verifying a downloaded archive."""
        # Compute expected hash
        expected_hash = compute_file_hash(sample_zip_archive)

        # Simulate downloading to temp location
        download_path = temp_dir / "downloads" / "toolchain.zip"
        download_path.parent.mkdir(parents=True)

        # Copy archive (simulates download)
        shutil.copy(sample_zip_archive, download_path)

        # Verify hash
        actual_hash = compute_file_hash(download_path)
        assert actual_hash == expected_hash

        # Extract if verification passed
        extract_dir = temp_dir / "extracted"
        extract_archive(download_path, extract_dir)

        assert (extract_dir / "file1.txt").exists()

    def test_cleanup_old_cache(self, temp_dir):
        """Simulate cleaning up old cache directories."""
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()

        # Create some old toolchain directories
        old_toolchain = cache_dir / "llvm-14"
        old_toolchain.mkdir()
        (old_toolchain / "bin" / "clang").mkdir(parents=True)

        # Calculate size before cleanup
        size_before = directory_size(cache_dir)
        assert size_before >= 0

        # Cleanup
        safe_rmtree(old_toolchain, require_prefix=cache_dir)

        # Verify cleanup
        assert not old_toolchain.exists()
        assert is_empty_directory(cache_dir)


# ============================================================================
# Additional Edge Case Tests for Missing Coverage
# ============================================================================


class TestPathUtilitiesEdgeCases:
    """Edge cases for path utilities to improve coverage."""

    def test_is_relative_to_fallback_python38(self, temp_dir):
        """Test fallback path for is_relative_to on Python < 3.9."""
        # This test is for Python < 3.9 which doesn't have is_relative_to
        # On Python 3.9+, the builtin method is used directly
        # We can't easily test the fallback on Python 3.9+ without complex mocking

        # Just test that is_relative_to works correctly
        child = temp_dir / "subdir" / "file.txt"
        assert is_relative_to(child, temp_dir)

        # Test ValueError case
        other_path = Path("/completely/different/path")
        assert not is_relative_to(other_path, temp_dir)

    def test_resolve_link_resolves_broken_link(self, temp_dir):
        """Test resolving a link that's not actually a symlink."""
        # This should already be tested, but ensure ValueError is raised
        regular_file = temp_dir / "regular.txt"
        regular_file.write_text("content")

        with pytest.raises(ValueError, match="not a symbolic link"):
            resolve_link(regular_file)

    def test_find_executable_empty_path_env(self, monkeypatch):
        """Test find_executable with empty PATH environment variable."""
        monkeypatch.setenv("PATH", "")
        result = find_executable("nonexistent")
        assert result is None

    def test_find_executable_with_extension_variations(self, temp_dir):
        """Test find_executable with different extensions on Windows."""
        if not IS_WINDOWS:
            pytest.skip("Windows-specific test")

        # Create executable with .cmd extension
        exe_path = temp_dir / "test.cmd"
        exe_path.write_text("@echo off\necho test")

        result = find_executable("test", search_paths=[temp_dir])
        assert result == exe_path

    def test_find_executable_non_executable_file(self, temp_dir):
        """Test that non-executable files are skipped."""
        if IS_WINDOWS:
            pytest.skip("Unix-specific test (executable bit)")

        # Create a file without execute permission
        non_exe = temp_dir / "not_executable"
        non_exe.write_text("#!/bin/sh\necho test")
        non_exe.chmod(0o644)  # No execute bit

        result = find_executable("not_executable", search_paths=[temp_dir])
        assert result is None

    def test_make_long_path_safe_already_has_prefix(self, temp_dir):
        """Test that paths with existing \\\\?\\ prefix are not modified."""
        if not IS_WINDOWS:
            pytest.skip("Windows-specific test")

        # Simulate a path that already has the prefix
        long_path = "\\\\?\\" + "C:\\" + "a" * 300
        result = make_long_path_safe(long_path)

        # Should not duplicate the prefix
        assert result.count("\\\\?\\") == 1


class TestLinkCreationEdgeCases:
    """Edge cases for link creation to improve coverage."""

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_create_junction_source_not_directory(self, temp_dir):
        """Test creating junction to non-directory source fails."""
        source_file = temp_dir / "file.txt"
        source_file.write_text("content")

        target = temp_dir / "junction"

        with pytest.raises(LinkCreationError, match="must be a directory"):
            create_link(source_file, target, link_type="junction", allow_fallback=False)

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_create_symlink_windows_no_privileges(self, temp_dir, monkeypatch):
        """Test symlink creation on Windows without admin privileges."""
        import os

        # Mock os.symlink to raise permission error
        def mock_symlink(*args, **kwargs):
            error = OSError("A required privilege is not held by the client.")
            error.winerror = 1314  # ERROR_PRIVILEGE_NOT_HELD
            raise error

        monkeypatch.setattr(os, "symlink", mock_symlink)

        source = temp_dir / "source"
        source.mkdir()
        target = temp_dir / "link"

        with pytest.raises(PermissionError, match="administrator privileges"):
            create_link(source, target, link_type="symlink", allow_fallback=False)

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_create_junction_mklink_fails_fallback_api(self, temp_dir, monkeypatch):
        """Test junction creation falls back to Windows API when mklink fails."""
        import subprocess

        # Mock subprocess.run to fail for mklink
        original_run = subprocess.run

        def mock_run(args, **kwargs):
            if "mklink" in args:
                # Simulate mklink failure
                result = type(
                    "Result",
                    (),
                    {"returncode": 1, "stderr": "mklink failed", "stdout": ""},
                )()
                return result
            return original_run(args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        source = temp_dir / "source"
        source.mkdir()
        target = temp_dir / "junction"

        # This should fall back to Windows API (which may fail without proper setup)
        try:
            create_link(source, target, link_type="junction", allow_fallback=False)
        except LinkCreationError as e:
            # Expected if Windows API also fails
            assert "Failed to create junction" in str(e)

    def test_create_link_invalid_link_type_windows(self, temp_dir):
        """Test create_link with unsupported link type on Windows."""
        if not IS_WINDOWS:
            pytest.skip("Windows-specific test")

        source = temp_dir / "source"
        source.mkdir()
        target = temp_dir / "link"

        with pytest.raises(ValueError, match="Unsupported link type for Windows"):
            create_link(source, target, link_type="hardlink", allow_fallback=False)

    def test_create_link_invalid_link_type_unix(self, temp_dir):
        """Test create_link with unsupported link type on Unix."""
        if IS_WINDOWS:
            pytest.skip("Unix-specific test")

        source = temp_dir / "source"
        source.mkdir()
        target = temp_dir / "link"

        with pytest.raises(ValueError, match="Unsupported link type for Unix"):
            create_link(source, target, link_type="hardlink", allow_fallback=False)

    def test_create_link_permission_error_with_fallback(self, temp_dir, monkeypatch):
        """Test that PermissionError triggers fallback to reference tracking."""
        import os

        # Mock os.symlink to raise PermissionError
        def mock_symlink(*args, **kwargs):
            raise PermissionError("No permission to create symlink")

        monkeypatch.setattr(os, "symlink", mock_symlink)

        source = temp_dir / "source"
        source.mkdir()
        target = temp_dir / "link"

        # Should fall back to reference tracking
        create_link(source, target, link_type="symlink", allow_fallback=True)

        # Verify reference file was created
        reference_file = target.with_suffix(".link_reference")
        assert reference_file.exists()


class TestArchiveExtractionEdgeCases:
    """Edge cases for archive extraction to improve coverage."""

    def test_extract_tar_with_python312_filter(self, temp_dir):
        """Test tar extraction uses filter parameter on Python 3.12+."""
        import sys
        import tarfile

        # Only run this test on Python 3.12+
        if sys.version_info < (3, 12):
            pytest.skip("Test requires Python 3.12+ for filter parameter")

        # Create a tar.gz archive
        archive_path = temp_dir / "test.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            temp_file = temp_dir / "temp.txt"
            temp_file.write_text("Content")
            tar.add(temp_file, arcname="file.txt")
            temp_file.unlink()

        dest = temp_dir / "extracted"
        extract_archive(archive_path, dest)

        assert (dest / "file.txt").exists()

    def test_extract_exe_no_7zip(self, temp_dir, monkeypatch):
        """Test extracting .exe without 7-Zip installed."""
        import shutil

        # Mock shutil.which to return None
        monkeypatch.setattr(shutil, "which", lambda x: None)

        # Mock Path.exists to return False for 7zip paths
        original_exists = Path.exists

        def mock_exists(self):
            path_str = str(self)
            # Return False for 7-Zip paths
            if "7-Zip" in path_str or "7z.exe" in path_str:
                return False
            # Use original for other paths
            return original_exists(self)

        monkeypatch.setattr(Path, "exists", mock_exists)

        # Create a fake .exe file
        exe_path = temp_dir / "installer.exe"
        exe_path.write_bytes(b"fake exe")

        dest = temp_dir / "extracted"

        with pytest.raises(UnsupportedArchiveFormat, match="requires 7-Zip"):
            extract_archive(exe_path, dest)

    def test_extract_exe_7zip_extraction_fails(self, temp_dir, monkeypatch):
        """Test .exe extraction when 7-Zip command fails."""
        if not IS_WINDOWS:
            pytest.skip("Windows-specific test")

        import subprocess
        import shutil

        # Mock shutil.which to find 7z
        monkeypatch.setattr(shutil, "which", lambda x: "7z.exe" if x == "7z" else None)

        # Mock subprocess.run to fail
        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "7z", stderr="extraction failed")

        monkeypatch.setattr(subprocess, "run", mock_run)

        exe_path = temp_dir / "installer.exe"
        exe_path.write_bytes(b"fake exe")

        dest = temp_dir / "extracted"

        with pytest.raises(ArchiveExtractionError, match="7-Zip extraction failed"):
            extract_archive(exe_path, dest)

    def test_extract_7z_no_py7zr(self, temp_dir, monkeypatch):
        """Test extracting .7z without py7zr installed."""
        import sys

        # Mock import of py7zr to fail
        def mock_import(name, *args, **kwargs):
            if name == "py7zr":
                raise ImportError("No module named 'py7zr'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setitem(sys.modules, "py7zr", None)

        archive_path = temp_dir / "test.7z"
        archive_path.write_bytes(b"fake 7z")

        dest = temp_dir / "extracted"

        with pytest.raises(UnsupportedArchiveFormat, match="requires 'py7zr'"):
            extract_archive(archive_path, dest)

    def test_extract_archive_generic_exception(self, temp_dir, monkeypatch):
        """Test that generic exceptions during extraction are wrapped."""
        import zipfile

        # Create a valid zip file
        archive_path = temp_dir / "test.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("file.txt", "content")

        # Mock ZipFile to raise a generic exception
        class FailingZipFile:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Simulated extraction failure")

        monkeypatch.setattr(zipfile, "ZipFile", FailingZipFile)

        dest = temp_dir / "extracted"

        with pytest.raises(ArchiveExtractionError, match="Failed to extract"):
            extract_archive(archive_path, dest)


class TestSafeFileOperationsEdgeCases:
    """Edge cases for safe file operations to improve coverage."""

    def test_atomic_write_failure_cleanup(self, temp_dir, monkeypatch):
        """Test that temp file is cleaned up on write failure."""

        file_path = temp_dir / "test.txt"

        # Mock os.replace to fail
        def mock_replace(self, target):
            raise OSError("Simulated replace failure")

        monkeypatch.setattr(Path, "replace", mock_replace)

        # Attempt atomic write
        with pytest.raises(OSError, match="Simulated replace failure"):
            atomic_write(file_path, "content")

        # Verify no temp files left behind
        temp_files = list(temp_dir.glob(".test.txt.*.tmp"))
        assert len(temp_files) == 0

    def test_safe_rmtree_deletion_fails(self, temp_dir, monkeypatch):
        """Test safe_rmtree when deletion fails."""
        import shutil

        target_dir = temp_dir / "to_delete"
        target_dir.mkdir()

        # Mock shutil.rmtree to fail
        def mock_rmtree(*args, **kwargs):
            raise PermissionError("Cannot delete")

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        with pytest.raises(FilesystemError, match="Failed to remove directory"):
            safe_rmtree(target_dir)

    def test_recursive_copy_with_symlinks(self, temp_dir):
        """Test recursive copy preserving symlinks."""
        if IS_WINDOWS:
            pytest.skip("Symlink test requires Unix or Windows admin")

        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create a file and a symlink to it
        real_file = source_dir / "real.txt"
        real_file.write_text("content")

        link_file = source_dir / "link.txt"
        os.symlink(real_file, link_file)

        dest_dir = temp_dir / "dest"

        # Copy with symlinks=True
        recursive_copy(source_dir, dest_dir, symlinks=True)

        # Verify symlink was copied as symlink
        dest_link = dest_dir / "link.txt"
        assert dest_link.is_symlink()

    def test_recursive_copy_overwrites_symlink(self, temp_dir):
        """Test that recursive copy overwrites existing symlinks."""
        if IS_WINDOWS:
            pytest.skip("Symlink test requires Unix or Windows admin")

        source_dir = temp_dir / "source"
        source_dir.mkdir()

        real_file = source_dir / "real.txt"
        real_file.write_text("content")

        link_file = source_dir / "link.txt"
        os.symlink(real_file, link_file)

        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Create existing symlink at destination
        dest_link = dest_dir / "link.txt"
        dest_fake = dest_dir / "fake.txt"
        dest_fake.write_text("fake")
        os.symlink(dest_fake, dest_link)

        # Copy should overwrite the existing symlink
        recursive_copy(source_dir, dest_dir, symlinks=True)

        # Verify new symlink points to correct target
        assert dest_link.is_symlink()

    def test_compute_file_hash_empty_file(self, temp_dir):
        """Test hashing an empty file."""
        file_path = temp_dir / "empty.txt"
        file_path.write_text("")

        hash_value = compute_file_hash(file_path)

        # Empty file should have consistent hash
        assert len(hash_value) == 64
        assert hash_value == compute_file_hash(file_path)


class TestWindowsSpecificEdgeCases:
    """Windows-specific edge cases."""

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_has_symlink_privilege_check(self, temp_dir):
        """Test _has_symlink_privilege function."""
        from toolchainkit.core.filesystem import _has_symlink_privilege

        # Just call it - it should return True or False
        result = _has_symlink_privilege()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_safe_rmtree_readonly_error_handler(self, temp_dir):
        """Test readonly error handler in safe_rmtree on Windows."""
        readonly_dir = temp_dir / "readonly_test"
        readonly_dir.mkdir()

        readonly_file = readonly_dir / "readonly.txt"
        readonly_file.write_text("content")
        readonly_file.chmod(0o444)

        # Should successfully delete despite readonly attribute
        safe_rmtree(readonly_dir)

        assert not readonly_dir.exists()

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific test")
    def test_create_junction_target_exists_as_symlink(self, temp_dir):
        """Test junction creation removes existing target symlink."""
        source = temp_dir / "source"
        source.mkdir()

        target = temp_dir / "junction"

        # Create the target first (will be removed)
        try:
            os.symlink(source, target, target_is_directory=True)
        except (OSError, PermissionError):
            pytest.skip("Cannot create symlink for test setup")

        # Now create junction at same location
        create_link(source, target, link_type="junction")

        # Verify junction was created
        assert target.exists()


class TestUnixSpecificEdgeCases:
    """Unix-specific edge cases."""

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-specific test")
    def test_create_symlink_to_nonexistent_target(self, temp_dir):
        """Test creating symlink to nonexistent target (allowed on Unix)."""
        source = temp_dir / "nonexistent"
        target = temp_dir / "link"

        create_link(source, target, link_type="symlink")

        # Symlink should exist even though target doesn't
        assert target.is_symlink()

        # But resolving it should fail
        with pytest.raises(FileNotFoundError):
            target.resolve(strict=True)


class TestIntegrationEdgeCases:
    """Integration edge cases combining multiple functions."""

    def test_extract_and_hash_verification_failure(self, temp_dir, sample_zip_archive):
        """Test extraction with hash verification failure scenario."""
        # Compute original hash
        original_hash = compute_file_hash(sample_zip_archive)

        # Copy archive
        copied_archive = temp_dir / "copied.zip"
        shutil.copy(sample_zip_archive, copied_archive)

        # Compute copied hash
        copied_hash = compute_file_hash(copied_archive)

        # They should match
        assert original_hash == copied_hash

        # Now modify the copied archive
        with open(copied_archive, "ab") as f:
            f.write(b"corrupted")

        # Hash should no longer match
        corrupted_hash = compute_file_hash(copied_archive)
        assert corrupted_hash != original_hash

    def test_temporary_directory_with_atomic_write(self):
        """Test using atomic_write inside temporary_directory."""
        with temporary_directory() as tmp:
            file_path = tmp / "config.json"
            content = '{"key": "value"}'

            atomic_write(file_path, content)

            assert file_path.exists()
            assert file_path.read_text() == content

        # Directory should be cleaned up
        assert not tmp.exists()

    def test_recursive_copy_with_progress_tracking(self, temp_dir, sample_directory):
        """Test recursive copy tracks all files in progress callback."""
        dest = temp_dir / "copy"
        copied_files = []

        def progress(path):
            copied_files.append(str(path))

        recursive_copy(sample_directory, dest, progress_callback=progress)

        # Should have tracked file1.txt, file2.txt, and subdir/file3.txt
        # (directories are also tracked)
        assert len(copied_files) >= 3

    def test_ensure_directory_with_long_path_windows(self, temp_dir):
        """Test ensure_directory with very long path on Windows."""
        if not IS_WINDOWS:
            pytest.skip("Windows-specific test")

        # Create nested directory structure
        long_path = temp_dir / "a" / "b" / "c" / "d" / "e" / "f" / "g"
        result = ensure_directory(long_path)

        assert result.exists()
        assert result.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
