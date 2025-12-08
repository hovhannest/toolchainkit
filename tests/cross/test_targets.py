"""
Unit tests for cross-compilation target configuration.
"""

import pytest
from pathlib import Path
from toolchainkit.cross.targets import CrossCompileTarget, CrossCompilationConfigurator


class TestCrossCompileTarget:
    """Tests for CrossCompileTarget dataclass."""

    def test_minimal_target(self):
        """Test creation with minimal required fields."""
        target = CrossCompileTarget(system_name="Linux", system_processor="x86_64")

        assert target.system_name == "Linux"
        assert target.system_processor == "x86_64"
        assert target.sysroot is None
        assert target.toolchain_prefix is None
        assert target.cmake_system_version is None

    def test_complete_target(self):
        """Test creation with all fields."""
        sysroot = Path("/opt/sysroot")
        target = CrossCompileTarget(
            system_name="Android",
            system_processor="aarch64",
            sysroot=sysroot,
            toolchain_prefix="aarch64-linux-android-",
            cmake_system_version="21",
        )

        assert target.system_name == "Android"
        assert target.system_processor == "aarch64"
        assert target.sysroot == sysroot
        assert target.toolchain_prefix == "aarch64-linux-android-"
        assert target.cmake_system_version == "21"

    def test_dataclass_fields(self):
        """Test that dataclass has expected fields."""
        target = CrossCompileTarget("Linux", "x86_64")

        assert hasattr(target, "system_name")
        assert hasattr(target, "system_processor")
        assert hasattr(target, "sysroot")
        assert hasattr(target, "toolchain_prefix")
        assert hasattr(target, "cmake_system_version")


class TestAndroidConfiguration:
    """Tests for Android NDK configuration."""

    def test_android_arm64_v8a(self):
        """Test Android arm64-v8a configuration."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)

        assert target.system_name == "Android"
        assert target.system_processor == "aarch64"
        assert target.cmake_system_version == "21"
        assert target.sysroot is not None
        assert "sysroot" in str(target.sysroot)

    def test_android_armeabi_v7a(self):
        """Test Android armeabi-v7a configuration."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path, "armeabi-v7a", 21)

        assert target.system_name == "Android"
        assert target.system_processor == "armv7-a"
        assert target.cmake_system_version == "21"

    def test_android_x86_64(self):
        """Test Android x86_64 configuration."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path, "x86_64", 29)

        assert target.system_name == "Android"
        assert target.system_processor == "x86_64"
        assert target.cmake_system_version == "29"

    def test_android_x86(self):
        """Test Android x86 configuration."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path, "x86", 21)

        assert target.system_name == "Android"
        assert target.system_processor == "i686"
        assert target.cmake_system_version == "21"

    def test_android_default_abi(self):
        """Test Android with default ABI."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path)

        assert target.system_name == "Android"
        assert target.system_processor == "aarch64"  # Default is arm64-v8a
        assert target.cmake_system_version == "21"  # Default API level

    def test_android_different_api_levels(self):
        """Test Android with different API levels."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        for api_level in [21, 23, 28, 29, 30, 33]:
            target = configurator.configure_android(ndk_path, "arm64-v8a", api_level)
            assert target.cmake_system_version == str(api_level)

    def test_android_invalid_abi(self):
        """Test Android with invalid ABI."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        with pytest.raises(ValueError, match="Unsupported Android ABI"):
            configurator.configure_android(ndk_path, "invalid-abi", 21)

    def test_android_sysroot_path_structure(self):
        """Test Android sysroot path has correct structure."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)

        # Check path components
        sysroot_str = str(target.sysroot)
        assert "toolchains" in sysroot_str
        assert "llvm" in sysroot_str
        assert "prebuilt" in sysroot_str
        assert "sysroot" in sysroot_str


class TestIOSConfiguration:
    """Tests for iOS configuration."""

    def test_ios_device(self):
        """Test iOS device configuration."""
        configurator = CrossCompilationConfigurator()

        target = configurator.configure_ios("iphoneos", "12.0")

        assert target.system_name == "iOS"
        assert target.system_processor == "arm64"
        assert target.cmake_system_version == "12.0"
        assert target.sysroot is None  # iOS doesn't require explicit sysroot

    def test_ios_simulator(self):
        """Test iOS simulator configuration."""
        configurator = CrossCompilationConfigurator()

        target = configurator.configure_ios("iphonesimulator", "12.0")

        assert target.system_name == "iOS"
        assert target.system_processor == "x86_64"
        assert target.cmake_system_version == "12.0"

    def test_ios_default_settings(self):
        """Test iOS with default settings."""
        configurator = CrossCompilationConfigurator()

        target = configurator.configure_ios()

        assert target.system_name == "iOS"
        assert target.system_processor == "arm64"  # Default is iphoneos
        assert target.cmake_system_version == "12.0"  # Default deployment target

    def test_ios_different_deployment_targets(self):
        """Test iOS with different deployment targets."""
        configurator = CrossCompilationConfigurator()

        for target_version in ["10.0", "11.0", "12.0", "13.0", "14.0", "15.0"]:
            target = configurator.configure_ios("iphoneos", target_version)
            assert target.cmake_system_version == target_version

    def test_ios_invalid_sdk(self):
        """Test iOS with invalid SDK."""
        configurator = CrossCompilationConfigurator()

        with pytest.raises(ValueError, match="Unsupported iOS SDK"):
            configurator.configure_ios("invalid-sdk", "12.0")


