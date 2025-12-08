# Toolchain Metadata

This directory contains toolchain metadata in modular format.

## Structure

Each toolchain has its own directory with:
- `manifest.json` - Toolchain metadata (type, versions, defaults)
- `{version}.json` - Version-specific download URLs and platform data
- `platforms/` - Optional platform-specific overrides

## Format

### registry.json
Top-level index of all available toolchains.

### {toolchain}/manifest.json
Toolchain-level metadata:
- Name, type, description
- List of available versions
- Default settings (stdlib, linker, etc.)

### {toolchain}/{version}.json
Version-specific metadata:
- Download URLs per platform
- Checksums (SHA256)
- File sizes
- Platform-specific settings

## Adding New Toolchain Version

Example: Adding LLVM 19.0.0

1. Create `llvm/19.0.0.json`:
```json
{
  "version": "19.0.0",
  "platforms": {
    "linux-x64": {
      "url": "https://github.com/llvm/llvm-project/releases/...",
      "sha256": "abc123...",
      "size_mb": 650
    },
    ...
  }
}
```

2. Update `llvm/manifest.json` to include version in versions list:
```json
{
  "versions": [
    {"version": "19.0.0", "file": "19.0.0.json", "status": "stable"},
    ...
  ]
}
```

That's it! No code changes needed.

## Benefits

- **Scalable**: Easy to add new versions (one file per version)
- **Maintainable**: Small, focused files instead of one large file
- **Safe**: Reduced merge conflict risk
- **Fast**: Lazy loading (only load what's needed)

## Backward Compatibility

Legacy `toolchains.json` still supported. Loader tries modular structure first, falls back to legacy if not found.

## Migration Status

- ✅ LLVM: Migrated to modular format
- ✅ GCC: Migrated to modular format
- ⏳ MSVC: Still in legacy format (requires special handling)
