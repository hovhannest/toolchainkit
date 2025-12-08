# VS Code Integration

Configure VS Code for ToolchainKit projects with automatic toolchain, compiler, and code quality tools integration.

## Quick Start

```bash
# Auto-generate VS Code settings
tkgen vscode
```

Generates `.vscode/settings.json`:
```json
{
  "cmake.configureSettings": {
    "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
  },
  "C_Cpp.default.compilerPath": "/opt/llvm-18/bin/clang++",
  "cmake.buildDirectory": "${workspaceFolder}/build",
  "cmake.generator": "Ninja",
  "cmake.exportCompileCommandsFile": true
}
```

## Required Extensions

- **C/C++** (`ms-vscode.cpptools`) - IntelliSense, code formatting, and static analysis
- **CMake Tools** (`ms-vscode.cmake-tools`) - CMake integration

Auto-generated in `.vscode/extensions.json`:
```json
{
  "recommendations": [
    "ms-vscode.cpptools",
    "ms-vscode.cmake-tools",
    "twxs.cmake"
  ]
}
```

## Clang Format Integration

ToolchainKit automatically configures `clang-format` when using LLVM toolchains and a `.clang-format` file is present in the project root.

### Automatic Configuration

When you run `tkgen vscode` with an LLVM toolchain and `.clang-format` file:

```json
{
  "C_Cpp.clang_format_path": "/opt/llvm-18/bin/clang-format",
  "editor.formatOnSave": true,
  "editor.formatOnSaveMode": "modifications"
}
```

### Format on Save

Code is automatically formatted on save, but only modified lines are reformatted to avoid unnecessary changes.

### Tasks

A task is generated in `.vscode/tasks.json` to format the entire codebase:

```json
{
  "label": "Clang Format: All Files",
  "type": "shell",
  "command": "/opt/llvm-18/bin/clang-format -i src/**/*.cpp src/**/*.h"
}
```

Run via **Terminal > Run Task > Clang Format: All Files**.

### Configuration File

Create a `.clang-format` file in your project root:

```yaml
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
```

## Clang Tidy Integration

ToolchainKit automatically configures `clang-tidy` when using LLVM toolchains and a `.clang-tidy` file is present in the project root.

### Automatic Configuration

When you run `tkgen vscode` with an LLVM toolchain and `.clang-tidy` file:

```json
{
  "C_Cpp.codeAnalysis.clangTidy.enabled": true,
  "C_Cpp.codeAnalysis.clangTidy.path": "/opt/llvm-18/bin/clang-tidy"
}
```

### Tasks

Two tasks are generated in `.vscode/tasks.json`:

**Check Mode** (read-only analysis):
```json
{
  "label": "Clang Tidy: Check",
  "type": "shell",
  "command": "/opt/llvm-18/bin/clang-tidy -p build src/**/*.cpp"
}
```

**Fix Mode** (applies automatic fixes):
```json
{
  "label": "Clang Tidy: Fix",
  "type": "shell",
  "command": "/opt/llvm-18/bin/clang-tidy -p build --fix src/**/*.cpp"
}
```

Run via **Terminal > Run Task > Clang Tidy: Check** or **Clang Tidy: Fix**.

### Configuration File

Create a `.clang-tidy` file in your project root:

```yaml
Checks: '-*,modernize-*,readability-*,performance-*'
WarningsAsErrors: ''
HeaderFilterRegex: '.*'
FormatStyle: file
```

### CMake Integration

When using `tkgen configure`, Clang Tidy is also configured in the CMake toolchain file:

```cmake
set(CMAKE_CXX_CLANG_TIDY "/opt/llvm-18/bin/clang-tidy" CACHE STRING "Clang-Tidy setup" FORCE)
```

This enables Clang Tidy checks during the build process.

## Manual Configuration

```json
// .vscode/settings.json
{
  "cmake.configureSettings": {
    "CMAKE_TOOLCHAIN_FILE": "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
  },
  "C_Cpp.default.configurationProvider": "ms-vscode.cmake-tools",
  "C_Cpp.clang_format_path": "/opt/llvm-18/bin/clang-format",
  "editor.formatOnSave": true,
  "editor.formatOnSaveMode": "modifications",
  "C_Cpp.codeAnalysis.clangTidy.enabled": true,
  "C_Cpp.codeAnalysis.clangTidy.path": "/opt/llvm-18/bin/clang-tidy"
}
```

## API

```python
from toolchainkit.ide.vscode import VSCodeIntegrator
from pathlib import Path

integrator = VSCodeIntegrator(project_root)

# Generate settings with Clang tools
integrator.generate_settings(
    toolchain_file=Path(".toolchainkit/cmake/toolchain.cmake"),
    compiler_path=Path("/opt/llvm-18/bin/clang++"),
    build_dir="build",
    generator="Ninja",
    clang_format_path=Path("/opt/llvm-18/bin/clang-format"),
    clang_tidy_path=Path("/opt/llvm-18/bin/clang-tidy")
)

# Generate tasks with Clang tools
integrator.generate_tasks_config(
    clang_format_path=Path("/opt/llvm-18/bin/clang-format"),
    clang_tidy_path=Path("/opt/llvm-18/bin/clang-tidy")
)

# Generate extensions recommendations
integrator.generate_extensions_json()
```

## CMake Kit

VS Code CMake Tools can also use kits:
```json
// .vscode/cmake-kits.json
[
  {
    "name": "ToolchainKit LLVM 18",
    "toolchainFile": "${workspaceFolder}/.toolchainkit/cmake/toolchain.cmake"
  }
]
```

## Workflow

1. Install recommended extensions
2. Create `.clang-format` and/or `.clang-tidy` configuration files (optional)
3. Run `tkgen vscode` to generate VSCode configuration
4. Open project in VS Code
5. CMake Tools auto-detects toolchain file
6. IntelliSense uses correct compiler paths
7. Code formatting happens automatically on save
8. Clang Tidy analysis runs in the background
9. Build with Cmd+Shift+B (macOS) or Ctrl+Shift+B (Windows/Linux)

## Troubleshooting

### Clang Format Not Working

- Ensure `.clang-format` file exists in project root
- Verify `C_Cpp.clang_format_path` points to correct executable
- Check that LLVM toolchain is active: `tkgen doctor`

### Clang Tidy Not Running

- Ensure `.clang-tidy` file exists in project root
- Verify `C_Cpp.codeAnalysis.clangTidy.path` points to correct executable
- Ensure `compile_commands.json` is generated: `cmake.exportCompileCommandsFile: true`
- Run CMake configure at least once to generate compilation database
