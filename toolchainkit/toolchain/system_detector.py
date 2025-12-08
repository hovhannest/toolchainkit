"""
toolchainkit/toolchain/system_detector.py

System toolchain detection - discovers compilers already installed on the system.
"""

import os
import subprocess
import re
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from ..core.platform import PlatformInfo

logger = logging.getLogger(__name__)


@dataclass
class SystemToolchain:
    """
    Represents a toolchain found on the system.

    Attributes:
        type: Toolchain type ('llvm', 'gcc', 'msvc')
        version: Detected version string
        compiler_path: Path to C++ compiler executable
        c_compiler_path: Path to C compiler executable
        linker_path: Path to linker executable (optional)
        ar_path: Path to archiver executable (optional)
        ranlib_path: Path to ranlib executable (optional)
        include_paths: System include directories
        library_paths: System library directories
        source: How it was found ('path', 'standard_location', 'registry', 'package_manager')
        install_dir: Installation root directory
        target: Target triplet (e.g., 'x86_64-linux-gnu')
    """

    type: str
    version: str
    compiler_path: Path
    c_compiler_path: Path
    linker_path: Optional[Path] = None
    ar_path: Optional[Path] = None
    ranlib_path: Optional[Path] = None
    include_paths: List[Path] = field(default_factory=list)
    library_paths: List[Path] = field(default_factory=list)
    source: str = "unknown"
    install_dir: Optional[Path] = None
    target: Optional[str] = None

    def __str__(self) -> str:
        """String representation."""
        return f"{self.type} {self.version} ({self.source}) at {self.compiler_path}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for registry integration.

        Returns:
            Dictionary representation suitable for storage/serialization
        """
        return {
            "toolchain_id": f"{self.type}-{self.version}-system",
            "name": f"{self.type.upper()} {self.version}",
            "version": self.version,
            "type": self.type,
            "platform": str(self.target) if self.target else "system",
            "install_path": str(self.install_dir) if self.install_dir else "",
            "compiler_path": str(self.compiler_path),
            "c_compiler_path": str(self.c_compiler_path),
            "linker_path": str(self.linker_path) if self.linker_path else "",
            "source": self.source,
        }


class CompilerVersionExtractor:
    """
    Extract version and metadata from compiler executables.

    Runs compilers with --version, -dumpmachine, and other flags to extract:
    - Version string (e.g., "18.1.8", "13.2.0")
    - Target triplet (e.g., "x86_64-linux-gnu")
    - System include paths
    """

    def extract_version(self, compiler_path: Path) -> Optional[str]:
        """
        Extract version from compiler.

        Runs 'compiler --version' and parses the output for version patterns like:
        - LLVM: "clang version 18.1.8"
        - GCC: "gcc (GCC) 13.2.0"
        - MSVC: "Version 19.38.33133"

        Args:
            compiler_path: Path to compiler executable

        Returns:
            Version string (e.g., "18.1.8") or None if extraction failed
        """
        try:
            result = subprocess.run(
                [str(compiler_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                logger.debug(
                    f"Compiler {compiler_path} --version returned {result.returncode}"
                )
                return None

            output = result.stdout + result.stderr

            # Try to extract version number - most compilers use X.Y.Z format
            # Match patterns like "14.0.0", "11.4.0", "19.38.33133"
            match = re.search(r"\b(\d+\.\d+\.\d+(?:\.\d+)?)\b", output)
            if match:
                version = match.group(1)
                logger.debug(f"Extracted version {version} from {compiler_path}")
                return version

            # Try major.minor only (some compilers)
            match = re.search(r"\b(\d+\.\d+)\b", output)
            if match:
                version = match.group(1)
                logger.debug(
                    f"Extracted version {version} (major.minor) from {compiler_path}"
                )
                return version

            logger.debug(f"Could not parse version from output: {output[:200]}")
            return None

        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout extracting version from {compiler_path}")
            return None
        except Exception as e:
            logger.debug(f"Failed to extract version from {compiler_path}: {e}")
            return None

    def extract_target(self, compiler_path: Path) -> Optional[str]:
        """
        Extract target triplet from compiler.

        Runs 'compiler -dumpmachine' to get the target triplet like:
        - x86_64-linux-gnu
        - arm-linux-gnueabihf
        - x86_64-pc-windows-msvc

        Args:
            compiler_path: Path to compiler executable

        Returns:
            Target triplet string or None if extraction failed
        """
        try:
            result = subprocess.run(
                [str(compiler_path), "-dumpmachine"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                target = result.stdout.strip()
                if target:
                    logger.debug(f"Extracted target {target} from {compiler_path}")
                    return target

            return None

        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout extracting target from {compiler_path}")
            return None
        except Exception as e:
            logger.debug(f"Failed to extract target from {compiler_path}: {e}")
            return None

    def extract_includes(self, compiler_path: Path) -> List[Path]:
        """
        Extract system include paths from compiler.

        Runs 'compiler -E -v -' with empty input to get include search paths.
        Parses the output for lines between:
        - "#include <...> search starts here:"
        - "End of search list."

        Args:
            compiler_path: Path to compiler executable

        Returns:
            List of include directory paths
        """
        try:
            # Use -E -v with empty input to get include paths
            result = subprocess.run(
                [str(compiler_path), "-E", "-v", "-"],
                input="",
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Parse output (includes appear in stderr for GCC/Clang)
            includes = []
            in_include_section = False

            # Check both stdout and stderr
            output = result.stderr + result.stdout

            for line in output.split("\n"):
                if (
                    "#include <...> search starts here:" in line
                    or '#include "..." search starts here:' in line
                ):
                    in_include_section = True
                    continue
                elif "End of search list." in line:
                    break
                elif in_include_section:
                    path_str = line.strip()
                    if path_str and not path_str.startswith("#"):
                        # Remove framework annotations (macOS)
                        path_str = path_str.split(" (")[0].strip()
                        try:
                            path = Path(path_str)
                            if path.exists():
                                includes.append(path)
                        except Exception:
                            pass

            logger.debug(
                f"Extracted {len(includes)} include paths from {compiler_path}"
            )
            return includes

        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout extracting includes from {compiler_path}")
            return []
        except Exception as e:
            logger.debug(f"Failed to extract includes from {compiler_path}: {e}")
            return []


class PathSearcher:
    """
    Search for compilers in PATH environment variable.

    Uses shutil.which() to find common compiler executables:
    - clang++, g++, cl.exe (C++ compilers)
    - clang, gcc, cl.exe (C compilers)
    """

    def search(self) -> List[SystemToolchain]:
        """
        Search PATH for compilers.

        Returns:
            List of discovered toolchains
        """
        toolchains = []
        extractor = CompilerVersionExtractor()

        # Search for various C++ compilers
        compilers = {
            "clang++": "llvm",
            "g++": "gcc",
            "cl.exe": "msvc",
        }

        for compiler_name, toolchain_type in compilers.items():
            path = self._find_in_path(compiler_name)
            if path:
                toolchain = self._create_toolchain(path, toolchain_type, extractor)
                if toolchain:
                    toolchain.source = "path"
                    toolchains.append(toolchain)
                    logger.info(
                        f"Found {toolchain_type} {toolchain.version} in PATH: {path}"
                    )

        return toolchains

    def _find_in_path(self, executable: str) -> Optional[Path]:
        """
        Find executable in PATH.

        Args:
            executable: Executable name to search for

        Returns:
            Path to executable or None if not found
        """
        path_str = shutil.which(executable)
        return Path(path_str).resolve() if path_str else None

    def _create_toolchain(
        self,
        compiler_path: Path,
        toolchain_type: str,
        extractor: CompilerVersionExtractor,
    ) -> Optional[SystemToolchain]:
        """
        Create toolchain from compiler path.

        Args:
            compiler_path: Path to C++ compiler
            toolchain_type: Type of toolchain ('llvm', 'gcc', 'msvc')
            extractor: Version extractor instance

        Returns:
            SystemToolchain or None if creation failed
        """
        # Extract version
        version = extractor.extract_version(compiler_path)
        if not version:
            logger.debug(f"Could not extract version from {compiler_path}")
            return None

        # Find C compiler
        if toolchain_type == "llvm":
            c_compiler_name = "clang"
        elif toolchain_type == "gcc":
            c_compiler_name = "gcc"
        elif toolchain_type == "msvc":
            c_compiler_name = "cl.exe"
        else:
            c_compiler_name = compiler_path.stem

        # Add .exe on Windows
        if compiler_path.suffix == ".exe" and not c_compiler_name.endswith(".exe"):
            c_compiler_name += ".exe"

        c_compiler = compiler_path.parent / c_compiler_name

        if not c_compiler.exists():
            # Fallback to C++ compiler for C compilation (MSVC does this)
            c_compiler = compiler_path

        # Find install directory (usually parent of bin)
        install_dir = compiler_path.parent
        if install_dir.name in ("bin", "Bin"):
            install_dir = install_dir.parent

        # Find linker and other tools
        linker_path = None
        ar_path = None
        ranlib_path = None

        if toolchain_type == "llvm":
            linker_candidates = ["lld", "ld.lld"]
            ar_candidates = ["llvm-ar"]
            ranlib_candidates = ["llvm-ranlib"]
        elif toolchain_type == "gcc":
            linker_candidates = ["ld"]
            ar_candidates = ["ar", "gcc-ar"]
            ranlib_candidates = ["ranlib", "gcc-ranlib"]
        elif toolchain_type == "msvc":
            linker_candidates = ["link.exe"]
            ar_candidates = ["lib.exe"]
            ranlib_candidates = []
        else:
            linker_candidates = []
            ar_candidates = []
            ranlib_candidates = []

        # Find linker
        for linker_name in linker_candidates:
            if compiler_path.suffix == ".exe" and not linker_name.endswith(".exe"):
                linker_name += ".exe"
            linker = compiler_path.parent / linker_name
            if linker.exists():
                linker_path = linker
                break

        # Find ar
        for ar_name in ar_candidates:
            if compiler_path.suffix == ".exe" and not ar_name.endswith(".exe"):
                ar_name += ".exe"
            ar = compiler_path.parent / ar_name
            if ar.exists():
                ar_path = ar
                break

        # Find ranlib
        for ranlib_name in ranlib_candidates:
            if compiler_path.suffix == ".exe" and not ranlib_name.endswith(".exe"):
                ranlib_name += ".exe"
            ranlib = compiler_path.parent / ranlib_name
            if ranlib.exists():
                ranlib_path = ranlib
                break

        # Create toolchain
        toolchain = SystemToolchain(
            type=toolchain_type,
            version=version,
            compiler_path=compiler_path,
            c_compiler_path=c_compiler,
            linker_path=linker_path,
            ar_path=ar_path,
            ranlib_path=ranlib_path,
            install_dir=install_dir,
            target=extractor.extract_target(compiler_path),
            include_paths=extractor.extract_includes(compiler_path),
        )

        return toolchain


class StandardLocationSearcher:
    """
    Search standard installation directories for compilers.

    Platform-specific standard locations:
    - Windows: C:/Program Files/LLVM, C:/mingw64, C:/msys64
    - Linux: /usr/lib/llvm-*, /usr/lib/gcc, /opt/gcc
    - macOS: /usr/local/opt/llvm, /opt/homebrew, Xcode.app
    """

    def __init__(self, platform: PlatformInfo):
        """
        Initialize searcher.

        Args:
            platform: Platform information for determining search paths
        """
        self.platform = platform

    def search(self) -> List[SystemToolchain]:
        """
        Search standard locations.

        Returns:
            List of discovered toolchains
        """
        toolchains = []

        locations = self._get_standard_locations()
        extractor = CompilerVersionExtractor()
        path_searcher = PathSearcher()

        for location in locations:
            if not location.exists():
                logger.debug(f"Standard location does not exist: {location}")
                continue

            logger.debug(f"Searching standard location: {location}")

            # Search for compiler executables
            # Limit depth to avoid excessive searching
            try:
                for compiler_path in self._find_compilers(location):
                    toolchain_type = self._detect_type(compiler_path)
                    if toolchain_type:
                        toolchain = path_searcher._create_toolchain(
                            compiler_path, toolchain_type, extractor
                        )
                        if toolchain:
                            toolchain.source = "standard_location"
                            toolchains.append(toolchain)
                            logger.info(
                                f"Found {toolchain_type} {toolchain.version} at {compiler_path}"
                            )
            except Exception as e:
                logger.debug(f"Error searching {location}: {e}")

        return toolchains

    def _get_standard_locations(self) -> List[Path]:
        """
        Get platform-specific standard locations.

        Returns:
            List of paths to search
        """
        if self.platform.os == "windows":
            return [
                Path("C:/Program Files/LLVM"),
                Path("C:/Program Files/Microsoft Visual Studio"),
                Path("C:/mingw64"),
                Path("C:/msys64/mingw64"),
                Path("C:/msys64/ucrt64"),
                Path("C:/msys64/clang64"),
            ]
        elif self.platform.os == "darwin":
            return [
                Path("/usr/local/opt/llvm"),
                Path("/opt/homebrew/opt/llvm"),
                Path("/opt/homebrew/opt/gcc"),
                Path("/Applications/Xcode.app/Contents/Developer/Toolchains"),
            ]
        else:  # Linux
            locations = [
                Path("/opt/gcc"),
                Path("/opt/llvm"),
            ]

            # Add versioned LLVM installations
            for i in range(20, 10, -1):  # Check LLVM 20 down to 11
                locations.append(Path(f"/usr/lib/llvm-{i}"))

            # Add GCC locations
            locations.extend(
                [
                    Path("/usr/lib/gcc"),
                    Path("/usr/local/gcc"),
                ]
            )

            return locations

    def _find_compilers(self, location: Path) -> List[Path]:
        """
        Find compiler executables in a location.

        Args:
            location: Directory to search

        Returns:
            List of compiler executable paths
        """
        compilers = []

        # Check common compiler locations
        common_paths = [
            location / "bin",
            location / "Bin",
        ]

        for bin_dir in common_paths:
            if not bin_dir.exists():
                continue

            try:
                for entry in bin_dir.iterdir():
                    if self._is_compiler(entry):
                        compilers.append(entry)
            except Exception as e:
                logger.debug(f"Error iterating {bin_dir}: {e}")

        return compilers

    def _is_compiler(self, path: Path) -> bool:
        """
        Check if path is a compiler executable.

        Args:
            path: Path to check

        Returns:
            True if path is a compiler executable
        """
        if not path.is_file():
            return False

        name = path.name.lower()

        # Check for known compiler names
        compiler_names = [
            "clang++",
            "clang++.exe",
            "g++",
            "g++.exe",
            "gcc",
            "gcc.exe",
            "cl.exe",
        ]

        if name in compiler_names:
            # Check if executable (Unix) or .exe (Windows)
            if path.suffix == ".exe" or os.access(path, os.X_OK):
                return True

        return False

    def _detect_type(self, compiler_path: Path) -> Optional[str]:
        """
        Detect compiler type from path.

        Args:
            compiler_path: Path to compiler

        Returns:
            Toolchain type ('llvm', 'gcc', 'msvc') or None
        """
        name = compiler_path.name.lower()

        if "clang" in name:
            return "llvm"
        elif "g++" in name or "gcc" in name:
            return "gcc"
        elif "cl.exe" in name:
            return "msvc"

        return None


class RegistrySearcher:
    """
    Search Windows registry for MSVC installations.

    Uses vswhere.exe to find Visual Studio installations and locate cl.exe.
    Falls back to direct registry search if vswhere is not available.

    Windows only.
    """

    def search(self) -> List[SystemToolchain]:
        """
        Search Windows registry.

        Returns:
            List of discovered MSVC toolchains
        """
        toolchains = []

        try:
            # Try using vswhere first
            vswhere_path = Path(
                "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
            )

            if vswhere_path.exists():
                logger.debug("Using vswhere to find Visual Studio installations")
                toolchains.extend(self._search_with_vswhere(vswhere_path))
            else:
                logger.debug("vswhere not found, skipping MSVC detection")

        except Exception as e:
            logger.debug(f"Registry search failed: {e}")

        return toolchains

    def _search_with_vswhere(self, vswhere_path: Path) -> List[SystemToolchain]:
        """
        Use vswhere to find Visual Studio installations.

        Args:
            vswhere_path: Path to vswhere.exe

        Returns:
            List of MSVC toolchains
        """
        try:
            result = subprocess.run(
                [
                    str(vswhere_path),
                    "-products",
                    "*",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode != 0:
                logger.debug(f"vswhere returned {result.returncode}")
                return []

            toolchains = []

            for install_path_str in result.stdout.strip().split("\n"):
                if not install_path_str:
                    continue

                logger.debug(f"Found VS installation: {install_path_str}")

                # Find cl.exe in VC/Tools
                install_path = Path(install_path_str)
                vc_tools = install_path / "VC" / "Tools" / "MSVC"
                if not vc_tools.exists():
                    logger.debug(f"VC/Tools/MSVC not found in {install_path}")
                    continue

                # Get all MSVC versions (sorted newest first)
                try:
                    versions = sorted(vc_tools.iterdir(), reverse=True)
                except Exception as e:
                    logger.debug(f"Error listing MSVC versions: {e}")
                    continue

                for version_dir in versions:
                    if not version_dir.is_dir():
                        continue

                    cl_path = version_dir / "bin" / "Hostx64" / "x64" / "cl.exe"

                    if cl_path.exists():
                        version = version_dir.name
                        link_path = cl_path.parent / "link.exe"
                        lib_path = cl_path.parent / "lib.exe"

                        toolchain = SystemToolchain(
                            type="msvc",
                            version=version,
                            compiler_path=cl_path,
                            c_compiler_path=cl_path,  # MSVC uses same compiler for C and C++
                            install_dir=version_dir,
                            source="registry",
                            linker_path=link_path if link_path.exists() else None,
                            ar_path=lib_path if lib_path.exists() else None,
                        )
                        toolchains.append(toolchain)
                        logger.info(f"Found MSVC {version} via vswhere: {cl_path}")

                        # Only report the latest version from each VS installation
                        break

            return toolchains

        except subprocess.TimeoutExpired:
            logger.debug("vswhere timed out")
            return []
        except Exception as e:
            logger.debug(f"vswhere search failed: {e}")
            return []


class PackageManagerSearcher:
    """
    Search package manager installations.

    Platform-specific package managers:
    - macOS: Homebrew (/usr/local/Cellar, /opt/homebrew/Cellar)
    - Linux: apt (versioned compilers in /usr/bin)
    - Windows: Chocolatey (C:/ProgramData/chocolatey/lib)
    """

    def __init__(self, platform: PlatformInfo):
        """
        Initialize searcher.

        Args:
            platform: Platform information
        """
        self.platform = platform

    def search(self) -> List[SystemToolchain]:
        """
        Search package manager directories.

        Returns:
            List of discovered toolchains
        """
        if self.platform.os == "darwin":
            return self._search_homebrew()
        elif self.platform.os == "linux":
            return self._search_apt()
        elif self.platform.os == "windows":
            return self._search_chocolatey()
        return []

    def _search_homebrew(self) -> List[SystemToolchain]:
        """
        Search Homebrew installations (macOS).

        Returns:
            List of toolchains from Homebrew
        """
        toolchains = []

        # Check both Intel and Apple Silicon Homebrew paths
        brew_prefixes = [
            Path("/usr/local"),
            Path("/opt/homebrew"),
        ]

        for brew_prefix in brew_prefixes:
            cellar = brew_prefix / "Cellar"
            if not cellar.exists():
                continue

            logger.debug(f"Searching Homebrew cellar: {cellar}")

            # Search for llvm and gcc in Cellar
            for package_name in ["llvm", "gcc"]:
                package_dir = cellar / package_name
                if not package_dir.exists():
                    continue

                # Each version is a subdirectory
                try:
                    for version_dir in package_dir.iterdir():
                        if not version_dir.is_dir():
                            continue

                        bin_dir = version_dir / "bin"
                        if not bin_dir.exists():
                            continue

                        # Look for compilers
                        if package_name == "llvm":
                            compiler = bin_dir / "clang++"
                        else:
                            compiler = bin_dir / "g++"

                        if compiler.exists():
                            extractor = CompilerVersionExtractor()
                            path_searcher = PathSearcher()

                            toolchain_type = "llvm" if package_name == "llvm" else "gcc"
                            toolchain = path_searcher._create_toolchain(
                                compiler, toolchain_type, extractor
                            )
                            if toolchain:
                                toolchain.source = "package_manager"
                                toolchains.append(toolchain)
                                logger.info(
                                    f"Found {package_name} {toolchain.version} from Homebrew"
                                )
                except Exception as e:
                    logger.debug(f"Error searching {package_dir}: {e}")

        return toolchains

    def _search_apt(self) -> List[SystemToolchain]:
        """
        Search apt installations (Linux).

        Returns:
            List of toolchains from apt
        """
        toolchains = []

        # Check /usr/bin for versioned compilers (gcc-13, clang-17, etc.)
        usr_bin = Path("/usr/bin")
        if not usr_bin.exists():
            return []

        logger.debug("Searching /usr/bin for versioned compilers")

        extractor = CompilerVersionExtractor()
        path_searcher = PathSearcher()

        try:
            for entry in usr_bin.iterdir():
                name = entry.name

                # Match patterns like gcc-13, g++-13, clang++-17
                gcc_match = re.match(r"g\+\+-(\d+)$", name)
                clang_match = re.match(r"clang\+\+-(\d+)$", name)

                if gcc_match or clang_match:
                    if gcc_match:
                        toolchain_type = "gcc"
                    else:
                        toolchain_type = "llvm"

                    toolchain = path_searcher._create_toolchain(
                        entry, toolchain_type, extractor
                    )
                    if toolchain:
                        toolchain.source = "package_manager"
                        toolchains.append(toolchain)
                        logger.info(f"Found {name} from apt")
        except Exception as e:
            logger.debug(f"Error searching /usr/bin: {e}")

        return toolchains

    def _search_chocolatey(self) -> List[SystemToolchain]:
        """
        Search Chocolatey installations (Windows).

        Returns:
            List of toolchains from Chocolatey
        """
        # Chocolatey typically installs to standard locations that are
        # already covered by StandardLocationSearcher, so return empty
        return []


class SystemToolchainDetector:
    """
    Detects compilers installed on the system.

    Orchestrates multiple search strategies:
    - PATH search
    - Standard location search
    - Registry search (Windows)
    - Package manager search

    Deduplicates results and provides filtered views.
    """

    def __init__(self, platform: PlatformInfo):
        """
        Initialize detector.

        Args:
            platform: Platform information for platform-specific searches
        """
        self.platform = platform
        self.searchers = [
            PathSearcher(),
            StandardLocationSearcher(platform),
            PackageManagerSearcher(platform),
        ]

        if platform.os == "windows":
            self.searchers.append(RegistrySearcher())

    def detect_all(self) -> List[SystemToolchain]:
        """
        Detect all available system toolchains.

        Runs all searchers and deduplicates results by compiler path.

        Returns:
            List of unique system toolchains
        """
        toolchains = []
        seen = set()

        logger.info("Starting system toolchain detection")

        for searcher in self.searchers:
            try:
                logger.debug(f"Running {searcher.__class__.__name__}")
                found = searcher.search()  # type: ignore[attr-defined]
                logger.debug(
                    f"{searcher.__class__.__name__} found {len(found)} toolchains"
                )

                for toolchain in found:
                    # Deduplicate by compiler path
                    key = str(toolchain.compiler_path.resolve())
                    if key not in seen:
                        toolchains.append(toolchain)
                        seen.add(key)
            except Exception as e:
                logger.warning(f"Searcher {searcher.__class__.__name__} failed: {e}")

        logger.info(f"Detected {len(toolchains)} system toolchains")
        return toolchains

    def detect_type(self, toolchain_type: str) -> List[SystemToolchain]:
        """
        Detect toolchains of a specific type.

        Args:
            toolchain_type: Type to filter for ('llvm', 'gcc', 'msvc')

        Returns:
            List of toolchains matching the type
        """
        all_toolchains = self.detect_all()
        filtered = [tc for tc in all_toolchains if tc.type == toolchain_type]
        logger.info(f"Found {len(filtered)} {toolchain_type} toolchains")
        return filtered

    def detect_best(self) -> Optional[SystemToolchain]:
        """
        Detect the best available toolchain.

        Prefers LLVM > GCC > MSVC, and selects the newest version.

        Returns:
            Best toolchain or None if no toolchains found
        """
        toolchains = self.detect_all()

        if not toolchains:
            logger.info("No system toolchains found")
            return None

        # Prefer LLVM, then GCC, then MSVC
        for preferred_type in ["llvm", "gcc", "msvc"]:
            candidates = [tc for tc in toolchains if tc.type == preferred_type]
            if candidates:
                # Return newest version (simple string comparison works for semantic versions)
                best = max(candidates, key=lambda tc: tc.version)
                logger.info(f"Best toolchain: {best.type} {best.version}")
                return best

        # Fallback to first found
        logger.info(
            f"Using first available toolchain: {toolchains[0].type} {toolchains[0].version}"
        )
        return toolchains[0]
