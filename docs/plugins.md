# Plugin System

> **✅ Status: Fully Implemented (v0.1.0)**
> The plugin system is complete and production-ready.

ToolchainKit provides a powerful plugin system for extending functionality with custom compilers, package managers, and build backends.

## Overview

The plugin system enables third-party extensions through a well-defined API:

- **CompilerPlugin** - Add custom compiler toolchains (Zig, D, Rust, etc.)
- **PackageManagerPlugin** - Integrate package managers (Hunter, Buckaroo, etc.)
- **BuildBackendPlugin** - Add build systems (Bazel, Meson, etc.)

### Features

- 🔌 **Auto-discovery** - Plugins automatically discovered from standard locations
- 📦 **Isolated** - Each plugin runs in its own namespace
- ✅ **Validated** - Metadata and dependencies validated on load
- 🔄 **Lifecycle managed** - Initialize, use, cleanup lifecycle
- 🛠️ **Rich API** - Access to ToolchainKit's full infrastructure

## Quick Start

### Using Existing Plugins

```python
from toolchainkit.plugins import PluginManager
from pathlib import Path

# Initialize plugin manager
manager = PluginManager()

# Discover and load all plugins
manager.discover_and_load_all()

# List available plugins
for plugin in manager.list_plugins():
    print(f"{plugin.name} v{plugin.version} - {plugin.description}")

# Use a specific plugin (example: Zig compiler)
if manager.has_plugin("zig-compiler"):
    plugin = manager.get_plugin("zig-compiler")
    # Plugin is now active and registered
```

### Creating a Plugin

#### 1. Plugin Structure

```
my-plugin/
├── plugin.yaml          # Metadata
├── my_plugin.py         # Implementation
├── compilers/           # Optional: compiler configs
│   └── my_compiler.yaml
└── tests/               # Recommended: tests
    └── test_my_plugin.py
```

#### 2. Plugin Metadata (plugin.yaml)

```yaml
name: my-compiler
version: 1.0.0
description: My custom compiler support
author: Your Name
homepage: https://github.com/example/my-plugin
license: MIT

# Plugin type: compiler, package_manager, or build_backend
type: compiler

# Entry point: Python file containing plugin class
entry_point: my_plugin.py
class_name: MyCompilerPlugin

# Dependencies (optional)
requires:
  - base-utils >= 1.0.0

# Tags for searchability (optional)
tags:
  - compiler
  - cross-platform
```

#### 3. Plugin Implementation

```python
"""My Compiler Plugin for ToolchainKit."""

from toolchainkit.plugins import CompilerPlugin, PluginInitializationError
from pathlib import Path
import shutil


class MyCompilerPlugin(CompilerPlugin):
    """Plugin adding my custom compiler support."""

    def metadata(self):
        """Return plugin metadata."""
        return {
            'name': 'my-compiler',
            'version': '1.0.0',
            'description': 'My custom compiler support',
            'author': 'Your Name',
            'license': 'MIT'
        }

    def initialize(self, context):
        """
        Initialize plugin.

        Args:
            context: PluginContext with registry access and helpers
        """
        # Check if compiler exists
        if not self._find_compiler():
            raise PluginInitializationError(
                'my-compiler',
                'My compiler not found in PATH'
            )

        # Load compiler configuration
        config_file = Path(__file__).parent / "compilers" / "my_compiler.yaml"
        if config_file.exists():
            compiler_config = context.load_yaml_compiler(config_file)
            context.register_compiler('my-compiler', compiler_config)

        print("✓ My Compiler plugin initialized")

    def validate(self):
        """Validate compiler is available."""
        return self._find_compiler() is not None

    def cleanup(self):
        """Cleanup on unload."""
        pass  # Optional: cleanup resources

    def _find_compiler(self):
        """Find compiler executable."""
        return shutil.which('mycompiler')


# Export plugin class
__plugin__ = MyCompilerPlugin
```

#### 4. Compiler Configuration (compilers/my_compiler.yaml)

```yaml
# Compiler metadata
name: my-compiler
display_name: My Compiler
version_pattern: "my-compiler version (\\d+\\.\\d+\\.\\d+)"

# Executables
executables:
  c: mycompiler
  cxx: mycompiler++
  ar: myar
  ranlib: myranlib

# Flags by build type
flags:
  common:
    - "-fPIC"

  debug:
    - "-g"
    - "-O0"

  release:
    - "-O3"
    - "-DNDEBUG"

  relwithdebinfo:
    - "-g"
    - "-O2"
    - "-DNDEBUG"

# Cross-compilation support
cross_compilation:
  enabled: true
  targets:
    linux-arm64: "-target aarch64-linux-gnu"
    windows-x64: "-target x86_64-w64-mingw32"

# Standard libraries
stdlib:
  default: "libmystd"
  options:
    - "libmystd"
    - "libmystd-static"
```