class TestRaspberryPiConfiguration:
    """Tests for Raspberry Pi configuration."""

    def test_raspberry_pi_armv7(self):
        """Test Raspberry Pi armv7 configuration."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")

        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        assert target.system_name == "Linux"
        assert target.system_processor == "armv7"
        assert target.sysroot == sysroot
        assert target.toolchain_prefix == "arm-linux-gnueabihf-"

    def test_raspberry_pi_aarch64(self):
        """Test Raspberry Pi aarch64 configuration."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot-64")

        target = configurator.configure_raspberry_pi(sysroot, "aarch64")

        assert target.system_name == "Linux"
        assert target.system_processor == "aarch64"
        assert target.sysroot == sysroot
        assert target.toolchain_prefix == "aarch64-linux-gnu-"

    def test_raspberry_pi_default_arch(self):
        """Test Raspberry Pi with default architecture."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")

        target = configurator.configure_raspberry_pi(sysroot)

        assert target.system_processor == "armv7"  # Default is armv7
        assert target.toolchain_prefix == "arm-linux-gnueabihf-"

    def test_raspberry_pi_invalid_arch(self):
        """Test Raspberry Pi with invalid architecture."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")

        with pytest.raises(ValueError, match="Unsupported Raspberry Pi architecture"):
            configurator.configure_raspberry_pi(sysroot, "invalid-arch")


