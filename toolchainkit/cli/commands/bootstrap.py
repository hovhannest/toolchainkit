"""
Bootstrap command implementation.

Generates or regenerates bootstrap scripts for the project.
"""

import logging
from pathlib import Path
from typing import Dict

from toolchainkit.bootstrap.generator import BootstrapGenerator, BootstrapGeneratorError
from toolchainkit.cli.utils import (
    check_initialized,
    format_success_message,
    load_yaml_config,
    print_error,
    safe_print,
)
from toolchainkit.core.compatibility import validate_bootstrap_compatibility
from toolchainkit.packages import PackageManagerDetector

logger = logging.getLogger(__name__)


def run(args) -> int:
    """
    Run the bootstrap command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Generating bootstrap scripts")
    logger.debug(f"Arguments: {args}")

    # 1. Validation - Check project is initialized
    project_root = Path(args.project_root).resolve()
    config_file = (
        Path(args.config) if args.config else (project_root / "toolchainkit.yaml")
    )

    if not check_initialized(project_root, config_file):
        logger.error("Project not initialized")
        print_error(
            "Project not initialized",
            f"Configuration file not found: {config_file}\n  Run 'tkgen init' first",
        )
        return 1

    # 2. Load configuration
    logger.debug(f"Loading configuration from {config_file}")

    try:
        config = load_yaml_config(config_file, required=True)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        print_error("Failed to load configuration", str(e))
        return 1

    # 3. Override configuration with CLI arguments
    if args.toolchain:
        # Override in defaults section to ensure it takes precedence
        if "defaults" not in config:
            config["defaults"] = {}
        config["defaults"]["toolchain"] = args.toolchain
        logger.debug(f"Overriding toolchain: {args.toolchain}")

    if args.build_type:
        if "build" not in config:
            config["build"] = {}
        config["build"]["build_type"] = args.build_type
        logger.debug(f"Overriding build_type: {args.build_type}")

    # Flatten config for BootstrapGenerator
    flat_config = _flatten_config(config)

    # Add config file path (relative to project root if possible)
    try:
        config_file_resolved = config_file.resolve()
        config_file_rel = config_file_resolved.relative_to(project_root)
        flat_config["config_file"] = str(config_file_rel)
    except ValueError:
        # Config file is outside project root, use absolute path
        flat_config["config_file"] = str(config_file.resolve())

    logger.debug(f"Config file for bootstrap: {flat_config['config_file']}")

    # Add advanced configuration options (Phase 2)
    if hasattr(args, "cmake_args") and args.cmake_args is not None:
        flat_config["cmake_args"] = args.cmake_args
        logger.debug(f"Adding CMake args: {args.cmake_args}")

    if hasattr(args, "env") and args.env is not None:
        flat_config["env_vars"] = dict(args.env)
        logger.debug(f"Adding environment variables: {dict(args.env)}")

    if hasattr(args, "pre_configure_hook") and args.pre_configure_hook is not None:
        if "hooks" not in flat_config:
            flat_config["hooks"] = {}
        flat_config["hooks"]["pre_configure"] = args.pre_configure_hook
        logger.debug(f"Adding pre-configure hook: {args.pre_configure_hook}")

    if hasattr(args, "post_configure_hook") and args.post_configure_hook is not None:
        if "hooks" not in flat_config:
            flat_config["hooks"] = {}
        flat_config["hooks"]["post_configure"] = args.post_configure_hook
        logger.debug(f"Adding post-configure hook: {args.post_configure_hook}")

    # 3.5. Auto-detect package manager if not configured or if configured but not available
    configured_pm = flat_config.get("package_manager")
    should_auto_detect = False

    if not configured_pm:
        logger.debug("No package manager configured, attempting auto-detection")
        should_auto_detect = True
    else:
        # Verify configured package manager is actually available
        try:
            from toolchainkit.cli.utils import get_package_manager_instance

            logger.debug(f"Verifying configured package manager: {configured_pm}")
            pm_instance = get_package_manager_instance(
                configured_pm, project_root, {"manager": configured_pm}
            )
            if not pm_instance.detect():
                logger.warning(
                    f"Configured package manager '{configured_pm}' not found in project "
                    f"(no manifest file detected). Attempting auto-detection..."
                )
                safe_print(
                    f"⚠️  Configured package manager '{configured_pm}' not found, auto-detecting..."
                )
                should_auto_detect = True
        except Exception as e:
            logger.warning(
                f"Failed to verify configured package manager '{configured_pm}': {e}. "
                f"Attempting auto-detection..."
            )
            safe_print(
                f"⚠️  Package manager '{configured_pm}' unavailable, auto-detecting..."
            )
            should_auto_detect = True

    if should_auto_detect:
        try:
            detector = PackageManagerDetector(project_root)
            # Register known package managers
            from toolchainkit.packages.conan import ConanIntegration
            # from toolchainkit.packages.vcpkg import VcpkgIntegration

            detector.register(ConanIntegration(project_root))
            # detector.register(VcpkgIntegration(project_root))

            primary_pm = detector.detect_primary()
            if primary_pm:
                pm_name = primary_pm.get_name()
                flat_config["package_manager"] = pm_name
                logger.info(f"Auto-detected package manager: {pm_name}")
                safe_print(f"✓ Auto-detected package manager: {pm_name}")
            else:
                # No package manager found, clear the invalid config
                flat_config["package_manager"] = None
                logger.info("No package manager detected")
                if configured_pm:
                    print(f"No package manager found ('{configured_pm}' not available)")
        except Exception as e:
            logger.warning(f"Package manager detection failed: {e}")

    # 3.6. Validate compatibility for bootstrap generation
    logger.debug("Validating configuration compatibility for bootstrap generation")
    compat_result = validate_bootstrap_compatibility(flat_config)

    # Display warnings even if valid
    for warning in compat_result.warnings:
        logger.warning(f"{warning.category}: {warning.message}")
        if not args.quiet:
            safe_print(f"⚠️  WARNING: {warning.message}")
            if warning.suggestion and args.verbose:
                print(f"   Suggestion: {warning.suggestion}")

    # If there are errors, fail immediately
    if not compat_result.valid:
        logger.error("Configuration is incompatible with current platform")
        for error in compat_result.issues:
            logger.error(f"{error.category}: {error.message}")
            print_error(
                f"Incompatible configuration ({error.category})",
                f"{error.message}\n\n  {error.suggestion}",
            )
        return 1

    # 4. Check existing scripts
    shell_script = project_root / "bootstrap.sh"
    batch_script = project_root / "bootstrap.bat"
    powershell_script = project_root / "bootstrap.ps1"

    existing_scripts = []
    if shell_script.exists():
        existing_scripts.append("bootstrap.sh")
    if batch_script.exists():
        existing_scripts.append("bootstrap.bat")
    if powershell_script.exists():
        existing_scripts.append("bootstrap.ps1")

    if existing_scripts:
        if args.force and not args.dry_run:
            logger.info("Removing existing bootstrap scripts (forced)")
            for script in existing_scripts:
                try:
                    (project_root / script).unlink()
                    logger.debug(f"Removed {script}")
                except Exception as e:
                    logger.warning(f"Failed to remove {script}: {e}")
        elif not args.dry_run:
            logger.error("Bootstrap scripts already exist")
            print_error(
                "Bootstrap scripts already exist",
                f"Found: {', '.join(existing_scripts)}\n  Use --force to overwrite",
            )
            return 1

    # 4.5. Clean up build artifacts if --force is used
    if args.force and not args.dry_run:
        _cleanup_build_artifacts(project_root, flat_config.get("build_dir", "build"))

    # 5. Handle dry-run mode
    if args.dry_run:
        logger.info("Dry-run mode: previewing scripts")
        return _preview_scripts(project_root, flat_config, args.platform)

    # 6. Generate scripts
    logger.debug("Generating bootstrap scripts")
    try:
        generator = BootstrapGenerator(project_root, flat_config)

        generated_scripts = {}

        if args.platform in ["unix", "all"]:
            shell_path = generator.generate_shell_script()
            generated_scripts["shell"] = shell_path
            logger.info(f"Generated: {shell_path}")

        if args.platform in ["windows", "all"]:
            batch_path = generator.generate_batch_script()
            generated_scripts["batch"] = batch_path
            logger.info(f"Generated: {batch_path}")

        if args.platform in ["powershell", "all"]:
            powershell_path = generator.generate_powershell_script()
            generated_scripts["powershell"] = powershell_path
            logger.info(f"Generated: {powershell_path}")

    except BootstrapGeneratorError as e:
        logger.error(f"Failed to generate bootstrap scripts: {e}")
        print_error("Failed to generate bootstrap scripts", str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print_error("Unexpected error", str(e))
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    # 7. Validate scripts if requested (Phase 3)
    if hasattr(args, "validate") and args.validate:
        logger.info("Validating generated scripts")
        validation_failed = False

        for script_type, script_path in generated_scripts.items():
            logger.debug(f"Validating {script_type} script: {script_path}")

            if script_type == "shell":
                is_valid, errors = generator.validate_shell_script(script_path)
            elif script_type == "batch":
                is_valid, errors = generator.validate_batch_script(script_path)
            elif script_type == "powershell":
                is_valid, errors = generator.validate_powershell_script(script_path)
            else:
                continue

            if not is_valid:
                validation_failed = True
                print_error(
                    f"Validation failed for {script_path.name}", "\n".join(errors)
                )
            else:
                logger.info(f"Validation passed: {script_path.name}")

        if validation_failed:
            logger.error("Script validation failed")
            return 1

    # 8. Display success message
    _print_success_message(project_root, generated_scripts, flat_config)

    logger.info("Bootstrap script generation complete")
    return 0


def _cleanup_build_artifacts(project_root: Path, build_dir: str) -> None:
    """
    Clean up build and toolchainkit directories before regenerating bootstrap.

    Args:
        project_root: Project root directory
        build_dir: Build directory name (from config)
    """
    import shutil

    build_path = project_root / build_dir
    toolchainkit_path = project_root / ".toolchainkit"

    cleaned = []

    if build_path.exists():
        try:
            logger.info(f"Removing build directory: {build_path}")
            shutil.rmtree(build_path, ignore_errors=False)
            cleaned.append(str(build_path.relative_to(project_root)))
        except Exception as e:
            logger.warning(f"Failed to remove build directory: {e}")

    if toolchainkit_path.exists():
        try:
            logger.info(f"Removing toolchainkit directory: {toolchainkit_path}")
            shutil.rmtree(toolchainkit_path, ignore_errors=False)
            cleaned.append(str(toolchainkit_path.relative_to(project_root)))
        except Exception as e:
            logger.warning(f"Failed to remove toolchainkit directory: {e}")

    if cleaned:
        print(f"Cleaned: {', '.join(cleaned)}")


def _flatten_config(config: dict) -> dict:
    """
    Flatten nested configuration for BootstrapGenerator.

    Args:
        config: Nested configuration dictionary

    Returns:
        Flattened configuration dictionary with expected keys
    """
    flat = {}

    # Extract toolchain - check multiple sources
    # Priority: defaults > bootstrap > toolchain
    if "defaults" in config and "toolchain" in config["defaults"]:
        flat["toolchain"] = config["defaults"]["toolchain"]
    elif "bootstrap" in config and "toolchain" in config["bootstrap"]:
        flat["toolchain"] = config["bootstrap"]["toolchain"]
    elif "toolchain" in config:
        if isinstance(config["toolchain"], dict):
            flat["toolchain"] = config["toolchain"].get("name", "llvm-18")
        else:
            flat["toolchain"] = config["toolchain"]
    else:
        flat["toolchain"] = "llvm-18"

    # Extract build settings - check multiple sources
    # Priority: defaults > bootstrap > build
    if "defaults" in config and "build_type" in config["defaults"]:
        flat["build_type"] = config["defaults"]["build_type"]
    elif "bootstrap" in config and "build_type" in config["bootstrap"]:
        flat["build_type"] = config["bootstrap"]["build_type"]
    elif "build" in config:
        if "build_type" in config["build"]:
            flat["build_type"] = config["build"]["build_type"]
        elif "type" in config["build"]:
            flat["build_type"] = config["build"]["type"]

    # Set default if not found
    if "build_type" not in flat:
        flat["build_type"] = "Release"

    # Extract build directory
    if "bootstrap" in config and "build_dir" in config["bootstrap"]:
        flat["build_dir"] = config["bootstrap"]["build_dir"]
    elif "build" in config:
        if "build_dir" in config["build"]:
            flat["build_dir"] = config["build"]["build_dir"]
        elif "dir" in config["build"]:
            flat["build_dir"] = config["build"]["dir"]

    # Set default if not found
    if "build_dir" not in flat:
        flat["build_dir"] = "build"

    # Extract package manager
    if "bootstrap" in config and "package_manager" in config["bootstrap"]:
        flat["package_manager"] = config["bootstrap"]["package_manager"]
    elif "packages" in config:
        flat["package_manager"] = config["packages"].get("manager")

    return flat


def _preview_scripts(project_root: Path, config: dict, platform: str) -> int:
    """
    Preview script content without creating files.

    Args:
        project_root: Project root directory
        config: Configuration dictionary
        platform: Platform to preview ('unix', 'windows', 'powershell', 'all')

    Returns:
        Exit code (0 for success)
    """
    try:
        generator = BootstrapGenerator(project_root, config)
        scripts = generator.preview_scripts()

        print("\n" + "=" * 70)
        print("PREVIEW: Bootstrap Scripts (not created)")
        print("=" * 70)

        if platform in ["unix", "all"]:
            print("\n" + "-" * 70)
            print("bootstrap.sh (Unix/Linux/macOS)")
            print("-" * 70)
            print(scripts["shell"])

        if platform in ["windows", "all"]:
            print("\n" + "-" * 70)
            print("bootstrap.bat (Windows)")
            print("-" * 70)
            print(scripts["batch"])

        if platform in ["powershell", "all"]:
            print("\n" + "-" * 70)
            print("bootstrap.ps1 (PowerShell)")
            print("-" * 70)
            print(scripts["powershell"])

        print("\n" + "=" * 70)
        print("END PREVIEW - No files created")
        print("=" * 70)

    except Exception as e:
        logger.error(f"Failed to preview scripts: {e}")
        print_error("Failed to preview scripts", str(e))
        return 1

    return 0


def _print_success_message(project_root: Path, scripts: Dict[str, Path], config: dict):
    """
    Print success message with script details.

    Args:
        project_root: Project root directory
        scripts: Dictionary of generated scripts
        config: Configuration dictionary
    """
    details = {}

    if scripts:
        script_list = []
        for key, path in scripts.items():
            script_list.append(str(path.relative_to(project_root)))
        details["Generated scripts"] = ", ".join(script_list)

    toolchain = config.get("toolchain", "llvm-18")
    build_type = config.get("build_type", "Release")
    details["Toolchain"] = toolchain
    details["Build type"] = build_type

    next_steps = [
        "Run the bootstrap script to set up your environment:",
        "",
    ]

    # Platform-specific instructions

    if "shell" in scripts:
        next_steps.append("  ./bootstrap.sh      # Linux/macOS")
    if "batch" in scripts:
        next_steps.append("  bootstrap.bat       # Windows Command Prompt")
    if "powershell" in scripts:
        next_steps.append("  .\\bootstrap.ps1    # Windows PowerShell")

    next_steps.extend(
        [
            "",
            "Then build your project:",
            f"  cmake --build {config.get('build_dir', 'build')}",
        ]
    )

    message = format_success_message(
        "Bootstrap scripts generated successfully!", details, next_steps=next_steps
    )
    print()
    print(message)
