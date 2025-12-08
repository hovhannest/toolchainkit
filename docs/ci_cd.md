# CI/CD Integration

> **✅ Status: Fully Implemented (v0.1.0)**
> CI template generation and GitHub Actions workflows are fully functional.

Comprehensive CI/CD support for building projects with ToolchainKit, including:
- Automated CI/CD configuration generation
- GitHub Actions workflow templates
- GitLab CI configurations
- Built-in workflows for ToolchainKit itself

## Quick Start

### Automatic CI/CD Generation

ToolchainKit can automatically generate CI/CD configuration files:

```python
from toolchainkit.ci import CITemplateGenerator
from pathlib import Path

# Initialize generator
generator = CITemplateGenerator(project_root=Path.cwd())

# Generate GitHub Actions workflow
workflow_file = generator.generate_github_actions(
    os_matrix=["ubuntu-latest", "macos-latest", "windows-latest"],
    build_types=["Debug", "Release"],
    enable_caching=True,
    enable_tests=True,
    enable_artifacts=True
)
print(f"✓ GitHub Actions: {workflow_file}")

# Generate GitLab CI configuration
gitlab_file = generator.generate_gitlab_ci(
    enable_caching=True,
    enable_tests=True,
    enable_artifacts=True
)
print(f"✓ GitLab CI: {gitlab_file}")

# Generate all at once
all_configs = generator.generate_all()
for platform, path in all_configs.items():
    print(f"✓ {platform}: {path}")
```

## CI Template Generator API

### CITemplateGenerator

```python
from toolchainkit.ci import CITemplateGenerator
from pathlib import Path
from typing import List, Optional

class CITemplateGenerator:
    """Generate CI/CD configuration files for various platforms."""

    def __init__(self, project_root: Path):
        """
        Initialize the CI template generator.

        Args:
            project_root: Root directory of the project
        """

    def generate_github_actions(
        self,
        os_matrix: Optional[List[str]] = None,
        build_types: Optional[List[str]] = None,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> Path:
        """
        Generate GitHub Actions workflow file.

        Creates .github/workflows/build.yml with matrix builds across
        multiple operating systems and build types.

        Args:
            os_matrix: Operating systems (default: ubuntu-latest, macos-latest, windows-latest)
            build_types: Build types (default: Debug, Release)
            enable_caching: Enable caching for toolchains and builds
            enable_tests: Enable test execution with ctest
            enable_artifacts: Upload build artifacts

        Returns:
            Path to generated .github/workflows/build.yml

        Example:
            >>> generator = CITemplateGenerator(Path.cwd())
            >>> workflow = generator.generate_github_actions(
            ...     os_matrix=["ubuntu-latest", "macos-latest"],
            ...     build_types=["Release"]
            ... )
            >>> print(f"Created: {workflow}")
        """

    def generate_gitlab_ci(
        self,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> Path:
        """
        Generate GitLab CI configuration file.

        Creates .gitlab-ci.yml with build and test stages.

        Args:
            enable_caching: Enable caching for toolchains
            enable_tests: Enable test execution
            enable_artifacts: Save build artifacts

        Returns:
            Path to generated .gitlab-ci.yml

        Example:
            >>> generator = CITemplateGenerator(Path.cwd())
            >>> config = generator.generate_gitlab_ci()
            >>> print(f"Created: {config}")
        """

    def generate_all(
        self,
        os_matrix: Optional[List[str]] = None,
        build_types: Optional[List[str]] = None,
        enable_caching: bool = True,
        enable_tests: bool = True,
        enable_artifacts: bool = True,
    ) -> dict:
        """
        Generate configurations for all supported CI/CD platforms.

        Args:
            Same as generate_github_actions()

        Returns:
            Dict mapping platform name to generated file path:
            {
                'github_actions': Path('.github/workflows/build.yml'),
                'gitlab_ci': Path('.gitlab-ci.yml')
            }

        Example:
            >>> generator = CITemplateGenerator(Path.cwd())
            >>> configs = generator.generate_all()
            >>> for platform, path in configs.items():
            ...     print(f"{platform}: {path}")
        """
```

## ToolchainKit's Built-in CI/CD Workflows

ToolchainKit itself uses GitHub Actions for continuous integration. These workflows serve as reference examples for projects using ToolchainKit.

### Unit Tests Workflow

