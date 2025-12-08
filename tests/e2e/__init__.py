"""
End-to-End test suite for ToolchainKit.

This package contains E2E tests that verify complete workflows and system integration.
Tests are designed to work with both Python API and CLI (when implemented).

Test categories:
- Smoke tests: Fast sanity checks to catch obvious breakage
- API workflows: Complete workflows using Python API
- Error recovery: Error handling and edge cases

Run E2E tests with:
    pytest tests/e2e/ -m e2e -v

Run only smoke tests:
    pytest tests/e2e/ -m smoke -v
"""
