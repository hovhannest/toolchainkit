"""Smoke tests to verify link validation infrastructure."""

import pytest


@pytest.mark.link_validation
def test_validation_level_fixture(validation_level):
    """Verify validation level fixture works."""
    assert validation_level in ["head", "partial", "full"]


@pytest.mark.link_validation
def test_cache_dir_fixture(validation_cache_dir):
    """Verify cache directory fixture works."""
    assert validation_cache_dir.exists()
    assert validation_cache_dir.is_dir()


@pytest.mark.link_validation
@pytest.mark.link_validation_slow
def test_marker_combination():
    """Test can have multiple markers."""
    assert True