## Plugin Installation

### User Installation

```bash
# Copy to user plugin directory
mkdir -p ~/.toolchainkit/plugins
cp -r my-plugin ~/.toolchainkit/plugins/

# Or install via pip (if packaged)
pip install toolchainkit-my-plugin
```

### Project-Local Installation

```bash
# Place in project plugins directory
mkdir -p plugins
cp -r my-plugin plugins/

# Add to .gitignore or commit (your choice)
```

## Plugin API Reference

### Base Plugin Class

```python
from toolchainkit.plugins import Plugin

class Plugin(ABC):
    """Base class for all plugins."""

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def initialize(self, context: PluginContext) -> None:
        """Initialize with context."""
        pass

    def cleanup(self) -> None:
        """Cleanup on unload (optional)."""
        pass

    def validate(self) -> bool:
        """Validate environment (optional)."""
        return True
```

### CompilerPlugin

```python
from toolchainkit.plugins import CompilerPlugin

class MyCompiler(CompilerPlugin):
    """Extend CompilerPlugin for compiler support."""

    def get_compiler_info(self) -> Dict[str, Any]:
        """Return compiler information."""
        return {
            'name': 'my-compiler',
            'version': self._detect_version(),
            'path': self._find_compiler(),
            'targets': ['x86_64', 'arm64']
        }
```

### PackageManagerPlugin

```python
from toolchainkit.plugins import PackageManagerPlugin

class MyPackageManager(PackageManagerPlugin):
    """Extend PackageManagerPlugin for package manager support."""

    def detect(self) -> bool:
        """Check if package manager is installed."""
        pass

    def install(self) -> bool:
        """Install package manager."""
        pass

    def install_dependencies(self, deps: List[str]) -> bool:
        """Install project dependencies."""
        pass
```

### BuildBackendPlugin

```python
from toolchainkit.plugins import BuildBackendPlugin

class MyBuildBackend(BuildBackendPlugin):
    """Extend BuildBackendPlugin for build system support."""

    def configure(self, config: Dict) -> bool:
        """Configure build."""
        pass

    def build(self, target: Optional[str] = None) -> bool:
        """Run build."""
        pass
```

### PluginContext

Provided to `initialize()` method:

```python
class PluginContext:
    """Context provided to plugins during initialization."""

    def register_compiler(self, name: str, config: Any) -> None:
        """Register a compiler configuration."""

    def register_package_manager(self, name: str, manager: Any) -> None:
        """Register a package manager."""

    def register_build_backend(self, name: str, backend: Any) -> None:
        """Register a build backend."""

    def load_yaml_compiler(self, path: Path) -> Any:
        """Load compiler config from YAML file."""

    def get_cache_dir(self) -> Path:
        """Get plugin cache directory."""

    def get_config(self) -> Any:
        """Get global configuration."""
```

## Plugin Discovery

Plugins are discovered from:

1. **Global directory**: `~/.toolchainkit/plugins/`
2. **Project directory**: `<project>/plugins/`
3. **Python packages**: Installed via pip with entry points

### Discovery Process

```python
from toolchainkit.plugins import PluginDiscoverer

discoverer = PluginDiscoverer()

# Discover from all locations
plugins = discoverer.discover_all()

# Discover from specific path
plugins = discoverer.discover_from_path(Path("/custom/plugins"))

# Each discovery returns PluginMetadata
for metadata in plugins:
    print(f"Found: {metadata.name} v{metadata.version}")
```

## Plugin Manager

Central management of plugin lifecycle:

```python
from toolchainkit.plugins import PluginManager

manager = PluginManager()

# Discover and load
manager.discover_and_load_all()

# Query plugins
if manager.has_plugin("zig-compiler"):
    plugin = manager.get_plugin("zig-compiler")
    print(f"Loaded: {plugin.metadata()['name']}")

# List all
for plugin in manager.list_plugins():
    print(f"- {plugin.name}")

# Unload plugin
manager.unload_plugin("zig-compiler")
```

## Example Plugins

ToolchainKit includes example plugins in `examples/plugins/`:

### Zig Compiler Plugin

Full-featured example showing:
- Compiler detection
- YAML configuration
- Cross-compilation support
- CMake integration

Location: `examples/plugins/zig-compiler/`

### Hunter Package Manager Plugin

Example showing:
- Package manager integration
- CMake integration
- Dependency resolution

