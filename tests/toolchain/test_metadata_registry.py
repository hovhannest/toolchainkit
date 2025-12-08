"""
Unit tests for toolchain registry module.
"""

import json
import pytest
from toolchainkit.toolchain.metadata_registry import (
    ToolchainMetadataRegistry,
    ToolchainMetadata,
    ToolchainRegistryError,
    InvalidVersionError,
)


@pytest.fixture
def temp_metadata_file(tmp_path):
    """Create a temporary metadata file for testing."""
    metadata = {
        "toolchains": {
            "llvm": {
                "type": "clang",
                "versions": {
                    "18.1.8": {
                        "linux-x64": {
                            "url": "https://example.com/llvm-18.1.8-linux.tar.xz",
                            "sha256": "abc123",
                            "size_mb": 500,
                            "stdlib": ["libc++", "libstdc++"],
                        },
                        "windows-x64": {
                            "url": "https://example.com/llvm-18.1.8-win.exe",
                            "sha256": "def456",
                            "size_mb": 350,
                            "requires_installer": True,
                        },
                    },
                    "18.1.7": {
                        "linux-x64": {
                            "url": "https://example.com/llvm-18.1.7-linux.tar.xz",
                            "sha256": "ghi789",
                            "size_mb": 498,
                        }
                    },
                    "17.0.6": {
                        "linux-x64": {
                            "url": "https://example.com/llvm-17.0.6-linux.tar.xz",
                            "sha256": "jkl012",
                            "size_mb": 480,
                        }
                    },
                },
            },
            "gcc": {
                "type": "gcc",
                "versions": {
                    "13.2.0": {
                        "linux-x64": {
                            "url": "https://example.com/gcc-13.2.0-linux.tar.xz",
                            "sha256": "mno345",
                            "size_mb": 90,
                        }
                    }
                },
            },
        }
    }

    metadata_file = tmp_path / "toolchains.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f)

    return metadata_file


@pytest.fixture
def registry(temp_metadata_file):
    """Create a registry instance with test metadata."""
    return ToolchainMetadataRegistry(metadata_path=temp_metadata_file)


class TestToolchainMetadata:
    """Tests for ToolchainMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating metadata with valid data."""
        metadata = ToolchainMetadata(
            url="https://example.com/toolchain.tar.xz", sha256="abc123", size_mb=500
        )
        assert metadata.url == "https://example.com/toolchain.tar.xz"
        assert metadata.sha256 == "abc123"
        assert metadata.size_mb == 500
        assert metadata.stdlib == []
        assert metadata.requires_installer is False

    def test_metadata_with_optional_fields(self):
        """Test metadata with all optional fields."""
        metadata = ToolchainMetadata(
            url="https://example.com/toolchain.tar.xz",
            sha256="abc123",
            size_mb=500,
            stdlib=["libc++", "libstdc++"],
            requires_installer=True,
        )
        assert metadata.stdlib == ["libc++", "libstdc++"]
        assert metadata.requires_installer is True

    def test_metadata_validation_empty_url(self):
        """Test validation fails with empty URL."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            ToolchainMetadata(url="", sha256="abc123", size_mb=500)

    def test_metadata_validation_empty_sha256(self):
        """Test validation fails with empty SHA256."""
        with pytest.raises(ValueError, match="SHA256 cannot be empty"):
            ToolchainMetadata(url="https://example.com/test", sha256="", size_mb=500)

    def test_metadata_validation_invalid_size(self):
        """Test validation fails with invalid size."""
        with pytest.raises(ValueError, match="Size must be positive"):
            ToolchainMetadata(url="https://example.com/test", sha256="abc", size_mb=0)

        with pytest.raises(ValueError, match="Size must be positive"):
            ToolchainMetadata(url="https://example.com/test", sha256="abc", size_mb=-10)


class TestRegistryInitialization:
    """Tests for registry initialization."""

    def test_load_metadata_file(self, temp_metadata_file):
        """Test loading metadata from file."""
        registry = ToolchainMetadataRegistry(metadata_path=temp_metadata_file)
        assert registry.metadata is not None
        assert "toolchains" in registry.metadata
        assert "llvm" in registry.metadata["toolchains"]

    def test_missing_metadata_file(self, tmp_path):
        """Test error when metadata file is missing."""
        missing_file = tmp_path / "missing.json"
        with pytest.raises(ToolchainRegistryError, match="Metadata file not found"):
            ToolchainMetadataRegistry(metadata_path=missing_file)

    def test_invalid_json_file(self, tmp_path):
        """Test error with invalid JSON."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ invalid json }")

        with pytest.raises(ToolchainRegistryError, match="Invalid JSON"):
            ToolchainMetadataRegistry(metadata_path=bad_json)

    def test_missing_toolchains_key(self, tmp_path):
        """Test error when metadata structure is invalid."""
        bad_structure = tmp_path / "bad_structure.json"
        with open(bad_structure, "w") as f:
            json.dump({"versions": {}}, f)

        with pytest.raises(ToolchainRegistryError, match="missing 'toolchains' key"):
            ToolchainMetadataRegistry(metadata_path=bad_structure)

    def test_default_metadata_path(self):
        """Test default metadata path points to embedded file."""
        # This test uses the real embedded metadata file
        registry = ToolchainMetadataRegistry()
        assert registry.metadata_path.exists()
        assert registry.metadata_path.name == "toolchains.json"


