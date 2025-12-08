from pathlib import Path
from unittest.mock import MagicMock
from toolchainkit.toolchain.strategies.standard import ClangStrategy


def test_clang_strategy_windows_rc_compiler():
    strategy = ClangStrategy()
    toolchain_root = Path("/path/to/toolchain")
    platform = MagicMock()
    platform.os = "windows"

    paths = strategy.get_compiler_paths(toolchain_root, platform)

    assert "CMAKE_RC_COMPILER" in paths
    assert paths["CMAKE_RC_COMPILER"].endswith("llvm-rc.exe")
    assert "CMAKE_C_COMPILER" in paths
    assert paths["CMAKE_C_COMPILER"].endswith("clang.exe")
    assert "CMAKE_CXX_COMPILER" in paths
    assert paths["CMAKE_CXX_COMPILER"].endswith("clang++.exe")


def test_clang_strategy_linux_no_rc_compiler():
    strategy = ClangStrategy()
    toolchain_root = Path("/path/to/toolchain")
    platform = MagicMock()
    platform.os = "linux"

    paths = strategy.get_compiler_paths(toolchain_root, platform)

    assert "CMAKE_RC_COMPILER" not in paths
    assert "CMAKE_C_COMPILER" in paths
    assert paths["CMAKE_C_COMPILER"].endswith("clang")