class TestCMakeVariableGeneration:
    """Tests for CMake variable generation."""

    def test_minimal_target_variables(self):
        """Test variable generation for minimal target."""
        configurator = CrossCompilationConfigurator()
        target = CrossCompileTarget("Linux", "x86_64")

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSTEM_NAME"] == "Linux"
        assert vars["CMAKE_SYSTEM_PROCESSOR"] == "x86_64"
        assert "CMAKE_SYSROOT" not in vars
        assert "CMAKE_SYSTEM_VERSION" not in vars

    def test_target_with_sysroot(self):
        """Test variable generation with sysroot."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/sysroot")
        target = CrossCompileTarget("Linux", "arm", sysroot=sysroot)

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSROOT"] == str(sysroot)
        assert vars["CMAKE_FIND_ROOT_PATH"] == str(sysroot)
        assert vars["CMAKE_FIND_ROOT_PATH_MODE_PROGRAM"] == "NEVER"
        assert vars["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] == "ONLY"
        assert vars["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] == "ONLY"

    def test_target_with_toolchain_prefix(self):
        """Test variable generation with toolchain prefix."""
        configurator = CrossCompilationConfigurator()
        target = CrossCompileTarget(
            "Linux", "arm", toolchain_prefix="arm-linux-gnueabihf-"
        )

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_C_COMPILER"] == "arm-linux-gnueabihf-gcc"
        assert vars["CMAKE_CXX_COMPILER"] == "arm-linux-gnueabihf-g++"

    def test_target_with_system_version(self):
        """Test variable generation with system version."""
        configurator = CrossCompilationConfigurator()
        target = CrossCompileTarget("Android", "aarch64", cmake_system_version="21")

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSTEM_VERSION"] == "21"

    def test_android_variables(self):
        """Test variable generation for Android target."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")
        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSTEM_NAME"] == "Android"
        assert vars["CMAKE_SYSTEM_PROCESSOR"] == "aarch64"
        assert vars["CMAKE_SYSTEM_VERSION"] == "21"
        assert "CMAKE_SYSROOT" in vars
        assert "CMAKE_FIND_ROOT_PATH" in vars

    def test_ios_variables(self):
        """Test variable generation for iOS target."""
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_ios("iphoneos", "12.0")

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSTEM_NAME"] == "iOS"
        assert vars["CMAKE_SYSTEM_PROCESSOR"] == "arm64"
        assert vars["CMAKE_SYSTEM_VERSION"] == "12.0"
        assert "CMAKE_SYSROOT" not in vars  # iOS doesn't use explicit sysroot

    def test_raspberry_pi_variables(self):
        """Test variable generation for Raspberry Pi target."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSTEM_NAME"] == "Linux"
        assert vars["CMAKE_SYSTEM_PROCESSOR"] == "armv7"
        assert vars["CMAKE_SYSROOT"] == str(sysroot)
        assert vars["CMAKE_C_COMPILER"] == "arm-linux-gnueabihf-gcc"
        assert vars["CMAKE_CXX_COMPILER"] == "arm-linux-gnueabihf-g++"


class TestCMakeSnippetGeneration:
    """Tests for CMake snippet generation."""

    def test_minimal_snippet(self):
        """Test CMake snippet for minimal target."""
        configurator = CrossCompilationConfigurator()
        target = CrossCompileTarget("Linux", "x86_64")

        snippet = configurator.generate_cmake_snippet(target)

        assert "# Cross-compilation for Linux x86_64" in snippet
        assert 'set(CMAKE_SYSTEM_NAME "Linux")' in snippet
        assert 'set(CMAKE_SYSTEM_PROCESSOR "x86_64")' in snippet

    def test_android_snippet(self):
        """Test CMake snippet for Android target."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")
        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)

        snippet = configurator.generate_cmake_snippet(target)

        assert "Android" in snippet
        assert "aarch64" in snippet
        assert "CMAKE_SYSTEM_NAME" in snippet
        assert "CMAKE_SYSTEM_VERSION" in snippet
        assert "CMAKE_SYSROOT" in snippet

    def test_ios_snippet(self):
        """Test CMake snippet for iOS target."""
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_ios("iphoneos", "14.0")

        snippet = configurator.generate_cmake_snippet(target)

        assert "iOS" in snippet
        assert "arm64" in snippet
        assert "CMAKE_SYSTEM_VERSION" in snippet
        assert "14.0" in snippet

    def test_raspberry_pi_snippet(self):
        """Test CMake snippet for Raspberry Pi target."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        snippet = configurator.generate_cmake_snippet(target)

        assert "Linux" in snippet
        assert "armv7" in snippet
        assert "CMAKE_SYSROOT" in snippet
        assert "CMAKE_C_COMPILER" in snippet
        assert "arm-linux-gnueabihf-gcc" in snippet

    def test_snippet_format(self):
        """Test CMake snippet has proper format."""
        configurator = CrossCompilationConfigurator()
        target = CrossCompileTarget("Linux", "arm")

        snippet = configurator.generate_cmake_snippet(target)

        lines = snippet.split("\n")
        # First line should be a comment
        assert lines[0].startswith("#")
        # Second line should be empty
        assert lines[1] == ""
        # Remaining lines should be set() commands
        for line in lines[2:]:
            if line:  # Skip empty lines
                assert line.startswith("set(")
                assert line.endswith(")")

    def test_snippet_all_variables(self):
        """Test snippet contains all generated variables."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/sysroot")
        target = CrossCompileTarget(
            "Linux",
            "arm",
            sysroot=sysroot,
            toolchain_prefix="arm-linux-gnueabihf-",
            cmake_system_version="1.0",
        )

        snippet = configurator.generate_cmake_snippet(target)
        vars = configurator.generate_cmake_variables(target)

        # All variables should be in the snippet
        for key in vars.keys():
            assert key in snippet


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_ndk_path(self):
        """Test Android configuration with empty path."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("")

        # Should not raise exception, just create path
        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)
        assert target is not None

    def test_special_characters_in_path(self):
        """Test paths with special characters."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/sysroot with spaces/arm")

        target = configurator.configure_raspberry_pi(sysroot, "armv7")
        vars = configurator.generate_cmake_variables(target)

        assert vars["CMAKE_SYSROOT"] == str(sysroot)

    def test_windows_path_style(self):
        """Test with Windows-style paths."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("C:\\opt\\sysroot")

        target = configurator.configure_raspberry_pi(sysroot, "armv7")
        vars = configurator.generate_cmake_variables(target)

        # Path should be converted to string properly
        assert vars["CMAKE_SYSROOT"] == str(sysroot)

    def test_configurator_reuse(self):
        """Test that configurator can be reused for multiple targets."""
        configurator = CrossCompilationConfigurator()

        target1 = configurator.configure_ios("iphoneos", "12.0")
        target2 = configurator.configure_android(Path("/ndk"), "arm64-v8a", 21)
        target3 = configurator.configure_raspberry_pi(Path("/sysroot"), "armv7")

        # All targets should be independent
        assert target1.system_name == "iOS"
        assert target2.system_name == "Android"
        assert target3.system_name == "Linux"


class TestCrossTargetsCoverage:
    """Additional coverage tests."""

    def test_configure_android_platform_paths(self):
        """Test configure_android with different host platforms."""
        from unittest.mock import patch

        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        # Test Windows
        with patch("platform.system", return_value="Windows"):
            target = configurator.configure_android(ndk_path, "arm64-v8a", 21)
            assert "windows-x86_64" in str(target.sysroot)

        # Test Darwin
        with patch("platform.system", return_value="Darwin"):
            target = configurator.configure_android(ndk_path, "arm64-v8a", 21)
            assert "darwin-x86_64" in str(target.sysroot)

        # Test Linux (default/else)
        with patch("platform.system", return_value="Linux"):
            target = configurator.configure_android(ndk_path, "arm64-v8a", 21)
            assert "linux-x86_64" in str(target.sysroot)

    def test_configure_ios_processor_selection(self):
        """Test configure_ios processor selection."""
        configurator = CrossCompilationConfigurator()

        # Test iphoneos -> arm64
        target = configurator.configure_ios("iphoneos", "12.0")
        assert target.system_processor == "arm64"

        # Test iphonesimulator -> x86_64
        target = configurator.configure_ios("iphonesimulator", "12.0")
        assert target.system_processor == "x86_64"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
