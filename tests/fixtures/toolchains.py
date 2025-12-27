"""Reusable toolchain fixtures for testing.

This module provides pytest fixtures that create mock toolchain directory structures
for testing toolchain-related functionality without requiring actual compiler installations.
"""

import platform
import pytest
from pathlib import Path
from typing import Dict


@pytest.fixture
def mock_llvm_toolchain(tmp_path) -> Path:
    """
    Create mock LLVM toolchain directory structure.

    Creates a realistic LLVM/Clang toolchain directory with:
    - bin/clang, bin/clang++, bin/llvm-ar
    - lib/libc++.a, lib/libc++abi.a
    - include/c++/v1/

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to toolchain root directory

    Example:
        def test_llvm_detection(mock_llvm_toolchain):
            assert (mock_llvm_toolchain / "bin" / "clang").exists()
            assert (mock_llvm_toolchain / "lib" / "libc++.a").exists()
    """
    toolchain_root = tmp_path / "llvm-18.1.8"
    toolchain_root.mkdir()

    # Create bin directory with executables
    bin_dir = toolchain_root / "bin"
    bin_dir.mkdir()

    if platform.system() == "Windows":
        # Windows uses clang-cl (MSVC-compatible driver)
        executables = [
            "clang-cl",
            "clang",
            "clang++",
            "clang-format",
            "llvm-ar",
            "llvm-lib",
            "lld",
            "lld-link",
        ]
        exe_ext = ".exe"
    else:
        executables = ["clang", "clang++", "clang-format", "llvm-ar", "lld", "ld.lld"]
        exe_ext = ""

    for executable in executables:
        exe_path = bin_dir / f"{executable}{exe_ext}"
        exe_path.write_text(f"#!/bin/bash\necho {executable} mock\n")
        if platform.system() != "Windows":
            exe_path.chmod(0o755)

    # Create lib directory with standard library files
    lib_dir = toolchain_root / "lib"
    lib_dir.mkdir()
    (lib_dir / "libc++.a").write_bytes(b"mock library content")
    (lib_dir / "libc++abi.a").write_bytes(b"mock library content")

    # Create include directory with C++ standard library headers
    include_dir = toolchain_root / "include" / "c++" / "v1"
    include_dir.mkdir(parents=True)
    (include_dir / "iostream").write_text("#pragma once\n// Mock iostream header\n")
    (include_dir / "vector").write_text("#pragma once\n// Mock vector header\n")
    (include_dir / "string").write_text("#pragma once\n// Mock string header\n")

    return toolchain_root


@pytest.fixture
def mock_gcc_toolchain(tmp_path) -> Path:
    """
    Create mock GCC toolchain directory structure.

    Creates a realistic GCC toolchain directory with:
    - bin/gcc, bin/g++, bin/ar
    - lib64/libstdc++.a
    - include/c++/13.2.0/

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to toolchain root directory

    Example:
        def test_gcc_detection(mock_gcc_toolchain):
            assert (mock_gcc_toolchain / "bin" / "gcc").exists()
            assert (mock_gcc_toolchain / "lib64" / "libstdc++.a").exists()
    """
    toolchain_root = tmp_path / "gcc-13.2.0"
    toolchain_root.mkdir()

    # Create bin directory with executables
    bin_dir = toolchain_root / "bin"
    bin_dir.mkdir()

    exe_ext = ".exe" if platform.system() == "Windows" else ""
    for executable in ["gcc", "g++", "ar", "as", "ld"]:
        exe_path = bin_dir / f"{executable}{exe_ext}"
        exe_path.write_text(f"#!/bin/bash\necho {executable} mock\n")
        if platform.system() != "Windows":
            exe_path.chmod(0o755)

    # Create lib64 directory with standard library files
    lib_dir = toolchain_root / "lib64"
    lib_dir.mkdir()
    (lib_dir / "libstdc++.a").write_bytes(b"mock library content")
    (lib_dir / "libgcc.a").write_bytes(b"mock library content")

    # Create include directory with C++ standard library headers
    include_dir = toolchain_root / "include" / "c++" / "13.2.0"
    include_dir.mkdir(parents=True)
    (include_dir / "iostream").write_text("#pragma once\n// Mock iostream header\n")
    (include_dir / "vector").write_text("#pragma once\n// Mock vector header\n")
    (include_dir / "string").write_text("#pragma once\n// Mock string header\n")

    return toolchain_root


@pytest.fixture
def mock_msvc_toolchain(tmp_path) -> Path:
    """
    Create mock MSVC toolchain directory structure.

    Creates a realistic MSVC toolchain directory with:
    - bin/Hostx64/x64/cl.exe, link.exe, lib.exe
    - lib/x64/msvcrt.lib
    - include/vcruntime.h

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to toolchain root directory

    Example:
        def test_msvc_detection(mock_msvc_toolchain):
            assert (mock_msvc_toolchain / "bin" / "Hostx64" / "x64" / "cl.exe").exists()
    """
    toolchain_root = tmp_path / "msvc-19.38"
    toolchain_root.mkdir()

    # Create bin directory with executables (MSVC structure)
    bin_dir = toolchain_root / "bin" / "Hostx64" / "x64"
    bin_dir.mkdir(parents=True)

    for executable in ["cl.exe", "link.exe", "lib.exe", "ml64.exe"]:
        exe_path = bin_dir / executable
        exe_path.write_text(f"REM {executable} mock\n")

    # Create lib directory
    lib_dir = toolchain_root / "lib" / "x64"
    lib_dir.mkdir(parents=True)
    (lib_dir / "msvcrt.lib").write_bytes(b"mock library content")
    (lib_dir / "msvcprt.lib").write_bytes(b"mock library content")

    # Create include directory
    include_dir = toolchain_root / "include"
    include_dir.mkdir()
    (include_dir / "vcruntime.h").write_text("#pragma once\n// Mock vcruntime header\n")
    (include_dir / "iostream").write_text("#pragma once\n// Mock iostream header\n")
    (include_dir / "vector").write_text("#pragma once\n// Mock vector header\n")

    return toolchain_root


@pytest.fixture
def mock_toolchain_metadata() -> Dict:
    """
    Create mock toolchain metadata dictionary.

    Returns a dictionary with realistic toolchain metadata suitable for testing
    metadata parsing, validation, and download operations.

    Returns:
        Dict containing toolchain metadata

    Example:
        def test_metadata_parsing(mock_toolchain_metadata):
            assert mock_toolchain_metadata['url'].startswith('https://')
            assert len(mock_toolchain_metadata['sha256']) == 64
    """
    return {
        "name": "llvm",
        "version": "18.1.8",
        "platform": "linux-x64",
        "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-linux-gnu-ubuntu-18.04.tar.xz",
        "sha256": "a3d5f6e8b9c4d1f2a7b8c3e9f4d5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3",
        "size_mb": 1024,
        "stdlib": ["libc++", "libstdc++"],
        "compilers": ["clang", "clang++"],
        "requires": {"cmake": ">=3.20", "python": ">=3.8"},
    }