**File**: `.github/workflows/unit-tests.yml`
**Triggers**: Push and PR to main/dev_hovt/develop branches
**Matrix**:
- OS: Ubuntu, Windows, macOS
- Python: 3.9, 3.10, 3.11, 3.12
- Total: 12 combinations

**Features**:
- ✅ Cross-platform testing
- ✅ Python version compatibility testing
- ✅ Coverage reporting (Codecov)
- ✅ Coverage threshold enforcement (80%)
- ✅ Pip caching for faster runs

```yaml
name: Unit Tests

on:
  push:
    branches: [ main, dev_hovt, develop ]
  pull_request:
    branches: [ main, dev_hovt, develop ]

jobs:
  unit-tests:
    name: Unit Tests - ${{ matrix.os }} - Python ${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}

    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock pyyaml

      - name: Run unit tests
        run: |
          pytest -m unit -v --cov=toolchainkit --cov-report=xml --cov-report=term
```

**Duration**: ~3-5 minutes per matrix combination

### Integration Tests Workflow

**File**: `.github/workflows/integration-tests.yml`
**Triggers**: Push and PR to main/develop
**Matrix**: Ubuntu, Windows, macOS (Python 3.11)

**Features**:
- ✅ Multi-component integration testing
- ✅ Real toolchain download tests
- ✅ CMake integration validation

```yaml
- name: Run integration tests
  run: pytest -m integration -v --tb=short
```

**Duration**: ~10-15 minutes

### End-to-End Tests Workflow

**File**: `.github/workflows/e2e-tests.yml`
**Triggers**:
- Manual trigger (workflow_dispatch)
- Scheduled (nightly at 2 AM UTC)
- PR to main

**Test Levels**:
1. **Smoke tests** - Quick validation of critical paths (~15 min)
2. **Full suite** - Comprehensive E2E testing (~45 min)

```yaml
# Smoke tests
- name: Run smoke tests
  run: pytest -m "e2e and smoke" -v

# Full E2E (nightly)
- name: Run full E2E suite
  if: github.event_name == 'schedule'
  run: pytest -m "e2e and not slow" -v
```

### Link Validation Workflow

**File**: `.github/workflows/link-validation.yml`
**Triggers**:
- Weekly (Sundays at 2 AM UTC)
- Manual with validation level selection

**Features**:
- ✅ Validates external URLs (toolchain downloads, documentation links)
- ✅ Three validation levels: HEAD, partial, full
- ✅ Caching of validation results
- ✅ Automatic issue creation on failure
- ✅ Parallel execution (pytest-xdist)

```yaml
- name: Run link validation tests
  env:
    VALIDATION_LEVEL: ${{ github.event.inputs.validation_level || 'head' }}
  run: |
    pytest --link-validation \
           --validation-level=$VALIDATION_LEVEL \
           --validation-cache-dir=$HOME/.cache/toolchainkit-link-validation \
           -n auto \
           tests/link_validation/
```

**Validation Levels**:
- `head` - Quick HEAD requests to check URL availability (~10s)
- `partial` - Sample downloads with partial range (~2 min)
- `full` - Full downloads and SHA256 verification (~5 min, ~7GB)

**Duration**: 10 seconds (head) to 5 minutes (full)

### Full Link Validation Workflow

**File**: `.github/workflows/link-validation-full.yml`
**Triggers**:
- Monthly (1st of month at 3 AM UTC)
- Manual trigger

**Purpose**: Complete validation of all toolchain download URLs and hashes

```yaml
- name: Run full link validation
  run: |
    pytest --link-validation \
           --validation-level=full \
           --no-cache \
           tests/link_validation/
```

**Duration**: ~5 minutes, downloads ~7GB

### Code Quality Workflow

**File**: `.github/workflows/code-quality.yml`
**Triggers**: Push and PR to main/develop

**Checks**:
- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Ruff)
- ✅ Type checking (mypy)
- ✅ Security scanning

```yaml
- name: Check code formatting
  run: black --check .

- name: Check import sorting
  run: isort --check-only .

- name: Run Ruff linter
  run: ruff check .

- name: Type checking
  run: mypy toolchainkit/
```

**Duration**: ~2-3 minutes

## Manual CI/CD Integration

### GitHub Actions Template

Complete workflow for building C++ projects with ToolchainKit:

```yaml
# .github/workflows/build.yml
name: Build

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build:
    name: Build - ${{ matrix.os }} - ${{ matrix.build_type }}
    runs-on: ${{ matrix.os }}

    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        build_type: [Debug, Release]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Cache ToolchainKit toolchains
        uses: actions/cache@v4
        with:
          path: ~/.toolchainkit
          key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.yaml', 'toolchainkit.lock') }}
          restore-keys: |
            ${{ runner.os }}-toolchainkit-

      - name: Install ToolchainKit
        run: |
          python -m pip install --upgrade pip
          pip install toolchainkit
        shell: bash

      - name: Bootstrap project (if bootstrap script exists)
        run: |
          if [ -f "bootstrap.sh" ] && [ "${{ runner.os }}" != "Windows" ]; then
            chmod +x bootstrap.sh
            ./bootstrap.sh
          elif [ -f "bootstrap.bat" ] && [ "${{ runner.os }}" == "Windows" ]; then
            ./bootstrap.bat
          fi
        shell: bash
        continue-on-error: true

      - name: Configure CMake
        run: |
          cmake -B build/${{ matrix.build_type }} \
                -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
                -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
        shell: bash

      - name: Build
        run: cmake --build build/${{ matrix.build_type }} --config ${{ matrix.build_type }}
        shell: bash

      - name: Test
        run: ctest --test-dir build/${{ matrix.build_type }} --config ${{ matrix.build_type }} --output-on-failure
        shell: bash

      - name: Upload build artifacts
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.os }}-${{ matrix.build_type }}
          path: build/${{ matrix.build_type }}/
          retention-days: 7
```

### GitLab CI Template

```yaml
# .gitlab-ci.yml
image: ubuntu:22.04

stages:
  - setup
  - build
  - test
  - deploy

variables:
  GIT_SUBMODULE_STRATEGY: recursive

before_script:
  - apt-get update && apt-get install -y python3 python3-pip cmake ninja-build build-essential
  - pip3 install toolchainkit

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .toolchainkit/
    - ~/.toolchainkit/

setup:
  stage: setup
  script:
    - python3 -m toolchainkit.core.platform detect
  artifacts:
    paths:
      - toolchainkit.yaml
    expire_in: 1 hour

build:debug:
  stage: build
  script:
    - cmake -B build/Debug -DCMAKE_BUILD_TYPE=Debug -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
    - cmake --build build/Debug
  artifacts:
    paths:
      - build/Debug/
    expire_in: 1 week
  dependencies:
    - setup

build:release:
  stage: build
  script:
    - cmake -B build/Release -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
    - cmake --build build/Release
  artifacts:
    paths:
      - build/Release/
    expire_in: 1 week
  dependencies:
    - setup

test:debug:
  stage: test
  script:
    - ctest --test-dir build/Debug --output-on-failure
  dependencies:
    - build:debug

test:release:
  stage: test
  script:
    - ctest --test-dir build/Release --output-on-failure
  dependencies:
    - build:release
```