Location: `examples/plugins/hunter-package-manager/`

## Testing Plugins

### Unit Testing

```python
import pytest
from pathlib import Path
from toolchainkit.plugins import PluginLoader, PluginContext

def test_my_plugin_loads():
    """Test plugin loads successfully."""
    loader = PluginLoader()
    plugin_dir = Path(__file__).parent.parent

    plugin = loader.load_from_path(plugin_dir)
    assert plugin is not None
    assert plugin.metadata()['name'] == 'my-compiler'

def test_my_plugin_initializes():
    """Test plugin initializes with context."""
    # Create mock context
    context = PluginContext()

    # Load and initialize plugin
    plugin = MyCompilerPlugin()
    plugin.initialize(context)

    # Verify registration
    assert context.has_compiler('my-compiler')
```

### Integration Testing

```python
def test_my_plugin_integration():
    """Test plugin works with ToolchainKit."""
    from toolchainkit.plugins import PluginManager
    from toolchainkit.cmake.toolchain_generator import CMakeToolchainGenerator

    # Load plugin
    manager = PluginManager()
    manager.load_from_path(Path(__file__).parent.parent)

    # Use with CMake generator
    generator = CMakeToolchainGenerator(project_root)
    # ... test CMake generation with custom compiler
```

## Best Practices

### 1. Error Handling

```python
def initialize(self, context):
    try:
        # Validate environment
        if not self._validate_environment():
            raise PluginInitializationError(
                self.metadata()['name'],
                "Required dependencies not found"
            )

        # Initialize resources
        self._setup_resources()

    except Exception as e:
        raise PluginInitializationError(
            self.metadata()['name'],
            f"Initialization failed: {e}"
        ) from e
```

### 2. Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(CompilerPlugin):
    def initialize(self, context):
        logger.info(f"Initializing {self.metadata()['name']}")
        # ... initialization
        logger.debug("Initialization complete")
```

### 3. Validation

```python
def validate(self):
    """Comprehensive environment validation."""
    checks = [
        self._check_compiler_exists(),
        self._check_required_libs(),
        self._check_system_compatibility()
    ]

    if not all(checks):
        logger.warning("Plugin validation failed")
        return False

    return True
```

### 4. Resource Cleanup

```python
def cleanup(self):
    """Clean up resources on unload."""
    # Close file handles
    if hasattr(self, '_cache_file'):
        self._cache_file.close()

    # Terminate processes
    if hasattr(self, '_background_process'):
        self._background_process.terminate()

    # Remove temp files
    if hasattr(self, '_temp_dir'):
        shutil.rmtree(self._temp_dir, ignore_errors=True)
```

## Debugging Plugins

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Or configure ToolchainKit logger
logging.getLogger('toolchainkit.plugins').setLevel(logging.DEBUG)
```

### Common Issues

**Plugin not discovered:**
- Check `plugin.yaml` exists in plugin directory
- Verify YAML syntax is valid
- Ensure plugin directory is in search path

**Plugin load fails:**
- Check entry_point file exists
- Verify class_name matches Python class
- Check for Python syntax errors

**Initialization fails:**
- Check dependencies are installed
- Verify compiler/tool exists in PATH
- Review error messages from PluginInitializationError

## Related Documentation

- [Compiler Configuration](cmake_toolchain.md) - CMake compiler setup
- [Package Managers](package_managers.md) - Package manager integration
- [Extension Guide](dev/extending.md) - Developer extension guide
- [Architecture](architecture.md) - System design

## API Reference

Complete plugin API documentation:

### Exceptions

```python
# Base exception
PluginError

# Specific exceptions
PluginNotFoundError(plugin_name, search_paths)
PluginLoadError(plugin_name, reason)
PluginValidationError(plugin_name, issues)
PluginDependencyError(plugin_name, dependency, reason)
PluginInitializationError(plugin_name, reason)

# Package manager specific
PackageManagerError

# Build backend specific
BuildBackendError
```

### Global Registry

```python
from toolchainkit.plugins import get_global_registry, reset_global_registry

# Get singleton registry
registry = get_global_registry()

# Reset (for testing)
reset_global_registry()
```

## Contributing Plugins

To contribute a plugin to the ToolchainKit ecosystem:

1. **Create plugin** following this guide
2. **Add comprehensive tests** (>80% coverage)
3. **Document usage** in README.md
4. **Submit PR** or publish independently

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

## License

Plugins can use any license compatible with MIT (ToolchainKit's license). Common choices:
- MIT (recommended for maximum compatibility)
- Apache 2.0
- BSD 3-Clause

Declare license in `plugin.yaml` metadata.
