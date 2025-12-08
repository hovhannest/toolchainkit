# Plugin Management

ToolchainKit provides CLI commands for managing plugins, similar to `conan remote` commands.

## Overview

Plugins extend ToolchainKit with additional compiler support, package managers, or custom toolchains. The plugin management commands allow you to:

- List all discovered plugins
- Add custom plugin search paths
- Remove plugin search paths
- View all plugin search locations

## Commands

### List Plugins

Display all currently loaded plugins:

```bash
toolchainkit plugin list
```

**Example output:**
```
Loaded Plugins:
  - zig-compiler (ZigCompilerPlugin)
    Path: C:\workspace\cpp\toolchainkit\examples\plugins\zig-compiler
  - custom-allocator (CustomAllocatorPlugin)
    Path: C:\Users\user\.toolchainkit\plugins\custom-allocator
```

### Add Plugin Search Path

Add a new directory to search for plugins:

```bash
toolchainkit plugin add <path>
```

**Examples:**
```bash
# Add a local plugin directory
toolchainkit plugin add C:\dev\my-plugins

# Add a shared team directory
toolchainkit plugin add \\server\shared\toolchainkit-plugins

# Add relative path (will be converted to absolute)
toolchainkit plugin add ../team-plugins
```

The path is saved to `~/.toolchainkit/plugins.yaml` and will be used for all future plugin discovery.

### Remove Plugin Search Path

Remove a previously added search path:

```bash
toolchainkit plugin remove <path>
```

**Examples:**
```bash
# Remove by exact path
toolchainkit plugin remove C:\dev\my-plugins

# Remove by relative path (will be resolved)
toolchainkit plugin remove ../team-plugins
```

### List Search Paths

Display all directories being searched for plugins (in priority order):

```bash
toolchainkit plugin list-paths
```

**Example output:**
```
Plugin Search Paths (in priority order):
  1. C:\workspace\cpp\project\.toolchainkit\plugins (project-local)
  2. C:\Users\user\.toolchainkit\plugins (user-global)
  3. C:\dev\my-plugins (configured)
  4. \\server\shared\toolchainkit-plugins (configured)
  5. C:\extra\plugins (environment: TOOLCHAINKIT_PLUGIN_PATH)
```

## Plugin Discovery Priority

Plugins are discovered in the following order (highest to lowest priority):

1. **Project-local**: `<project>/.toolchainkit/plugins/`
   - Plugins specific to the current project
   - Always checked first if a project is configured

2. **User-global**: `~/.toolchainkit/plugins/`
   - Personal plugins available to all projects
   - Default installation location

3. **Configured paths**: From `~/.toolchainkit/plugins.yaml`
   - Custom paths added via `toolchainkit plugin add`
   - Can be shared team locations or external plugin repositories

4. **Environment variable**: `TOOLCHAINKIT_PLUGIN_PATH`
   - Lowest priority
   - Can contain multiple paths separated by `;` (Windows) or `:` (Unix)

## Configuration File

Plugin paths are stored in `~/.toolchainkit/plugins.yaml`:

```yaml
search_paths:
  - C:\dev\my-plugins
  - \\server\shared\toolchainkit-plugins
  - /home/user/custom-plugins
```

This file is automatically created and updated by the `plugin add` and `plugin remove` commands.

## Use Cases

### Team Plugin Repository

Share plugins across a team:

```bash
# Each team member adds the shared location
toolchainkit plugin add \\teamserver\toolchainkit\plugins

# Now everyone has access to team plugins
toolchainkit plugin list
```

### Development and Testing

Test plugins during development:

```bash
# Add your development directory
toolchainkit plugin add C:\dev\my-new-plugin

# Test the plugin
toolchainkit init --compiler my-new-compiler

# Remove when done testing
toolchainkit plugin remove C:\dev\my-new-plugin
```

### Multiple Plugin Sources

Combine different plugin sources:

```bash
# Company-wide plugins
toolchainkit plugin add \\company\toolchainkit\plugins

# Team-specific plugins
toolchainkit plugin add \\teamserver\plugins

# Personal experimental plugins
toolchainkit plugin add C:\Users\me\experimental-plugins

# View all sources
toolchainkit plugin list-paths
```

## Plugin Structure

For a directory to be recognized as a plugin, it must contain a Python file with a plugin class. See [plugins.md](plugins.md) for details on creating plugins.

**Minimal plugin structure:**
```
my-plugin/
  my_plugin.py        # Contains plugin class
  toolchains.json     # (optional) Plugin-specific toolchain registry
  README.md           # (optional) Plugin documentation
```

## Troubleshooting

### Plugin Not Found

If a plugin isn't appearing in `toolchainkit plugin list`:

1. Check that the path is added:
   ```bash
   toolchainkit plugin list-paths
   ```

2. Verify the plugin directory structure:
   - Must contain a `.py` file
   - File must contain a class implementing the plugin interface

3. Check for errors in the plugin code:
   - Syntax errors prevent the plugin from loading
   - Import errors will be silently skipped

### Path Already Exists

When adding a path that's already configured:

```bash
toolchainkit plugin add C:\existing\path
# Output: Path already in plugin search paths: C:\existing\path
```

### Path Not Found

When removing a path that doesn't exist:

```bash
toolchainkit plugin remove C:\nonexistent\path
# Output: Path not found in plugin search paths: C:\nonexistent\path
```

## Related Documentation

- [Plugin Development Guide](plugins.md)
- [Zig Compiler Plugin Example](../examples/plugins/zig-compiler/)
- [Custom Allocator Plugin Example](../examples/plugins/custom-allocator/)

## See Also

- [CLI Reference](cli.md) - Complete CLI documentation
- [Configuration](config.md) - General configuration options
- [Toolchain Registry](registry.md) - Managing toolchain definitions
