"""
Unit tests for toolchain verification module.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from toolchainkit.core.platform import PlatformInfo
from toolchainkit.toolchain.verifier import (
    VerificationLevel,
    VerificationResult,
    ToolchainSpec,
    FilePresenceCheck,
    SymlinkCheck,
    ExecutabilityCheck,
    VersionCheck,
    ABICheck,
    CompileTestCheck,
    ToolchainVerifier,
    verify_toolchain,
)


# Fixtures


import sys

# ... (existing imports)

# Fixtures


@pytest.fixture
def linux_platform():
    """Create Linux platform info."""
    return PlatformInfo(
        os="linux",
        arch="x64",
        os_version="5.15.0",
        distribution="ubuntu",
        abi="glibc-2.31",
    )


@pytest.fixture
def windows_platform():
    """Create Windows platform info."""
    return PlatformInfo(
        os="windows", arch="x64", os_version="10.0.19045", distribution="", abi="msvc"
    )


@pytest.fixture
def host_platform(linux_platform, windows_platform):
    """Return platform info matching the host OS."""
    if sys.platform == "win32":
        return windows_platform
    return linux_platform


@pytest.fixture
def llvm_spec():
    """Create LLVM toolchain spec."""
    return ToolchainSpec(
        id="llvm-18.1.8-linux-x64", name="LLVM", version="18.1.8", type="llvm"
    )


@pytest.fixture
def gcc_spec():
    """Create GCC toolchain spec."""
    return ToolchainSpec(
        id="gcc-13.2.0-linux-x64", name="GCC", version="13.2.0", type="gcc"
    )


@pytest.fixture
def msvc_spec():
    """Create MSVC toolchain spec."""
    return ToolchainSpec(
        id="msvc-2022-windows-x64", name="MSVC", version="19.38", type="msvc"
    )


# ... (TestCheckResult and TestVerificationResult classes unchanged)


# Test FilePresenceCheck


class TestFilePresenceCheck:
    def test_llvm_files_present(self, mock_llvm_toolchain, host_platform, llvm_spec):
        """
        Test LLVM file presence check using fixture.

        Uses host_platform to match the executables created by the fixture
        (which uses platform.system() to decide on .exe extension).
        """
        check = FilePresenceCheck(host_platform)
        result = check.check(mock_llvm_toolchain, llvm_spec)

        assert result.passed is True
        assert "expected files present" in result.message

    def test_llvm_files_missing(self, tmp_path, linux_platform, llvm_spec):
        """Test LLVM file presence check with missing files."""
        # Create only partial files
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "clang").touch()
        # Missing clang++ and lld

        check = FilePresenceCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "Missing" in result.message
        assert len(result.details["missing_files"]) == 2

    def test_gcc_files_present(self, mock_gcc_toolchain, host_platform, gcc_spec):
        """
        Test GCC file presence check using fixture.

        Fixture provides realistic GCC structure instead of minimal touch() setup.
        Uses host_platform to match the executables created by the fixture.
        """
        check = FilePresenceCheck(host_platform)
        result = check.check(mock_gcc_toolchain, gcc_spec)

        assert result.passed is True
        assert "expected files present" in result.message

    def test_gcc_files_partial(self, tmp_path, linux_platform, gcc_spec):
        """Test GCC file presence check with partial files."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "gcc").touch()
        (bin_dir / "g++").touch()
        (bin_dir / "ld").touch()

        check = FilePresenceCheck(linux_platform)
        result = check.check(tmp_path, gcc_spec)

        assert result.passed is True

    def test_msvc_files_present(self, tmp_path, windows_platform, msvc_spec):
        """Test MSVC file presence check."""
        bin_dir = tmp_path / "bin" / "Hostx64" / "x64"
        bin_dir.mkdir(parents=True)
        (bin_dir / "cl.exe").touch()
        (bin_dir / "link.exe").touch()

        check = FilePresenceCheck(windows_platform)
        result = check.check(tmp_path, msvc_spec)

        assert result.passed is True

    def test_windows_exe_extension(self, tmp_path, windows_platform, llvm_spec):
        """Test that .exe extension is expected on Windows."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "clang.exe").touch()
        (bin_dir / "clang++.exe").touch()
        (bin_dir / "lld.exe").touch()

        check = FilePresenceCheck(windows_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True


# Test SymlinkCheck


class TestSymlinkCheck:
    def test_no_symlinks(self, tmp_path, llvm_spec):
        """Test symlink check with no symlinks."""
        (tmp_path / "bin").mkdir()
        (tmp_path / "bin" / "clang").touch()

        check = SymlinkCheck()
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True

    def test_valid_symlinks(self, tmp_path, llvm_spec):
        """Test symlink check with valid symlinks."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        target = bin_dir / "clang"
        target.touch()

        # Create symlink
        link = bin_dir / "clang-18"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

        check = SymlinkCheck()
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True

    def test_broken_symlinks(self, tmp_path, llvm_spec):
        """Test symlink check with broken symlinks."""
        import os

        # Skip test on Windows since symlink checks are skipped there
        if os.name == "nt":
            pytest.skip("Symlink check is skipped on Windows")

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create symlink to non-existent target
        link = bin_dir / "broken-link"
        nonexistent = bin_dir / "nonexistent"
        try:
            link.symlink_to(nonexistent)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

        check = SymlinkCheck()
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "broken symlink" in result.message.lower()


