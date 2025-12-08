"""
Test project templates for CMake integration testing.

Provides reusable test project structures (Hello World, Library projects, etc.)
for testing CMake toolchain generation and build backend configuration.
"""

from pathlib import Path
from typing import List
import textwrap


class TestProject:
    """Base class for test CMake projects."""

    def __init__(self, name: str):
        """
        Initialize test project.

        Args:
            name: Project name
        """
        self.name = name

    def create(self, target_dir: Path):
        """
        Create test project files in target directory.

        Args:
            target_dir: Directory to create project in
        """
        raise NotImplementedError

    def get_expected_outputs(self) -> List[str]:
        """
        Get list of expected build artifact names.

        Returns:
            List of expected output file names (platform-agnostic)
        """
        raise NotImplementedError


class HelloWorldProject(TestProject):
    """Simple hello world C++ project."""

    CMAKELISTS = textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.20)
        project(HelloWorld CXX)

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)

        add_executable(hello main.cpp)
    """
    ).strip()

    MAIN_CPP = textwrap.dedent(
        """
        #include <iostream>
        #include <string>

        int main() {
            std::string greeting = "Hello, World!";
            std::cout << greeting << std::endl;
            return 0;
        }
    """
    ).strip()

    def __init__(self):
        super().__init__("HelloWorld")

    def create(self, target_dir: Path):
        """Create hello world project files."""
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "CMakeLists.txt").write_text(self.CMAKELISTS)
        (target_dir / "main.cpp").write_text(self.MAIN_CPP)

    def get_expected_outputs(self) -> List[str]:
        """Expected build outputs (platform-agnostic)."""
        return ["hello", "hello.exe"]  # Unix, Windows


class LibraryProject(TestProject):
    """Project with library and executable."""

    CMAKELISTS = textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.20)
        project(LibTest CXX)

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)

        add_library(mylib lib.cpp)
        add_executable(app main.cpp)
        target_link_libraries(app PRIVATE mylib)
    """
    ).strip()

    LIB_CPP = textwrap.dedent(
        """
        #include "lib.h"

        int add(int a, int b) {
            return a + b;
        }

        int multiply(int a, int b) {
            return a * b;
        }
    """
    ).strip()

    LIB_H = textwrap.dedent(
        """
        #pragma once

        int add(int a, int b);
        int multiply(int a, int b);
    """
    ).strip()

    MAIN_CPP = textwrap.dedent(
        """
        #include "lib.h"
        #include <iostream>

        int main() {
            std::cout << "2 + 3 = " << add(2, 3) << std::endl;
            std::cout << "2 * 3 = " << multiply(2, 3) << std::endl;
            return 0;
        }
    """
    ).strip()

    def __init__(self):
        super().__init__("LibTest")

    def create(self, target_dir: Path):
        """Create library project files."""
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "CMakeLists.txt").write_text(self.CMAKELISTS)
        (target_dir / "lib.cpp").write_text(self.LIB_CPP)
        (target_dir / "lib.h").write_text(self.LIB_H)
        (target_dir / "main.cpp").write_text(self.MAIN_CPP)

    def get_expected_outputs(self) -> List[str]:
        """Expected build outputs."""
        return [
            "app",
            "app.exe",  # Executable
            "libmylib.a",
            "libmylib.so",
            "mylib.lib",
            "mylib.dll",  # Library variants
        ]


