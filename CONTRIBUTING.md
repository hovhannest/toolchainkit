# Contributing to ToolchainKit

Thank you for your interest in contributing to ToolchainKit! We welcome contributions from the community and appreciate your help in making this project better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Contributing Code](#contributing-code)
  - [Improving Documentation](#improving-documentation)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Code Review Process](#code-review-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. ...
2. ...
3. ...

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Windows 11, Ubuntu 22.04, macOS 14]
- Python version: [e.g., 3.11.5]
- ToolchainKit version: [e.g., 0.1.0-alpha]

**Code Sample**
```python
# Minimal code sample to reproduce
```

**Error Message/Stack Trace**
```
Full error message and stack trace
```

**Additional context**
Any other context about the problem.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

**Enhancement Request Template:**

```markdown
**Is your feature request related to a problem?**
A clear and concise description of the problem.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Use Case**
Explain how this feature would be used and who would benefit.

**Additional context**
Any other context, mockups, or examples.
```

### Contributing Code

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `dev_hovt`
4. **Make your changes**
5. **Test your changes**
6. **Commit your changes** with clear commit messages
7. **Push to your fork**
8. **Open a pull request**

### Improving Documentation

Documentation improvements are always welcome:

- Fix typos, grammar, or unclear explanations
- Add missing documentation for existing features
- Create tutorials or guides
- Improve code examples
- Update outdated information

Documentation is located in:
- `README.md` - Main project readme
- `docs/` - User documentation
- `docs/dev/` - Developer documentation
- `docs/testing/` - Testing documentation
- Docstrings in Python code

## Development Setup

### Prerequisites

- Python 3.9, 3.10, 3.11, 3.12, or 3.13
- Git
- (Optional) pre-commit for code quality checks

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hovhannest/toolchainkit.git
   cd toolchainkit
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

4. **Install development dependencies:**
   ```bash
   # Already included in requirements.txt:
   # - pytest
   # - pytest-cov
   # - pytest-mock
   # - responses
   ```

5. **Optional: Install pre-commit hooks:**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. **Verify setup:**
   ```bash
   pytest
   ```
   You should see 2385 tests passing.

## Development Workflow

### Branch Strategy

- `main` - Stable releases only
- `dev_hovt` - Active development branch (default)
- `feature/<name>` - Feature branches
- `fix/<name>` - Bug fix branches
- `docs/<name>` - Documentation branches

### Creating a Feature Branch

```bash
git checkout dev_hovt
git pull origin dev_hovt
git checkout -b feature/my-feature
```

### Making Changes

1. **Write code** following our [coding standards](#coding-standards)
2. **Write tests** for new functionality
3. **Update documentation** if needed
4. **Run tests** to ensure nothing breaks
5. **Run pre-commit checks** (if installed)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Fast unit tests
pytest -m integration    # Integration tests
pytest -m e2e            # End-to-end tests

# Run tests for specific module
pytest tests/core/test_platform.py

# Run with coverage
pytest --cov=toolchainkit --cov-report=html

# Stop on first failure
pytest -x

# Verbose output
pytest -vv
```

### Code Quality Checks

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Or manually:
# - Linting: ruff check toolchainkit/
# - Formatting: ruff format toolchainkit/
# - Type checking: mypy toolchainkit/
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use [Black](https://black.readthedocs.io/) or [Ruff](https://docs.astral.sh/ruff/) formatting
- Maximum line length: 100 characters (flexible for readability)
- Use type hints for all function signatures (Python 3.9+ compatible)

### Code Organization

- One class per file (for major classes)
- Group related functions together
- Keep modules focused on a single responsibility
- Use clear, descriptive names (verbose is better than cryptic)

### Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `lowercase_with_underscores()`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private Members**: `_leading_underscore`

### Documentation

- **All public modules** must have a module-level docstring
- **All public classes** must have a class-level docstring
- **All public functions/methods** must have docstrings with:
  - Description of what it does
  - Args section (parameters)
  - Returns section (if applicable)
  - Raises section (if applicable)
  - Example usage (for complex functions)

**Docstring Format (Google Style):**

```python
def download_toolchain(
    toolchain_name: str,
    version: str,
    platform: str,
    force: bool = False
) -> DownloadResult:
    """Download and extract a toolchain.

    This function downloads a toolchain archive, verifies its checksum,
    and extracts it to the cache directory. If the toolchain is already
    cached, it will skip the download unless force=True.

    Args:
        toolchain_name: Name of the toolchain (e.g., 'llvm', 'gcc')
        version: Version string or pattern (e.g., '18.1.8', '18')
        platform: Platform string (e.g., 'linux-x64', 'windows-x64')
        force: Force re-download even if cached

    Returns:
        DownloadResult with toolchain_id, path, timing metrics

    Raises:
        ToolchainDownloadError: If download fails
        ToolchainExtractionError: If extraction fails
        InvalidVersionError: If version is invalid

    Example:
        >>> downloader = ToolchainDownloader()
        >>> result = downloader.download_toolchain('llvm', '18.1.8', 'linux-x64')
        >>> print(f"Installed at: {result.toolchain_path}")
    """
    ...
```

### Error Handling

- Use custom exceptions from `toolchainkit.core.exceptions`
- Provide clear, actionable error messages
- Include context in exceptions (paths, values, etc.)
- Document exceptions in function docstrings

### Type Hints

- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable values
- Use `Union[A, B]` for multiple possible types (or `A | B` in Python 3.10+)
- Use `List[T]`, `Dict[K, V]`, etc. for collections (or built-in equivalents in Python 3.9+)

```python
from typing import Optional, Dict, List
from pathlib import Path

def get_toolchain_info(
    toolchain_id: str,
    include_refs: bool = False
) -> Optional[Dict[str, any]]:
    """Get toolchain information from registry."""
    ...
```

## Testing Guidelines

### Test Organization

- **Unit tests**: `tests/<module>/test_*.py`
- **Integration tests**: `tests/integration/test_*.py`
- **E2E tests**: `tests/e2e/test_*.py`
- **Fixtures**: `tests/fixtures/`
- **Mocks**: `tests/mocks/`

### Writing Tests

1. **Test file naming**: `test_<module_name>.py`
2. **Test function naming**: `test_<what_it_tests>()`
3. **Use pytest markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
4. **Use fixtures**: Leverage shared fixtures from `conftest.py`
5. **Test one thing**: Each test should test one specific behavior
6. **Arrange-Act-Assert**: Follow AAA pattern

**Example Test:**

```python
import pytest
from toolchainkit.core.platform import detect_platform

@pytest.mark.unit
def test_detect_platform_returns_platform_info():
    """Test that detect_platform returns valid PlatformInfo."""
    # Arrange (if needed)

    # Act
    platform = detect_platform()

    # Assert
    assert platform is not None
    assert platform.os in ['windows', 'linux', 'macos']
    assert platform.arch in ['x64', 'arm64', 'x86', 'arm']
    assert isinstance(platform.platform_string(), str)


@pytest.mark.unit
def test_platform_string_format():
    """Test platform string format is OS-ARCH."""
    platform = detect_platform()
    platform_str = platform.platform_string()

    assert '-' in platform_str
    os, arch = platform_str.split('-', 1)
    assert len(os) > 0
    assert len(arch) > 0
```

### Test Coverage

- **Target**: >80% coverage for all modules
- **Critical modules**: >90% coverage (core, toolchain, cmake)
- Run coverage reports: `pytest --cov=toolchainkit --cov-report=html`
- Check `htmlcov/index.html` for detailed report

### Test Best Practices

- Write tests before or alongside code (TDD encouraged)
- Test both success and failure cases
- Test edge cases and boundary conditions
- Use mocks for external dependencies (network, filesystem)
- Keep tests fast (unit tests < 100ms each)
- Make tests deterministic (no random values, fixed time)

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass**: `pytest`
2. **Check code coverage**: Coverage should not decrease
3. **Update documentation**: If adding features or changing APIs
4. **Update CHANGELOG.md**: Add entry under `[Unreleased]`
5. **Rebase on latest dev_hovt**: `git rebase origin/dev_hovt`

### Submitting a Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```

2. **Open a pull request** on GitHub:
   - Base branch: `dev_hovt`
   - Compare branch: `feature/my-feature`

3. **Fill out the PR template**:

   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix (non-breaking change fixing an issue)
   - [ ] New feature (non-breaking change adding functionality)
   - [ ] Breaking change (fix or feature causing existing functionality to change)
   - [ ] Documentation update

   ## Testing
   - [ ] All existing tests pass
   - [ ] New tests added for new functionality
   - [ ] Coverage maintained or improved

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   - [ ] Commit messages follow guidelines
   - [ ] No unnecessary dependencies added

   ## Related Issues
   Closes #<issue_number>
   ```

### PR Review Process

- A maintainer will review your PR within 1-2 weeks
- Address review comments by pushing new commits
- Once approved, a maintainer will merge your PR
- PRs are typically squashed or rebased when merging

## Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semi-colons, etc.)
- `refactor`: Code refactoring (no functional changes)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes (dependencies, tooling)

### Examples

```
feat(downloader): add progress callback support

Add optional progress_callback parameter to download_toolchain()
to allow callers to track download progress in real-time.

Closes #123
```

```
fix(platform): correct ARM64 detection on macOS

Fix platform detection incorrectly identifying Apple Silicon
as 'arm' instead of 'arm64'.

Fixes #456
```

```
docs(readme): update quick start guide

- Add Python 3.13 to supported versions
- Fix typo in code example
- Add link to API documentation
```

### Best Practices

- Use imperative mood ("add feature" not "added feature")
- Keep subject line under 72 characters
- Capitalize subject line
- No period at end of subject
- Separate subject from body with blank line
- Wrap body at 72 characters
- Explain *what* and *why*, not *how*

## Code Review Process

### For Contributors

- Be responsive to review comments
- Be open to feedback and suggestions
- Ask for clarification if feedback is unclear
- Make requested changes promptly
- Thank reviewers for their time

### For Reviewers

- Be respectful and constructive
- Focus on code, not the person
- Explain *why* changes are needed
- Suggest alternatives when possible
- Approve quickly if changes are good
- Request changes if needed, explain clearly

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are comprehensive and passing
- [ ] Documentation is updated
- [ ] No unnecessary dependencies
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] Error handling is appropriate
- [ ] API is intuitive and consistent

## Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)
- **Alpha/Beta/RC**: Pre-release versions (e.g., 0.1.0-alpha, 1.0.0-beta.1)

### Release Steps (Maintainers Only)

1. Update version in `toolchainkit/__init__.py`
2. Update `CHANGELOG.md` (move `[Unreleased]` to `[X.Y.Z]`)
3. Commit: `git commit -m "chore(release): v X.Y.Z"`
4. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push: `git push && git push --tags`
6. Create GitHub release with changelog
7. (Future) Publish to PyPI: `python -m build && twine upload dist/*`

## Getting Help

- **Documentation**: Check [docs/](docs/) directory
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Discord/Slack**: (To be announced)

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- GitHub contributors page

Thank you for contributing to ToolchainKit! 🎉
