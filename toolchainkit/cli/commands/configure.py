"""
Configure command implementation.

Configures toolchain and runs CMake.
"""

import logging
import shutil
import sys
from pathlib import Path
from typing import Optional


from toolchainkit.cli.utils import (
    check_initialized,
    format_success_message,
    get_package_manager_instance,
    load_yaml_config,
    print_error,
    print_warning,
    safe_print,
)

logger = logging.getLogger(__name__)


def run(args) -> int:
    """
    Run the configure command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Configuring ToolchainKit project")
    logger.debug(f"Arguments: {args}")

    # 0. Set environment variables
    if hasattr(args, "env") and args.env:
        import os

        for key, value in args.env:
            os.environ[key] = value
            logger.debug(f"Set environment variable: {key}={value}")

    # 1. Setup paths
    project_root = Path(args.project_root).resolve()

    if args.config:
        config_file = args.config.resolve()
    else:
        config_file = project_root / "toolchainkit.yaml"

    toolchainkit_dir = project_root / ".toolchainkit"

    # 2. Check if initialized
    if not check_initialized(project_root, config_file):
        logger.error("Project not initialized")
        print_error(
            "Project not initialized",
            f"Configuration file not found: {config_file}\n  Run 'tkgen init' first",
        )
        return 1

    # 3. Load configuration
    logger.debug(f"Loading configuration from {config_file}")
    try:
        config = load_yaml_config(config_file, required=True)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load configuration: {e}")
        print_error("Failed to load configuration", str(e))
        return 1

    # 3.5. Auto-detect package manager if not configured or if configured but not available
    configured_pm = (
        config.get("packages", {}).get("manager") if config.get("packages") else None
    )
    should_auto_detect = False

    if not configured_pm:
        logger.debug("No package manager configured, attempting auto-detection")
        should_auto_detect = True
    else:
        # Verify configured package manager is actually available
        try:
            logger.debug(f"Verifying configured package manager: {configured_pm}")
            pm_instance = get_package_manager_instance(
                configured_pm, project_root, config.get("packages", {})
            )
            if not pm_instance.detect():
                logger.warning(
                    f"Configured package manager '{configured_pm}' not found in project "
                    f"(no manifest file detected). Attempting auto-detection..."
                )
                print(
                    f"⚠️  Configured package manager '{configured_pm}' not found, auto-detecting..."
                )
                should_auto_detect = True
        except Exception as e:
            logger.warning(
                f"Failed to verify configured package manager '{configured_pm}': {e}. "
                f"Attempting auto-detection..."
            )
            print(
                f"⚠️  Package manager '{configured_pm}' unavailable, auto-detecting..."
            )
            should_auto_detect = True

    if should_auto_detect:
        try:
            from toolchainkit.packages import PackageManagerDetector
            from toolchainkit.packages.conan import ConanIntegration
            # from toolchainkit.packages.vcpkg import VcpkgIntegration

            detector = PackageManagerDetector(project_root)
            detector.register(ConanIntegration(project_root))
            # detector.register(VcpkgIntegration(project_root))

            primary_pm = detector.detect_primary()
            if primary_pm:
                pm_name = primary_pm.get_name()
                if "packages" not in config:
                    config["packages"] = {}
                config["packages"]["manager"] = pm_name
                logger.info(f"Auto-detected package manager: {pm_name}")
                safe_print(f"✓ Auto-detected package manager: {pm_name}")
            else:
                # No package manager found, clear the invalid config
                if "packages" in config:
                    config["packages"]["manager"] = None
                logger.info("No package manager detected")
                if configured_pm:
                    print(f"No package manager found ('{configured_pm}' not available)")
        except Exception as e:
            logger.warning(f"Package manager detection failed: {e}")

    # 4. Merge CLI arguments with config
    config = _merge_arguments(config, args)
    toolchain_name = args.toolchain

    logger.info(f"Toolchain: {toolchain_name}")
    logger.info(f"Build type: {args.build_type}")
    logger.info(f"Build directory: {args.build_dir}")

    # 5. Setup directories
    toolchainkit_dir.mkdir(exist_ok=True)
    cmake_dir = toolchainkit_dir / "cmake"
    cmake_dir.mkdir(exist_ok=True)

    # 6. Download/verify toolchain
    print(f"Configuring toolchain: {toolchain_name}")
    print(f"Build type: {args.build_type}")
    print(f"Build directory: {args.build_dir}")
    print()

    try:
        from toolchainkit.core.platform import detect_platform
        from toolchainkit.plugins.registry import get_global_registry

        platform_info = detect_platform()
        platform_str = f"{platform_info.os}-{platform_info.arch}"

        # Get toolchain type and version from config if available
        if "toolchain" in config:
            toolchain_type = config["toolchain"].get("type", "")
            version = config["toolchain"].get("version", "latest")
        else:
            # Fallback: parse from toolchain name (format: type-version)
            parts = toolchain_name.rsplit("-", 1)
            if len(parts) == 2:
                toolchain_type, version = parts
            else:
                toolchain_type, version = toolchain_name, "latest"

        logger.debug(
            f"Requesting toolchain: {toolchain_type} {version} for {platform_str}"
        )
        print(f"Downloading toolchain {toolchain_name}...")

        # Get toolchain providers from registry
        registry = get_global_registry()
        providers = registry.get_toolchain_providers()

        if not providers:
            raise RuntimeError(
                "No toolchain providers registered. Ensure plugins are loaded."
            )

        # Define progress callback to show download status
        def show_progress(progress_info):
            """Display download/extraction progress."""

            if progress_info.phase == "downloading":
                # Show download progress bar
                bar_length = 40
                filled = int(bar_length * progress_info.percentage / 100)
                bar = "=" * filled + "-" * (bar_length - filled)

                # Format speed
                speed_mbps = (
                    progress_info.speed_bps / (1024 * 1024)
                    if progress_info.speed_bps
                    else 0
                )

                # Format ETA with h:m:s for large values
                if progress_info.eta_seconds and progress_info.eta_seconds > 0:
                    eta_secs = int(progress_info.eta_seconds)
                    if eta_secs >= 3600:  # 1 hour or more
                        hours = eta_secs // 3600
                        minutes = (eta_secs % 3600) // 60
                        seconds = eta_secs % 60
                        eta_str = f"{hours}h {minutes}m {seconds}s"
                    elif eta_secs >= 60:  # 1 minute or more
                        minutes = eta_secs // 60
                        seconds = eta_secs % 60
                        eta_str = f"{minutes}m {seconds}s"
                    else:
                        eta_str = f"{eta_secs}s"
                else:
                    eta_str = "..."

                print(
                    f"\r  Downloading: [{bar}] {progress_info.percentage:.1f}% | {speed_mbps:.1f} MB/s | ETA: {eta_str}",
                    end="",
                    flush=True,
                )

            elif progress_info.phase == "extracting":
                # Show extraction progress
                bar_length = 40
                filled = int(bar_length * progress_info.percentage / 100)
                bar = "=" * filled + "-" * (bar_length - filled)
                print(
                    f"\r  Extracting:  [{bar}] {progress_info.percentage:.1f}%",
                    end="",
                    flush=True,
                )

            elif progress_info.phase == "complete":
                # Clear the progress line and show completion
                print("\r" + " " * 100 + "\r", end="")  # Clear line

        # Try each provider until one can provide the toolchain
        toolchain_path = None
        toolchain_id = None

        for provider in providers:
            if provider.can_provide(toolchain_type, version):
                logger.info(f"Found provider for {toolchain_type}")
                toolchain_path = provider.provide_toolchain(
                    toolchain_type,
                    version,
                    platform_str,
                    progress_callback=show_progress,
                )
                if toolchain_path:
                    toolchain_id = provider.get_toolchain_id(
                        toolchain_type, version, platform_str
                    )
                    break

        if not toolchain_path:
            raise RuntimeError(
                f"No provider could supply toolchain: {toolchain_type} {version} for {platform_str}"
            )

        logger.info(f"Toolchain installed at: {toolchain_path}")
        print(f"  Toolchain path: {toolchain_path}")
        print()

    except Exception as e:
        logger.error(f"Failed to download toolchain: {e}")
        print_error("Failed to download toolchain", str(e))
        print(
            "  This is expected if you haven't set up toolchain registry yet",
            file=sys.stderr,
        )
        print(
            "  The toolchain download functionality requires Task 14 (Registry) to be fully configured",
            file=sys.stderr,
        )
        print()
        # For now, create a placeholder toolchain file
        toolchain_path = None
        toolchain_id = toolchain_name

    # 7. Generate CMake toolchain file
    logger.debug("Generating CMake toolchain file")
    print("Generating CMake toolchain file...")

    try:
        toolchain_file = cmake_dir / "toolchain.cmake"

        # Determine compiler type from config or toolchain name
        compiler_type = None
        if "toolchain" in config and "type" in config["toolchain"]:
            compiler_type = config["toolchain"]["type"]
            logger.debug(f"Using compiler type from config: {compiler_type}")

        if not compiler_type:
            # Fallback: detect from toolchain name
            if "llvm" in toolchain_name.lower() or "clang" in toolchain_name.lower():
                compiler_type = "clang"
            elif "gcc" in toolchain_name.lower():
                compiler_type = "gcc"
            elif "msvc" in toolchain_name.lower():
                compiler_type = "msvc"
            else:
                # Use the toolchain type directly (e.g., "zig", "rust", etc.)
                compiler_type = toolchain_type

        if toolchain_path:
            # Generate proper toolchain file
            from toolchainkit.cmake.toolchain_generator import (
                CMakeToolchainGenerator,
                ToolchainFileConfig,
            )

            generator = CMakeToolchainGenerator(project_root)

            # Build cross-compile dict if target specified
            cross_compile = None
            if args.target:
                # Parse target triple (e.g., arm64-linux-gnu)
                parts = args.target.split("-")
                if len(parts) >= 2:
                    cross_compile = {
                        "arch": parts[0],
                        "os": parts[1] if len(parts) > 1 else "linux",
                    }

            # Detect Clang tools if we have an LLVM toolchain and config files
            clang_tidy_path = None
            clang_format_path = None

            if compiler_type == "clang":
                bin_dir = toolchain_path / "bin"
                is_windows = sys.platform == "win32"

                # Check for .clang-tidy
                if (project_root / ".clang-tidy").exists():
                    tidy_exe = bin_dir / (
                        "clang-tidy.exe" if is_windows else "clang-tidy"
                    )
                    if tidy_exe.exists():
                        clang_tidy_path = tidy_exe
                        logger.info(f"Found clang-tidy: {tidy_exe}")

                # Check for .clang-format
                if (project_root / ".clang-format").exists():
                    format_exe = bin_dir / (
                        "clang-format.exe" if is_windows else "clang-format"
                    )
                    if format_exe.exists():
                        clang_format_path = format_exe
                        logger.info(f"Found clang-format: {format_exe}")

            config_obj = ToolchainFileConfig(
                toolchain_id=toolchain_id,
                toolchain_path=toolchain_path,
                compiler_type=compiler_type,
                stdlib=args.stdlib,
                linker=None,
                cross_compile=cross_compile,
                clang_tidy_path=clang_tidy_path,
                clang_format_path=clang_format_path,
            )

            toolchain_file = generator.generate(config_obj)
        else:
            # No toolchain path - generate minimal placeholder with strategy flags
            # Try to use compiler strategy if available
            from toolchainkit.plugins.registry import get_global_registry

            registry = get_global_registry()

            strategy_content = ""
            if registry.has_compiler_strategy(compiler_type):
                try:
                    strategy = registry.get_compiler_strategy(compiler_type)

                    # Generate compiler flags from strategy
                    flags = strategy.get_flags(config)
                    if flags:
                        strategy_content = "\n".join(flags) + "\n\n"
                except Exception as e:
                    logger.warning(f"Failed to generate strategy content: {e}")

            content = f"""\
