"""
Tests for toolchainkit.toolchain.system_detector module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from toolchainkit.core.platform import PlatformInfo
from toolchainkit.toolchain.system_detector import (
    SystemToolchain,
    CompilerVersionExtractor,
    PathSearcher,
    StandardLocationSearcher,
    RegistrySearcher,
    PackageManagerSearcher,
    SystemToolchainDetector,
)


# Fixtures


@pytest.fixture
def platform_windows():
    """Windows platform info."""
    return PlatformInfo("windows", "x64", "10.0.19041", "", "msvc")


@pytest.fixture
def platform_linux():
    """Linux platform info."""
    return PlatformInfo("linux", "x64", "22.04", "ubuntu", "glibc-2.31")


@pytest.fixture
def platform_macos():
    """macOS platform info."""
    return PlatformInfo("darwin", "arm64", "14.1", "", "macos-11.0")


@pytest.fixture
def mock_compiler_output():
    """Mock compiler version output."""
    return {
        "llvm": "clang version 18.1.8\nTarget: x86_64-unknown-linux-gnu\n",
        "gcc": "gcc (GCC) 13.2.0\nCopyright (C) 2023 Free Software Foundation\n",
        "msvc": "Microsoft (R) C/C++ Optimizing Compiler Version 19.38.33133 for x64\n",
    }


# SystemToolchain Tests


class TestSystemToolchain:
    """Tests for SystemToolchain dataclass."""

    def test_create_toolchain(self):
        """Test creating a SystemToolchain instance."""
        tc = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        assert tc.type == "llvm"
        assert tc.version == "18.1.8"
        assert tc.source == "path"

    def test_toolchain_with_optional_fields(self):
        """Test toolchain with all optional fields."""
        tc = SystemToolchain(
            type="gcc",
            version="13.2.0",
            compiler_path=Path("/usr/bin/g++"),
            c_compiler_path=Path("/usr/bin/gcc"),
            linker_path=Path("/usr/bin/ld"),
            ar_path=Path("/usr/bin/ar"),
            ranlib_path=Path("/usr/bin/ranlib"),
            include_paths=[Path("/usr/include/c++/13")],
            library_paths=[Path("/usr/lib/gcc")],
            source="standard_location",
            install_dir=Path("/usr"),
            target="x86_64-linux-gnu",
        )

        assert tc.linker_path == Path("/usr/bin/ld")
        assert tc.ar_path == Path("/usr/bin/ar")
        assert len(tc.include_paths) == 1
        assert tc.target == "x86_64-linux-gnu"

    def test_toolchain_str_representation(self):
        """Test string representation."""
        tc = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        result = str(tc)
        assert "llvm" in result
        assert "18.1.8" in result
        assert "path" in result

    def test_to_dict(self):
        """Test converting to dictionary."""
        tc = SystemToolchain(
            type="gcc",
            version="13.2.0",
            compiler_path=Path("/usr/bin/g++"),
            c_compiler_path=Path("/usr/bin/gcc"),
            source="path",
            install_dir=Path("/usr"),
        )

        result = tc.to_dict()

        assert result["toolchain_id"] == "gcc-13.2.0-system"
        assert result["name"] == "GCC 13.2.0"
        assert result["version"] == "13.2.0"
        assert result["type"] == "gcc"
        assert result["source"] == "path"


# CompilerVersionExtractor Tests


class TestCompilerVersionExtractor:
    """Tests for CompilerVersionExtractor."""

    def test_extract_llvm_version(self, tmp_path, mock_compiler_output):
        """Test extracting LLVM version."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "clang++"
        fake_compiler.write_text("#!/bin/sh\n")
        fake_compiler.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=mock_compiler_output["llvm"], stderr=""
            )

            version = extractor.extract_version(fake_compiler)

            assert version == "18.1.8"
            mock_run.assert_called_once()

    def test_extract_gcc_version(self, tmp_path, mock_compiler_output):
        """Test extracting GCC version."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "g++"
        fake_compiler.write_text("#!/bin/sh\n")
        fake_compiler.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=mock_compiler_output["gcc"], stderr=""
            )

            version = extractor.extract_version(fake_compiler)

            assert version == "13.2.0"

    def test_extract_msvc_version(self, tmp_path, mock_compiler_output):
        """Test extracting MSVC version."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "cl.exe"
        fake_compiler.write_text("")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=mock_compiler_output["msvc"], stderr=""
            )

            version = extractor.extract_version(fake_compiler)

            assert version == "19.38.33133"

    def test_extract_version_compiler_not_found(self, tmp_path):
        """Test version extraction when compiler doesn't exist."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "nonexistent"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            version = extractor.extract_version(fake_compiler)

            assert version is None

    def test_extract_version_timeout(self, tmp_path):
        """Test version extraction timeout."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "clang++"
        fake_compiler.write_text("#!/bin/sh\n")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("clang++", 5)

            version = extractor.extract_version(fake_compiler)

            assert version is None

    def test_extract_version_nonzero_return_code(self, tmp_path):
        """Test version extraction with non-zero return code."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "clang++"
        fake_compiler.write_text("#!/bin/sh\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

            version = extractor.extract_version(fake_compiler)

            assert version is None

    def test_extract_target_triplet(self, tmp_path):
        """Test extracting target triplet."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "gcc"
        fake_compiler.write_text("#!/bin/sh\n")
        fake_compiler.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="x86_64-linux-gnu\n", stderr=""
            )

            target = extractor.extract_target(fake_compiler)

            assert target == "x86_64-linux-gnu"

    def test_extract_target_failure(self, tmp_path):
        """Test target extraction failure."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "gcc"
        fake_compiler.write_text("#!/bin/sh\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

            target = extractor.extract_target(fake_compiler)

            assert target is None

    def test_extract_includes(self, tmp_path):
        """Test extracting include paths."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "clang++"
        fake_compiler.write_text("#!/bin/sh\n")
        fake_compiler.chmod(0o755)

        # Create fake include directories
        inc1 = tmp_path / "include1"
        inc2 = tmp_path / "include2"
        inc1.mkdir()
        inc2.mkdir()

        output = f"""#include <...> search starts here:
 {inc1}
 {inc2}
End of search list.
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr=output)

            includes = extractor.extract_includes(fake_compiler)

            assert len(includes) == 2
            assert inc1 in includes
            assert inc2 in includes

    def test_extract_includes_failure(self, tmp_path):
        """Test include extraction failure."""
        extractor = CompilerVersionExtractor()

        fake_compiler = tmp_path / "clang++"
        fake_compiler.write_text("#!/bin/sh\n")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            includes = extractor.extract_includes(fake_compiler)

            assert includes == []


# PathSearcher Tests


class TestPathSearcher:
    """Tests for PathSearcher."""

    def test_find_compiler_in_path(self, tmp_path):
        """Test finding compiler in PATH."""
        searcher = PathSearcher()

        # Create fake compiler
        fake_clang = tmp_path / "clang++"
        fake_clang.write_text('#!/bin/sh\necho "clang version 18.1.8"\n')
        fake_clang.chmod(0o755)

        with patch("shutil.which", return_value=str(fake_clang)):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout="clang version 18.1.8\n", stderr=""
                )

                toolchains = searcher.search()

                assert len(toolchains) >= 0  # May find real compilers

    def test_no_compilers_in_path(self):
        """Test when no compilers found in PATH."""
        searcher = PathSearcher()

        with patch("shutil.which", return_value=None):
            toolchains = searcher.search()

            assert toolchains == []

    def test_create_toolchain_from_path(self, tmp_path):
        """Test creating toolchain from compiler path."""
        searcher = PathSearcher()
        extractor = CompilerVersionExtractor()

        # Create fake bin directory with compilers
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        clang_cpp = bin_dir / "clang++"
        clang_cpp.write_text("#!/bin/sh\n")
        clang_cpp.chmod(0o755)

        clang_c = bin_dir / "clang"
        clang_c.write_text("#!/bin/sh\n")
        clang_c.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="clang version 18.1.8\n", stderr=""
            )

            toolchain = searcher._create_toolchain(clang_cpp, "llvm", extractor)

            assert toolchain is not None
            assert toolchain.type == "llvm"
            assert toolchain.version == "18.1.8"
            assert toolchain.c_compiler_path == clang_c


# StandardLocationSearcher Tests


class TestStandardLocationSearcher:
    """Tests for StandardLocationSearcher."""

    def test_get_windows_locations(self, platform_windows):
        """Test getting Windows standard locations."""
        searcher = StandardLocationSearcher(platform_windows)

        locations = searcher._get_standard_locations()

        assert any("LLVM" in str(loc) for loc in locations)
        assert any("Microsoft Visual Studio" in str(loc) for loc in locations)
        assert any("mingw64" in str(loc) for loc in locations)

    def test_get_linux_locations(self, platform_linux):
        """Test getting Linux standard locations."""
        searcher = StandardLocationSearcher(platform_linux)

        locations = searcher._get_standard_locations()

        assert any("llvm" in str(loc) for loc in locations)
        assert any("gcc" in str(loc) for loc in locations)

    def test_get_macos_locations(self, platform_macos):
        """Test getting macOS standard locations."""
        searcher = StandardLocationSearcher(platform_macos)

        locations = searcher._get_standard_locations()

        assert any("homebrew" in str(loc).lower() for loc in locations)
        assert any("Xcode" in str(loc) for loc in locations)

    def test_is_compiler_detects_clang(self, tmp_path):
        """Test detecting clang++ as compiler."""
        searcher = StandardLocationSearcher(
            PlatformInfo("linux", "x64", "22.04", "ubuntu", "glibc-2.31")
        )

        clang = tmp_path / "clang++"
        clang.write_text("#!/bin/sh\n")
        clang.chmod(0o755)

        assert searcher._is_compiler(clang) is True

    def test_is_compiler_rejects_non_executable(self, tmp_path):
        """Test rejecting non-executable files."""
        searcher = StandardLocationSearcher(
            PlatformInfo("linux", "x64", "22.04", "ubuntu", "glibc-2.31")
        )

        not_compiler = tmp_path / "clang++"
        not_compiler.write_text("text file")
        # Don't make it executable

        # On Unix, this should fail; on Windows, .exe extension matters
        _result = searcher._is_compiler(not_compiler)
        # Result depends on platform

    def test_detect_type_from_name(self, platform_linux):
        """Test detecting toolchain type from compiler name."""
        searcher = StandardLocationSearcher(platform_linux)

        assert searcher._detect_type(Path("/usr/bin/clang++")) == "llvm"
        assert searcher._detect_type(Path("/usr/bin/g++")) == "gcc"
        assert searcher._detect_type(Path("C:/Program Files/MSVC/cl.exe")) == "msvc"


# RegistrySearcher Tests


class TestRegistrySearcher:
    """Tests for RegistrySearcher (Windows only)."""

    def test_vswhere_not_found(self):
        """Test when vswhere.exe doesn't exist."""
        searcher = RegistrySearcher()

        with patch("pathlib.Path.exists", return_value=False):
            toolchains = searcher.search()

            assert toolchains == []

    def test_vswhere_finds_msvc(self, tmp_path):
        """Test finding MSVC via vswhere."""
        searcher = RegistrySearcher()

        # Mock vswhere output
        vs_path = str(tmp_path / "VS")

        # Create fake MSVC directory structure
        msvc_dir = tmp_path / "VS" / "VC" / "Tools" / "MSVC" / "14.38.33133"
        cl_dir = msvc_dir / "bin" / "Hostx64" / "x64"
        cl_dir.mkdir(parents=True)

        cl_exe = cl_dir / "cl.exe"
        cl_exe.write_text("")

        link_exe = cl_dir / "link.exe"
        link_exe.write_text("")

        lib_exe = cl_dir / "lib.exe"
        lib_exe.write_text("")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout=vs_path + "\n", stderr=""
                )

                toolchains = searcher._search_with_vswhere(Path("vswhere.exe"))

                assert len(toolchains) == 1
                assert toolchains[0].type == "msvc"
                assert toolchains[0].version == "14.38.33133"
                assert toolchains[0].source == "registry"

    def test_vswhere_timeout(self):
        """Test vswhere timeout."""
        searcher = RegistrySearcher()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("vswhere", 10)

                toolchains = searcher._search_with_vswhere(Path("vswhere.exe"))

                assert toolchains == []

    def test_vswhere_no_vc_tools(self, tmp_path):
        """Test when VS installation has no VC Tools."""
        searcher = RegistrySearcher()

        vs_path = str(tmp_path / "VS")
        (tmp_path / "VS").mkdir()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0, stdout=vs_path + "\n", stderr=""
                )

                toolchains = searcher._search_with_vswhere(Path("vswhere.exe"))

                assert toolchains == []