class MultiFileProject(TestProject):
    """Project with multiple source files."""

    CMAKELISTS = textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.20)
        project(MultiFile CXX)

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)

        add_executable(multifile
            main.cpp
            math.cpp
            string_utils.cpp
        )
    """
    ).strip()

    MAIN_CPP = textwrap.dedent(
        """
        #include "math.h"
        #include "string_utils.h"
        #include <iostream>

        int main() {
            std::cout << "10 + 5 = " << Math::add(10, 5) << std::endl;
            std::cout << "Uppercase: " << StringUtils::toUpper("hello") << std::endl;
            return 0;
        }
    """
    ).strip()

    MATH_H = textwrap.dedent(
        """
        #pragma once

        namespace Math {
            int add(int a, int b);
            int subtract(int a, int b);
        }
    """
    ).strip()

    MATH_CPP = textwrap.dedent(
        """
        #include "math.h"

        namespace Math {
            int add(int a, int b) {
                return a + b;
            }

            int subtract(int a, int b) {
                return a - b;
            }
        }
    """
    ).strip()

    STRING_UTILS_H = textwrap.dedent(
        """
        #pragma once
        #include <string>

        namespace StringUtils {
            std::string toUpper(const std::string& str);
            std::string toLower(const std::string& str);
        }
    """
    ).strip()

    STRING_UTILS_CPP = textwrap.dedent(
        """
        #include "string_utils.h"
        #include <algorithm>
        #include <cctype>

        namespace StringUtils {
            std::string toUpper(const std::string& str) {
                std::string result = str;
                std::transform(result.begin(), result.end(), result.begin(),
                             [](unsigned char c){ return std::toupper(c); });
                return result;
            }

            std::string toLower(const std::string& str) {
                std::string result = str;
                std::transform(result.begin(), result.end(), result.begin(),
                             [](unsigned char c){ return std::tolower(c); });
                return result;
            }
        }
    """
    ).strip()

    def __init__(self):
        super().__init__("MultiFile")

    def create(self, target_dir: Path):
        """Create multi-file project."""
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "CMakeLists.txt").write_text(self.CMAKELISTS)
        (target_dir / "main.cpp").write_text(self.MAIN_CPP)
        (target_dir / "math.h").write_text(self.MATH_H)
        (target_dir / "math.cpp").write_text(self.MATH_CPP)
        (target_dir / "string_utils.h").write_text(self.STRING_UTILS_H)
        (target_dir / "string_utils.cpp").write_text(self.STRING_UTILS_CPP)

    def get_expected_outputs(self) -> List[str]:
        """Expected build outputs."""
        return ["multifile", "multifile.exe"]


class ModernCppProject(TestProject):
    """Project using modern C++17/20 features."""

    CMAKELISTS = textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.20)
        project(ModernCpp CXX)

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)
        set(CMAKE_CXX_EXTENSIONS OFF)

        add_executable(modern main.cpp)
    """
    ).strip()

    MAIN_CPP = textwrap.dedent(
        """
        #include <iostream>
        #include <vector>
        #include <string>
        #include <algorithm>
        #include <optional>
        #include <variant>

        // Structured bindings
        std::pair<int, std::string> getPair() {
            return {42, "answer"};
        }

        // std::optional
        std::optional<int> parseNumber(const std::string& str) {
            try {
                return std::stoi(str);
            } catch (...) {
                return std::nullopt;
            }
        }

        // std::variant
        using Value = std::variant<int, double, std::string>;

        int main() {
            // Auto with structured bindings
            auto [num, text] = getPair();
            std::cout << "Pair: " << num << ", " << text << std::endl;

            // Optional
            if (auto val = parseNumber("123"); val) {
                std::cout << "Parsed: " << *val << std::endl;
            }

            // Range-based for with init
            std::vector<int> numbers = {1, 2, 3, 4, 5};
            for (const auto& n : numbers) {
                std::cout << n << " ";
            }
            std::cout << std::endl;

            // Variant
            Value v = 42;
            std::cout << "Variant holds: " << std::get<int>(v) << std::endl;

            return 0;
        }
    """
    ).strip()

    def __init__(self):
        super().__init__("ModernCpp")

    def create(self, target_dir: Path):
        """Create modern C++ project."""
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "CMakeLists.txt").write_text(self.CMAKELISTS)
        (target_dir / "main.cpp").write_text(self.MAIN_CPP)

    def get_expected_outputs(self) -> List[str]:
        """Expected build outputs."""
        return ["modern", "modern.exe"]


