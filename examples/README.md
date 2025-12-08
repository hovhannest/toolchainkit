# ToolchainKit Examples

Comprehensive examples demonstrating how to use ToolchainKit in various scenarios.

## Usage Examples

### Core Use Cases

1. **[New Project from Scratch](01-new-project/)**
   - Bootstrap a brand new C++ project
   - Modern toolchain setup (LLVM 18)
   - Package management (Conan)
   - CI/CD ready from day one

2. **[Existing CMake Project](02-existing-cmake/)**
   - Migrate legacy project to ToolchainKit
   - Minimal changes to existing code
   - Backwards compatible approach
   - Migration checklist and rollback plan

3. **[CI/CD Integration](03-cicd-integration/)**
   - GitHub Actions workflows
   - GitLab CI pipelines
   - Azure Pipelines configuration
   - Multi-platform build matrices
   - Caching strategies for fast builds

4. **[Cross-Platform & Cross-Compilation](04-cross-compilation/)**
   - Build for Windows, Linux, macOS
   - Android and iOS targets
   - Embedded systems (Raspberry Pi)
   - Unified build workflow

5. **[Developer Onboarding](05-developer-onboarding/)**
   - 10-minute setup (vs 2-4 hours manual)
   - Complete onboarding guide
   - Troubleshooting documentation
   - Team collaboration best practices

6. **[Reproducible & Secure Builds](06-reproducible-builds/)**
   - Lock file system for version pinning
   - Cryptographic verification
   - Supply chain security
   - SBOM generation
   - Compliance and auditing

7. **[Custom Allocator Integration](07-custom-allocator/)**
   - Add custom allocators (mimalloc, jemalloc, tcmalloc)
   - Minimal CMakeLists.txt modifications
   - Performance benchmarking
   - Switch allocators via configuration
   - CI/CD testing with multiple allocators

## Plugin Examples

This directory also contains example plugins demonstrating how to extend ToolchainKit with custom compilers and package managers.

### Available Plugins

- **[zig-compiler](plugins/zig-compiler/)** - Complete example adding Zig compiler support
  - Demonstrates custom compiler integration
  - Cross-compilation configuration
  - CMake toolchain generation
  - Comprehensive documentation and tests

- **[hunter-package-manager](plugins/hunter-package-manager/)** - Hunter package manager integration
  - Shows package manager plugin structure
  - CMake-based dependency management
  - Configuration examples

## Quick Start

Each example includes:
- ✅ Complete README with step-by-step instructions
- ✅ Sample configuration files (`toolchainkit.yaml`)
- ✅ Bootstrap scripts (where applicable)
- ✅ CMakeLists.txt examples
- ✅ CI/CD workflow examples

### Running an Example

```bash
# Navigate to example directory
cd 01-new-project

# Read the guide
cat README.md

# Try it out (assuming bootstrap CLI is implemented)
tkgen init --toolchain llvm-18
tkgen bootstrap
cmake --build build
```

## Use Case Matrix

| Example | New Project | Existing Project | CI/CD | Cross-Platform | Onboarding | Security |
|---------|-------------|------------------|-------|----------------|------------|----------|
| 01-new-project | ✅ | ❌ | ✅ | ✅ | ✅ | ⚠️ |
| 02-existing-cmake | ⚠️ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| 03-cicd-integration | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| 04-cross-compilation | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| 05-developer-onboarding | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ |
| 06-reproducible-builds | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| 07-custom-allocator | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |

Legend: ✅ Primary focus | ⚠️ Covered | ❌ Not applicable

## Using Example Plugins

### Installation

Copy the plugin to your ToolchainKit plugins directory:

```bash
# Linux/macOS
cp -r plugins/zig-compiler ~/.toolchainkit/plugins/

# Windows
xcopy /E /I plugins\zig-compiler %USERPROFILE%\.toolchainkit\plugins\zig-compiler\
```

Or use project-local plugins by placing them in your project's `plugins/` directory.

### Configuration

Each plugin includes detailed configuration instructions in its README.md.

## Plugin Development

These examples serve as templates for creating your own plugins. See:

- [Plugin Development Guide](../docs/plugins.md)
- [Plugin API Documentation](../docs/dev/extending.md)
- Individual plugin READMEs for implementation details

## Contributing Examples

We welcome additional examples! Please ensure:

- Complete README.md with usage instructions
- Sample configuration files
- Working code (if applicable)
- Clear documentation of prerequisites
- Appropriate license (MIT preferred)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## Additional Resources

- [Documentation](../docs/) - Complete ToolchainKit documentation
- [Bootstrap Guide](../docs/bootstrap.md) - Bootstrap script details
- [CI/CD Guide](../docs/ci_cd.md) - CI/CD integration guide
- [Configuration Reference](../docs/config.md) - Configuration options