### Azure Pipelines Template

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - docs/*
      - README.md

pr:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  buildConfiguration: 'Release'

stages:
  - stage: Build
    jobs:
      - job: BuildJob
        strategy:
          matrix:
            Linux:
              vmImage: 'ubuntu-latest'
            Windows:
              vmImage: 'windows-latest'
            macOS:
              vmImage: 'macOS-latest'
        pool:
          vmImage: $(vmImage)

        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
              addToPath: true

          - script: |
              python -m pip install --upgrade pip
              pip install toolchainkit
            displayName: 'Install ToolchainKit'

          - task: Cache@2
            inputs:
              key: 'toolchainkit | "$(Agent.OS)" | toolchainkit.yaml'
              path: $(HOME)/.toolchainkit
              restoreKeys: |
                toolchainkit | "$(Agent.OS)"
            displayName: 'Cache ToolchainKit toolchains'

          - script: |
              cmake -B build -DCMAKE_BUILD_TYPE=$(buildConfiguration) -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
            displayName: 'Configure CMake'

          - script: |
              cmake --build build --config $(buildConfiguration)
            displayName: 'Build'

          - script: |
              ctest --test-dir build --config $(buildConfiguration) --output-on-failure
            displayName: 'Test'

          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: 'build'
              artifactName: 'build-$(Agent.OS)-$(buildConfiguration)'
            displayName: 'Publish Build Artifacts'
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    parameters {
        choice(name: 'BUILD_TYPE', choices: ['Debug', 'Release'], description: 'Build configuration')
    }

    environment {
        TOOLCHAINKIT_CACHE = "${WORKSPACE}/.toolchainkit"
    }

    stages {
        stage('Setup') {
            steps {
                sh 'python3 -m pip install --upgrade pip'
                sh 'pip3 install toolchainkit'
            }
        }

        stage('Configure') {
            steps {
                sh """
                    cmake -B build \
                          -DCMAKE_BUILD_TYPE=${params.BUILD_TYPE} \
                          -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
                """
            }
        }

        stage('Build') {
            steps {
                sh 'cmake --build build --config ${params.BUILD_TYPE}'
            }
        }

        stage('Test') {
            steps {
                sh 'ctest --test-dir build --config ${params.BUILD_TYPE} --output-on-failure'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'build/**', allowEmptyArchive: true
            junit 'build/**/test-results/**/*.xml'
        }
        success {
            echo 'Build succeeded!'
        }
        failure {
            echo 'Build failed!'
        }
    }
}
```

## Caching Strategies

Effective caching is essential for fast CI/CD pipelines. ToolchainKit supports multiple caching layers:

### 1. Toolchain Caching

Cache downloaded toolchains to avoid repeated downloads:

**GitHub Actions:**
```yaml
- name: Cache ToolchainKit toolchains
  uses: actions/cache@v4
  with:
    path: |
      ~/.toolchainkit/toolchains
      ~/.toolchainkit/downloads
    key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.yaml', 'toolchainkit.lock') }}
    restore-keys: |
      ${{ runner.os }}-toolchainkit-
```

**GitLab CI:**
```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}-toolchainkit
  paths:
    - .toolchainkit/
    - ~/.toolchainkit/
```

**Azure Pipelines:**
```yaml
- task: Cache@2
  inputs:
    key: 'toolchainkit | "$(Agent.OS)" | $(Build.SourcesDirectory)/toolchainkit.lock'
    path: $(HOME)/.toolchainkit
    restoreKeys: |
      toolchainkit | "$(Agent.OS)"
```

### 2. Build Cache (sccache)

Use `sccache` to cache compiler artifacts across builds:

**Installation & Configuration:**
```yaml
# GitHub Actions
- name: Setup sccache
  uses: mozilla-actions/sccache-action@v0.0.3
  with:
    version: "v0.5.0"

- name: Configure CMake with sccache
  run: |
    cmake -B build \
          -DCMAKE_C_COMPILER_LAUNCHER=sccache \
          -DCMAKE_CXX_COMPILER_LAUNCHER=sccache \
          -DCMAKE_TOOLCHAIN_FILE=.toolchainkit/cmake/toolchainkit/toolchain.cmake
  env:
    SCCACHE_DIR: ${{ github.workspace }}/.sccache
    SCCACHE_CACHE_SIZE: "2G"

- name: Show sccache stats
  run: sccache --show-stats
```

**ToolchainKit Integration:**
```python
# toolchainkit.yaml
build:
  cache:
    enabled: true
    type: sccache
    config:
      max_size: "2G"
      local_cache_dir: ".sccache"
```

### 3. CMake Build Cache

Cache CMake-generated files and object files:

```yaml
# GitHub Actions
- name: Cache CMake build
  uses: actions/cache@v4
  with:
    path: |
      build/CMakeCache.txt
      build/CMakeFiles
      build/**/*.o
      build/**/*.obj
    key: ${{ runner.os }}-cmake-${{ hashFiles('**/CMakeLists.txt') }}-${{ hashFiles('**/*.cpp', '**/*.h') }}
    restore-keys: |
      ${{ runner.os }}-cmake-${{ hashFiles('**/CMakeLists.txt') }}-
      ${{ runner.os }}-cmake-
```

### 4. Package Manager Cache

Cache vcpkg, Conan, or other package manager artifacts:

**vcpkg:**
```yaml
- name: Cache vcpkg
  uses: actions/cache@v4
  with:
    path: |
      ${{ github.workspace }}/vcpkg
      ~/.cache/vcpkg
    key: ${{ runner.os }}-vcpkg-${{ hashFiles('vcpkg.json') }}
