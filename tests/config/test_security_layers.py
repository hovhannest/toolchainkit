"""Tests for SecurityLayer configuration."""

import pytest

from toolchainkit.config.layers import (
    SecurityLayer,
    LayerContext,
)


class TestSecurityLayerInit:
    """Test SecurityLayer initialization."""

    def test_init_stack_protector(self):
        """Test stack protector initialization."""
        layer = SecurityLayer(
            name="stack-protector-strong",
            security_type="stack_protector",
            level="strong",
        )
        assert layer.name == "stack-protector-strong"
        assert layer.layer_type == "security"
        assert layer.security_type == "stack_protector"
        assert layer.level == "strong"

    def test_init_fortify(self):
        """Test fortify initialization."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="2",
        )
        assert layer.name == "fortify"
        assert layer.security_type == "fortify"
        assert layer.level == "2"

    def test_init_with_description(self):
        """Test initialization with custom description."""
        layer = SecurityLayer(
            name="pie",
            security_type="pie",
            description="Custom PIE description",
        )
        assert layer.description == "Custom PIE description"

    def test_init_default_description(self):
        """Test default description generation."""
        layer = SecurityLayer(
            name="relro",
            security_type="relro",
            mode="full",
        )
        assert "relro" in layer.description.lower()


class TestStackProtector:
    """Test stack protector functionality."""

    def test_stack_protector_strong(self):
        """Test stack protector strong level."""
        layer = SecurityLayer(
            name="stack-protector-strong",
            security_type="stack_protector",
            level="strong",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fstack-protector-strong" in context.compile_flags

    def test_stack_protector_all(self):
        """Test stack protector all level."""
        layer = SecurityLayer(
            name="stack-protector-all",
            security_type="stack_protector",
            level="all",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fstack-protector-all" in context.compile_flags

    def test_stack_protector_basic(self):
        """Test stack protector basic level."""
        layer = SecurityLayer(
            name="stack-protector",
            security_type="stack_protector",
            level="basic",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fstack-protector" in context.compile_flags

    def test_stack_protector_none(self):
        """Test stack protector disabled."""
        layer = SecurityLayer(
            name="no-stack-protector",
            security_type="stack_protector",
            level="none",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fno-stack-protector" in context.compile_flags

    def test_stack_protector_default_level(self):
        """Test stack protector with default level (strong)."""
        layer = SecurityLayer(
            name="stack-protector",
            security_type="stack_protector",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fstack-protector-strong" in context.compile_flags

    def test_stack_protector_invalid_level(self):
        """Test stack protector with invalid level."""
        layer = SecurityLayer(
            name="stack-protector",
            security_type="stack_protector",
            level="invalid",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="Invalid stack protector level"):
            layer.apply(context)


class TestFortify:
    """Test fortify source functionality."""

    def test_fortify_level_0(self):
        """Test fortify level 0 (disabled)."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="0",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=0" in context.compile_flags
        # Level 0 shouldn't add optimization
        assert not any("-O" in f for f in context.compile_flags)

    def test_fortify_level_1(self):
        """Test fortify level 1."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="1",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=1" in context.compile_flags
        assert "-O2" in context.compile_flags

    def test_fortify_level_2(self):
        """Test fortify level 2."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="2",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=2" in context.compile_flags
        assert "-O2" in context.compile_flags

    def test_fortify_level_3(self):
        """Test fortify level 3 (GCC 12+)."""
        layer = SecurityLayer(
            name="fortify-3",
            security_type="fortify",
            level="3",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=3" in context.compile_flags
        assert "-O2" in context.compile_flags

    def test_fortify_default_level(self):
        """Test fortify with default level (2)."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=2" in context.compile_flags

    def test_fortify_with_existing_optimization(self):
        """Test fortify doesn't add -O2 if optimization already present."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="2",
        )
        context = LayerContext()
        context.compile_flags.append("-O3")
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=2" in context.compile_flags
        # Should not add -O2 since -O3 is already present
        assert context.compile_flags.count("-O2") == 0
        assert "-O3" in context.compile_flags

    def test_fortify_invalid_level(self):
        """Test fortify with invalid level."""
        layer = SecurityLayer(
            name="fortify",
            security_type="fortify",
            level="5",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="Invalid fortify level"):
            layer.apply(context)