# CMake Toolchain File (Generated by ToolchainKit)
# Toolchain: {toolchain_name}
# Compiler Type: {compiler_type}
# Build Type: {args.build_type}

# WARNING: Toolchain not available
# The configured toolchain could not be downloaded or found.

# Conan toolchain integration (if CONAN_TOOLCHAIN_FILE is provided)
if(DEFINED CONAN_TOOLCHAIN_FILE AND EXISTS ${{CONAN_TOOLCHAIN_FILE}})
    message(STATUS "ToolchainKit: Including Conan toolchain: ${{CONAN_TOOLCHAIN_FILE}}")
    include(${{CONAN_TOOLCHAIN_FILE}})
endif()

{strategy_content}message(WARNING "ToolchainKit: Toolchain '{toolchain_name}' not available")
message(STATUS "  Compiler type: {compiler_type}")
message(STATUS "  Using strategy configuration without toolchain binaries")
"""
            toolchain_file.write_text(content, encoding="utf-8")

        logger.info(f"CMake toolchain file: {toolchain_file}")
        print(f"  Toolchain file: {toolchain_file}")
        print()

    except Exception as e:
        logger.error(f"Failed to generate toolchain file: {e}")
        print_error("Failed to generate toolchain file", str(e))
        return 1

    # 8. Generate Conan profile if using Conan
    # Generate profile even if toolchain download failed (e.g., MSVC on Windows)
    if config.get("packages") and config["packages"].get("manager") == "conan":
        try:
            _generate_conan_profile(
                project_root,
                toolchain_name,
                toolchain_path,
                platform_str,
                args.build_type,
            )
        except Exception as e:
            logger.warning(f"Failed to generate Conan profile: {e}")
            print_warning(f"Failed to generate Conan profile: {e}")
            print()

    # 9. Install package dependencies (if configured)
    if config.get("packages") and config["packages"].get("manager"):
        pkg_manager = config["packages"]["manager"]
        logger.debug(f"Installing dependencies with {pkg_manager}")
        print(f"Installing dependencies ({pkg_manager})...")

        try:
            _install_dependencies(project_root, config["packages"])
            print("  Dependencies installed")
            print()
        except Exception as e:
            logger.warning(f"Failed to install dependencies: {e}")
            print_warning(f"Failed to install dependencies: {e}")
            print()

    # 9. Clean if requested
    build_dir = project_root / args.build_dir
    if args.clean and build_dir.exists():
        logger.info(f"Cleaning build directory: {build_dir}")
        print(f"Cleaning build directory: {build_dir}...")
        try:
            shutil.rmtree(build_dir)
            print("  Build directory cleaned")
            print()
        except Exception as e:
            logger.warning(f"Failed to clean build directory: {e}")
            print_warning(f"Failed to clean build directory: {e}")
            print()

    # 10. Bootstrap mode (if requested)
    if hasattr(args, "bootstrap") and args.bootstrap:
        return _run_bootstrap(
            project_root, args, config, toolchain_file, toolchain_path
        )

    # 11. CMake configuration
    # Note: CMake configuration is handled by the bootstrap script or user
    # after package dependencies are installed. We don't run CMake here
    # to avoid issues with missing dependencies.
    logger.info("Toolchain configured successfully")
    print("Toolchain configured successfully!")
    print()
    print("Next steps:")
    print("  1. Install package dependencies (if using Conan/vcpkg)")
    print(
        f"  2. Run CMake: cmake -B {build_dir} -S {project_root} -DCMAKE_TOOLCHAIN_FILE={toolchain_file}"
    )
    print(f"  3. Build: cmake --build {build_dir} --config {args.build_type}")
    # 12. Update state
    logger.debug("Updating project state")
    try:
        from toolchainkit.core.state import StateManager

        state = StateManager(project_root)
        state.update_toolchain(toolchain_id, "")
        state.update_build_config(build_dir, args.build_type)
    except Exception as e:
        logger.warning(f"Failed to update state: {e}")
        # Not critical, continue

    logger.info("Toolchain configuration complete")
    return 0


def _run_bootstrap(
    project_root: Path,
    args,
    config: dict,
    toolchain_file: Path,
    toolchain_path: Optional[Path],
) -> int:
    """
    Run bootstrap steps (Ninja, Dependencies, CMake).

    Args:
        project_root: Project root directory
        args: CLI arguments
        config: Project configuration
        toolchain_file: Generated toolchain file path
        toolchain_path: Toolchain installation path

    Returns:
        Exit code
    """
    import subprocess
    import os
    from toolchainkit.packages.tool_downloader import NinjaDownloader
    from toolchainkit.core.platform import detect_platform

    logger.info("Running bootstrap steps...")
    print("Bootstrapping project...")
    print()

    # 1. Setup build system generator (if needed)
    # Query the compiler strategy for its preferred generator
    platform = detect_platform()
    use_ninja = False
    ninja_path = None
    preferred_generator = None

    # Try to get preferred generator from config or strategy
    from toolchainkit.plugins.registry import get_global_registry

    registry = get_global_registry()

    # Determine compiler type from config
    compiler_type = None
    if "toolchain" in config and "type" in config["toolchain"]:
        compiler_type = config["toolchain"]["type"]

    # Check config for generator preference first
    # Check defaults or build section
    configured_generator = None
    if "defaults" in config and "generator" in config["defaults"]:
        configured_generator = config["defaults"]["generator"]
    elif "build" in config and "generator" in config["build"]:
        configured_generator = config["build"]["generator"]

    if configured_generator:
        # Use user configured generator
        preferred_generator = configured_generator
        logger.debug(f"Using configured generator: {preferred_generator}")
    elif compiler_type and registry.has_compiler_strategy(compiler_type):
        try:
            strategy = registry.get_compiler_strategy(compiler_type)
            preferred_generator = strategy.get_preferred_generator(platform)
            logger.debug(f"Strategy preferred generator: {preferred_generator}")
        except Exception as e:
            logger.warning(f"Failed to query strategy for preferred generator: {e}")

    # Setup Ninja if it's the preferred generator
    if preferred_generator == "Ninja":
        logger.info("Strategy requires Ninja generator, setting up Ninja...")
        print("Setting up Ninja build system...")

        try:
            tools_dir = project_root / ".toolchainkit" / "tools"
            downloader = NinjaDownloader(tools_dir, platform=platform)
            if not downloader.is_installed():
                downloader.download()

            ninja_path = downloader.get_executable_path()
            if ninja_path:
                use_ninja = True
                # Add to PATH for this process
                ninja_dir = ninja_path.parent
                os.environ["PATH"] = str(ninja_dir) + os.pathsep + os.environ["PATH"]
                print(f"  Ninja installed: {ninja_path}")
        except Exception as e:
            logger.warning(f"Failed to setup Ninja: {e}")
            print_warning(f"Failed to setup Ninja: {e}")

    # 2. Install Dependencies
    if config.get("packages") and config["packages"].get("manager"):
        pkg_manager = config["packages"]["manager"]
        logger.info(f"Installing dependencies with {pkg_manager}...")
        print(f"Installing dependencies ({pkg_manager})...")

        try:
            manager = get_package_manager_instance(
                pkg_manager, project_root, config["packages"]
            )
            if manager.detect():
                # Pass bootstrap-specific args
                install_kwargs = {
                    "build_type": args.build_type,
                }

                if pkg_manager == "conan":
                    # Use generated profile
                    profile_path = (
                        project_root
                        / ".toolchainkit"
                        / "conan"
                        / "profiles"
                        / "default"
                    )
                    if profile_path.exists():
                        install_kwargs["profile_path"] = profile_path

                    if use_ninja and platform.os == "windows":
                        # Pass 1: Build dependencies with default generator (VS)
                        # This ensures ABI compatibility and successful build without manual vcvars setup
                        logger.info("Building dependencies (Phase 1: Build)...")
                        print("  Building dependencies (Phase 1)...")
                        manager.install_dependencies(**install_kwargs)

                        # Pass 2: Generate toolchain for Ninja
                        # This ensures the generated CMake toolchain is compatible with Ninja
                        logger.info(
                            "Configuring toolchain for Ninja (Phase 2: Generate)..."
                        )
                        print("  Configuring toolchain for Ninja (Phase 2)...")
                        install_kwargs["generator"] = "Ninja"
                        manager.install_dependencies(**install_kwargs)

                    elif use_ninja:
                        install_kwargs["generator"] = "Ninja"
                        manager.install_dependencies(**install_kwargs)

                    else:
                        manager.install_dependencies(**install_kwargs)

                else:
                    manager.install_dependencies(**install_kwargs)

                print("  Dependencies installed")
                print()
            else:
                print(f"  No {pkg_manager} manifest found, skipping dependencies")
        except Exception as e:
            logger.error(f"Dependency installation failed: {e}")
            print_error("Dependency installation failed", str(e))
            return 1

    # 3. Run CMake
    build_dir = project_root / args.build_dir
    logger.info(f"Configuring CMake in {build_dir}...")
    print("Configuring CMake...")

    cmake_cmd = ["cmake", "-B", str(build_dir), "-S", str(project_root)]

    if use_ninja:
        cmake_cmd.extend(["-G", "Ninja"])
    elif preferred_generator:
        # Pass other generators if specified
        cmake_cmd.extend(["-G", preferred_generator])

    # Toolchain file selection
    # We use the ToolchainKit toolchain as primary
    cmake_cmd.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}")

    # Pass Conan toolchain if it exists
    conan_toolchain = build_dir / "conan_toolchain.cmake"
    if conan_toolchain.exists():
        cmake_cmd.append(f"-DCONAN_TOOLCHAIN_FILE={conan_toolchain}")

    # Build type
    cmake_cmd.append(f"-DCMAKE_BUILD_TYPE={args.build_type}")

    # Extra args
    if hasattr(args, "cmake_args") and args.cmake_args:
        cmake_cmd.extend(args.cmake_args)

    try:
        logger.debug(f"Running CMake: {cmake_cmd}")
        subprocess.run(cmake_cmd, check=True)
        print("  CMake configuration successful")
        print()
    except subprocess.CalledProcessError as e:
        logger.error(f"CMake configuration failed: {e}")
        print_error("CMake configuration failed", str(e))
        return 1

    # Success
    _print_success_message(args.toolchain, build_dir, args.build_type)
    return 0


def _merge_arguments(config: dict, args) -> dict:
    """
    Merge command-line arguments with config file.
    CLI args override config file values.

    Args:
        config: Configuration dictionary from file
        args: Parsed command-line arguments

    Returns:
        Merged configuration dictionary
    """
    # Start with config file
    merged = config.copy()

    # Override with CLI args (CLI takes precedence)
    if not merged.get("build"):
        merged["build"] = {}

    merged["build"]["build_type"] = args.build_type
    merged["build"]["build_dir"] = args.build_dir

    return merged


def _generate_conan_profile(
    project_root: Path,
    toolchain_name: str,
    toolchain_path: Path,
    platform_str: str,
    build_type: str = "Release",
):
    """
    Generate a Conan profile for the ToolchainKit toolchain.

    Args:
        project_root: Project root directory
        toolchain_name: Name of the toolchain
        toolchain_path: Path to the toolchain installation
        platform_str: Platform string (os-arch)
        build_type: Build type (Debug/Release/etc.)
    """

    logger.debug(f"Generating Conan profile for {toolchain_name}")
    print(f"Generating Conan profile for {toolchain_name}...")

    # Create Conan profiles directory
    # Use 'profiles/default' to match Conan's expected default profile location
    profile_dir = project_root / ".toolchainkit" / "conan" / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profile_dir / "default"

    # Parse toolchain name
    parts = toolchain_name.rsplit("-", 1)
    if len(parts) == 2:
        vendor, version = parts
    else:
        vendor, version = toolchain_name, "latest"

    # Parse platform
    platform_parts = platform_str.split("-")
    os_name = platform_parts[0] if len(platform_parts) > 0 else "linux"
    arch = platform_parts[1] if len(platform_parts) > 1 else "x86_64"

    # Map to Conan settings
    os_map = {
        "linux": "Linux",
        "macos": "Macos",
        "darwin": "Macos",
        "windows": "Windows",
        "android": "Android",
        "ios": "iOS",
    }

    arch_map = {
        "x86_64": "x86_64",
        "x64": "x86_64",
        "amd64": "x86_64",
        "arm64": "armv8",
        "aarch64": "armv8",
    }

    conan_os = os_map.get(os_name.lower(), "Linux")
    conan_arch = arch_map.get(arch.lower(), "x86_64")

    # On Windows, use MSVC profile for Conan packages (for compatibility with prebuilt binaries)
    # The actual project will still use LLVM toolchain via CMake
    if conan_os == "Windows":
        # Use MSVC for Conan package builds
        conan_compiler = "msvc"
        compiler_version = "193"  # Visual Studio 2022
        runtime = "dynamic"
        # Map CMake build type to Conan runtime_type (only Debug or Release allowed)
        # RelWithDebInfo and MinSizeRel use Release runtime
        runtime_type = "Debug" if build_type == "Debug" else "Release"

        # Generate Windows MSVC profile
        profile_content = f"""# Conan profile generated by ToolchainKit
