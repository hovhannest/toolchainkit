"""Tests for ProfilingLayer configuration."""

import pytest

from toolchainkit.config.layers import (
    ProfilingLayer,
    LayerContext,
)


class TestProfilingLayerInit:
    """Test ProfilingLayer initialization."""

    def test_init_gprof(self):
        """Test gprof initialization."""
        layer = ProfilingLayer(
            name="gprof",
            profiling_type="gprof",
        )
        assert layer.name == "gprof"
        assert layer.layer_type == "profiling"
        assert layer.profiling_type == "gprof"

    def test_init_instrument_functions(self):
        """Test instrument-functions initialization."""
        layer = ProfilingLayer(
            name="instrument-functions",
            profiling_type="instrument_functions",
        )
        assert layer.name == "instrument-functions"
        assert layer.profiling_type == "instrument_functions"

    def test_init_with_description(self):
        """Test initialization with custom description."""
        layer = ProfilingLayer(
            name="perf",
            profiling_type="perf",
            description="Custom perf description",
        )
        assert layer.description == "Custom perf description"

    def test_init_default_description(self):
        """Test default description generation."""
        layer = ProfilingLayer(
            name="gprof",
            profiling_type="gprof",
        )
        assert "gprof" in layer.description.lower()


class TestGprof:
    """Test gprof profiling functionality."""

    def test_gprof_basic(self):
        """Test basic gprof configuration."""
        layer = ProfilingLayer(
            name="gprof",
            profiling_type="gprof",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-pg" in context.compile_flags
        assert "-pg" in context.link_flags

    def test_gprof_no_duplicates(self):
        """Test gprof doesn't add duplicate flags."""
        layer = ProfilingLayer(
            name="gprof",
            profiling_type="gprof",
        )
        context = LayerContext()
        context.compile_flags.append("-pg")
        layer.apply(context)

        assert context.compile_flags.count("-pg") == 1
        assert "-pg" in context.link_flags


class TestInstrumentFunctions:
    """Test function instrumentation functionality."""

    def test_instrument_functions_basic(self):
        """Test basic function instrumentation."""
        layer = ProfilingLayer(
            name="instrument-functions",
            profiling_type="instrument_functions",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-finstrument-functions" in context.compile_flags

    def test_instrument_functions_no_duplicates(self):
        """Test instrument-functions doesn't add duplicate flags."""
        layer = ProfilingLayer(
            name="instrument-functions",
            profiling_type="instrument_functions",
        )
        context = LayerContext()
        context.compile_flags.append("-finstrument-functions")
        layer.apply(context)

        assert context.compile_flags.count("-finstrument-functions") == 1


class TestAsanProfile:
    """Test ASan profiling functionality."""

    def test_asan_profile_basic(self):
        """Test ASan profiling with ASan already enabled."""
        layer = ProfilingLayer(
            name="asan-profile",
            profiling_type="asan_profile",
        )
        context = LayerContext()
        # Simulate ASan being enabled
        context.compile_flags.append("-fsanitize=address")
        layer.apply(context)

        assert "-fsanitize-address-use-after-scope" in context.compile_flags

    def test_asan_profile_without_asan(self):
        """Test ASan profiling without ASan raises error."""
        layer = ProfilingLayer(
            name="asan-profile",
            profiling_type="asan_profile",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="requires AddressSanitizer"):
            layer.apply(context)

    def test_asan_profile_no_duplicates(self):
        """Test ASan profiling doesn't add duplicate flags."""
        layer = ProfilingLayer(
            name="asan-profile",
            profiling_type="asan_profile",
        )
        context = LayerContext()
        context.compile_flags.append("-fsanitize=address")
        context.compile_flags.append("-fsanitize-address-use-after-scope")
        layer.apply(context)

        assert context.compile_flags.count("-fsanitize-address-use-after-scope") == 1


class TestPerf:
    """Test perf profiling functionality."""

    def test_perf_basic(self):
        """Test basic perf configuration."""
        layer = ProfilingLayer(
            name="perf",
            profiling_type="perf",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fno-omit-frame-pointer" in context.compile_flags
        assert "-g" in context.compile_flags

    def test_perf_no_duplicates(self):
        """Test perf doesn't add duplicate flags."""
        layer = ProfilingLayer(
            name="perf",
            profiling_type="perf",
        )
        context = LayerContext()
        context.compile_flags.append("-fno-omit-frame-pointer")
        context.compile_flags.append("-g")
        layer.apply(context)

        assert context.compile_flags.count("-fno-omit-frame-pointer") == 1
        assert context.compile_flags.count("-g") == 1

    def test_perf_with_existing_debug_info(self):
        """Test perf respects existing debug info flags."""
        layer = ProfilingLayer(
            name="perf",
            profiling_type="perf",
        )
        context = LayerContext()
        context.compile_flags.append("-g3")  # More detailed debug info
        layer.apply(context)

        assert "-fno-omit-frame-pointer" in context.compile_flags
        # Should not add -g since -g3 is already present
        assert context.compile_flags.count("-g") == 0
        assert "-g3" in context.compile_flags


class TestInvalidProfilingType:
    """Test invalid profiling types."""

    def test_unknown_profiling_type(self):
        """Test unknown profiling type raises error."""
        layer = ProfilingLayer(
            name="unknown",
            profiling_type="unknown_type",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="Unknown profiling type"):
            layer.apply(context)


class TestProfilingLayerComposition:
    """Test profiling layer composition scenarios."""

    def test_multiple_profiling_layers_conceptually(self):
        """Test applying multiple profiling layers (conceptually conflicting)."""
        # Note: In reality, users should use only one profiling layer
        # but technically they can be applied if needed
        gprof = ProfilingLayer(name="gprof", profiling_type="gprof")
        perf = ProfilingLayer(name="perf", profiling_type="perf")

        context = LayerContext()
        gprof.apply(context)
        perf.apply(context)

        # Both should be applied (conflict detection would be in composer)
        assert "-pg" in context.compile_flags
        assert "-pg" in context.link_flags
        assert "-fno-omit-frame-pointer" in context.compile_flags
        assert "-g" in context.compile_flags

    def test_profiling_with_optimization(self):
        """Test profiling layers work with optimization flags."""
        layer = ProfilingLayer(name="gprof", profiling_type="gprof")
        context = LayerContext()
        context.compile_flags.extend(["-O2", "-march=native"])
        layer.apply(context)

        assert "-pg" in context.compile_flags
        assert "-O2" in context.compile_flags
        assert "-march=native" in context.compile_flags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
