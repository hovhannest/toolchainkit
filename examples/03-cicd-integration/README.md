# Example 3: CI/CD Integration

This example demonstrates how to use ToolchainKit in CI/CD pipelines for automated building, testing, and deployment.

## Scenario

You want to:
- Build and test across multiple platforms (Linux, Windows, macOS)
- Use consistent, reproducible toolchains in CI
- Cache toolchains and dependencies for fast builds
- Run static analysis and code quality checks
- Deploy artifacts automatically

## Project Structure

```
03-cicd-integration/
├── .github/
│   └── workflows/
│       ├── build.yml              # Multi-platform build
│       ├── release.yml            # Release workflow
│       └── code-quality.yml       # Linting and analysis
├── .gitlab-ci.yml                 # GitLab CI config
├── azure-pipelines.yml            # Azure Pipelines config
├── CMakeLists.txt
├── toolchainkit.yaml
├── bootstrap.sh
├── bootstrap.bat
└── src/
    └── main.cpp
```

## GitHub Actions Examples

### 1. Multi-Platform Build

`.github/workflows/build.yml`:

```yaml
name: Build and Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

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
          path: |
            ~/.toolchainkit
            .toolchainkit
          key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.yaml', 'toolchainkit.lock') }}
          restore-keys: |
            ${{ runner.os }}-toolchainkit-

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap project
        run: |
          tkgen bootstrap --force --build-type ${{ matrix.build_type }}
        shell: bash

      - name: Build
        run: cmake --build build --config ${{ matrix.build_type }}

      - name: Test
        run: ctest --test-dir build --config ${{ matrix.build_type }} --output-on-failure

      - name: Upload artifacts
        if: success() && matrix.build_type == 'Release'
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.os }}
          path: build/
          retention-days: 7
```

### 2. Release Workflow

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  create-release:
    name: Create Release
    runs-on: ubuntu-latest
    outputs:
      upload_url: ${{ steps.create_release.outputs.upload_url }}

    steps:
      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false

  build-release:
    name: Build Release - ${{ matrix.os }}
    needs: create-release
    runs-on: ${{ matrix.os }}

    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Cache toolchains
        uses: actions/cache@v4
        with:
          path: ~/.toolchainkit
          key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.lock') }}

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap and build
        run: |
          tkgen bootstrap --force --build-type Release
          cmake --build build --config Release

      - name: Package artifacts
        run: |
          cd build
          cpack -G ZIP
          cpack -G TGZ

      - name: Upload Release Asset
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ needs.create-release.outputs.upload_url }}
          asset_path: ./build/myproject-*.zip
          asset_name: myproject-${{ runner.os }}.zip
          asset_content_type: application/zip
```

### 3. Code Quality Checks

`.github/workflows/code-quality.yml`:

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  lint:
    name: Lint and Format Check
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap
        run: ./bootstrap.sh

      - name: Run clang-format
        run: |
          find src include -name '*.cpp' -o -name '*.h' | \
          xargs clang-format --dry-run --Werror

      - name: Run clang-tidy
        run: |
          cmake --build build --target tidy

      - name: Check for warnings
        run: |
          cmake --build build 2>&1 | tee build.log
          ! grep -i "warning:" build.log

  coverage:
    name: Code Coverage
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ToolchainKit
        run: pip install toolchainkit

      - name: Bootstrap with coverage
        run: |
          tkgen bootstrap --force --build-type Debug
          cmake -B build -DCMAKE_CXX_FLAGS="--coverage"

      - name: Build and test
        run: |
          cmake --build build
          ctest --test-dir build

      - name: Generate coverage report
        run: |
          lcov --capture --directory build --output-file coverage.info
          lcov --remove coverage.info '/usr/*' --output-file coverage.info

      - name: Upload to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: coverage.info
          fail_ci_if_error: true
```

## GitLab CI Example

`.gitlab-ci.yml`:

```yaml
image: ubuntu:22.04

stages:
  - setup
  - build
  - test
  - deploy

variables:
  GIT_SUBMODULE_STRATEGY: recursive

before_script:
  - apt-get update && apt-get install -y python3 python3-pip git
  - pip3 install toolchainkit

cache:
  key: ${CI_COMMIT_REF_SLUG}-toolchainkit
  paths:
    - .toolchainkit/
    - ~/.toolchainkit/

setup:
  stage: setup
  script:
    - tkgen doctor
  artifacts:
    paths:
      - toolchainkit.yaml
    expire_in: 1 hour

build:linux:
  stage: build
  script:
    - tkgen bootstrap --force --build-type Release
    - cmake --build build --config Release
  artifacts:
    paths:
      - build/
    expire_in: 1 week
  dependencies:
    - setup

build:debug:
  stage: build
  script:
    - tkgen bootstrap --force --build-type Debug
    - cmake --build build --config Debug
  artifacts:
    paths:
      - build/
    expire_in: 1 week
  dependencies:
    - setup

test:unit:
  stage: test
  script:
    - ctest --test-dir build --output-on-failure
  dependencies:
    - build:linux

test:integration:
  stage: test
  script:
    - ctest --test-dir build -R integration --output-on-failure
  dependencies:
    - build:linux

deploy:production:
  stage: deploy
  script:
    - echo "Deploying to production..."
    - ./scripts/deploy.sh
  dependencies:
    - build:linux
  only:
    - main
    - tags
```

## Azure Pipelines Example

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main
      - develop
  tags:
    include:
      - v*

pr:
  branches:
    include:
      - main

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

          - task: Cache@2
            inputs:
              key: 'toolchainkit | "$(Agent.OS)" | toolchainkit.lock'
              path: $(HOME)/.toolchainkit
              restoreKeys: |
                toolchainkit | "$(Agent.OS)"
            displayName: 'Cache ToolchainKit'

          - script: |
              python -m pip install --upgrade pip
              pip install toolchainkit
            displayName: 'Install ToolchainKit'

          - script: |
              tkgen bootstrap --force --build-type $(buildConfiguration)
            displayName: 'Bootstrap Project'

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
            displayName: 'Publish Artifacts'

  - stage: Deploy
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployProduction
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "Deploying to production"
```

## Benefits of ToolchainKit in CI/CD

✅ **Consistent Environments**: Same toolchain in CI as on developer machines
✅ **Fast Builds**: Toolchain caching saves 5-10 minutes per build
✅ **Cross-Platform**: Single workflow for Windows, Linux, macOS
✅ **Reproducible**: Lock files ensure exact versions
✅ **Easy Debugging**: Run `./bootstrap.sh` locally to replicate CI environment
✅ **No Manual Setup**: CI images don't need pre-installed compilers

## Caching Strategy

### GitHub Actions
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.toolchainkit/toolchains
      ~/.toolchainkit/downloads
      .toolchainkit
    key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.lock') }}
    restore-keys: |
      ${{ runner.os }}-toolchainkit-
```

### GitLab CI
```yaml
cache:
  key: ${CI_COMMIT_REF_SLUG}-toolchainkit
  paths:
    - .toolchainkit/
    - ~/.toolchainkit/
```

### Azure Pipelines
```yaml
- task: Cache@2
  inputs:
    key: 'toolchainkit | "$(Agent.OS)" | toolchainkit.lock'
    path: $(HOME)/.toolchainkit
```

## Performance Metrics

From real projects using ToolchainKit in CI:

| Metric | Without Caching | With Caching | Speed-up |
|--------|-----------------|--------------|----------|
| Toolchain download | 3-5 min | 30 sec | 6-10× |
| Dependency install | 2-4 min | 1 min | 2-4× |
| Total CI time | 15-20 min | 5-8 min | 3× |

## Troubleshooting CI Issues

### Issue: Bootstrap fails in CI

**Solution**: Check Python version and install ToolchainKit:
```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
- run: pip install toolchainkit
```

### Issue: Cache not restoring

**Solution**: Include lock file in cache key:
```yaml
key: ${{ runner.os }}-toolchainkit-${{ hashFiles('toolchainkit.lock') }}
```

### Issue: Builds too slow

**Solution**: Enable all caching layers:
1. Toolchain cache
2. Build cache (sccache)
3. Dependency cache
4. CMake cache

## See Also

- [CI/CD Documentation](../../docs/ci_cd.md)
- [Caching Strategies](../../docs/ci_cd.md#caching-strategies)
- [Bootstrap Scripts](../../docs/bootstrap.md)
- [Lock Files](../../docs/lockfile.md)
