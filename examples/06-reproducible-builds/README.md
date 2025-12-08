# Example 6: Reproducible and Secure Builds

This example demonstrates how to use ToolchainKit's lockfile system to ensure reproducible builds and improve supply chain security.

## Scenario

You need to:
- Guarantee builds are reproducible months or years later
- Track exact versions of toolchains and dependencies
- Detect unauthorized changes to dependencies
- Meet compliance requirements (SBOM, audit trails)
- Prevent supply chain attacks

## Project Structure

```
06-reproducible-builds/
├── CMakeLists.txt
├── toolchainkit.yaml          # Main configuration
├── toolchainkit.lock          # Lock file (version pins)
├── .toolchainkit/
│   └── checksums.txt          # Verification hashes
├── bootstrap.sh
├── src/
└── docs/
    ├── SECURITY.md            # Security policy
    └── SBOM.json              # Software Bill of Materials
```

## Lock File System

### What is a Lock File?

A lock file pins exact versions and cryptographic hashes of:
- Toolchains (compiler, linker, tools)
- Dependencies (libraries, headers)
- Build tools (CMake, Ninja)

**Example `toolchainkit.lock`:**

```yaml
version: "1.0"
generated: "2024-11-27T10:30:00Z"
generator: "toolchainkit 0.1.0"

toolchain:
  name: llvm-18
  version: "18.1.0"
  sha256: "a1b2c3d4e5f6..."
  url: "https://github.com/llvm/llvm-project/releases/..."
  download_date: "2024-11-27"

dependencies:
  - name: fmt
    version: "10.1.1"
    sha256: "abc123def456..."
    source: conan

  - name: spdlog
    version: "1.12.0"
    sha256: "789xyz012345..."
    source: conan
    requires:
      - fmt/10.1.1

  - name: boost
    version: "1.83.0"
    sha256: "fedcba987654..."
    source: conan

build_tools:
  cmake:
    version: "3.27.0"
    sha256: "1a2b3c4d5e6f..."

  ninja:
    version: "1.11.1"
    sha256: "6f5e4d3c2b1a..."
```

### Generating Lock Files

```bash
# Initial project setup
tkgen init --toolchain llvm-18
tkgen bootstrap

# Generate lock file
tkgen lock generate

# This creates toolchainkit.lock with:
# - Exact toolchain version and hash
# - All dependency versions and hashes
# - Build tool versions
```

### Using Lock Files

```bash
# Bootstrap from lock file (exact versions)
tkgen bootstrap

# The bootstrap script:
# 1. Reads toolchainkit.lock
# 2. Downloads exact versions
# 3. Verifies SHA256 hashes
# 4. Fails if hashes don't match
```

## Configuration

`toolchainkit.yaml`:

```yaml
version: "1.0"

project:
  name: secure-project
  version: "1.0.0"

toolchain:
  name: llvm-18
  # Version will be pinned in lock file

build:
  type: Release
  dir: build

packages:
  manager: conan
  conanfile: conanfile.txt

security:
  # Verify checksums on every build
  verify_checksums: true

  # Fail if lock file is missing
  require_lockfile: true

  # Warn if dependencies are outdated
  warn_outdated: true

  # Maximum age for dependencies (days)
  max_dependency_age: 90

lockfile:
  # Auto-generate on bootstrap
  auto_generate: true

  # Include transitive dependencies
  include_transitive: true

  # Track build tools
  include_build_tools: true

bootstrap:
  toolchain: llvm-18
  build_type: Release
  package_manager: conan

  # Verify lock file before bootstrap
  verify_lockfile: true
```

## Workflow

### 1. Initial Setup (Developer)

```bash
# Set up project
tkgen init --toolchain llvm-18
tkgen bootstrap

# Generate lock file
tkgen lock generate

# Verify everything matches
tkgen lock verify

# Commit lock file
git add toolchainkit.lock
git commit -m "Add lock file for reproducible builds"
git push
```

### 2. New Developer Setup

