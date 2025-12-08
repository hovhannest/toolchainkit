# Maintenance Guide

This guide provides information for maintaining and troubleshooting ToolchainKit.

## Routine Maintenance Tasks

### 1. Updating Toolchain Metadata

The toolchain metadata registry (`toolchainkit/data/toolchains.json`) needs regular updates when new compiler versions are released.

#### Adding New Toolchain Versions

1. **Download and verify the new toolchain**:
   ```bash
   wget https://github.com/llvm/llvm-project/releases/download/llvmorg-19.0.0/clang+llvm-19.0.0-x86_64-linux-gnu-ubuntu-22.04.tar.xz
   sha256sum clang+llvm-19.0.0-x86_64-linux-gnu-ubuntu-22.04.tar.xz
   ```

2. **Add to metadata registry**:
   ```json
   {
     "toolchains": {
       "llvm": {
         "19.0.0": {
           "linux-x64": {
             "url": "https://github.com/llvm/llvm-project/releases/download/llvmorg-19.0.0/clang+llvm-19.0.0-x86_64-linux-gnu-ubuntu-22.04.tar.xz",
             "sha256": "abc123...",
             "size_mb": 2100,
             "stdlib": ["libc++", "libstdc++"],
             "requires_installer": false
           }
         }
       }
     }
   }
   ```

3. **Test the new metadata**:
   ```bash
   pytest tests/toolchain/test_registry.py::test_lookup_llvm_19 -v
   ```

4. **Document in README**:
   Update the supported versions list in `README.md`.

---

### 2. Dependency Updates

#### Updating Python Dependencies

1. **Check for updates**:
   ```bash
   pip list --outdated
   ```

2. **Update dependencies**:
   ```bash
   pip install --upgrade requests filelock
   pip freeze > requirements.txt
   ```

3. **Test with new versions**:
   ```bash
   pytest tests/ -v
   ```

4. **Update documentation** if API changes occur.

#### Embedded Python Version

If updating the embedded Python version (currently 3.11.7):

1. **Update version in** `toolchainkit/core/python_env.py`:
   ```python
   PYTHON_VERSION = "3.11.8"  # Update this
   ```

2. **Update download URLs** for all platforms (Windows, Linux, macOS).

3. **Test on all platforms**:
   ```bash
   pytest tests/core/test_python_env.py -v
   ```

---

### 3. Security Updates

#### Handling Security Vulnerabilities

1. **Monitor security advisories**:
   - GitHub Dependabot alerts
   - Python security mailing list
   - CVE databases

2. **Update vulnerable dependencies immediately**:
   ```bash
   pip install --upgrade <vulnerable-package>
   ```

3. **Run security checks**:
   ```bash
   pip install safety
   safety check
   ```

4. **Release patch version** if vulnerability is critical.

---

### 4. Documentation Updates

#### When to Update Documentation

- **New features**: Add user guides and integration guides
- **API changes**: Update API documentation
- **Bug fixes**: Update known issues section
- **Breaking changes**: Add migration guide

#### Documentation Structure

```
docs/
├── user_guide_*.md           # User-facing guides
├── integration_guide_*.md    # API integration guides
├── architecture_*.md         # Architecture documentation
└── dev/                      # Developer documentation
    ├── architecture.md
    ├── building_blocks.md
    ├── extending.md
    ├── testing.md
    └── maintenance.md
```

---

## Troubleshooting Common Issues

### Issue 1: Download Failures

**Symptoms**: Toolchain downloads fail with network errors.

**Diagnosis**:
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

from toolchainkit.core.download import download_file
download_file(url, dest, expected_sha256=hash)
```

**Common Causes**:
1. **Network connectivity**: Check internet connection
2. **Firewall/Proxy**: Check proxy settings
3. **Invalid URL**: Verify URL is correct
4. **TLS/SSL issues**: Update certificates

**Solutions**:
```bash
# Test network connectivity
curl -I https://github.com/llvm/llvm-project/releases/download/...

# Set proxy (if needed)
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=https://proxy.example.com:8080

