# Toolchain Management

Download, install, verify, and manage compiler toolchains.

## Toolchain Download

```python
from toolchainkit.toolchain.downloader import ToolchainDownloader

downloader = ToolchainDownloader()

# Download toolchain
toolchain_dir = downloader.download_toolchain(
    name="llvm",
    version="18.1.8",  # or "latest"
    platform=None      # Auto-detect
)

print(f"Installed to: {toolchain_dir}")
```

## Toolchain Verification

```python
from toolchainkit.toolchain.verifier import verify_toolchain, VerificationLevel

# Quick sanity check
verify_toolchain(
    toolchain_dir,
    level=VerificationLevel.MINIMAL  # ~1s
)

# Full verification with compile test
verify_toolchain(
    toolchain_dir,
    level=VerificationLevel.PARANOID  # ~30s
)
```

## Verification Levels

- `MINIMAL`: File presence (~1s)
- `STANDARD`: + Executability (~5s)
- `THOROUGH`: + Version validation (~10s)
- `PARANOID`: + Full compile test (~30s)

## System Detection

```python
from toolchainkit.toolchain.system_detector import SystemToolchainDetector
from toolchainkit.core.platform import detect_platform

# Find installed compilers
platform = detect_platform()
detector = SystemToolchainDetector(platform)
toolchains = detector.detect_all()

for tc in toolchains:
    print(f"{tc.name}: {tc.path} (version {tc.version})")

# Get best toolchain (LLVM > GCC > MSVC, newest version)
best = detector.detect_best()
```

## Toolchain Registry

```python
from toolchainkit.toolchain.registry import ToolchainRegistry

registry = ToolchainRegistry()

# Get toolchain metadata
metadata = registry.get("llvm", "18.1.8", "linux-x64")
print(f"URL: {metadata.url}")
print(f"SHA256: {metadata.sha256}")

# List available versions
versions = registry.list_versions("llvm")
print(f"Available: {versions}")
```

## Cleanup

```python
from toolchainkit.toolchain.cleanup import ToolchainCleanupManager

manager = ToolchainCleanupManager()

# List unused toolchains (30+ days old)
unused = manager.list_unused(min_age_days=30)

# Remove specific toolchain
result = manager.cleanup(toolchain_name="llvm-18.1.8", dry_run=False)

# Auto-cleanup (removes very old unused toolchains)
result = manager.auto_cleanup(dry_run=False)

# Dry run (preview only)
result = manager.cleanup(toolchain_name="llvm-18.1.8", dry_run=True)
```

## Linking

```python
from toolchainkit.toolchain.linking import link_toolchain_to_project

# Create symlink/junction from global cache to project
link_toolchain_to_project(
    toolchain_dir=Path("~/.toolchainkit/toolchains/llvm-18.1.8"),
    project_root=Path("/my/project")
)
```

## Features

- **Auto-download**: Fetch toolchains from official sources
- **Verification**: SHA-256 integrity checks
- **Caching**: Shared global cache across projects
- **Versioning**: Multiple versions side-by-side
- **Cleanup**: Auto-remove unused toolchains
- **Reference Counting**: Safe deletion (never removes in-use toolchains)

## Supported Toolchains

| Toolchain | Platforms | Versions |
|-----------|-----------|----------|
| LLVM/Clang | Linux, Windows, macOS (x64/ARM64) | 16+, 17+, 18+ |
| GCC | Linux (x64/ARM64) | 11+, 12+, 13+ |
| MSVC | Windows (x64) | Detected from VS installation |