```bash
# Clone repository
git clone https://github.com/myteam/myproject.git
cd myproject

# Bootstrap (uses lock file automatically)
./bootstrap.sh

# This:
# ✓ Reads toolchainkit.lock
# ✓ Downloads LLVM 18.1.0 (exact version)
# ✓ Verifies SHA256: a1b2c3d4e5f6...
# ✓ Installs fmt 10.1.1, spdlog 1.12.0, boost 1.83.0
# ✓ Verifies all checksums
# ✓ Configures CMake

# Build
cmake --build build
```

### 3. Dependency Update

```bash
# Update dependency versions in conanfile.txt
vim conanfile.txt

# Regenerate lock file
tkgen lock generate --force

# Review changes
tkgen lock diff

# Output:
# Dependency changes:
#   fmt: 10.1.1 → 10.2.0
#   spdlog: 1.12.0 → 1.12.1 (no API changes)
#
# Security updates:
#   boost: 1.83.0 → 1.83.1 (CVE-2024-XXXX fixed)

# Test with new versions
tkgen bootstrap --force
cmake --build build
ctest --test-dir build

# Commit if tests pass
git add toolchainkit.lock conanfile.txt
git commit -m "Update dependencies: fmt 10.2.0, boost 1.83.1 (security fix)"
```

### 4. Verification

```bash
# Verify lock file matches current environment
tkgen lock verify

# Output:
# ✓ Toolchain: llvm-18.1.0 (hash: a1b2c3d4...)
# ✓ fmt: 10.1.1 (hash: abc123de...)
# ✓ spdlog: 1.12.0 (hash: 789xyz01...)
# ✓ boost: 1.83.0 (hash: fedcba98...)
# ✓ All checksums verified

# Or with errors:
# ✗ fmt: hash mismatch
#   Expected: abc123de...
#   Got:      DEADBEEF...
#   Possible supply chain attack!
```

## CI/CD Integration

`.github/workflows/build.yml`:

```yaml
name: Secure Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Verify lock file
        run: |
          # Ensure lock file exists
          if [ ! -f toolchainkit.lock ]; then
            echo "ERROR: Lock file missing"
            exit 1
          fi

          # Verify lock file is up to date
          tkgen lock verify || {
            echo "ERROR: Lock file verification failed"
            echo "This could indicate:"
            echo "  - Dependency versions changed"
            echo "  - Checksums don't match"
            echo "  - Possible supply chain attack"
            exit 1
          }

      - name: Bootstrap with verification
        run: ./bootstrap.sh

        # Bootstrap script will:
        # 1. Read lock file
        # 2. Download exact versions
        # 3. Verify SHA256 hashes
        # 4. Fail if any hash mismatches

      - name: Build
        run: cmake --build build

      - name: Test
        run: ctest --test-dir build --output-on-failure

      - name: Generate SBOM
        run: |
          tkgen lock export --format sbom > SBOM.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: SBOM.json
```

## Security Features

### 1. Checksum Verification

Every dependency is verified:

```bash
# Manual verification
tkgen verify --full

# Output:
# Verifying toolchain: llvm-18.1.0
#   ✓ Archive hash matches
#   ✓ Extracted files match
#   ✓ Compiler executable verified
#
# Verifying dependencies:
#   ✓ fmt-10.1.1.tar.gz: abc123...
#   ✓ spdlog-1.12.0.tar.gz: 789xyz...
#   ✓ boost-1.83.0.tar.bz2: fedcba...
```

### 2. Supply Chain Attack Detection

```bash
# If someone modifies a dependency:
tkgen lock verify

# Output:
# ✗ ERROR: Checksum mismatch detected!
#   Package: fmt-10.1.1
#   Expected: abc123def456...
#   Got:      EVIL_HASH_HERE...
#
#   This could indicate:
#   - Corrupted download
#   - Man-in-the-middle attack
#   - Compromised package repository
#
#   Action: DO NOT USE THIS BUILD
#   Report to security team immediately
```

### 3. Dependency Age Warnings

```bash
# Warn about old dependencies
tkgen doctor

# Output:
# ⚠ Warning: Outdated dependencies detected
#   boost 1.83.0 (120 days old)
#     - Security fix available: 1.83.2
#     - Consider updating
#
#   fmt 10.1.1 (30 days old)
#     - Up to date
```

### 4. SBOM Generation