# Toolchain: {toolchain_name} (using MSVC profile for Conan packages)
# Generated for: {platform_str}
# Note: Project will use LLVM toolchain via CMake, Conan packages use MSVC for compatibility

[settings]
os={conan_os}
arch={conan_arch}
compiler={conan_compiler}
compiler.version={compiler_version}
compiler.cppstd=17
compiler.runtime={runtime}
compiler.runtime_type={runtime_type}
build_type={build_type}
"""
    else:
        # For Linux/macOS, use the actual toolchain compiler
        compiler_map = {
            "llvm": "clang",
            "clang": "clang",
            "gcc": "gcc",
            "msvc": "msvc",
        }

        conan_compiler = compiler_map.get(vendor.lower(), "gcc")

        # Extract major version
        version_parts = version.split(".")
        compiler_version = version_parts[0] if version_parts else "18"

        # Determine libcxx
        if conan_compiler == "clang":
            libcxx = "libc++"
        else:
            libcxx = "libstdc++11"

        # Determine compiler executables
        if toolchain_path:
            bin_dir = toolchain_path / "bin"
            c_compiler = bin_dir / "clang"
            cxx_compiler = bin_dir / "clang++"

            c_compiler_str = str(c_compiler).replace("\\", "/")
            cxx_compiler_str = str(cxx_compiler).replace("\\", "/")
        else:
            c_compiler_str = "clang"
            cxx_compiler_str = "clang++"

        # Generate Linux/macOS profile with actual toolchain
        profile_content = f"""# Conan profile generated by ToolchainKit
