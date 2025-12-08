"""
Integration tests for cross-compilation configuration.
"""

import pytest
from pathlib import Path
from toolchainkit.cross.targets import CrossCompilationConfigurator


@pytest.mark.integration
class TestCrossCompilationCMakeIntegration:
    """Tests for integration with CMake toolchain generator."""

    def test_generate_android_toolchain_file(self, temp_dir):
        """Test generating CMake toolchain file for Android."""
        # Configure Android target
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")
        target = configurator.configure_android(ndk_path, "arm64-v8a", 21)

        # Generate CMake snippet
        snippet = configurator.generate_cmake_snippet(target)

        # Write to file
        toolchain_file = temp_dir / "android-toolchain.cmake"
        toolchain_file.write_text(snippet)

        # Verify file exists and content is correct
        assert toolchain_file.exists()
        content = toolchain_file.read_text()
        assert "CMAKE_SYSTEM_NAME" in content
        assert "Android" in content
        assert "aarch64" in content

    def test_generate_ios_toolchain_file(self, temp_dir):
        """Test generating CMake toolchain file for iOS."""
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_ios("iphoneos", "14.0")

        snippet = configurator.generate_cmake_snippet(target)

        toolchain_file = temp_dir / "ios-toolchain.cmake"
        toolchain_file.write_text(snippet)

        assert toolchain_file.exists()
        content = toolchain_file.read_text()
        assert "iOS" in content
        assert "14.0" in content

    def test_generate_raspberry_pi_toolchain_file(self, temp_dir):
        """Test generating CMake toolchain file for Raspberry Pi."""
        configurator = CrossCompilationConfigurator()
        sysroot = Path("/opt/rpi-sysroot")
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        snippet = configurator.generate_cmake_snippet(target)

        toolchain_file = temp_dir / "rpi-toolchain.cmake"
        toolchain_file.write_text(snippet)

        assert toolchain_file.exists()
        content = toolchain_file.read_text()
        assert "armv7" in content
        assert "arm-linux-gnueabihf-gcc" in content

    def test_cmake_snippet_syntax(self, temp_dir):
        """Test that generated CMake snippet has valid syntax."""
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_ios()

        snippet = configurator.generate_cmake_snippet(target)

        # Check basic CMake syntax
        lines = [line.strip() for line in snippet.split("\n") if line.strip()]

        for line in lines:
            if line.startswith("#"):
                # Comment line
                continue
            # Should be a set() command
            assert line.startswith("set(")
            assert line.endswith(")")
            # Should have matching quotes
            assert line.count('"') % 2 == 0

    def test_multiple_targets_different_files(self, temp_dir):
        """Test generating toolchain files for multiple targets."""
        configurator = CrossCompilationConfigurator()

        # Android
        android_target = configurator.configure_android(Path("/ndk"), "arm64-v8a", 21)
        android_file = temp_dir / "android.cmake"
        android_file.write_text(configurator.generate_cmake_snippet(android_target))

        # iOS
        ios_target = configurator.configure_ios("iphoneos", "12.0")
        ios_file = temp_dir / "ios.cmake"
        ios_file.write_text(configurator.generate_cmake_snippet(ios_target))

        # Raspberry Pi
        rpi_target = configurator.configure_raspberry_pi(Path("/sysroot"), "armv7")
        rpi_file = temp_dir / "rpi.cmake"
        rpi_file.write_text(configurator.generate_cmake_snippet(rpi_target))

        # All files should exist and be different
        assert android_file.exists()
        assert ios_file.exists()
        assert rpi_file.exists()

        android_content = android_file.read_text()
        ios_content = ios_file.read_text()
        rpi_content = rpi_file.read_text()

        assert "Android" in android_content
        assert "iOS" in ios_content
        assert "Linux" in rpi_content

        # Each should be unique
        assert android_content != ios_content
        assert ios_content != rpi_content
        assert android_content != rpi_content

    def test_cmake_variables_match_snippet(self, temp_dir):
        """Test that variables dict matches generated snippet."""
        configurator = CrossCompilationConfigurator()
        target = configurator.configure_android(Path("/ndk"), "arm64-v8a", 29)

        # Get variables and snippet
        vars = configurator.generate_cmake_variables(target)
        snippet = configurator.generate_cmake_snippet(target)

        # All variables should appear in snippet
        for key, value in vars.items():
            assert key in snippet
            # Value should be in snippet (as string)
            assert str(value) in snippet or value in snippet

    def test_round_trip_configuration(self, temp_dir):
        """Test that configuration can be saved and read back."""
        configurator = CrossCompilationConfigurator()

        # Original configuration
        original_target = configurator.configure_ios("iphoneos", "13.0")

        # Save to file
        toolchain_file = temp_dir / "toolchain.cmake"
        toolchain_file.write_text(configurator.generate_cmake_snippet(original_target))

        # Read back and verify
        content = toolchain_file.read_text()

        # Verify all original properties are preserved in file
        assert original_target.system_name in content
        assert original_target.system_processor in content
        assert original_target.cmake_system_version in content


