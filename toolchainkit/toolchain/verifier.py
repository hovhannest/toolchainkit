"""
Toolchain verification system.

This module provides comprehensive verification of downloaded and extracted toolchains,
ensuring they are complete, functional, and ready for use. Supports multiple verification
levels from minimal file checks to full compile tests.
"""

import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from toolchainkit.core.platform import PlatformInfo

logger = logging.getLogger(__name__)


class VerificationLevel(Enum):
    """Verification thoroughness levels."""

    MINIMAL = "minimal"  # File presence only (~1s)
    STANDARD = "standard"  # + Executability + Version (~5s)
    THOROUGH = "thorough"  # + ABI + Symlinks (~10s)
    PARANOID = "paranoid"  # + Full compile test (~30s)


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of toolchain verification."""

    success: bool
    checks_passed: List[str]
    checks_failed: List[str]
    errors: List[str]
    warnings: List[str]
    verification_time: float

    def add_check(self, result: CheckResult):
        """
        Add check result to verification.

        Args:
            result: CheckResult to add
        """
        if result.passed:
            self.checks_passed.append(result.name)
            if result.message:
                logger.debug(f"{result.name}: {result.message}")
        else:
            self.checks_failed.append(result.name)
            self.errors.append(f"{result.name}: {result.message}")
            self.success = False


@dataclass
class ToolchainSpec:
    """Specification for toolchain verification."""

    id: str
    name: str
    version: str
    type: str  # 'llvm', 'gcc', 'msvc'


class FilePresenceCheck:
    """Verify expected files exist in toolchain."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize file presence check.

        Args:
            platform: Platform information
        """
        self.platform = platform

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Check if critical files exist.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with file presence status
        """
        expected_files = self._get_expected_files(spec)
        missing_files = []

        for file_rel in expected_files:
            file_path = toolchain_path / file_rel
            if not file_path.exists():
                missing_files.append(str(file_rel))

        if missing_files:
            return CheckResult(
                name="file_presence",
                passed=False,
                message=f"Missing {len(missing_files)} file(s): {', '.join(missing_files[:5])}{'...' if len(missing_files) > 5 else ''}",
                details={"missing_files": missing_files},
            )

        return CheckResult(
            name="file_presence",
            passed=True,
            message=f"All {len(expected_files)} expected files present",
        )

    def _get_expected_files(self, spec: ToolchainSpec) -> List[str]:
        """
        Get list of expected files based on toolchain type.

        Args:
            spec: Toolchain specification

        Returns:
            List of expected file paths relative to toolchain root
        """
        if spec.type == "llvm":
            return self._llvm_files()
        elif spec.type == "gcc":
            return self._gcc_files()
        elif spec.type == "msvc":
            return self._msvc_files()
        else:
            logger.warning(f"Unknown toolchain type: {spec.type}")
            return []

    def _llvm_files(self) -> List[str]:
        """Expected files for LLVM/Clang toolchain."""
        exe = ".exe" if self.platform.os == "windows" else ""
        return [
            f"bin/clang{exe}",
            f"bin/clang++{exe}",
            f"bin/lld{exe}",
        ]

    def _gcc_files(self) -> List[str]:
        """Expected files for GCC toolchain."""
        exe = ".exe" if self.platform.os == "windows" else ""
        return [
            f"bin/gcc{exe}",
            f"bin/g++{exe}",
            f"bin/ld{exe}",
        ]

    def _msvc_files(self) -> List[str]:
        """Expected files for MSVC toolchain."""
        return [
            "bin/Hostx64/x64/cl.exe",
            "bin/Hostx64/x64/link.exe",
        ]