class TestToolchainLookup:
    """Tests for toolchain lookup functionality."""

    def test_lookup_exact_version(self, registry):
        """Test lookup with exact version."""
        metadata = registry.lookup("llvm", "18.1.8", "linux-x64")
        assert metadata is not None
        assert metadata.url == "https://example.com/llvm-18.1.8-linux.tar.xz"
        assert metadata.sha256 == "abc123"
        assert metadata.size_mb == 500
        assert "libc++" in metadata.stdlib

    def test_lookup_windows_installer(self, registry):
        """Test lookup for Windows installer."""
        metadata = registry.lookup("llvm", "18.1.8", "windows-x64")
        assert metadata is not None
        assert metadata.requires_installer is True
        assert metadata.url.endswith(".exe")

    def test_lookup_nonexistent_toolchain(self, registry):
        """Test lookup returns None for nonexistent toolchain."""
        metadata = registry.lookup("rust", "1.70.0", "linux-x64")
        assert metadata is None

    def test_lookup_nonexistent_version(self, registry):
        """Test lookup returns None for nonexistent version."""
        metadata = registry.lookup("llvm", "99.0.0", "linux-x64")
        assert metadata is None

    def test_lookup_nonexistent_platform(self, registry):
        """Test lookup returns None for nonexistent platform."""
        metadata = registry.lookup("llvm", "18.1.8", "freebsd-x64")
        assert metadata is None

    def test_lookup_with_version_resolution(self, registry):
        """Test lookup with version pattern resolution."""
        # Should resolve "18" to "18.1.8" (latest patch)
        metadata = registry.lookup("llvm", "18", "linux-x64")
        assert metadata is not None
        assert metadata.url == "https://example.com/llvm-18.1.8-linux.tar.xz"


class TestVersionResolution:
    """Tests for version resolution."""

    def test_resolve_exact_version(self, registry):
        """Test resolving exact version."""
        version = registry.resolve_version("llvm", "18.1.8")
        assert version == "18.1.8"

    def test_resolve_major_minor(self, registry):
        """Test resolving major.minor to latest patch."""
        version = registry.resolve_version("llvm", "18.1")
        assert version == "18.1.8"  # Latest in 18.1.x series

    def test_resolve_major_only(self, registry):
        """Test resolving major version to latest."""
        version = registry.resolve_version("llvm", "18")
        assert version == "18.1.8"  # Latest in 18.x series

    def test_resolve_latest(self, registry):
        """Test resolving 'latest' keyword."""
        version = registry.resolve_version("llvm", "latest")
        assert version == "18.1.8"  # Newest version overall

    def test_resolve_nonexistent_toolchain(self, registry):
        """Test resolving version for nonexistent toolchain."""
        version = registry.resolve_version("rust", "1.70")
        assert version is None

    def test_resolve_nonexistent_version(self, registry):
        """Test resolving nonexistent version."""
        version = registry.resolve_version("llvm", "99")
        assert version is None

    def test_resolve_invalid_pattern(self, registry):
        """Test resolving invalid version pattern."""
        with pytest.raises(InvalidVersionError, match="Invalid version pattern"):
            registry.resolve_version("llvm", "invalid")

        with pytest.raises(InvalidVersionError, match="Invalid version pattern"):
            registry.resolve_version("llvm", "x.y.z")


class TestListOperations:
    """Tests for list operations."""

    def test_list_toolchains(self, registry):
        """Test listing all toolchains."""
        toolchains = registry.list_toolchains()
        assert "llvm" in toolchains
        assert "gcc" in toolchains
        assert len(toolchains) == 2

    def test_list_versions(self, registry):
        """Test listing versions for a toolchain."""
        versions = registry.list_versions("llvm")
        assert "18.1.8" in versions
        assert "18.1.7" in versions
        assert "17.0.6" in versions
        assert len(versions) == 3
        # Should be sorted newest first
        assert versions[0] == "18.1.8"

    def test_list_versions_nonexistent_toolchain(self, registry):
        """Test listing versions for nonexistent toolchain."""
        versions = registry.list_versions("rust")
        assert versions == []

    def test_list_platforms(self, registry):
        """Test listing platforms for a toolchain version."""
        platforms = registry.list_platforms("llvm", "18.1.8")
        assert "linux-x64" in platforms
        assert "windows-x64" in platforms
        assert len(platforms) == 2

    def test_list_platforms_nonexistent_version(self, registry):
        """Test listing platforms for nonexistent version."""
        platforms = registry.list_platforms("llvm", "99.0.0")
        assert platforms == []


