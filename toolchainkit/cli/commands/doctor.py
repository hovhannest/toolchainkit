"""
Doctor command for diagnosing environment issues.

This module provides health checks for the ToolchainKit environment,
including Python version, CMake installation, toolchain configuration,
build cache tools, and build systems.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from abc import ABC, abstractmethod
import subprocess
import sys
import shutil
import logging

from toolchainkit.cli.utils import check_initialized, safe_print

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a health check."""

    name: str
    passed: bool
    message: str
    fix_command: Optional[str] = None
    fixable: bool = False


@dataclass
class FixResult:
    """Result of an automated fix attempt."""

    success: bool
    message: str
    action_taken: Optional[str] = None


class DoctorCheck(ABC):
    """Base class for health checks with optional auto-fix capability."""

    @abstractmethod
    def check(self) -> CheckResult:
        """Run the health check."""
        pass

    def can_autofix(self) -> bool:
        """Whether this check supports automatic fixing."""
        return False

    def fix(self) -> FixResult:
        """
        Attempt to automatically fix the issue.

        Returns:
            FixResult indicating success/failure
        """
        return FixResult(
            success=False,
            message="Auto-fix not implemented for this check",
            action_taken=None,
        )


class EnvironmentChecker:
    """Check development environment health."""

    def check_python(self) -> CheckResult:
        """
        Check Python version.

        Returns:
            CheckResult indicating if Python version is 3.8 or newer
        """
        version = sys.version_info

        if version >= (3, 8):
            return CheckResult(
                name="Python",
                passed=True,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
                fixable=False,
            )
        else:
            return CheckResult(
                name="Python",
                passed=False,
                message=f"Python {version.major}.{version.minor} is too old (need 3.8+)",
                fix_command="Install Python 3.8 or newer from https://www.python.org/downloads/",
                fixable=False,
            )

    def check_cmake(self) -> CheckResult:
        """
        Check CMake installation.

        Returns:
            CheckResult indicating if CMake is installed and accessible
        """
        try:
            result = subprocess.run(
                ["cmake", "--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                version_line = result.stdout.split("\n")[0]
                return CheckResult(
                    name="CMake", passed=True, message=version_line, fixable=False
                )
        except FileNotFoundError:
            return CheckResult(
                name="CMake",
                passed=False,
                message="CMake not found in PATH",
                fix_command="Install CMake from https://cmake.org/download/",
                fixable=False,
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                name="CMake",
                passed=False,
                message="CMake check timed out",
                fix_command="Check CMake installation",
                fixable=False,
            )

        return CheckResult(
            name="CMake",
            passed=False,
            message="CMake check failed",
            fix_command="Verify CMake installation",
            fixable=False,
        )

    def check_toolchain(
        self, project_root: Path, config_file: Optional[Path] = None
    ) -> CheckResult:
        """
        Check toolchain configuration.

        Args:
            project_root: Path to project root directory
            config_file: Optional path to configuration file

        Returns:
            CheckResult indicating toolchain configuration status
        """
        if not check_initialized(project_root, config_file):
            return CheckResult(
                name="Toolchain Config",
                passed=False,
                message=f"Configuration file not found: {config_file or 'toolchainkit.yaml'}",
                fix_command="Run: tkgen init",
                fixable=True,
            )

        # Check toolchain directory
        toolchain_dir = project_root / ".toolchainkit" / "toolchains"

        if not toolchain_dir.exists():
            return CheckResult(
                name="Toolchain",
                passed=False,
                message="No .toolchainkit directory found",
                fix_command="Run: tkgen configure",
                fixable=True,
            )

        # Check if any toolchains installed
        if not list(toolchain_dir.iterdir()):
            return CheckResult(
                name="Toolchain",
                passed=False,
                message="No toolchains installed",
                fix_command="Run: tkgen configure",
                fixable=True,
            )

        return CheckResult(
            name="Toolchain",
            passed=True,
            message=f"Toolchains found in {toolchain_dir}",
            fixable=False,
        )

    def check_build_cache(self) -> CheckResult:
        """
        Check for build cache tools (sccache, ccache).

        Returns:
            CheckResult indicating build cache tool availability
        """
        sccache = shutil.which("sccache")
        ccache = shutil.which("ccache")

        if sccache or ccache:
            tool = "sccache" if sccache else "ccache"
            return CheckResult(
                name="Build Cache",
                passed=True,
                message=f"{tool} found at {sccache or ccache}",
                fixable=False,
            )
        else:
            return CheckResult(
                name="Build Cache",
                passed=False,
                message="No build cache tool found (optional but recommended)",
                fix_command="Install sccache for faster builds: https://github.com/mozilla/sccache",
                fixable=False,
            )

    def check_ninja(self) -> CheckResult:
        """
        Check for Ninja build system.

        Returns:
            CheckResult indicating Ninja availability
        """
        ninja_path = shutil.which("ninja")

        if ninja_path:
            try:
                result = subprocess.run(
                    ["ninja", "--version"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return CheckResult(
                        name="Ninja",
                        passed=True,
                        message=f"Ninja {version} found at {ninja_path}",
                        fixable=False,
                    )
            except (subprocess.TimeoutExpired, Exception):
                pass

            return CheckResult(
                name="Ninja",
                passed=True,
                message=f"Ninja found at {ninja_path}",
                fixable=False,
            )
        else:
            return CheckResult(
                name="Ninja",
                passed=False,
                message="Ninja not found (optional but recommended for faster builds)",
                fix_command="Install Ninja: https://ninja-build.org/",
                fixable=False,
            )


class CorruptedCacheCheck(DoctorCheck):
    """Check for corrupted cache files."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache check."""
        from toolchainkit.core.directory import get_global_cache_dir

        self.cache_dir = cache_dir or get_global_cache_dir()

    def check(self) -> CheckResult:
        """Check for corrupted cache files."""
        corrupted = self._find_corrupted_files()

        if not corrupted:
            return CheckResult(
                name="Cache",
                passed=True,
                message="Cache is healthy",
                fixable=False,
            )

        return CheckResult(
            name="Cache",
            passed=False,
            message=f"{len(corrupted)} corrupted file(s) in cache",
            fix_command="Run with --fix to clean corrupted cache files",
            fixable=True,
        )

    def can_autofix(self) -> bool:
        """Corrupted cache files can be auto-fixed."""
        return True

    def fix(self) -> FixResult:
        """Remove corrupted cache files."""
        try:
            corrupted = self._find_corrupted_files()
            if not corrupted:
                return FixResult(
                    success=True,
                    message="No corrupted files found",
                    action_taken=None,
                )

            for path in corrupted:
                path.unlink()
                logger.info(f"Removed corrupted cache file: {path}")

            return FixResult(
                success=True,
                message=f"Cleaned {len(corrupted)} corrupted file(s)",
                action_taken=f"Removed: {', '.join(f.name for f in corrupted[:5])}{'...' if len(corrupted) > 5 else ''}",
            )
        except Exception as e:
            return FixResult(
                success=False,
                message=f"Failed to clean cache: {e}",
                action_taken=None,
            )

    def _find_corrupted_files(self) -> List[Path]:
        """Find corrupted files in the cache."""
        corrupted: List[Path] = []

        if not self.cache_dir.exists():
            return corrupted

        # Check for .partial files (incomplete downloads)
        for partial_file in self.cache_dir.rglob("*.partial"):
            corrupted.append(partial_file)

        # Check for empty archives
        for archive in self.cache_dir.rglob("*.tar.gz"):
            if archive.stat().st_size == 0:
                corrupted.append(archive)

        for archive in self.cache_dir.rglob("*.zip"):
            if archive.stat().st_size == 0:
                corrupted.append(archive)

        return corrupted


class DoctorRunner:
    """Manages running health checks and auto-fixes."""

    def __init__(self, project_root: Path, config_file: Optional[Path] = None):
        """Initialize doctor runner."""
        self.project_root = project_root
        self.config_file = config_file
        self.checker = EnvironmentChecker()

        # Create check instances
        self.checks: List[DoctorCheck] = [
            CorruptedCacheCheck(),
        ]

    def run_all_checks(self) -> List[CheckResult]:
        """Run all health checks."""
        results = [
            self.checker.check_python(),
            self.checker.check_cmake(),
            self.checker.check_toolchain(self.project_root, self.config_file),
            self.checker.check_build_cache(),
            self.checker.check_ninja(),
        ]

        # Add checks from DoctorCheck instances
        for check in self.checks:
            results.append(check.check())

        return results

    def fix_all(self, results: List[CheckResult]) -> List[FixResult]:
        """
        Attempt to fix all fixable issues.

        Args:
            results: Results from run_all_checks()

        Returns:
            List of fix results
        """
        fix_results = []

        # Match results with checks that can be fixed
        for check in self.checks:
            # Find the corresponding result
            check_result = next(
                (r for r in results if r.name == check.check().name), None
            )

            if check_result is None:
                continue

            # Skip if check passed or not fixable
            if check_result.passed or not check_result.fixable:
                continue

            # Skip if check doesn't support autofix
            if not check.can_autofix():
                continue

            # Attempt fix
            safe_print(f"🔧 Fixing: {check_result.message}")
            logger.info(f"Attempting to fix: {check_result.name}")

            fix_result = check.fix()
            fix_results.append(fix_result)

            # Show result
            if fix_result.success:
                safe_print(f"   ✅ {fix_result.message}")
                if fix_result.action_taken:
                    safe_print(f"   → {fix_result.action_taken}")
                logger.info(f"Fixed {check_result.name}: {fix_result.message}")
            else:
                print(f"   ❌ {fix_result.message}")
                logger.error(f"Failed to fix {check_result.name}: {fix_result.message}")

        return fix_results


def run(args) -> int:
    """
    Run doctor command.

    Args:
        args: Parsed arguments from argparse

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    quiet = args.quiet
    fix = getattr(args, "fix", False)
    project_root = args.project_root
    config_file = args.config

    if not quiet:
        print("🏥 Running ToolchainKit diagnostics...\n")
        logger.info("Starting environment diagnostics")

    # Use DoctorRunner for checks
    runner = DoctorRunner(project_root, config_file)
    checks = runner.run_all_checks()

    # Display results
    passed = 0
    failed = 0
    warnings = 0
    fixable_count = 0

    for result in checks:
        if result.passed:
            passed += 1
            if not quiet:
                print(f"✅ {result.name}: {result.message}")
                logger.debug(f"Check passed: {result.name}")
        else:
            # Treat optional tools as warnings, critical items as failures
            if result.name in ["Build Cache", "Ninja"]:
                warnings += 1
                if not quiet:
                    print(f"⚠️  {result.name}: {result.message}")
                logger.warning(f"{result.name}: {result.message}")
            else:
                failed += 1
                print(f"❌ {result.name}: {result.message}")
                logger.error(f"{result.name}: {result.message}")

            # Track fixable issues
            if result.fixable:
                fixable_count += 1

            # Show fix command if not auto-fixing
            if not fix and result.fix_command:
                print(f"   💡 Fix: {result.fix_command}")
                logger.info(f"Suggested fix for {result.name}: {result.fix_command}")

    # Summary
    if not quiet:
        safe_print(
            f"\n📊 Summary: {passed} passed, {failed} failed, {warnings} warnings"
        )

    # Run auto-fix if requested
    if fix and fixable_count > 0:
        safe_print(f"\n🔧 Attempting to fix {fixable_count} issue(s)...\n")
        logger.info(f"Running auto-fix for {fixable_count} issues")

        fix_results = runner.fix_all(checks)

        # Count successful fixes
        success_count = sum(1 for r in fix_results if r.success)
        fail_count = len(fix_results) - success_count

        safe_print(f"\n📊 Fix Summary: {success_count} fixed, {fail_count} failed")

        if success_count == len(fix_results):
            print("✅ All fixable issues resolved!")
            logger.info("All auto-fixes successful")
        elif success_count > 0:
            print(
                f"⚠️  {fail_count} issue(s) could not be auto-fixed and require manual intervention"
            )
            logger.warning(f"{fail_count} fixes failed")
        else:
            print("❌ No issues could be auto-fixed")
            logger.error("All auto-fixes failed")
    elif fixable_count > 0 and not fix:
        print(f"\n💡 {fixable_count} issue(s) can be auto-fixed with --fix")
        logger.info(f"{fixable_count} issues are auto-fixable")

    # Final status
    if failed == 0 and warnings == 0:
        if not quiet:
            print("\n✅ Your environment is healthy!")
        logger.info("All diagnostics passed")
        return 0
    elif failed == 0:
        if not quiet:
            print(
                f"\n⚠️  Found {warnings} optional tool(s) missing (builds will still work)"
            )
        logger.info(f"Diagnostics passed with {warnings} warnings")
        return 0
    else:
        print(f"\n❌ Found {failed} critical issue(s) that need attention")
        logger.error(f"Diagnostics failed: {failed} critical issues")
        return 1