```

**Conan:**
```yaml
- name: Cache Conan packages
  uses: actions/cache@v4
  with:
    path: ~/.conan
    key: ${{ runner.os }}-conan-${{ hashFiles('conanfile.txt') }}
```

### 5. Python Dependencies Cache

Cache pip packages used by ToolchainKit:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # Automatically caches pip packages
```

### 6. Multi-layer Cache Strategy

Combine multiple cache layers for optimal performance:

```yaml
# .github/workflows/optimized-build.yml
jobs:
  build:
    steps:
      # Layer 1: Python dependencies
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      # Layer 2: ToolchainKit toolchains
      - uses: actions/cache@v4
        with:
          path: ~/.toolchainkit
          key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.lock') }}

      # Layer 3: sccache compiler cache
      - uses: mozilla-actions/sccache-action@v0.0.3

      # Layer 4: CMake configuration
      - uses: actions/cache@v4
        with:
          path: build/CMakeCache.txt
          key: ${{ runner.os }}-cmake-config-${{ hashFiles('**/CMakeLists.txt') }}

      # Layer 5: Package manager
      - uses: actions/cache@v4
        with:
          path: vcpkg
          key: ${{ runner.os }}-vcpkg-${{ hashFiles('vcpkg.json') }}
```

### Cache Best Practices

1. **Use specific cache keys**: Include file hashes for accurate invalidation
2. **Set appropriate restore-keys**: Provide fallback keys for partial matches
3. **Monitor cache size**: Large caches can slow down save/restore
4. **Cache hit rate**: Check CI logs to verify caches are being used
5. **Parallel caching**: Use separate caches for different job matrices
6. **Retention policy**: Set appropriate expiration for large caches

### Cache Performance Metrics

From ToolchainKit's own CI workflows:

- **Toolchain cache**: ~500MB, saves 2-3 minutes per run
- **sccache**: ~1GB, saves 5-10 minutes on incremental builds
- **pip cache**: ~200MB, saves 30-60 seconds
- **Total time saved**: 7-14 minutes per workflow run (40-60% faster)

## Running Tests Locally

Replicate CI tests on your local machine:

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-xdist pytest-asyncio

# Run unit tests (fast, ~10 seconds)
pytest -m unit

# Run integration tests (~2 minutes)
pytest -m integration

# Run E2E smoke tests (~5 minutes)
pytest -m "e2e and smoke"

# Run all tests in parallel
pytest -n auto

# Check coverage with threshold enforcement
pytest --cov=toolchainkit --cov-report=html --cov-fail-under=80

# Run specific test file
pytest tests/test_lockfile.py -v

# Run with verbose output
pytest -vv --tb=long
```

### Local CI Simulation

Run the exact same workflow steps locally:

```bash
# 1. Clean environment
rm -rf build .toolchainkit .pytest_cache

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests with coverage
pytest -m unit --cov=toolchainkit --cov-report=xml

# 4. Run integration tests
pytest -m integration

# 5. Check coverage threshold
python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); coverage = float(tree.getroot().attrib['line-rate']) * 100; exit(0 if coverage >= 80 else 1)"