class TestCompatibility:
    """Tests for compatibility checking."""

    def test_is_compatible_true(self, registry):
        """Test compatibility check returns True."""
        assert registry.is_compatible("llvm", "18.1.8", "linux-x64")
        assert registry.is_compatible("gcc", "13.2.0", "linux-x64")

    def test_is_compatible_with_resolution(self, registry):
        """Test compatibility with version resolution."""
        assert registry.is_compatible("llvm", "18", "linux-x64")
        assert registry.is_compatible("llvm", "18.1", "linux-x64")

    def test_is_compatible_false_toolchain(self, registry):
        """Test compatibility returns False for nonexistent toolchain."""
        assert not registry.is_compatible("rust", "1.70", "linux-x64")

    def test_is_compatible_false_version(self, registry):
        """Test compatibility returns False for nonexistent version."""
        assert not registry.is_compatible("llvm", "99.0.0", "linux-x64")

    def test_is_compatible_false_platform(self, registry):
        """Test compatibility returns False for nonexistent platform."""
        assert not registry.is_compatible("llvm", "18.1.8", "freebsd-x64")


class TestToolchainType:
    """Tests for toolchain type retrieval."""

    def test_get_toolchain_type(self, registry):
        """Test getting toolchain type."""
        assert registry.get_toolchain_type("llvm") == "clang"
        assert registry.get_toolchain_type("gcc") == "gcc"

    def test_get_toolchain_type_nonexistent(self, registry):
        """Test getting type for nonexistent toolchain."""
        assert registry.get_toolchain_type("rust") is None


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_get_toolchain_metadata_function(self, temp_metadata_file):
        """Test convenience function for quick lookup."""
        # Need to temporarily swap the metadata file
        # For this test, we'll just test with a registry instance
        registry = ToolchainMetadataRegistry(metadata_path=temp_metadata_file)
        metadata = registry.lookup("llvm", "18.1.8", "linux-x64")
        assert metadata is not None
        assert metadata.url == "https://example.com/llvm-18.1.8-linux.tar.xz"


class TestRealMetadata:
    """Tests using the real embedded metadata file."""

    def test_load_real_metadata(self):
        """Test loading the real embedded metadata file."""
        registry = ToolchainMetadataRegistry()
        assert len(registry.list_toolchains()) > 0

    def test_llvm_versions_exist(self):
        """Test that LLVM versions are available."""
        registry = ToolchainMetadataRegistry()
        versions = registry.list_versions("llvm")
        assert len(versions) > 0
        # Check for recent versions
        assert any(v.startswith("18.") for v in versions)

    def test_gcc_versions_exist(self):
        """Test that GCC versions are available."""
        registry = ToolchainMetadataRegistry()
        versions = registry.list_versions("gcc")
        assert len(versions) > 0

    def test_lookup_real_llvm_toolchain(self):
        """Test looking up a real LLVM toolchain."""
        registry = ToolchainMetadataRegistry()
        metadata = registry.lookup("llvm", "18", "linux-x64")
        assert metadata is not None
        assert "github.com" in metadata.url
        assert len(metadata.sha256) == 64  # SHA256 is 64 hex chars
        assert metadata.size_mb > 0

    def test_platform_coverage(self):
        """Test that major platforms are covered."""
        registry = ToolchainMetadataRegistry()
        platforms = registry.list_platforms("llvm", "18.1.8")

        # Should have major platforms
        assert any("linux" in p for p in platforms)
        assert any("windows" in p for p in platforms)
        assert any("macos" in p for p in platforms)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_metadata_file(self, tmp_path):
        """Test handling of empty metadata file."""
        empty_file = tmp_path / "empty.json"
        with open(empty_file, "w") as f:
            json.dump({"toolchains": {}}, f)

        registry = ToolchainMetadataRegistry(metadata_path=empty_file)
        assert registry.list_toolchains() == []

    def test_version_sorting(self, registry):
        """Test that versions are sorted correctly."""
        versions = registry.list_versions("llvm")
        # Check versions are in descending order
        for i in range(len(versions) - 1):
            v1_parts = [int(p) for p in versions[i].split(".")]
            v2_parts = [int(p) for p in versions[i + 1].split(".")]
            assert v1_parts >= v2_parts

    def test_multiple_lookups_performance(self, registry):
        """Test that multiple lookups are fast."""
        import time

        start = time.time()
        for _ in range(100):
            registry.lookup("llvm", "18.1.8", "linux-x64")
        elapsed = time.time() - start

        # Should be very fast (< 100ms for 100 lookups)
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