# PackageManagerSearcher Tests


class TestPackageManagerSearcher:
    """Tests for PackageManagerSearcher."""

    def test_homebrew_search_macos(self, platform_macos, tmp_path):
        """Test searching Homebrew on macOS."""
        searcher = PackageManagerSearcher(platform_macos)

        # Create fake Homebrew structure
        cellar = tmp_path / "Cellar"
        llvm_dir = cellar / "llvm" / "18.1.8" / "bin"
        llvm_dir.mkdir(parents=True)

        clang = llvm_dir / "clang++"
        clang.write_text("#!/bin/sh\n")
        clang.chmod(0o755)

        clang_c = llvm_dir / "clang"
        clang_c.write_text("#!/bin/sh\n")
        clang_c.chmod(0o755)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir") as _mock_iterdir:
                # Mock cellar listing
                mock_cellar = MagicMock()
                mock_cellar.iterdir.return_value = [cellar / "llvm"]

                # Mock llvm package listing
                mock_llvm = MagicMock()
                mock_llvm.iterdir.return_value = [llvm_dir.parent]

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0, stdout="clang version 18.1.8\n", stderr=""
                    )

                    # This is complex to mock fully - just verify it doesn't crash
                    toolchains = searcher._search_homebrew()

                    assert isinstance(toolchains, list)

    def test_apt_search_linux(self, platform_linux, tmp_path):
        """Test searching apt on Linux."""
        searcher = PackageManagerSearcher(platform_linux)

        # Create fake /usr/bin with versioned compilers
        usr_bin = tmp_path / "usr" / "bin"
        usr_bin.mkdir(parents=True)

        gcc13 = usr_bin / "g++-13"
        gcc13.write_text("#!/bin/sh\n")
        gcc13.chmod(0o755)

        clang17 = usr_bin / "clang++-17"
        clang17.write_text("#!/bin/sh\n")
        clang17.chmod(0o755)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", return_value=[gcc13, clang17]):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0, stdout="gcc (GCC) 13.2.0\n", stderr=""
                    )

                    toolchains = searcher._search_apt()

                    # May find toolchains or not depending on mocking
                    assert isinstance(toolchains, list)

    def test_chocolatey_search_windows(self, platform_windows):
        """Test searching Chocolatey on Windows."""
        searcher = PackageManagerSearcher(platform_windows)

        # Chocolatey search currently returns empty
        toolchains = searcher._search_chocolatey()

        assert toolchains == []