# Update CA certificates (Linux)
sudo update-ca-certificates
```

---

### Issue 2: Verification Failures

**Symptoms**: Toolchain verification fails despite successful download.

**Diagnosis**:
```python
from toolchainkit.toolchain.verifier import ToolchainVerifier, VerificationLevel

verifier = ToolchainVerifier()
result = verifier.verify(
    toolchain_path=path,
    toolchain_type='clang',
    expected_version='18.1.8',
    level=VerificationLevel.THOROUGH  # Verbose mode
)

print(result.errors)
```

**Common Causes**:
1. **Corrupted download**: Hash mismatch
2. **Incomplete extraction**: Missing files
3. **Permission issues**: Files not executable
4. **Version mismatch**: Wrong version installed

**Solutions**:
```bash
# Re-download with force
rm -rf ~/.toolchainkit/toolchains/llvm-18.1.8-linux-x64
# Then re-download

# Fix permissions
chmod +x ~/.toolchainkit/toolchains/llvm-18.1.8-linux-x64/bin/*

# Verify manually
~/.toolchainkit/toolchains/llvm-18.1.8-linux-x64/bin/clang --version
```

---

### Issue 3: Locking Issues

**Symptoms**: "Lock timeout" or "Unable to acquire lock" errors.

**Diagnosis**:
```bash
# Check for stale locks
ls -la ~/.toolchainkit/lock/

# Check lock file ages
find ~/.toolchainkit/lock/ -type f -mtime +1
```

**Common Causes**:
1. **Stale locks**: Process crashed while holding lock
2. **Concurrent operations**: Multiple processes competing
3. **NFS issues**: Lock files on network filesystem

**Solutions**:
```bash
# Remove stale locks (older than 1 day)
find ~/.toolchainkit/lock/ -type f -mtime +1 -delete

# Check for running ToolchainKit processes
ps aux | grep toolchainkit

# Force remove specific lock (if safe)
rm ~/.toolchainkit/lock/registry.lock
```

---

### Issue 4: CMake Configuration Failures

**Symptoms**: CMake configure fails with generated toolchain file.

**Diagnosis**:
```bash
# View generated toolchain file
cat .toolchainkit/cmake/toolchain-llvm-18.cmake

# Run CMake with verbose output
cmake -B build -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchain-llvm-18.cmake --trace
```

**Common Causes**:
1. **Invalid compiler paths**: Compiler not found
2. **Missing standard library**: stdlib not found
3. **Incorrect flags**: Invalid compiler flags
4. **CMake version**: CMake too old

**Solutions**:
```bash
# Verify compiler exists
ls -la $(cat .toolchainkit/cmake/toolchain-llvm-18.cmake | grep CMAKE_CXX_COMPILER)

# Update CMake
pip install --upgrade cmake

# Regenerate toolchain file
rm -rf .toolchainkit/cmake/
# Then reconfigure
```

---

### Issue 5: Package Manager Integration Failures

**Symptoms**: Conan/vcpkg dependency installation fails.

**Diagnosis**:
```bash
# Check package manager availability
which conan
conan --version

which vcpkg
vcpkg version

# Check manifest files
cat conanfile.txt
cat vcpkg.json
```

**Common Causes**:
1. **Package manager not installed**
2. **Invalid manifest**: Syntax errors in conanfile.txt/vcpkg.json
3. **Network issues**: Can't download dependencies
4. **Version conflicts**: Incompatible package versions

**Solutions**:
```bash
# Install Conan
pip install conan

# Install vcpkg
git clone https://github.com/Microsoft/vcpkg.git
./vcpkg/bootstrap-vcpkg.sh

# Validate manifest
conan install . --dry-run  # Conan
vcpkg install --dry-run    # vcpkg

# Clear package caches
rm -rf ~/.conan/data
rm -rf ~/.toolchainkit/packages/
```

---

## Performance Optimization

### Monitoring Performance

#### Profiling Python Code

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
from toolchainkit.toolchain.downloader import ToolchainDownloader
downloader = ToolchainDownloader()
downloader.download('llvm', '18', 'linux-x64')

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

#### Measuring Download Performance

```python
from toolchainkit.core.download import download_file
import time

start = time.time()
download_file(url, dest, expected_sha256=hash)
elapsed = time.time() - start

size_mb = dest.stat().st_size / (1024 * 1024)
speed_mbps = size_mb / elapsed
print(f"Download speed: {speed_mbps:.2f} MB/s")
```

### Optimization Strategies

1. **Caching**:
   - Platform detection uses LRU cache
   - Toolchain metadata cached in memory
   - Enable build caching (sccache/ccache)

2. **Parallel Operations**:
   - Download multiple toolchains in parallel (if needed)
   - Use parallel build (Ninja with `-j` flag)

3. **Minimize Disk I/O**:
   - Stream downloads directly to disk
   - Use symlinks instead of copying toolchains
   - Compress logs and state files

4. **Network Optimization**:
   - Use CDN mirrors for toolchain downloads
   - Enable HTTP/2 and connection reuse
   - Configure reasonable timeouts

---

## Debugging Techniques

### Enable Debug Logging

```python
import logging

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run your code
from toolchainkit.core.directory import create_directory_structure
create_directory_structure()
```

### Using Python Debugger

```python
import pdb

def my_function():
    # Set breakpoint
    pdb.set_trace()

    # Code to debug
    result = some_operation()

    return result
```

**pdb Commands**:
- `n` (next): Execute next line
- `s` (step): Step into function
- `c` (continue): Continue execution
- `p variable`: Print variable value
- `l` (list): List source code
- `q` (quit): Quit debugger

### Inspecting State

```python
from toolchainkit.core.state import load_state

# Load current state
state = load_state(project_root)

# Inspect state
print(f"Active toolchain: {state.active_toolchain}")
print(f"CMake configured: {state.cmake_configured}")
print(f"Configuration hash: {state.config_hash}")
```

### Checking Registry

```python
from toolchainkit.core.registry import CacheRegistry

registry = CacheRegistry()

# List all toolchains
toolchains = registry.list_toolchains()
for tc_id in toolchains:
    info = registry.get_toolchain_info(tc_id)
    print(f"{tc_id}: {info.size_mb} MB, {len(info.projects)} projects")

# Check specific toolchain
info = registry.get_toolchain_info('llvm-18.1.8-linux-x64')
print(f"Projects using this toolchain: {info.projects}")
```

---

## Backup and Recovery

### Backing Up Global Cache

```bash
# Backup global cache
tar -czf toolchainkit-cache-backup.tar.gz ~/.toolchainkit/

# Backup excluding large toolchains (just registry and config)
tar -czf toolchainkit-config-backup.tar.gz \
  ~/.toolchainkit/registry.json \
  ~/.toolchainkit/lock/
```

### Recovering from Corrupted State

```bash
# Reset project-local state
rm -rf /path/to/project/.toolchainkit/
# Then re-initialize

# Reset global cache (nuclear option)
rm -rf ~/.toolchainkit/
# Then re-download toolchains
```

### Migrating to New Machine

```bash
# On old machine: Backup
tar -czf toolchainkit-backup.tar.gz ~/.toolchainkit/

# On new machine: Restore
tar -xzf toolchainkit-backup.tar.gz -C ~/

# Update project references (if paths changed)
# May need to re-link projects to cache
```

---

## Release Process

### Version Bumping

1. **Update version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.2.0"  # Update this
   ```

2. **Update version** in `toolchainkit/__init__.py`:
   ```python
   __version__ = "0.2.0"  # Update this
   ```

3. **Update CHANGELOG.md**:
   ```markdown
   ## [0.2.0] - 2025-11-22
   ### Added
   - Feature X
   ### Fixed
   - Bug Y
   ```

### Testing Before Release

```bash
# Run full test suite
pytest tests/ -v

# Run on all platforms (CI)
# Check GitHub Actions status

# Test installation from source
pip install -e .
python -c "import toolchainkit; print(toolchainkit.__version__)"

# Build distribution
python -m build

# Test installation from wheel
pip install dist/toolchainkit-0.2.0-py3-none-any.whl
```

### Creating Release

```bash
# Tag release
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0

# GitHub will automatically create release from tag
# Upload wheel to PyPI (if applicable)
twine upload dist/*
```

---

## Monitoring and Metrics

### Key Metrics to Track

1. **Test Coverage**: Aim for 80%+ overall
2. **Test Pass Rate**: 100% of tests should pass
3. **Build Time**: Monitor CI build duration
4. **Download Success Rate**: Track toolchain download failures
5. **User Issues**: Monitor GitHub issues

### Health Checks

```python
"""Health check script."""

from toolchainkit.core.platform import detect_platform
from toolchainkit.core.directory import get_global_cache_dir
from toolchainkit.core.registry import CacheRegistry

def health_check():
    """Run health checks."""
    checks = []

    # Platform detection
    try:
        platform = detect_platform()
        checks.append(('Platform Detection', 'OK', str(platform)))
    except Exception as e:
        checks.append(('Platform Detection', 'FAIL', str(e)))

    # Global cache
    try:
        cache_dir = get_global_cache_dir()
        if cache_dir.exists():
            checks.append(('Global Cache', 'OK', str(cache_dir)))
        else:
            checks.append(('Global Cache', 'WARN', 'Not initialized'))
    except Exception as e:
        checks.append(('Global Cache', 'FAIL', str(e)))

    # Registry
    try:
        registry = CacheRegistry()
        toolchains = registry.list_toolchains()
        checks.append(('Registry', 'OK', f'{len(toolchains)} toolchains'))
    except Exception as e:
        checks.append(('Registry', 'FAIL', str(e)))

    # Print results
    print("\nToolchainKit Health Check")
    print("=" * 70)
    for check, status, info in checks:
        print(f"{check:30} [{status:4}] {info}")

    # Overall status
    failed = sum(1 for _, status, _ in checks if status == 'FAIL')
    if failed == 0:
        print("\n✓ All checks passed")
        return 0
    else:
        print(f"\n✗ {failed} check(s) failed")
        return 1

if __name__ == '__main__':
    exit(health_check())
```

---

## Common Maintenance Commands

```bash
# View cache statistics
python -c "from toolchainkit.toolchain.cleanup import ToolchainCleaner; \
           cleaner = ToolchainCleaner(); \
           stats = cleaner.get_cache_stats(); \
           print(f'Total: {stats.total_size_mb} MB, Unused: {stats.unused_size_mb} MB')"

# Cleanup old toolchains (dry run)
python -c "from toolchainkit.toolchain.cleanup import ToolchainCleaner; \
           cleaner = ToolchainCleaner(); \
           removed = cleaner.cleanup_by_age(min_age_days=30, dry_run=True); \
           print(f'Would remove: {removed}')"

# Find broken links
python -c "from toolchainkit.toolchain.linking import find_broken_links; \
           from pathlib import Path; \
           broken = find_broken_links(Path.cwd() / '.toolchainkit'); \
           print(f'Broken links: {broken}')"

# Verify toolchain
python -c "from toolchainkit.toolchain.verifier import ToolchainVerifier, VerificationLevel; \
           from pathlib import Path; \
           verifier = ToolchainVerifier(); \
           result = verifier.verify(Path('~/.toolchainkit/toolchains/llvm-18.1.8-linux-x64'), 'clang', '18.1.8', VerificationLevel.STANDARD); \
           print('OK' if result.passed else result.errors)"
```

---

## Summary

Maintenance tasks:
1. **Update toolchain metadata** when new versions release
2. **Update dependencies** regularly (especially security updates)
3. **Monitor CI** and test results
4. **Update documentation** with changes
5. **Respond to issues** promptly
6. **Perform releases** following semantic versioning

Troubleshooting:
- Enable debug logging for diagnosis
- Check common failure points (network, locks, paths)
- Use health check scripts
- Maintain backups of configuration

When in doubt:
- Consult existing tests for examples
- Check GitHub issues for similar problems
- Review architecture and building blocks documentation
- Ask for help in GitHub Discussions
