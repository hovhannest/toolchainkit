import unittest
from unittest.mock import MagicMock

from toolchainkit.toolchain.providers import DownloadToolchainProvider


class TestDownloadToolchainProvider(unittest.TestCase):
    def setUp(self):
        self.mock_downloader = MagicMock()
        self.mock_registry = MagicMock()
        self.mock_downloader.metadata_registry = self.mock_registry
        self.provider = DownloadToolchainProvider(self.mock_downloader)

    def test_can_provide_returns_true_for_valid_toolchain(self):
        # Setup mock to simulate valid toolchain
        self.mock_registry.list_toolchains.return_value = ["llvm"]
        self.mock_registry.resolve_version.return_value = "18.1.8"

        # Verify
        result = self.provider.can_provide("llvm", "18")
        self.assertTrue(result)

        # Verify calls
        self.mock_registry.list_toolchains.assert_called_once()
        self.mock_registry.resolve_version.assert_called_with("llvm", "18")

    def test_can_provide_returns_false_for_invalid_toolchain(self):
        # Setup mock to simulate unknown toolchain
        self.mock_registry.list_toolchains.return_value = ["gcc"]

        # Verify
        result = self.provider.can_provide("llvm", "18")
        self.assertFalse(result)

    def test_can_provide_returns_false_for_invalid_version(self):
        # Setup mock to simulate valid toolchain but invalid version
        self.mock_registry.list_toolchains.return_value = ["llvm"]
        self.mock_registry.resolve_version.return_value = None

        # Verify
        result = self.provider.can_provide("llvm", "99")
        self.assertFalse(result)

    def test_can_provide_handles_exceptions(self):
        # Setup mock to raise exception
        self.mock_registry.list_toolchains.side_effect = Exception("Registry error")

        # Verify
        result = self.provider.can_provide("llvm", "18")
        self.assertFalse(result)
