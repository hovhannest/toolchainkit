"""
Upgrade command implementation.

Upgrades toolchains and ToolchainKit itself to latest versions.
"""

import logging

from toolchainkit.toolchain.upgrader import (
    ToolchainUpgrader,
    check_toolchainkit_updates,
    upgrade_toolchainkit,
    UpdateCheckError,
    UpgradeError,
)
from toolchainkit.core.directory import get_global_cache_dir
from toolchainkit.cli.utils import safe_print

logger = logging.getLogger(__name__)


def run(args) -> int:
    """
    Run the upgrade command.

    Args:
        args: Parsed command-line arguments with:
            - toolchain: Specific toolchain to upgrade
            - all: Upgrade all toolchains
            - self: Upgrade ToolchainKit itself (not implemented in argparse yet)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if --self flag (need to check if it exists in args)
    upgrade_self = hasattr(args, "self") and getattr(args, "self", False)

    # Determine which upgrade operation to perform
    if upgrade_self:
        return _upgrade_toolchainkit()
    elif args.all:
        return _upgrade_all_toolchains()
    elif args.toolchain:
        return _upgrade_toolchain(args.toolchain)
    else:
        print("Error: Specify --toolchain NAME, --all, or --self")
        print("Use 'tkgen upgrade --help' for more information")
        return 1


def _upgrade_toolchainkit() -> int:
    """
    Upgrade ToolchainKit itself using pip.

    Returns:
        Exit code (0 for success)
    """
    safe_print("🔍 Checking for ToolchainKit updates...")

    # Check for updates
    update_info = check_toolchainkit_updates()

    if not update_info:
        safe_print("✅ ToolchainKit is up to date")
        return 0

    current_version, latest_version = update_info
    safe_print(
        f"📦 New version available: {latest_version} (current: {current_version})"
    )
    print()

    # Prompt for confirmation
    try:
        response = input("Upgrade ToolchainKit? [Y/n] ").strip().lower()
        if response and response not in ["y", "yes"]:
            print("Upgrade cancelled")
            return 0
    except (EOFError, KeyboardInterrupt):
        print("\nUpgrade cancelled")
        return 130

    # Perform upgrade
    safe_print(f"⬇️  Upgrading ToolchainKit to {latest_version}...")

    if upgrade_toolchainkit():
        safe_print(f"✅ ToolchainKit upgraded successfully to {latest_version}")
        print()
        print("Note: You may need to restart your terminal for changes to take effect")
        return 0
    else:
        safe_print("❌ Failed to upgrade ToolchainKit")
        print("Please check your network connection and try again")
        return 1


def _upgrade_toolchain(toolchain_name: str) -> int:
    """
    Upgrade specific toolchain to latest version.

    Args:
        toolchain_name: Name of toolchain to upgrade

    Returns:
        Exit code (0 for success)
    """
    print(f"🔍 Checking for updates to {toolchain_name}...")

    try:
        upgrader = ToolchainUpgrader()

        # Find matching toolchain in cache
        from toolchainkit.core.cache_registry import ToolchainCacheRegistry

        cache_registry = ToolchainCacheRegistry(
            get_global_cache_dir() / "registry.json"
        )

        with cache_registry._lock():
            installed_ids = cache_registry.list_toolchains()

        # Find toolchain matching the name
        matching_toolchains = [
            tc_id for tc_id in installed_ids if tc_id.startswith(toolchain_name)
        ]

        if not matching_toolchains:
            safe_print(f"❌ Toolchain not found: {toolchain_name}")
            print("\nInstalled toolchains:")
            for tc_id in installed_ids:
                print(f"  - {tc_id}")
            return 1

        if len(matching_toolchains) > 1:
            safe_print(f"❌ Multiple toolchains match '{toolchain_name}':")
            for tc_id in matching_toolchains:
                print(f"  - {tc_id}")
            print("\nPlease specify the full toolchain ID")
            return 1

        toolchain_id = matching_toolchains[0]

        # Check for updates
        update_info = upgrader.check_for_updates(toolchain_id)

        if not update_info:
            safe_print(f"✅ {toolchain_id} is up to date")
            return 0

        # Display update information
        safe_print(
            f"📦 New version available: {update_info.latest_version} (current: {update_info.current_version})"
        )
        print(f"   Size: {update_info.size_mb} MB")
        print()

        # Prompt for confirmation
        try:
            response = input("Upgrade toolchain? [Y/n] ").strip().lower()
            if response and response not in ["y", "yes"]:
                print("Upgrade cancelled")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nUpgrade cancelled")
            return 130

        # Perform upgrade with progress reporting
        safe_print(f"⬇️  Upgrading {toolchain_id}...")

        def progress_callback(phase: str, current: int, total: int):
            """Display progress."""
            if total > 0:
                percentage = (current / total) * 100
                print(f"\r{phase}: {percentage:.1f}%", end="", flush=True)

        result = upgrader.upgrade_toolchain(
            toolchain_id=toolchain_id, progress_callback=progress_callback
        )

        print()  # New line after progress

        if result.success:
            safe_print(f"✅ Upgraded to {result.new_version}")
            return 0
        else:
            safe_print(f"❌ Upgrade failed: {result.error}")
            return 1

    except UpdateCheckError as e:
        logger.error(f"Failed to check for updates: {e}")
        safe_print(f"❌ Failed to check for updates: {e}")
        return 1
    except UpgradeError as e:
        logger.error(f"Upgrade failed: {e}")
        safe_print(f"❌ Upgrade failed: {e}")
        return 1
    except Exception as e:
        logger.exception("Unexpected error during upgrade")
        safe_print(f"❌ Unexpected error: {e}")
        return 1


def _upgrade_all_toolchains() -> int:
    """
    Upgrade all installed toolchains.

    Returns:
        Exit code (0 for success)
    """
    safe_print("🔍 Checking all toolchains for updates...")

    try:
        upgrader = ToolchainUpgrader()

        # Get all installed toolchains
        from toolchainkit.core.cache_registry import ToolchainCacheRegistry

        cache_registry = ToolchainCacheRegistry(
            get_global_cache_dir() / "registry.json"
        )

        with cache_registry._lock():
            installed_ids = cache_registry.list_toolchains()

        if not installed_ids:
            print("No toolchains installed")
            return 0

        # Check each for updates
        updates_available = []

        for toolchain_id in installed_ids:
            try:
                update_info = upgrader.check_for_updates(toolchain_id)
                if update_info:
                    updates_available.append((toolchain_id, update_info))
            except Exception as e:
                logger.warning(f"Failed to check {toolchain_id}: {e}")

        if not updates_available:
            safe_print("✅ All toolchains are up to date")
            return 0

        # Display available updates
        print(f"\n{len(updates_available)} update(s) available:")
        for toolchain_id, update_info in updates_available:
            safe_print(f"  • {toolchain_id}")
            safe_print(
                f"    {update_info.current_version} → {update_info.latest_version} ({update_info.size_mb} MB)"
            )
        print()

        # Prompt for confirmation
        try:
            response = (
                input(f"Upgrade {len(updates_available)} toolchain(s)? [Y/n] ")
                .strip()
                .lower()
            )
            if response and response not in ["y", "yes"]:
                print("Upgrade cancelled")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nUpgrade cancelled")
            return 130

        # Perform upgrades
        print()
        success_count = 0
        failure_count = 0

        for i, (toolchain_id, update_info) in enumerate(updates_available, 1):
            print(f"[{i}/{len(updates_available)}] Upgrading {toolchain_id}...")

            def progress_callback(phase: str, current: int, total: int):
                """Display progress."""
                if total > 0:
                    percentage = (current / total) * 100
                    print(f"\r  {phase}: {percentage:.1f}%", end="", flush=True)

            result = upgrader.upgrade_toolchain(
                toolchain_id=toolchain_id, progress_callback=progress_callback
            )

            print()  # New line after progress

            if result.success:
                safe_print(f"  ✅ Upgraded to {result.new_version}")
                success_count += 1
            else:
                safe_print(f"  ❌ Failed: {result.error}")
                failure_count += 1
            print()

        # Summary
        print(f"Summary: {success_count} upgraded, {failure_count} failed")

        return 0 if failure_count == 0 else 1

    except Exception as e:
        logger.exception("Unexpected error during bulk upgrade")
        safe_print(f"❌ Unexpected error: {e}")
        return 1