class TestRELRO:
    """Test RELRO functionality."""

    def test_relro_full(self):
        """Test full RELRO."""
        layer = SecurityLayer(
            name="relro-full",
            security_type="relro",
            mode="full",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-Wl,-z,relro,-z,now" in context.link_flags

    def test_relro_partial(self):
        """Test partial RELRO."""
        layer = SecurityLayer(
            name="relro-partial",
            security_type="relro",
            mode="partial",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-Wl,-z,relro" in context.link_flags

    def test_relro_none(self):
        """Test RELRO disabled."""
        layer = SecurityLayer(
            name="no-relro",
            security_type="relro",
            mode="none",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-Wl,-z,norelro" in context.link_flags

    def test_relro_default_mode(self):
        """Test RELRO with default mode (full)."""
        layer = SecurityLayer(
            name="relro",
            security_type="relro",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-Wl,-z,relro,-z,now" in context.link_flags

    def test_relro_invalid_mode(self):
        """Test RELRO with invalid mode."""
        layer = SecurityLayer(
            name="relro",
            security_type="relro",
            mode="invalid",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="Invalid RELRO mode"):
            layer.apply(context)


class TestPIE:
    """Test PIE functionality."""

    def test_pie_basic(self):
        """Test basic PIE configuration."""
        layer = SecurityLayer(
            name="pie",
            security_type="pie",
        )
        context = LayerContext()
        layer.apply(context)

        assert "-fPIE" in context.compile_flags
        assert "-pie" in context.link_flags

    def test_pie_no_duplicates(self):
        """Test PIE doesn't add duplicate flags."""
        layer = SecurityLayer(
            name="pie",
            security_type="pie",
        )
        context = LayerContext()
        context.compile_flags.append("-fPIE")
        layer.apply(context)

        assert context.compile_flags.count("-fPIE") == 1
        assert "-pie" in context.link_flags


class TestStackSize:
    """Test stack size functionality."""

    def test_stack_size_basic(self):
        """Test stack size configuration."""
        layer = SecurityLayer(
            name="stack-size",
            security_type="stack_size",
            stack_size=1048576,  # 1MB
        )
        context = LayerContext()
        layer.apply(context)

        assert "-Wl,-z,stack-size=1048576" in context.link_flags

    def test_stack_size_missing(self):
        """Test stack size without value raises error."""
        layer = SecurityLayer(
            name="stack-size",
            security_type="stack_size",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="stack_size must be specified"):
            layer.apply(context)


class TestHardenedProfile:
    """Test hardened composite profile."""

    def test_hardened_basic(self):
        """Test hardened profile applies all security features."""
        layer = SecurityLayer(
            name="hardened",
            security_type="hardened",
        )
        context = LayerContext()
        layer.apply(context)

        # Check compile flags
        assert "-fstack-protector-strong" in context.compile_flags
        assert "-D_FORTIFY_SOURCE=2" in context.compile_flags
        assert "-O2" in context.compile_flags
        assert "-fPIE" in context.compile_flags

        # Check link flags
        assert "-Wl,-z,relro,-z,now" in context.link_flags
        assert "-pie" in context.link_flags

    def test_hardened_with_existing_optimization(self):
        """Test hardened respects existing optimization."""
        layer = SecurityLayer(
            name="hardened",
            security_type="hardened",
        )
        context = LayerContext()
        context.compile_flags.append("-O3")
        layer.apply(context)

        assert "-D_FORTIFY_SOURCE=2" in context.compile_flags
        # Should not add -O2 since -O3 is already present
        assert context.compile_flags.count("-O2") == 0

    def test_hardened_no_duplicates(self):
        """Test hardened doesn't add duplicate flags."""
        layer = SecurityLayer(
            name="hardened",
            security_type="hardened",
        )
        context = LayerContext()
        context.compile_flags.append("-fPIE")
        context.link_flags.append("-pie")
        layer.apply(context)

        assert context.compile_flags.count("-fPIE") == 1
        assert context.link_flags.count("-pie") == 1


class TestInvalidSecurityType:
    """Test invalid security types."""

    def test_unknown_security_type(self):
        """Test unknown security type raises error."""
        layer = SecurityLayer(
            name="unknown",
            security_type="unknown_type",
        )
        context = LayerContext()

        with pytest.raises(ValueError, match="Unknown security type"):
            layer.apply(context)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
