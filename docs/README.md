# ToolchainKit Documentation

Complete documentation for ToolchainKit - hermetic, cross-platform C++ build manager.

## Quick Links

- [README](../README.md) - Project overview and quick start
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)

## Core Concepts

### Infrastructure
- [Platform Detection](platform.md) - OS, architecture, and ABI detection
- [Directory Structure](directory.md) - Global cache and project-local layout
- [Filesystem](filesystem.md) - Cross-platform file operations
- [Download Manager](download.md) - Resumable downloads with verification
- [Concurrent Access](locking.md) - Multi-process coordination
- [Registry](registry.md) - Shared toolchain registry with reference counting
- [Verification](verification.md) - Hash verification and integrity checks

### Configuration
- [Configuration Files](config.md) - toolchainkit.yaml format
- [Configuration Layers](config_layers.md) - Composable build configurations
- [Lock Files](lockfile.md) - Reproducible builds with cryptographic verification
- [State Management](state.md) - Project state tracking

### Toolchains
- [Toolchain Management](toolchains.md) - Download, install, verify, cleanup
- [System Detection](toolchains.md#system-detection) - Find installed compilers
- [CMake Integration](cmake_toolchain.md) - CMake toolchain file generation

### Dependencies
- [Package Managers](package_managers.md) - Conan and vcpkg integration
- [Build Cache](build_cache.md) - sccache/ccache for faster builds

### Advanced Features
- [Cross-Compilation](cross_compilation.md) - Android, iOS, Raspberry Pi
- [Sysroot Management](sysroot.md) - System root filesystems for cross-compilation
- [Plugins](plugins.md) - Custom compilers and package managers

### CLI and Automation
- [CLI Reference](cli.md) - Command-line interface reference ⚠️ *In Development*
- [Bootstrap Scripts](bootstrap.md) - Generate automated setup scripts ⚠️ *Partial*
- [Doctor](doctor.md) - Diagnose environment issues with auto-fix
- [Upgrade](upgrade.md) - Upgrade toolchains and ToolchainKit

## IDE Integration

- [VS Code](ide_vscode.md) - VS Code integration
- [CMake Presets](ide_cmake_presets.md) - CMakePresets.json generation

## Additional Resources

- [Architecture](architecture.md) - System design
- [CI/CD Templates](ci_cd.md) - GitHub Actions, GitLab CI templates
- [Configuration Schema](config_schema.md) - Complete schema reference

## Getting Help

- GitHub Issues: https://github.com/hovhannest/toolchainkit/issues
- Discussions: https://github.com/hovhannest/toolchainkit/discussions

## Contributing

See [Contributing Guide](../CONTRIBUTING.md) for development setup and guidelines.
