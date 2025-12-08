"""Tests for Memory Allocator Layers.

This module tests the AllocatorLayer class and allocator YAML definitions.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from toolchainkit.config.layers import (
    AllocatorLayer,
    LayerContext,
    LayerRequirementError,
    LayerConflictError,
)


# ============================================================================
# Unit Tests - AllocatorLayer Class
# ============================================================================


class TestAllocatorLayerInit:
    """Test AllocatorLayer initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        assert layer.name == "jemalloc"
        assert layer.allocator_name == "jemalloc"
        assert layer.method == "auto"
        assert layer.layer_type == "allocator"
        assert "Memory allocator: jemalloc" in layer.description

    def test_init_with_custom_method(self):
        """Test initialization with custom integration method."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="link")
        assert layer.method == "link"

    def test_init_with_custom_description(self):
        """Test initialization with custom description."""
        desc = "Custom jemalloc layer"
        layer = AllocatorLayer("jemalloc", "jemalloc", description=desc)
        assert layer.description == desc


class TestAllocatorLayerConflicts:
    """Test allocator conflicts with sanitizers."""

    def test_conflict_with_asan(self):
        """Test that allocators conflict with AddressSanitizer."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()
        context.platform = "linux-x64"
        context.sanitizers.add("address")

        with pytest.raises(LayerConflictError, match="AddressSanitizer"):
            layer.apply(context)

    def test_conflict_with_tsan(self):
        """Test that allocators conflict with ThreadSanitizer."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()
        context.platform = "linux-x64"
        context.sanitizers.add("thread")

        with pytest.raises(LayerConflictError, match="ThreadSanitizer"):
            layer.apply(context)

    def test_conflict_with_msan(self):
        """Test that allocators conflict with MemorySanitizer."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()
        context.platform = "linux-x64"
        context.sanitizers.add("memory")

        with pytest.raises(LayerConflictError, match="MemorySanitizer"):
            layer.apply(context)

    def test_no_conflict_with_ubsan(self):
        """Test that allocators don't conflict with UBSan."""
        layer = AllocatorLayer("default", "default")
        context = LayerContext()
        context.platform = "linux-x64"
        context.sanitizers.add("undefined")

        # Should not raise
        layer.apply(context)


class TestDefaultAllocator:
    """Test default (system) allocator."""

    def test_default_allocator_no_config(self):
        """Test that default allocator needs no configuration."""
        layer = AllocatorLayer("default", "default")
        context = LayerContext()
        context.platform = "linux-x64"

        layer.apply(context)

        # No flags should be added
        assert len(context.link_flags) == 0
        assert len(context.runtime_env) == 0
        assert "allocator" in context.layer_types


class TestLibraryPatterns:
    """Test library pattern generation."""

    def test_jemalloc_linux_patterns(self):
        """Test jemalloc library patterns for Linux."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        patterns = layer._get_library_patterns("linux-x64")

        assert "libjemalloc.so" in patterns
        assert "libjemalloc.so.2" in patterns

    def test_jemalloc_macos_patterns(self):
        """Test jemalloc library patterns for macOS."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        patterns = layer._get_library_patterns("macos-x64")

        assert "libjemalloc.dylib" in patterns
        assert "libjemalloc.2.dylib" in patterns

    def test_jemalloc_windows_patterns(self):
        """Test jemalloc library patterns for Windows."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        patterns = layer._get_library_patterns("windows-x64")

        assert "jemalloc.lib" in patterns
        assert "jemalloc.dll" in patterns

    def test_tcmalloc_linux_patterns(self):
        """Test tcmalloc library patterns for Linux."""
        layer = AllocatorLayer("tcmalloc", "tcmalloc")
        patterns = layer._get_library_patterns("linux-x64")

        assert "libtcmalloc.so" in patterns

    def test_mimalloc_patterns(self):
        """Test mimalloc library patterns."""
        layer = AllocatorLayer("mimalloc", "mimalloc")

        linux_patterns = layer._get_library_patterns("linux-x64")
        assert "libmimalloc.so" in linux_patterns

        macos_patterns = layer._get_library_patterns("macos-arm64")
        assert "libmimalloc.dylib" in macos_patterns

        windows_patterns = layer._get_library_patterns("windows-x64")
        assert "mimalloc.lib" in windows_patterns


class TestSearchPaths:
    """Test library search paths."""

    def test_linux_search_paths(self):
        """Test Linux library search paths."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        paths = layer._get_search_paths("linux-x64")

        assert "/usr/lib" in paths
        assert "/usr/local/lib" in paths
        assert "/usr/lib/x86_64-linux-gnu" in paths

    def test_macos_search_paths(self):
        """Test macOS library search paths."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        paths = layer._get_search_paths("macos-x64")

        assert "/usr/local/lib" in paths
        assert "/opt/homebrew/lib" in paths
        assert "/usr/local/opt/jemalloc/lib" in paths

    def test_windows_search_paths(self):
        """Test Windows library search paths."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        paths = layer._get_search_paths("windows-x64")

        assert "C:\\Program Files" in paths
        assert "C:\\Program Files (x86)" in paths