# Test ExecutabilityCheck


class TestExecutabilityCheck:
    @patch("subprocess.run")
    def test_compiler_executable(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test compiler executability check - success."""
        # Setup
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()
        compiler.chmod(0o755)

        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0, stdout="clang version 18.1.8")

        check = ExecutabilityCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True
        assert "executable" in result.message.lower()
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_compiler_not_found(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test compiler executability check - not found."""
        check = ExecutabilityCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "not found" in result.message.lower()

    @patch("subprocess.run")
    def test_compiler_fails_to_run(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test compiler executability check - execution fails."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock subprocess failure
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        check = ExecutabilityCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "exited with code 1" in result.message

    @patch("subprocess.run")
    def test_compiler_timeout(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test compiler executability check - timeout."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("clang++", 10)

        check = ExecutabilityCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "timed out" in result.message.lower()


# Test VersionCheck


class TestVersionCheck:
    @patch("subprocess.run")
    def test_version_matches(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test version check - version matches."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock version output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="clang version 18.1.8\nTarget: x86_64-unknown-linux-gnu",
        )

        check = VersionCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True
        assert "18.1.8" in result.message

    @patch("subprocess.run")
    def test_version_mismatch(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test version check - version doesn't match."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock different version
        mock_run.return_value = MagicMock(returncode=0, stdout="clang version 17.0.6")

        check = VersionCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "Expected version" in result.message

    @patch("subprocess.run")
    def test_gcc_version_check(self, mock_run, tmp_path, linux_platform, gcc_spec):
        """Test version check for GCC."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "g++"
        compiler.touch()

        mock_run.return_value = MagicMock(returncode=0, stdout="g++ (GCC) 13.2.0")

        check = VersionCheck(linux_platform)
        result = check.check(tmp_path, gcc_spec)

        assert result.passed is True


# Test ABICheck


class TestABICheck:
    def test_llvm_libraries_present_linux(self, tmp_path, linux_platform, llvm_spec):
        """Test ABI check for LLVM on Linux."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libc++.a").touch()

        check = ABICheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True

    def test_llvm_libraries_missing(self, tmp_path, linux_platform, llvm_spec):
        """Test ABI check with missing libraries."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        # No libraries

        check = ABICheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "Missing" in result.message

    def test_gcc_libraries_present(self, tmp_path, linux_platform, gcc_spec):
        """Test ABI check for GCC."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "libstdc++.a").touch()
        (lib_dir / "libgcc.a").touch()

        check = ABICheck(linux_platform)
        result = check.check(tmp_path, gcc_spec)

        assert result.passed is True

    def test_msvc_abi_check_skipped(self, tmp_path, windows_platform, msvc_spec):
        """Test ABI check is skipped for MSVC."""
        # Create lib directory so check doesn't fail early
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        check = ABICheck(windows_platform)
        result = check.check(tmp_path, msvc_spec)

        assert result.passed is True
        assert "skipped" in result.message.lower()


# Test CompileTestCheck


class TestCompileTestCheck:
    @patch("subprocess.run")
    def test_compile_test_success(self, mock_run, tmp_path, linux_platform, llvm_spec):
        """Test compile test - success."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock compilation and execution
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "--version" in " ".join(str(c) for c in cmd):
                return MagicMock(returncode=0, stdout="clang version 18.1.8")
            elif any("test.cpp" in str(c) for c in cmd):
                # Compilation - create output file
                return MagicMock(returncode=0, stdout="", stderr="")
            else:
                # Execution
                return MagicMock(returncode=0, stdout="Hello from ToolchainKit!\n")

        mock_run.side_effect = run_side_effect

        check = CompileTestCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is True
        assert "Successfully compiled" in result.message

    @patch("subprocess.run")
    def test_compile_test_compilation_fails(
        self, mock_run, tmp_path, linux_platform, llvm_spec
    ):
        """Test compile test - compilation fails."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock compilation failure
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if any("test.cpp" in str(c) for c in cmd):
                return MagicMock(returncode=1, stderr="error: undeclared identifier")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect

        check = CompileTestCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "Compilation failed" in result.message

    @patch("subprocess.run")
    def test_compile_test_runtime_fails(
        self, mock_run, tmp_path, linux_platform, llvm_spec
    ):
        """Test compile test - runtime fails."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()

        # Mock successful compilation but runtime failure
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if any("test.cpp" in str(c) for c in cmd):
                return MagicMock(returncode=0, stdout="", stderr="")
            else:
                # Runtime failure
                return MagicMock(returncode=1, stderr="Segmentation fault")

        mock_run.side_effect = run_side_effect

        check = CompileTestCheck(linux_platform)
        result = check.check(tmp_path, llvm_spec)

        assert result.passed is False
        assert "failed to run" in result.message.lower()


# Test ToolchainVerifier


class TestToolchainVerifier:
    def test_verification_levels(self, linux_platform):
        """Test that all verification levels are defined."""
        verifier = ToolchainVerifier(linux_platform)

        assert VerificationLevel.MINIMAL in verifier.all_checks
        assert VerificationLevel.STANDARD in verifier.all_checks
        assert VerificationLevel.THOROUGH in verifier.all_checks
        assert VerificationLevel.PARANOID in verifier.all_checks

    def test_minimal_checks(self, linux_platform):
        """Test MINIMAL level has correct checks."""
        verifier = ToolchainVerifier(linux_platform)
        checks = verifier.all_checks[VerificationLevel.MINIMAL]

        assert len(checks) == 1
        assert isinstance(checks[0], FilePresenceCheck)

    def test_standard_checks(self, linux_platform):
        """Test STANDARD level has correct checks."""
        verifier = ToolchainVerifier(linux_platform)
        checks = verifier.all_checks[VerificationLevel.STANDARD]

        assert len(checks) == 3
        assert any(isinstance(c, FilePresenceCheck) for c in checks)
        assert any(isinstance(c, ExecutabilityCheck) for c in checks)
        assert any(isinstance(c, VersionCheck) for c in checks)

    def test_thorough_checks(self, linux_platform):
        """Test THOROUGH level has correct checks."""
        verifier = ToolchainVerifier(linux_platform)
        checks = verifier.all_checks[VerificationLevel.THOROUGH]

        assert len(checks) == 5
        assert any(isinstance(c, ABICheck) for c in checks)
        assert any(isinstance(c, SymlinkCheck) for c in checks)

    def test_paranoid_checks(self, linux_platform):
        """Test PARANOID level has correct checks."""
        verifier = ToolchainVerifier(linux_platform)
        checks = verifier.all_checks[VerificationLevel.PARANOID]

        assert len(checks) == 6
        assert any(isinstance(c, CompileTestCheck) for c in checks)

    def test_verify_minimal_success(self, tmp_path, linux_platform, llvm_spec):
        """Test verification at MINIMAL level - success."""
        # Create expected files
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "clang").touch()
        (bin_dir / "clang++").touch()
        (bin_dir / "lld").touch()

        verifier = ToolchainVerifier(linux_platform)
        result = verifier.verify(tmp_path, llvm_spec, VerificationLevel.MINIMAL)

        assert result.success is True
        assert len(result.checks_passed) == 1
        assert len(result.checks_failed) == 0

    def test_verify_minimal_failure(self, tmp_path, linux_platform, llvm_spec):
        """Test verification at MINIMAL level - failure."""
        # Missing files
        verifier = ToolchainVerifier(linux_platform)
        result = verifier.verify(tmp_path, llvm_spec, VerificationLevel.MINIMAL)

        assert result.success is False
        assert len(result.checks_failed) >= 1
        assert len(result.errors) >= 1

    @patch("subprocess.run")
    def test_verify_standard_success(
        self, mock_run, tmp_path, linux_platform, llvm_spec
    ):
        """Test verification at STANDARD level - success."""
        # Create files
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        compiler = bin_dir / "clang++"
        compiler.touch()
        (bin_dir / "clang").touch()
        (bin_dir / "lld").touch()

        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0, stdout="clang version 18.1.8")

        verifier = ToolchainVerifier(linux_platform)
        result = verifier.verify(tmp_path, llvm_spec, VerificationLevel.STANDARD)

        assert result.success is True
        assert len(result.checks_passed) == 3

    def test_verification_time(self, tmp_path, linux_platform, llvm_spec):
        """Test that verification time is recorded."""
        verifier = ToolchainVerifier(linux_platform)
        result = verifier.verify(tmp_path, llvm_spec, VerificationLevel.MINIMAL)

        assert result.verification_time >= 0


# Test convenience function


class TestConvenienceFunction:
    def test_verify_toolchain_convenience(self, tmp_path, linux_platform, llvm_spec):
        """Test verify_toolchain convenience function."""
        # Create expected files
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "clang").touch()
        (bin_dir / "clang++").touch()
        (bin_dir / "lld").touch()

        result = verify_toolchain(
            tmp_path, llvm_spec, VerificationLevel.MINIMAL, linux_platform
        )

        assert isinstance(result, VerificationResult)
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