class SymlinkCheck:
    """Verify symlinks point to valid targets."""

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Check symlink integrity.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with symlink status
        """
        broken_links = []

        # Skip symlink check on Windows (junctions are different)
        if os.name == "nt":
            return CheckResult(
                name="symlinks", passed=True, message="Symlink check skipped on Windows"
            )

        try:
            for path in toolchain_path.rglob("*"):
                if path.is_symlink():
                    try:
                        # Check if target exists
                        if not path.resolve().exists():
                            broken_links.append(str(path.relative_to(toolchain_path)))
                    except Exception as e:
                        broken_links.append(f"{path.relative_to(toolchain_path)} ({e})")
        except Exception as e:
            return CheckResult(
                name="symlinks", passed=False, message=f"Error scanning symlinks: {e}"
            )

        if broken_links:
            return CheckResult(
                name="symlinks",
                passed=False,
                message=f"Found {len(broken_links)} broken symlink(s): {', '.join(broken_links[:5])}{'...' if len(broken_links) > 5 else ''}",
                details={"broken_links": broken_links},
            )

        return CheckResult(name="symlinks", passed=True, message="All symlinks valid")


class ExecutabilityCheck:
    """Verify compilers can execute."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize executability check.

        Args:
            platform: Platform information
        """
        self.platform = platform

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Check if compiler executables can run.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with executability status
        """
        compiler_path = self._get_compiler_path(toolchain_path, spec)

        if not compiler_path or not compiler_path.exists():
            return CheckResult(
                name="executability",
                passed=False,
                message=f"Compiler executable not found at expected location: {compiler_path}",
            )

        try:
            # Try to run compiler with --version
            result = subprocess.run(
                [str(compiler_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return CheckResult(
                    name="executability",
                    passed=False,
                    message=f"Compiler exited with code {result.returncode}",
                    details={"stderr": result.stderr, "stdout": result.stdout},
                )

            return CheckResult(
                name="executability",
                passed=True,
                message="Compiler is executable",
                details={"output": result.stdout},
            )

        except subprocess.TimeoutExpired:
            return CheckResult(
                name="executability",
                passed=False,
                message="Compiler execution timed out after 10 seconds",
            )

        except Exception as e:
            return CheckResult(
                name="executability",
                passed=False,
                message=f"Compiler execution failed: {e}",
            )

    def _get_compiler_path(
        self, toolchain_path: Path, spec: ToolchainSpec
    ) -> Optional[Path]:
        """
        Get path to C++ compiler.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            Path to compiler executable, or None if unknown type
        """
        exe = ".exe" if self.platform.os == "windows" else ""

        if spec.type == "llvm":
            return toolchain_path / f"bin/clang++{exe}"
        elif spec.type == "gcc":
            return toolchain_path / f"bin/g++{exe}"
        elif spec.type == "msvc":
            return toolchain_path / "bin/Hostx64/x64/cl.exe"

        return None


class VersionCheck:
    """Verify compiler version matches expected."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize version check.

        Args:
            platform: Platform information
        """
        self.platform = platform
        self.exec_check = ExecutabilityCheck(platform)

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Check if compiler reports expected version.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with version check status
        """
        compiler_path = self.exec_check._get_compiler_path(toolchain_path, spec)

        if not compiler_path or not compiler_path.exists():
            return CheckResult(
                name="version", passed=False, message="Compiler not found"
            )

        try:
            result = subprocess.run(
                [str(compiler_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            version_output = result.stdout.lower()

            # Extract expected major version
            expected_major = spec.version.split(".")[0]

            # Check if version appears in output
            if expected_major not in version_output:
                return CheckResult(
                    name="version",
                    passed=False,
                    message=f"Expected version {spec.version}, output doesn't contain '{expected_major}': {version_output[:100]}",
                    details={"output": result.stdout},
                )

            return CheckResult(
                name="version",
                passed=True,
                message=f"Version {spec.version} confirmed",
                details={"output": result.stdout},
            )

        except subprocess.TimeoutExpired:
            return CheckResult(
                name="version", passed=False, message="Version check timed out"
            )

        except Exception as e:
            return CheckResult(
                name="version", passed=False, message=f"Version check failed: {e}"
            )


class ABICheck:
    """Verify library ABI compatibility."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize ABI check.

        Args:
            platform: Platform information
        """
        self.platform = platform

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Check library ABI compatibility.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with ABI check status
        """
        lib_path = toolchain_path / "lib"
        if not lib_path.exists():
            return CheckResult(
                name="abi", passed=False, message="Library directory not found"
            )

        # Check for standard library based on toolchain type
        if spec.type == "llvm":
            if self.platform.os == "windows":
                required_libs = ["c++.lib"]
            else:
                required_libs = ["libc++"]  # Can be .a or .so
        elif spec.type == "gcc":
            required_libs = ["libstdc++", "libgcc"]  # Can be .a or .so
        elif spec.type == "msvc":
            return CheckResult(
                name="abi", passed=True, message="ABI check skipped for MSVC"
            )
        else:
            return CheckResult(
                name="abi",
                passed=True,
                message=f"ABI check skipped for unknown toolchain type: {spec.type}",
            )

        # Check if any required library exists
        missing_libs = []
        for lib in required_libs:
            # Look for lib with any extension (.a, .so, .dylib, .lib)
            if not any(lib_path.rglob(f"{lib}*")):
                missing_libs.append(lib)

        if missing_libs:
            return CheckResult(
                name="abi",
                passed=False,
                message=f"Missing standard libraries: {', '.join(missing_libs)}",
            )

        return CheckResult(
            name="abi", passed=True, message="Standard libraries present"
        )


class CompileTestCheck:
    """Verify toolchain can compile a simple program."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize compile test check.

        Args:
            platform: Platform information
        """
        self.platform = platform
        self.exec_check = ExecutabilityCheck(platform)

    def check(self, toolchain_path: Path, spec: ToolchainSpec) -> CheckResult:
        """
        Compile and run a test program.

        Args:
            toolchain_path: Path to toolchain installation
            spec: Toolchain specification

        Returns:
            CheckResult with compile test status
        """
        test_program = """
#include <iostream>
int main() {
    std::cout << "Hello from ToolchainKit!" << std::endl;
    return 0;
}
"""

        compiler_path = self.exec_check._get_compiler_path(toolchain_path, spec)
        if not compiler_path or not compiler_path.exists():
            return CheckResult(
                name="compile_test", passed=False, message="Compiler not found"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source_file = tmpdir_path / "test.cpp"

            if self.platform.os == "windows":
                output_file = tmpdir_path / "test.exe"
            else:
                output_file = tmpdir_path / "test"

            source_file.write_text(test_program)

            try:
                # Build compile command
                if spec.type == "msvc":
                    compile_cmd = [
                        str(compiler_path),
                        str(source_file),
                        f"/Fe:{output_file}",
                    ]
                else:
                    compile_cmd = [
                        str(compiler_path),
                        str(source_file),
                        "-o",
                        str(output_file),
                    ]

                # Compile
                result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir_path,
                )

                if result.returncode != 0:
                    return CheckResult(
                        name="compile_test",
                        passed=False,
                        message=f"Compilation failed: {result.stderr[:200]}",
                        details={"stderr": result.stderr, "stdout": result.stdout},
                    )

                # Run compiled program
                run_result = subprocess.run(
                    [str(output_file)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tmpdir_path,
                )

                if run_result.returncode != 0:
                    return CheckResult(
                        name="compile_test",
                        passed=False,
                        message="Compiled program failed to run",
                        details={"stderr": run_result.stderr},
                    )

                # Check output contains expected string
                if "Hello from ToolchainKit!" not in run_result.stdout:
                    return CheckResult(
                        name="compile_test",
                        passed=False,
                        message="Program output doesn't match expected",
                        details={"output": run_result.stdout},
                    )

                return CheckResult(
                    name="compile_test",
                    passed=True,
                    message="Successfully compiled and ran test program",
                )

            except subprocess.TimeoutExpired:
                return CheckResult(
                    name="compile_test", passed=False, message="Compile test timed out"
                )

            except Exception as e:
                return CheckResult(
                    name="compile_test",
                    passed=False,
                    message=f"Compile test failed: {e}",
                )


class ToolchainVerifier:
    """Manages toolchain verification with configurable check levels."""

    def __init__(self, platform: PlatformInfo):
        """
        Initialize toolchain verifier.

        Args:
            platform: Platform information
        """
        self.platform = platform

        # Define check sets for each verification level
        self.all_checks = {
            VerificationLevel.MINIMAL: [
                FilePresenceCheck(platform),
            ],
            VerificationLevel.STANDARD: [
                FilePresenceCheck(platform),
                ExecutabilityCheck(platform),
                VersionCheck(platform),
            ],
            VerificationLevel.THOROUGH: [
                FilePresenceCheck(platform),
                ExecutabilityCheck(platform),
                VersionCheck(platform),
                ABICheck(platform),
                SymlinkCheck(),
            ],
            VerificationLevel.PARANOID: [
                FilePresenceCheck(platform),
                ExecutabilityCheck(platform),
                VersionCheck(platform),
                ABICheck(platform),
                SymlinkCheck(),
                CompileTestCheck(platform),
            ],
        }

    def verify(
        self,
        toolchain_path: Path,
        toolchain_spec: ToolchainSpec,
        level: VerificationLevel = VerificationLevel.STANDARD,
    ) -> VerificationResult:
        """
        Verify toolchain integrity and functionality.

        Args:
            toolchain_path: Path to extracted toolchain
            toolchain_spec: Expected toolchain specification
            level: Verification thoroughness level

        Returns:
            VerificationResult with check results

        Example:
            >>> from toolchainkit.core.platform import detect_platform
            >>> platform = detect_platform()
            >>> verifier = ToolchainVerifier(platform)
            >>> spec = ToolchainSpec(
            ...     id='llvm-18.1.8-linux-x64',
            ...     name='LLVM',
            ...     version='18.1.8',
            ...     type='llvm'
            ... )
            >>> result = verifier.verify(
            ...     Path('/path/to/toolchain'),
            ...     spec,
            ...     VerificationLevel.STANDARD
            ... )
            >>> if result.success:
            ...     print("Toolchain verified!")
        """
        start_time = time.time()

        result = VerificationResult(
            success=True,
            checks_passed=[],
            checks_failed=[],
            errors=[],
            warnings=[],
            verification_time=0.0,
        )

        # Get checks for the specified level
        checks_maybe = self.all_checks.get(
            level, self.all_checks[VerificationLevel.STANDARD]
        )
        logger.info(f"Verifying toolchain at {toolchain_path}")
        if checks_maybe is not None:
            checks: List = list(checks_maybe)  # type: ignore[call-overload,assignment]
            logger.info(f"Running {len(checks)} checks at {level.value} level")
        else:
            checks = []

        # Run each check
        for check in checks:
            check_name = check.__class__.__name__
            logger.debug(f"Running {check_name}...")

            try:
                check_result = check.check(toolchain_path, toolchain_spec)
                result.add_check(check_result)

                if check_result.passed:
                    logger.info(f"  ✓ {check_result.name}: {check_result.message}")
                else:
                    logger.error(f"  ✗ {check_result.name}: {check_result.message}")

            except Exception as e:
                logger.error(f"  ✗ {check_name} failed with exception: {e}")
                result.add_check(
                    CheckResult(
                        name=check_name,
                        passed=False,
                        message=f"Check failed with exception: {e}",
                    )
                )

        result.verification_time = time.time() - start_time

        if result.success:
            logger.info(
                f"✓ Toolchain verification passed ({result.verification_time:.2f}s)"
            )
        else:
            logger.error(
                f"✗ Toolchain verification failed ({result.verification_time:.2f}s)"
            )
            logger.error(f"Failed checks: {', '.join(result.checks_failed)}")

        return result


# Convenience function
def verify_toolchain(
    toolchain_path: Path,
    toolchain_spec: ToolchainSpec,
    level: VerificationLevel = VerificationLevel.STANDARD,
    platform: Optional[PlatformInfo] = None,
) -> VerificationResult:
    """
    Convenience function to verify a toolchain.

    Args:
        toolchain_path: Path to toolchain installation
        toolchain_spec: Toolchain specification
        level: Verification level (default: STANDARD)
        platform: Platform info (default: auto-detect)

    Returns:
        VerificationResult

    Example:
        >>> from pathlib import Path
        >>> spec = ToolchainSpec(
        ...     id='llvm-18.1.8-linux-x64',
        ...     name='LLVM',
        ...     version='18.1.8',
        ...     type='llvm'
        ... )
        >>> result = verify_toolchain(
        ...     Path('/path/to/toolchain'),
        ...     spec
        ... )
        >>> print(f"Success: {result.success}")
    """
    if platform is None:
        from toolchainkit.core.platform import detect_platform

        platform = detect_platform()

    verifier = ToolchainVerifier(platform)
    return verifier.verify(toolchain_path, toolchain_spec, level)