# Toolchain: {toolchain_name}
# Generated for: {platform_str}

[settings]
os={conan_os}
arch={conan_arch}
compiler={conan_compiler}
compiler.version={compiler_version}
compiler.libcxx={libcxx}
compiler.cppstd=17
build_type={build_type}

[buildenv]
CC={c_compiler_str}
CXX={cxx_compiler_str}

[conf]
tools.build:compiler_executables={{"c": "{c_compiler_str}", "cpp": "{cxx_compiler_str}"}}
"""

    # Write profile
    try:
        profile_path.write_text(profile_content, encoding="utf-8")
        logger.info(f"Conan profile generated: {profile_path}")
        print(f"  Conan profile: {profile_path}")
        print()
    except Exception as e:
        raise Exception(f"Failed to write Conan profile to {profile_path}: {e}") from e


def _install_dependencies(project_root: Path, packages_config: dict):
    """
    Install package dependencies based on configuration.

    Args:
        project_root: Project root directory
        packages_config: Package manager configuration
    """
    manager_name = packages_config.get("manager")
    if not manager_name:
        return

    try:
        # Get package manager instance
        manager = get_package_manager_instance(
            manager_name, project_root, packages_config
        )

        # Detect if used
        if manager.detect():
            # Install dependencies
            # Pass config if needed (currently install_dependencies takes no args in base,
            # but ConanIntegration takes profile_path. We might need to standardize this.)

            # For now, handle Conan specific config if possible, or rely on defaults
            if manager_name == "conan":
                # Use generated ToolchainKit profile if it exists
                profile_path = (
                    project_root / ".toolchainkit" / "conan" / "profiles" / "default"
                )
                if profile_path.exists():
                    logger.debug(f"Using ToolchainKit Conan profile: {profile_path}")
                    manager.install_dependencies(profile_path=profile_path)
                elif packages_config.get("conan") and packages_config["conan"].get(
                    "profile"
                ):
                    profile = packages_config["conan"].get("profile")
                    manager.install_dependencies(
                        profile_path=Path(profile) if profile else None
                    )
                else:
                    manager.install_dependencies()
            else:
                manager.install_dependencies()
        else:
            logger.info(
                f"Package manager {manager_name} configured but not detected in project"
            )

    except KeyError:
        # Fallback for legacy/hardcoded support if not in registry
        if manager_name == "vcpkg":
            logger.info("vcpkg integration via CMake toolchain file")
        elif manager_name == "cpm":
            logger.info("CPM.cmake - dependencies managed by CMake")
        else:
            logger.warning(f"Unknown package manager: {manager_name}")
            print_warning(f"Unknown package manager: {manager_name}")
    except Exception as e:
        raise e


def _print_success_message(toolchain_name: str, build_dir: Path, build_type: str):
    """
    Print success message with next steps.

    Args:
        toolchain_name: Name of configured toolchain
        build_dir: Build directory path
        build_type: Build type (Debug/Release/etc.)
    """
    next_steps = [
        f"cmake --build {build_dir}",
    ]
    if build_type != "Debug":
        next_steps.append(f"# Or: cmake --build {build_dir} --config {build_type}")
    next_steps.append("")
    next_steps.append("For help: tkgen --help")

    message = format_success_message(
        "Configuration complete!",
        {
            "Toolchain": toolchain_name,
            "Build directory": build_dir,
            "Build type": build_type,
        },
        next_steps=next_steps,
    )
    print(message)