# 6. Run link validation (if applicable)
pytest -m link_validation --validate-level=head
```

## Status Badges

Add CI/CD status badges to your project's README:

### GitHub Actions

```markdown
<!-- Build Status -->
[![Build Status](https://github.com/username/repo/workflows/build/badge.svg)](https://github.com/username/repo/actions?query=workflow%3Abuild)

<!-- Test Coverage -->
[![Coverage Status](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repo)

<!-- Code Quality -->
[![Code Quality](https://github.com/username/repo/workflows/code-quality/badge.svg)](https://github.com/username/repo/actions?query=workflow%3Acode-quality)
```

### GitLab CI

```markdown
[![pipeline status](https://gitlab.com/username/repo/badges/main/pipeline.svg)](https://gitlab.com/username/repo/-/commits/main)
[![coverage report](https://gitlab.com/username/repo/badges/main/coverage.svg)](https://gitlab.com/username/repo/-/commits/main)
```

### Azure Pipelines

```markdown
[![Build Status](https://dev.azure.com/username/repo/_apis/build/status/repo?branchName=main)](https://dev.azure.com/username/repo/_build/latest?definitionId=1&branchName=main)
```

## Best Practices

### 1. Matrix Testing

Test across multiple configurations:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python: ['3.9', '3.10', '3.11', '3.12']
    toolchain: [gcc, clang, msvc]
    build_type: [Debug, Release]
```

### 2. Fail-Fast Strategy

Control when to stop on failures:

```yaml
strategy:
  fail-fast: false  # Continue testing other matrix combinations
  max-parallel: 6   # Limit concurrent jobs
```

### 3. Conditional Steps

Run steps only when needed:

```yaml
- name: Upload artifacts
  if: success() && matrix.build_type == 'Release'
  uses: actions/upload-artifact@v4
  with:
    name: release-build
    path: build/

- name: Deploy
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh
```

### 4. Secrets Management

Store sensitive data securely:

```yaml
env:
  CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
```

### 5. Timeouts

Prevent hanging jobs:

```yaml
jobs:
  build:
    timeout-minutes: 30  # Kill job after 30 minutes
    steps:
      - name: Build
        timeout-minutes: 15  # Kill step after 15 minutes
```

### 6. Notifications

Get notified on failures:

```yaml
# GitHub Actions (via third-party actions)
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Build failed: ${{ github.repository }} - ${{ github.ref }}"
      }
```

### 7. Dependency Pinning

Use lock files for reproducibility:

```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    # Generate lock file if it doesn't exist
    if [ ! -f toolchainkit.lock ]; then
      python -m toolchainkit.cli lock
    fi
```

## Troubleshooting

### Common CI/CD Issues

#### 1. Toolchain Download Failures

**Symptom:** Toolchain downloads timeout or fail

**Solution:**
```yaml
- name: Download toolchain with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: python -m toolchainkit.cli download --toolchain gcc-12.2.0
```

#### 2. Cache Restoration Failures

**Symptom:** Cache not restored, builds slow

**Solution:**
```yaml
- name: Debug cache
  run: |
    echo "Cache key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.lock') }}"
    ls -la ~/.toolchainkit || echo "Cache directory not found"
```

#### 3. Permission Issues

**Symptom:** "Permission denied" errors on Linux/macOS

**Solution:**
```yaml
- name: Fix permissions
  run: |
    chmod +x bootstrap.sh
    chmod +x ~/.toolchainkit/toolchains/*/bin/*
```

#### 4. Out of Memory

**Symptom:** Build killed due to OOM

**Solution:**
```yaml
- name: Build with limited parallelism
  run: cmake --build build --parallel 2  # Limit to 2 parallel jobs
```

#### 5. Stale Build Artifacts

**Symptom:** Build uses old cached files

**Solution:**
```yaml
- name: Clean build
  run: |
    rm -rf build
    cmake -B build --fresh  # CMake 3.24+
```

### Debug Commands

```bash
# Check ToolchainKit installation
python -m toolchainkit.cli --version

# Verify configuration
python -m toolchainkit.cli config show

# Check toolchain availability
python -m toolchainkit.cli toolchain list

# Validate lock file
python -m toolchainkit.cli lock verify

# Run doctor command
python -m toolchainkit.cli doctor --auto-fix
```

## Performance Optimization

### Workflow Timing Breakdown

From ToolchainKit's CI workflows:

| Workflow | Duration (no cache) | Duration (cached) | Speed-up |
|----------|---------------------|-------------------|----------|
| Unit Tests | 12 min | 3 min | 4× |
| Integration Tests | 18 min | 8 min | 2.25× |
| E2E Tests | 25 min | 15 min | 1.67× |
| Link Validation | 10 min | 2 min | 5× |
| Code Quality | 8 min | 4 min | 2× |

### Optimization Checklist

- [ ] Enable all cache layers (toolchain, build, pip)
- [ ] Use `sccache` for compiler artifact caching
- [ ] Parallelize independent tests with `pytest -n auto`
- [ ] Use matrix strategy for cross-platform builds
- [ ] Set appropriate timeouts
- [ ] Use `fail-fast: false` for comprehensive results
- [ ] Leverage artifact uploads for debugging
- [ ] Monitor cache hit rates
- [ ] Profile slow tests and optimize

## See Also

- [Testing Guide](testing/README.md) - Comprehensive testing documentation
- [Configuration](config.md) - ToolchainKit configuration options
- [Lock Files](lockfile.md) - Reproducible builds with lock files
- [Bootstrap Scripts](bootstrap.md) - Automated project setup
- [Doctor Command](doctor.md) - Environment diagnostics
