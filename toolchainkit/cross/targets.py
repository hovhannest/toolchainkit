"""
Cross-compilation target configuration.

This module provides tools for configuring cross-compilation targets for various
platforms including Android, iOS, and embedded systems.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class CrossCompileTarget:
    """
    Cross-compilation target specification.

    This dataclass represents a complete cross-compilation target with all
    necessary information to configure CMake for cross-compilation.

    Attributes:
        system_name: Target operating system (e.g., 'Android', 'iOS', 'Linux')
        system_processor: Target CPU architecture (e.g., 'aarch64', 'arm64', 'x86_64')
        sysroot: Optional path to the target system root directory
        toolchain_prefix: Optional prefix for cross-compiler binaries (e.g., 'arm-linux-gnueabihf-')
        cmake_system_version: Optional CMake system version (API level for Android, deployment target for iOS)
    """

    system_name: str
    system_processor: str
    sysroot: Optional[Path] = None
    toolchain_prefix: Optional[str] = None
    cmake_system_version: Optional[str] = None


class CrossCompilationConfigurator:
    """
    Configure cross-compilation targets.

    This class provides methods to configure cross-compilation for various platforms,
    generating the necessary CMake variables and configuration.
    """

    def configure_android(
        self, ndk_path: Path, abi: str = "arm64-v8a", api_level: int = 21
    ) -> CrossCompileTarget:
        """
        Configure Android NDK cross-compilation.

        Args:
            ndk_path: Path to Android NDK installation
            abi: Android ABI (arm64-v8a, armeabi-v7a, x86_64, x86)
            api_level: Android API level (minimum 21 for modern Android)

        Returns:
            CrossCompileTarget configured for Android

        Raises:
            ValueError: If ABI is not supported

        Example:
            >>> configurator = CrossCompilationConfigurator()
            >>> ndk = Path('/opt/android-ndk')
            >>> target = configurator.configure_android(ndk, 'arm64-v8a', 21)
            >>> print(target.system_name)
            'Android'
        """
        processor_map = {
            "arm64-v8a": "aarch64",
            "armeabi-v7a": "armv7-a",
            "x86_64": "x86_64",
            "x86": "i686",
        }

        if abi not in processor_map:
            raise ValueError(
                f"Unsupported Android ABI: {abi}. "
                f"Supported ABIs: {', '.join(processor_map.keys())}"
            )

        # Determine the prebuilt directory based on host platform
        import platform

        system = platform.system().lower()
        if system == "windows":
            prebuilt = "windows-x86_64"
        elif system == "darwin":
            prebuilt = "darwin-x86_64"
        else:  # Linux
            prebuilt = "linux-x86_64"

        sysroot = ndk_path / "toolchains" / "llvm" / "prebuilt" / prebuilt / "sysroot"

        return CrossCompileTarget(
            system_name="Android",
            system_processor=processor_map[abi],
            sysroot=sysroot,
            cmake_system_version=str(api_level),
        )

    def configure_ios(
        self, sdk: str = "iphoneos", deployment_target: str = "12.0"
    ) -> CrossCompileTarget:
        """
        Configure iOS cross-compilation.

        Args:
            sdk: iOS SDK ('iphoneos' for device, 'iphonesimulator' for simulator)
            deployment_target: Minimum iOS version (e.g., '12.0', '14.0')

        Returns:
            CrossCompileTarget configured for iOS

        Raises:
            ValueError: If SDK is not supported

        Example:
            >>> configurator = CrossCompilationConfigurator()
            >>> target = configurator.configure_ios('iphoneos', '12.0')
            >>> print(target.system_processor)
            'arm64'
        """
        if sdk not in ["iphoneos", "iphonesimulator"]:
            raise ValueError(
                f"Unsupported iOS SDK: {sdk}. "
                f"Supported SDKs: iphoneos, iphonesimulator"
            )

        processor = "arm64" if sdk == "iphoneos" else "x86_64"

        return CrossCompileTarget(
            system_name="iOS",
            system_processor=processor,
            cmake_system_version=deployment_target,
        )

    def configure_raspberry_pi(
        self, sysroot: Path, arch: str = "armv7"
    ) -> CrossCompileTarget:
        """
        Configure Raspberry Pi cross-compilation.

        Args:
            sysroot: Path to Raspberry Pi sysroot
            arch: Target architecture ('armv7' for Pi 2/3, 'aarch64' for Pi 3/4 64-bit)

        Returns:
            CrossCompileTarget configured for Raspberry Pi

        Raises:
            ValueError: If architecture is not supported

        Example:
            >>> configurator = CrossCompilationConfigurator()
            >>> sysroot = Path('/opt/rpi-sysroot')
            >>> target = configurator.configure_raspberry_pi(sysroot, 'armv7')
            >>> print(target.toolchain_prefix)
            'arm-linux-gnueabihf-'
        """
        if arch not in ["armv7", "aarch64"]:
            raise ValueError(
                f"Unsupported Raspberry Pi architecture: {arch}. "
                f"Supported architectures: armv7, aarch64"
            )

        # Toolchain prefix depends on architecture
        if arch == "armv7":
            toolchain_prefix = "arm-linux-gnueabihf-"
        else:  # aarch64
            toolchain_prefix = "aarch64-linux-gnu-"

        return CrossCompileTarget(
            system_name="Linux",
            system_processor=arch,
            sysroot=sysroot,
            toolchain_prefix=toolchain_prefix,
        )

    def generate_cmake_variables(self, target: CrossCompileTarget) -> dict:
        """
        Generate CMake variables for cross-compilation.

        This method generates a dictionary of CMake variables required for
        cross-compilation, including system name, processor, sysroot, and
        find root path settings.

        Args:
            target: Cross-compilation target specification

        Returns:
            Dictionary of CMake variable names to values

        Example:
            >>> configurator = CrossCompilationConfigurator()
            >>> target = configurator.configure_ios()
            >>> vars = configurator.generate_cmake_variables(target)
            >>> print(vars['CMAKE_SYSTEM_NAME'])
            'iOS'
        """
        vars = {
            "CMAKE_SYSTEM_NAME": target.system_name,
            "CMAKE_SYSTEM_PROCESSOR": target.system_processor,
        }

        if target.sysroot:
            vars["CMAKE_SYSROOT"] = str(target.sysroot)
            vars["CMAKE_FIND_ROOT_PATH"] = str(target.sysroot)
            vars["CMAKE_FIND_ROOT_PATH_MODE_PROGRAM"] = "NEVER"
            vars["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "ONLY"
            vars["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "ONLY"

        if target.cmake_system_version:
            vars["CMAKE_SYSTEM_VERSION"] = target.cmake_system_version

        if target.toolchain_prefix:
            vars["CMAKE_C_COMPILER"] = f"{target.toolchain_prefix}gcc"
            vars["CMAKE_CXX_COMPILER"] = f"{target.toolchain_prefix}g++"

        return vars

    def generate_cmake_snippet(self, target: CrossCompileTarget) -> str:
        """
        Generate CMake configuration snippet.

        This method generates a ready-to-use CMake code snippet that can be
        included in a CMake toolchain file.

        Args:
            target: Cross-compilation target specification

        Returns:
            CMake code snippet as a string

        Example:
            >>> configurator = CrossCompilationConfigurator()
            >>> target = configurator.configure_ios()
            >>> snippet = configurator.generate_cmake_snippet(target)
            >>> print(snippet)
            # Cross-compilation for iOS arm64
            <BLANKLINE>
            set(CMAKE_SYSTEM_NAME "iOS")
            set(CMAKE_SYSTEM_PROCESSOR "arm64")
            set(CMAKE_SYSTEM_VERSION "12.0")
        """
        lines = [
            f"# Cross-compilation for {target.system_name} {target.system_processor}",
            "",
        ]

        for key, value in self.generate_cmake_variables(target).items():
            lines.append(f'set({key} "{value}")')

        return "\n".join(lines)