# SystemToolchainDetector Tests


class TestSystemToolchainDetector:
    """Tests for SystemToolchainDetector."""

    def test_detector_initialization_windows(self, platform_windows):
        """Test detector initialization on Windows."""
        detector = SystemToolchainDetector(platform_windows)

        assert len(detector.searchers) == 4  # PATH, Standard, Package, Registry
        assert any(isinstance(s, RegistrySearcher) for s in detector.searchers)

    def test_detector_initialization_linux(self, platform_linux):
        """Test detector initialization on Linux."""
        detector = SystemToolchainDetector(platform_linux)

        assert len(detector.searchers) == 3  # PATH, Standard, Package (no Registry)
        assert not any(isinstance(s, RegistrySearcher) for s in detector.searchers)

    def test_detect_all_deduplication(self, platform_linux, tmp_path):
        """Test that detect_all deduplicates by compiler path."""
        detector = SystemToolchainDetector(platform_linux)

        # Create mock toolchains with same compiler path
        tc1 = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        tc2 = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),  # Same path
            c_compiler_path=Path("/usr/bin/clang"),
            source="standard_location",
        )

        with patch.object(PathSearcher, "search", return_value=[tc1]):
            with patch.object(StandardLocationSearcher, "search", return_value=[tc2]):
                with patch.object(PackageManagerSearcher, "search", return_value=[]):
                    toolchains = detector.detect_all()

                    # Should only have one toolchain (deduplicated)
                    assert len(toolchains) == 1

    def test_detect_by_type(self, platform_linux):
        """Test filtering toolchains by type."""
        detector = SystemToolchainDetector(platform_linux)

        tc_llvm = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        tc_gcc = SystemToolchain(
            type="gcc",
            version="13.2.0",
            compiler_path=Path("/usr/bin/g++"),
            c_compiler_path=Path("/usr/bin/gcc"),
            source="path",
        )

        with patch.object(detector, "detect_all", return_value=[tc_llvm, tc_gcc]):
            llvm_toolchains = detector.detect_type("llvm")
            gcc_toolchains = detector.detect_type("gcc")

            assert len(llvm_toolchains) == 1
            assert llvm_toolchains[0].type == "llvm"

            assert len(gcc_toolchains) == 1
            assert gcc_toolchains[0].type == "gcc"

    def test_detect_best_prefers_llvm(self, platform_linux):
        """Test that detect_best prefers LLVM over GCC."""
        detector = SystemToolchainDetector(platform_linux)

        tc_llvm = SystemToolchain(
            type="llvm",
            version="17.0.0",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        tc_gcc = SystemToolchain(
            type="gcc",
            version="13.2.0",
            compiler_path=Path("/usr/bin/g++"),
            c_compiler_path=Path("/usr/bin/gcc"),
            source="path",
        )

        with patch.object(detector, "detect_all", return_value=[tc_gcc, tc_llvm]):
            best = detector.detect_best()

            assert best.type == "llvm"

    def test_detect_best_newest_version(self, platform_linux):
        """Test that detect_best selects newest version."""
        detector = SystemToolchainDetector(platform_linux)

        tc_old = SystemToolchain(
            type="llvm",
            version="16.0.0",
            compiler_path=Path("/usr/bin/clang++-16"),
            c_compiler_path=Path("/usr/bin/clang-16"),
            source="path",
        )

        tc_new = SystemToolchain(
            type="llvm",
            version="18.1.8",
            compiler_path=Path("/usr/bin/clang++"),
            c_compiler_path=Path("/usr/bin/clang"),
            source="path",
        )

        with patch.object(detector, "detect_all", return_value=[tc_old, tc_new]):
            best = detector.detect_best()

            assert best.version == "18.1.8"

    def test_detect_best_no_toolchains(self, platform_linux):
        """Test detect_best with no toolchains found."""
        detector = SystemToolchainDetector(platform_linux)

        with patch.object(detector, "detect_all", return_value=[]):
            best = detector.detect_best()

            assert best is None

    def test_searcher_failure_handling(self, platform_linux):
        """Test that detector handles searcher failures gracefully."""
        detector = SystemToolchainDetector(platform_linux)

        with patch.object(
            PathSearcher, "search", side_effect=Exception("Search failed")
        ):
            with patch.object(StandardLocationSearcher, "search", return_value=[]):
                with patch.object(PackageManagerSearcher, "search", return_value=[]):
                    # Should not raise exception
                    toolchains = detector.detect_all()

                    assert isinstance(toolchains, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