class TestIntegrationMethodSelection:
    """Test integration method selection."""

    def test_auto_method_linux(self):
        """Test auto method selection on Linux."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="auto")
        context = LayerContext()
        context.platform = "linux-x64"

        method = layer._choose_integration_method(context)
        assert method == "link"

    def test_auto_method_windows(self):
        """Test auto method selection on Windows (no LD_PRELOAD)."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="auto")
        context = LayerContext()
        context.platform = "windows-x64"

        method = layer._choose_integration_method(context)
        assert method == "link"

    def test_explicit_link_method(self):
        """Test explicit link method."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="link")
        context = LayerContext()

        method = layer._choose_integration_method(context)
        assert method == "link"

    def test_explicit_ld_preload_method(self):
        """Test explicit ld_preload method."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="ld_preload")
        context = LayerContext()

        method = layer._choose_integration_method(context)
        assert method == "ld_preload"


class TestLinkMethod:
    """Test link integration method."""

    def test_link_method_adds_flag(self):
        """Test that link method adds linker flag."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()

        layer._apply_link_method(context)

        assert "-ljemalloc" in context.link_flags

    def test_link_method_different_allocators(self):
        """Test link method for different allocators."""
        allocators = ["jemalloc", "tcmalloc", "mimalloc", "tbbmalloc"]

        for alloc_name in allocators:
            layer = AllocatorLayer(alloc_name, alloc_name)
            context = LayerContext()

            layer._apply_link_method(context)

            expected_flag = f"-l{alloc_name}"
            assert expected_flag in context.link_flags


class TestLdPreloadMethod:
    """Test LD_PRELOAD integration method."""

    def test_ld_preload_sets_env_var(self):
        """Test that LD_PRELOAD method sets environment variable."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        layer._available_library = "/usr/lib/libjemalloc.so.2"
        context = LayerContext()

        layer._apply_ld_preload_method(context)

        assert "LD_PRELOAD" in context.runtime_env
        assert context.runtime_env["LD_PRELOAD"] == "/usr/lib/libjemalloc.so.2"

    def test_ld_preload_no_library(self):
        """Test LD_PRELOAD with no library detected."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        layer._available_library = None
        context = LayerContext()

        layer._apply_ld_preload_method(context)

        # Should not set LD_PRELOAD if library not found
        assert "LD_PRELOAD" not in context.runtime_env


class TestAllocatorNotFound:
    """Test behavior when allocator is not found."""

    @patch.object(AllocatorLayer, "_detect_allocator", return_value=False)
    def test_allocator_not_found_error(self, mock_detect):
        """Test that error is raised when allocator not found."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()
        context.platform = "linux-x64"

        with pytest.raises(LayerRequirementError, match="not found on system"):
            layer.apply(context)

    @patch.object(AllocatorLayer, "_detect_allocator", return_value=False)
    def test_error_message_includes_install_instructions(self, mock_detect):
        """Test that error message includes installation instructions."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        context = LayerContext()
        context.platform = "linux-x64"

        with pytest.raises(LayerRequirementError) as exc_info:
            layer.apply(context)

        error_msg = str(exc_info.value)
        assert "apt install" in error_msg or "brew install" in error_msg


# ============================================================================
# Integration Tests - Layer Composition
# ============================================================================


class TestAllocatorLayerComposition:
    """Test allocator layer composition with other layers."""

    @patch.object(AllocatorLayer, "_detect_allocator", return_value=True)
    def test_compose_with_basic_layers(self, mock_detect):
        """Test composing allocator with base layers."""
        # Test applying allocator layer directly (composer requires base layer)
        layer = AllocatorLayer("jemalloc", "jemalloc")
        layer._link_flags = ["-ljemalloc"]

        context = LayerContext()
        context.platform = "linux-x64"

        # Apply layer (mock will make detection succeed)
        layer.apply(context)

        assert "allocator" in context.layer_types
        assert layer in context.applied_layers
        assert "-ljemalloc" in context.link_flags

    @patch.object(AllocatorLayer, "_detect_allocator", return_value=True)
    def test_allocator_with_sanitizer_fails(self, mock_detect):
        """Test that allocator + sanitizer composition fails."""

        # Create context with sanitizer
        context = LayerContext()
        context.platform = "linux-x64"
        context.sanitizers.add("address")

        # Try to apply allocator
        layer = AllocatorLayer("jemalloc", "jemalloc")

        with pytest.raises(LayerConflictError):
            layer.apply(context)


# ============================================================================
# YAML Loading Tests
# ============================================================================


class TestAllocatorYAMLLoading:
    """Test loading allocator YAML files."""

    def test_load_jemalloc_yaml(self):
        """Test loading jemalloc.yaml."""
        data_dir = Path(__file__).parent.parent.parent / "toolchainkit" / "data"
        yaml_file = data_dir / "layers" / "allocator" / "jemalloc.yaml"

        if not yaml_file.exists():
            pytest.skip("jemalloc.yaml not found")

        import yaml

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert data["type"] == "allocator"
        assert data["name"] == "jemalloc"
        assert "link" in data
        assert "flags" in data["link"]

    def test_load_all_allocator_yamls(self):
        """Test loading all allocator YAML files."""
        data_dir = Path(__file__).parent.parent.parent / "toolchainkit" / "data"
        allocator_dir = data_dir / "layers" / "allocator"

        if not allocator_dir.exists():
            pytest.skip("allocator directory not found")

        allocators = [
            "jemalloc",
            "tcmalloc",
            "mimalloc",
            "snmalloc",
            "hoard",
            "nedmalloc",
            "tbbmalloc",
            "default",
        ]

        import yaml

        for allocator in allocators:
            yaml_file = allocator_dir / f"{allocator}.yaml"
            if not yaml_file.exists():
                continue

            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            assert data["type"] == "allocator"
            assert data["name"] == allocator
            assert "description" in data or "display_name" in data


# ============================================================================
# Platform-Specific Tests
# ============================================================================


@pytest.mark.skipif(not Path("/usr/lib").exists(), reason="Linux-specific test")
class TestLinuxAllocatorDetection:
    """Test allocator detection on Linux."""

    def test_detect_system_glibc(self):
        """Test detection of system glibc (always available)."""
        layer = AllocatorLayer("default", "default")
        context = LayerContext()
        context.platform = "linux-x64"

        # Default allocator should always work
        layer.apply(context)
        assert "allocator" in context.layer_types


@pytest.mark.skipif(not Path("/usr/local/lib").exists(), reason="macOS-specific test")
class TestMacOSAllocatorDetection:
    """Test allocator detection on macOS."""

    def test_macos_search_paths_exist(self):
        """Test that macOS search paths exist."""
        layer = AllocatorLayer("jemalloc", "jemalloc")
        paths = layer._get_search_paths("macos-x64")

        # At least one path should exist
        existing_paths = [p for p in paths if Path(p).exists()]
        assert len(existing_paths) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in allocator layers."""

    def test_invalid_method_still_works(self):
        """Test that invalid method defaults to auto."""
        layer = AllocatorLayer("jemalloc", "jemalloc", method="invalid")
        context = LayerContext()

        # Should not raise, method will be used as-is (might fail later)
        method = layer._choose_integration_method(context)
        # Invalid method returned as-is
        assert method == "invalid"

    @patch.object(AllocatorLayer, "_detect_allocator", return_value=True)
    def test_apply_tracks_layer(self, mock_detect):
        """Test that apply adds layer to context."""
        layer = AllocatorLayer("default", "default")
        context = LayerContext()
        context.platform = "linux-x64"

        layer.apply(context)

        assert layer in context.applied_layers
        assert "allocator" in context.layer_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