```bash
# Generate Software Bill of Materials
tkgen lock export --format sbom > SBOM.json

# SBOM.json:
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "components": [
    {
      "type": "library",
      "name": "llvm",
      "version": "18.1.0",
      "hashes": [
        {
          "alg": "SHA-256",
          "content": "a1b2c3d4e5f6..."
        }
      ]
    },
    {
      "type": "library",
      "name": "fmt",
      "version": "10.1.1",
      "hashes": [...]
    }
  ]
}

# Also supports SPDX format
tkgen lock export --format spdx > SBOM.spdx
```

## Audit Trail

### Lock File Diff

```bash
# See what changed between versions
git diff HEAD~1 toolchainkit.lock

# Or use ToolchainKit
tkgen lock diff HEAD~1

# Output:
# Comparing: HEAD~1 → HEAD
#
# Toolchain changes:
#   llvm: 18.1.0 → 18.1.1
#
# Dependency changes:
#   + Added: catch2-3.4.0
#   ↑ Updated: boost 1.83.0 → 1.83.1
#   ↓ Downgraded: fmt 10.2.0 → 10.1.1
#   - Removed: deprecated-lib
#
# Security updates:
#   boost 1.83.1: Fixes CVE-2024-XXXX
```

### History Tracking

```bash
# View lock file history
tkgen lock history

# Output:
# 2024-11-27 10:30 - John Doe
#   Updated boost to 1.83.1 (security fix)
#
# 2024-11-20 14:15 - Jane Smith
#   Added catch2 for testing
#
# 2024-11-15 09:00 - Bob Wilson
#   Initial lock file
```

## Best Practices

### 1. Always Commit Lock Files

```bash
# .gitignore should NOT include:
# toolchainkit.lock  ← DO NOT IGNORE THIS

# Lock files MUST be in version control
git add toolchainkit.lock
git commit -m "Update lock file"
```

### 2. Verify Before Merging PRs

```yaml
# .github/workflows/pr-check.yml
- name: Check lock file
  run: |
    if git diff --name-only ${{ github.event.pull_request.base.sha }} | grep -q conanfile.txt; then
      if ! git diff --name-only ${{ github.event.pull_request.base.sha }} | grep -q toolchainkit.lock; then
        echo "ERROR: conanfile.txt changed but lock file not updated"
        exit 1
      fi
    fi
```

### 3. Regular Updates

```bash
# Weekly dependency check
tkgen doctor --check-updates

# Update and test
tkgen lock generate --force
cmake --build build --clean-first
ctest --test-dir build

# Commit if passing
git add toolchainkit.lock
git commit -m "Weekly dependency update"
```

### 4. Security Scanning

```bash
# Check for known vulnerabilities
tkgen lock audit

# Output:
# Scanning for known vulnerabilities...
#
# ⚠ 1 vulnerability found:
#   boost 1.83.0 - CVE-2024-XXXX (Medium severity)
#   Fixed in: 1.83.1
#
#   Recommendation: Update to boost 1.83.1
```

## Compliance and Auditing

### SOC 2 / ISO 27001

Lock files provide:
- ✅ Reproducible builds (audit requirement)
- ✅ Dependency tracking (supply chain security)
- ✅ Change history (audit trail)
- ✅ Verification (integrity checks)

### SBOM Requirements

Generate SBOM for compliance:

```bash
# CycloneDX format (OWASP)
tkgen lock export --format cyclonedx > sbom.json

# SPDX format (Linux Foundation)
tkgen lock export --format spdx > sbom.spdx

# Include in releases
git tag -a v1.0.0
tkgen lock export --format cyclonedx > release-sbom.json
```

## Benefits

✅ **Reproducible**: Same build months/years later
✅ **Secure**: Detects tampering via checksums
✅ **Auditable**: Complete dependency history
✅ **Compliant**: Meets security standards
✅ **Automated**: No manual tracking needed
✅ **Transparent**: Clear dependency tree

## See Also

- [Lock File Documentation](../../docs/lockfile.md)
- [Security Guide](../../docs/SECURITY.md)
- [Verification](../../docs/verification.md)
- [Doctor Command](../../docs/doctor.md)