class SubdirectoryProject(TestProject):
    """Project with subdirectories."""

    ROOT_CMAKE = textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.20)
        project(SubdirTest CXX)

        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)

        add_subdirectory(lib)
        add_subdirectory(app)
    """
    ).strip()

    LIB_CMAKE = textwrap.dedent(
        """
        add_library(calculator
            calculator.cpp
        )

        target_include_directories(calculator PUBLIC .)
    """
    ).strip()

    LIB_H = textwrap.dedent(
        """
        #pragma once

        class Calculator {
        public:
            static int add(int a, int b);
            static int multiply(int a, int b);
        };
    """
    ).strip()

    LIB_CPP = textwrap.dedent(
        """
        #include "calculator.h"

        int Calculator::add(int a, int b) {
            return a + b;
        }

        int Calculator::multiply(int a, int b) {
            return a * b;
        }
    """
    ).strip()

    APP_CMAKE = textwrap.dedent(
        """
        add_executable(calculator_app main.cpp)
        target_link_libraries(calculator_app PRIVATE calculator)
    """
    ).strip()

    APP_MAIN = textwrap.dedent(
        """
        #include "calculator.h"
        #include <iostream>

        int main() {
            std::cout << "5 + 3 = " << Calculator::add(5, 3) << std::endl;
            std::cout << "5 * 3 = " << Calculator::multiply(5, 3) << std::endl;
            return 0;
        }
    """
    ).strip()

    def __init__(self):
        super().__init__("SubdirTest")

    def create(self, target_dir: Path):
        """Create subdirectory project."""
        target_dir.mkdir(parents=True, exist_ok=True)

        # Root
        (target_dir / "CMakeLists.txt").write_text(self.ROOT_CMAKE)

        # Lib subdirectory
        lib_dir = target_dir / "lib"
        lib_dir.mkdir(exist_ok=True)
        (lib_dir / "CMakeLists.txt").write_text(self.LIB_CMAKE)
        (lib_dir / "calculator.h").write_text(self.LIB_H)
        (lib_dir / "calculator.cpp").write_text(self.LIB_CPP)

        # App subdirectory
        app_dir = target_dir / "app"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "CMakeLists.txt").write_text(self.APP_CMAKE)
        (app_dir / "main.cpp").write_text(self.APP_MAIN)

    def get_expected_outputs(self) -> List[str]:
        """Expected build outputs."""
        return ["calculator_app", "calculator_app.exe"]


# Registry of available test projects
TEST_PROJECTS = {
    "hello": HelloWorldProject,
    "library": LibraryProject,
    "multifile": MultiFileProject,
    "modern": ModernCppProject,
    "subdirectory": SubdirectoryProject,
}


def get_test_project(name: str) -> TestProject:
    """
    Get a test project by name.

    Args:
        name: Project name (e.g., 'hello', 'library')

    Returns:
        TestProject instance

    Raises:
        KeyError: If project name not found
    """
    project_class = TEST_PROJECTS.get(name.lower())
    if project_class is None:
        available = ", ".join(TEST_PROJECTS.keys())
        raise KeyError(
            f"Unknown test project: {name}. " f"Available projects: {available}"
        )

    return project_class()


def list_test_projects() -> List[str]:
    """
    List all available test project names.

    Returns:
        List of project names
    """
    return list(TEST_PROJECTS.keys())


if __name__ == "__main__":
    import tempfile

    # Example: Create all test projects
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        for name, project_class in TEST_PROJECTS.items():
            print(f"\n=== {name.upper()} ===")
            project = project_class()
            project_dir = tmp_path / name
            project.create(project_dir)

            print(f"Created: {project_dir}")
            print(f"Files: {[f.name for f in project_dir.rglob('*') if f.is_file()]}")
            print(f"Expected outputs: {project.get_expected_outputs()}")