@pytest.mark.integration
class TestRealWorldScenarios:
    """Tests for real-world cross-compilation scenarios."""

    def test_android_multi_abi_build(self, temp_dir):
        """Test configuring multiple Android ABIs."""
        configurator = CrossCompilationConfigurator()
        ndk_path = Path("/opt/android-ndk")

        abis = ["arm64-v8a", "armeabi-v7a", "x86_64", "x86"]

        for abi in abis:
            target = configurator.configure_android(ndk_path, abi, 21)

            # Create toolchain file for this ABI
            toolchain_file = temp_dir / f"android-{abi}.cmake"
            toolchain_file.write_text(configurator.generate_cmake_snippet(target))

            assert toolchain_file.exists()
            content = toolchain_file.read_text()
            assert "Android" in content

    def test_ios_universal_build(self, temp_dir):
        """Test configuring iOS device and simulator builds."""
        configurator = CrossCompilationConfigurator()

        # Device build
        device_target = configurator.configure_ios("iphoneos", "12.0")
        device_file = temp_dir / "ios-device.cmake"
        device_file.write_text(configurator.generate_cmake_snippet(device_target))

        # Simulator build
        sim_target = configurator.configure_ios("iphonesimulator", "12.0")
        sim_file = temp_dir / "ios-simulator.cmake"
        sim_file.write_text(configurator.generate_cmake_snippet(sim_target))

        # Both files should exist
        assert device_file.exists()
        assert sim_file.exists()

        # Content should be different (different processors)
        device_content = device_file.read_text()
        sim_content = sim_file.read_text()

        assert "arm64" in device_content
        assert "x86_64" in sim_content

    def test_raspberry_pi_variants(self, temp_dir):
        """Test configuring different Raspberry Pi variants."""
        configurator = CrossCompilationConfigurator()

        # 32-bit Raspberry Pi (Model 2/3)
        rpi32_target = configurator.configure_raspberry_pi(
            Path("/opt/rpi-sysroot-32"), "armv7"
        )
        rpi32_file = temp_dir / "rpi-32.cmake"
        rpi32_file.write_text(configurator.generate_cmake_snippet(rpi32_target))

        # 64-bit Raspberry Pi (Model 3/4)
        rpi64_target = configurator.configure_raspberry_pi(
            Path("/opt/rpi-sysroot-64"), "aarch64"
        )
        rpi64_file = temp_dir / "rpi-64.cmake"
        rpi64_file.write_text(configurator.generate_cmake_snippet(rpi64_target))

        # Both files should exist and be different
        assert rpi32_file.exists()
        assert rpi64_file.exists()

        rpi32_content = rpi32_file.read_text()
        rpi64_content = rpi64_file.read_text()

        assert "armv7" in rpi32_content
        assert "arm-linux-gnueabihf-" in rpi32_content
        assert "aarch64" in rpi64_content
        assert "aarch64-linux-gnu-" in rpi64_content


@pytest.mark.integration
class TestPathHandling:
    """Tests for path handling in cross-compilation."""

    def test_absolute_paths(self, temp_dir):
        """Test with absolute paths."""
        configurator = CrossCompilationConfigurator()

        # Use absolute path
        sysroot = temp_dir.resolve() / "sysroot"
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        vars = configurator.generate_cmake_variables(target)

        # Path should be absolute in variables
        assert Path(vars["CMAKE_SYSROOT"]).is_absolute()

    def test_relative_paths(self, temp_dir):
        """Test with relative paths."""
        configurator = CrossCompilationConfigurator()

        # Use relative path
        sysroot = Path("relative/path/to/sysroot")
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        vars = configurator.generate_cmake_variables(target)

        # Path should be preserved as-is
        assert vars["CMAKE_SYSROOT"] == str(sysroot)

    def test_path_with_spaces(self, temp_dir):
        """Test paths with spaces."""
        configurator = CrossCompilationConfigurator()

        sysroot = temp_dir / "path with spaces" / "sysroot"
        target = configurator.configure_raspberry_pi(sysroot, "armv7")

        snippet = configurator.generate_cmake_snippet(target)

        # Path should be properly quoted in CMake snippet
        assert str(sysroot) in snippet
        # Should be in quotes
        assert f'"{sysroot}"' in snippet


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling in integration scenarios."""

    def test_invalid_abi_produces_clear_error(self):
        """Test that invalid ABI produces clear error message."""
        configurator = CrossCompilationConfigurator()

        with pytest.raises(ValueError) as exc_info:
            configurator.configure_android(Path("/ndk"), "mips", 21)

        # Error message should be helpful
        assert "Unsupported Android ABI" in str(exc_info.value)
        assert "mips" in str(exc_info.value)
        assert "arm64-v8a" in str(exc_info.value)  # Should list valid options

    def test_invalid_ios_sdk_produces_clear_error(self):
        """Test that invalid iOS SDK produces clear error message."""
        configurator = CrossCompilationConfigurator()

        with pytest.raises(ValueError) as exc_info:
            configurator.configure_ios("macosx", "12.0")

        assert "Unsupported iOS SDK" in str(exc_info.value)
        assert "macosx" in str(exc_info.value)
        assert "iphoneos" in str(exc_info.value)  # Should list valid options

    def test_invalid_rpi_arch_produces_clear_error(self):
        """Test that invalid Raspberry Pi arch produces clear error message."""
        configurator = CrossCompilationConfigurator()

        with pytest.raises(ValueError) as exc_info:
            configurator.configure_raspberry_pi(Path("/sysroot"), "x86_64")

        assert "Unsupported Raspberry Pi architecture" in str(exc_info.value)
        assert "x86_64" in str(exc_info.value)
        assert "armv7" in str(exc_info.value)  # Should list valid options


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
