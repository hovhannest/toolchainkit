# Bootstrap Script Generation Enhancement Plan

**Status**: Enhancement Proposal
**Target Version**: v0.1.0
**Priority**: Medium
**Complexity**: Low-Medium

## Current State (v0.1.0)

### ✅ What's Implemented

1. **Core BootstrapGenerator Class** (`toolchainkit/bootstrap/generator.py`)
   - ✅ `BootstrapGenerator` class with full API
   - ✅ Shell script generation (`bootstrap.sh` for Linux/macOS)
   - ✅ Batch script generation (`bootstrap.bat` for Windows)
   - ✅ Configuration support (toolchain, build_type, build_dir, package_manager)
   - ✅ Package manager integration (Conan, vcpkg)
   - ✅ Python availability check
   - ✅ ToolchainKit installation
   - ✅ CMake configuration
   - ✅ Error handling with `BootstrapGeneratorError`
   - ✅ README section generation

2. **Integration with Init Command**
   - ✅ `init` command calls `BootstrapGenerator` to create scripts
   - ✅ Generated scripts listed in init output
   - ✅ Next steps show how to run bootstrap scripts

3. **Test Coverage**
   - ✅ Comprehensive unit tests (456 lines in `tests/bootstrap/test_generator.py`)
   - ✅ Tests for shell script generation
   - ✅ Tests for batch script generation
   - ✅ Tests for package manager integration
   - ✅ Tests for error handling
   - ✅ Tests for executable permissions (Unix)

4. **Documentation**
   - ✅ Comprehensive `docs/bootstrap.md` (283 lines)
   - ✅ API reference with all methods
   - ✅ Usage examples
   - ✅ Configuration options
   - ✅ Generated script examples
   - ✅ CI/CD integration examples
   - ✅ Customization guide

### ❌ What's Missing

#### 1. Standalone CLI Command
**Status**: NOT IMPLEMENTED
**Impact**: High

Currently, users must use the Python API directly to generate bootstrap scripts for existing projects. There's no `tkgen bootstrap` command.

**Missing Functionality**:
- No `bootstrap` subcommand in CLI parser
- No `toolchainkit/cli/commands/bootstrap.py` module
- Cannot run `tkgen bootstrap` to generate scripts
- Cannot regenerate scripts for existing projects

**User Impact**:
- Cannot regenerate bootstrap scripts if deleted
- Cannot update scripts when toolchain changes
- Must write Python script to use BootstrapGenerator
- Inconsistent with other CLI commands (doctor, verify, etc.)

#### 2. Advanced Configuration Options
**Status**: PARTIALLY IMPLEMENTED
**Impact**: Medium

The generator supports basic configuration but lacks advanced options:

**Missing Options**:
- ✅ Toolchain selection (implemented)
- ✅ Build type (implemented)
- ✅ Package manager (implemented)
- ❌ Custom CMake arguments
- ❌ Environment variable setup
- ❌ Pre-build/post-build hooks
- ❌ Dependency version pinning
- ❌ Custom Python requirements
- ❌ Multiple build configurations
- ❌ Cross-compilation target setup

#### 3. Template System
**Status**: NOT IMPLEMENTED
**Impact**: Low-Medium

Scripts are generated programmatically with f-strings. No template system for customization:

**Missing Features**:
- No Jinja2 templates for scripts
- Cannot easily customize script structure
- Hard to maintain complex scripts
- Difficult to add new script types

#### 4. Script Validation
**Status**: NOT IMPLEMENTED
**Impact**: Medium

No validation of generated scripts:

**Missing Features**:
- No syntax checking (bash/batch)
- No shellcheck integration
- No dry-run mode
- No verification after generation

#### 5. IDE Integration
**Status**: NOT IMPLEMENTED
**Impact**: Low

No integration with VS Code or other IDEs:

**Missing Features**:
- No tasks.json generation for running bootstrap
- No launch.json integration
- No VS Code task provider

#### 6. Multi-platform Support
**Status**: PARTIALLY IMPLEMENTED
**Impact**: Low

Only Unix (bash) and Windows (batch) supported:

**Missing Platforms**:
- ❌ PowerShell scripts (modern Windows)
- ❌ Fish shell scripts
- ❌ Nushell scripts
- ❌ Make-based bootstrap (Makefile)
- ❌ CMake script mode (-P)

## Implementation Plan

### Phase 1: Standalone CLI Command (High Priority)

**Goal**: Enable `tkgen bootstrap` command for script generation/regeneration

**Tasks**:

1. **Create Bootstrap Command Module** (~2 hours)
   ```
   File: toolchainkit/cli/commands/bootstrap.py

   Features:
   - Load existing toolchainkit.yaml
   - Generate bootstrap scripts
   - Support --force to regenerate
   - Support --dry-run to preview
   - Support --platform to specify platforms (unix, windows, all)
   ```

2. **Add CLI Parser Integration** (~1 hour)
   ```python
   # In toolchainkit/cli/parser.py
   def _add_bootstrap_command(self, subparsers):
       """Add 'bootstrap' subcommand."""
       parser = subparsers.add_parser(
           "bootstrap",
           help="Generate bootstrap scripts",
           description="Generate platform-specific bootstrap scripts"
       )
       parser.add_argument(
           "--force",
           action="store_true",
           help="Overwrite existing scripts"
       )
       parser.add_argument(
           "--dry-run",
           action="store_true",
           help="Preview without creating files"
       )
       parser.add_argument(
           "--platform",
           choices=["unix", "windows", "all"],
           default="all",
           help="Platform to generate scripts for"
       )
       parser.add_argument(
           "--toolchain",
           help="Override toolchain from config"
       )
       parser.add_argument(
           "--build-type",
           choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
           help="Override build type from config"
       )
   ```

3. **Write Command Implementation** (~3 hours)
   ```python
   # Pseudo-code for bootstrap.py
   def run(args) -> int:
       # 1. Check project is initialized
       if not check_initialized(args.project_root):
           print_error("Project not initialized")
           return 1

       # 2. Load config
       config = load_config(args.project_root / "toolchainkit.yaml")

       # 3. Override with CLI args
       if args.toolchain:
           config["toolchain"] = args.toolchain
       if args.build_type:
           config["build_type"] = args.build_type

       # 4. Check existing scripts
       shell_exists = (args.project_root / "bootstrap.sh").exists()
       batch_exists = (args.project_root / "bootstrap.bat").exists()

       if (shell_exists or batch_exists) and not args.force:
           print_error("Bootstrap scripts already exist")
           print_info("Use --force to overwrite")
           return 1

       # 5. Generate scripts
       generator = BootstrapGenerator(args.project_root, config)

       if args.dry_run:
           print_preview(generator)
           return 0

       scripts = generator.generate_all()

       # 6. Report success
       print_success("Bootstrap scripts generated")
       for name, path in scripts.items():
           print_info(f"  - {path}")

       return 0
   ```

4. **Add Tests** (~2 hours)
   ```
   File: tests/cli/test_bootstrap.py

   Tests:
   - test_bootstrap_generates_scripts()
   - test_bootstrap_respects_config()
   - test_bootstrap_cli_overrides()
   - test_bootstrap_requires_initialization()
   - test_bootstrap_force_flag()
   - test_bootstrap_dry_run()
   - test_bootstrap_platform_selection()
   ```

5. **Update Documentation** (~1 hour)
   - Update `docs/bootstrap.md` with CLI command examples
   - Update `docs/cli.md` with bootstrap command reference
   - Add to `README.md` quick start

**Estimated Time**: 9 hours
**Deliverables**:
- Working `tkgen bootstrap` command
- Tests with >90% coverage
- Updated documentation

---

### Phase 2: Advanced Configuration (Medium Priority)

**Goal**: Support advanced bootstrap options

**Tasks**:

1. **Add CMake Arguments Support** (~2 hours)
   ```python
   # In generator.py
   config = {
       "toolchain": "llvm-18",
       "cmake_args": [
           "-DENABLE_TESTS=ON",
           "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
       ]
   }
   ```

2. **Environment Variables** (~1 hour)
   ```python
   config = {
       "env": {
           "CC": "/usr/bin/clang",
           "CXX": "/usr/bin/clang++",
           "MAKEFLAGS": "-j8"
       }
   }
   ```

3. **Pre/Post Hooks** (~3 hours)
   ```python
   config = {
       "hooks": {
           "pre_configure": "scripts/pre_configure.sh",
           "post_configure": "scripts/post_configure.sh",
           "pre_build": "scripts/pre_build.sh"
       }
   }
   ```

4. **Multiple Build Configurations** (~2 hours)
   ```python
   config = {
       "builds": [
           {"name": "debug", "build_type": "Debug", "build_dir": "build-debug"},
           {"name": "release", "build_type": "Release", "build_dir": "build-release"}
       ]
   }
   ```

**Estimated Time**: 8 hours

---

### Phase 3: Script Validation (Medium Priority)

**Goal**: Validate generated scripts for correctness

**Tasks**:

1. **Add Shellcheck Integration** (~3 hours)
   ```python
   def validate_shell_script(script_path: Path) -> List[str]:
       """Run shellcheck on script."""
       result = subprocess.run(
           ["shellcheck", "-x", str(script_path)],
           capture_output=True
       )
       return parse_shellcheck_output(result.stdout)
   ```

2. **Add Dry-run Mode** (~2 hours)
   ```python
   def preview_scripts(self) -> Dict[str, str]:
       """Generate script content without writing files."""
       return {
           "shell": self._generate_shell_content(),
           "batch": self._generate_batch_content()
       }
   ```

3. **Add Verification** (~2 hours)
   ```python
   def verify_scripts(self) -> bool:
       """Verify scripts can be parsed and executed."""
       # Check bash syntax: bash -n bootstrap.sh
       # Check batch syntax: more permissive
   ```

**Estimated Time**: 7 hours

---

### Phase 4: Template System (Low Priority)

**Goal**: Use Jinja2 templates for flexibility

**Tasks**:

1. **Create Template Directory** (~1 hour)
   ```
   toolchainkit/bootstrap/templates/
       bootstrap.sh.j2
       bootstrap.bat.j2
       bootstrap.ps1.j2
   ```

2. **Implement Template Rendering** (~3 hours)
   ```python
   from jinja2 import Environment, PackageLoader

   def _render_template(self, template_name: str, context: dict) -> str:
       env = Environment(loader=PackageLoader('toolchainkit', 'bootstrap/templates'))
       template = env.get_template(template_name)
       return template.render(**context)
   ```

3. **Support Custom Templates** (~2 hours)
   ```python
   # Allow users to provide custom templates
   generator = BootstrapGenerator(
       project_root=path,
       config=config,
       template_dir=Path("./custom_templates")
   )
   ```

**Estimated Time**: 6 hours

---

### Phase 5: PowerShell Support (Low Priority)

**Goal**: Generate modern PowerShell scripts for Windows

**Tasks**:

1. **Create PowerShell Generator** (~3 hours)
   ```python
   def generate_powershell_script(self) -> Path:
       """Generate bootstrap.ps1 for Windows PowerShell."""
   ```

2. **Add PowerShell Template** (~2 hours)
   ```powershell
   # bootstrap.ps1
   $ErrorActionPreference = "Stop"

   Write-Host "Bootstrapping {{ project_name }}..." -ForegroundColor Green

   # Check Python
   if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
       Write-Error "Python not found"
       exit 1
   }
   ```

3. **Update CLI** (~1 hour)
   - Add `--platform powershell` option
   - Update documentation

**Estimated Time**: 6 hours

---

## Implementation Roadmap

### v0.2.0 (Next Release)
**Focus**: Core functionality completion

- ✅ **Phase 1**: Standalone CLI Command (9 hours)
  - Must-have for v0.2.0
  - Highest user impact
  - Completes the bootstrap feature

- ⚠️ **Phase 3**: Script Validation (7 hours) - Partial
  - Implement dry-run mode (2 hours)
  - Defer shellcheck integration to v0.3.0

**Total v0.2.0 Effort**: ~11 hours

### v0.3.0 (Future Release)
**Focus**: Advanced features

- **Phase 2**: Advanced Configuration (8 hours)
- **Phase 3**: Script Validation - Complete (5 hours remaining)
- **Phase 4**: Template System (6 hours)

**Total v0.3.0 Effort**: ~19 hours

### v0.4.0+ (Future)
**Focus**: Platform expansion

- **Phase 5**: PowerShell Support (6 hours)
- Additional platform support (Fish, Nushell, Make)

---

## Success Criteria

### For v0.2.0

1. ✅ Users can run `tkgen bootstrap` to generate scripts
2. ✅ Users can regenerate scripts with `--force`
3. ✅ Users can preview scripts with `--dry-run`
4. ✅ CLI overrides work for toolchain and build type
5. ✅ Test coverage >90%
6. ✅ Documentation complete with examples

### For v0.3.0

1. Users can specify custom CMake arguments
2. Users can add environment variables to scripts
3. Users can add pre/post hooks
4. Users can validate scripts with shellcheck
5. Users can use custom templates

---

## Technical Specifications

### CLI Command Signature

```bash
tkgen bootstrap [OPTIONS]

OPTIONS:
  --force              Overwrite existing bootstrap scripts
  --dry-run            Preview scripts without creating files
  --platform PLATFORM  Platform to generate for (unix|windows|all) [default: all]
  --toolchain NAME     Override toolchain from config
  --build-type TYPE    Override build type (Debug|Release|RelWithDebInfo|MinSizeRel)
  --config PATH        Path to toolchainkit.yaml [default: ./toolchainkit.yaml]
  --project-root PATH  Project root directory [default: current directory]
  -v, --verbose        Enable verbose output
  -q, --quiet          Enable quiet mode

EXAMPLES:
  # Generate all bootstrap scripts
  tkgen bootstrap

  # Regenerate with different toolchain
  tkgen bootstrap --force --toolchain gcc-14

  # Preview scripts without creating
  tkgen bootstrap --dry-run

  # Generate only Unix script
  tkgen bootstrap --platform unix
```

### Configuration Schema Extension

```yaml
# toolchainkit.yaml
bootstrap:
  # Basic configuration (already supported)
  toolchain: llvm-18
  build_type: Release
  build_dir: build
  package_manager: conan

  # Advanced configuration (Phase 2)
  cmake_args:
    - "-DENABLE_TESTS=ON"
    - "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"

  env:
    CC: /usr/bin/clang
    CXX: /usr/bin/clang++
    MAKEFLAGS: "-j8"

  hooks:
    pre_configure: scripts/pre_configure.sh
    post_configure: scripts/post_configure.sh

  # Multiple builds (Phase 2)
  builds:
    - name: debug
      build_type: Debug
      build_dir: build-debug
    - name: release
      build_type: Release
      build_dir: build-release

  # Template customization (Phase 4)
  template_dir: ./custom_templates
```

---

## Testing Strategy

### Unit Tests

```python
# tests/cli/test_bootstrap.py

class TestBootstrapCommand:
    """Test bootstrap CLI command."""

    def test_bootstrap_command_exists(self):
        """Test bootstrap command is registered."""

    def test_bootstrap_generates_scripts(self, tmp_project):
        """Test basic script generation."""

    def test_bootstrap_requires_initialization(self, tmp_path):
        """Test error when project not initialized."""

    def test_bootstrap_respects_existing_scripts(self, tmp_project):
        """Test doesn't overwrite without --force."""

    def test_bootstrap_force_overwrites(self, tmp_project):
        """Test --force overwrites existing scripts."""

    def test_bootstrap_dry_run(self, tmp_project):
        """Test --dry-run doesn't create files."""

    def test_bootstrap_platform_selection(self, tmp_project):
        """Test --platform filters scripts."""

    def test_bootstrap_cli_overrides(self, tmp_project):
        """Test CLI args override config."""

    def test_bootstrap_verbose_output(self, tmp_project):
        """Test --verbose shows detailed output."""

class TestAdvancedConfiguration:
    """Test advanced configuration options."""

    def test_cmake_args_in_script(self, tmp_project):
        """Test cmake_args appear in generated script."""

    def test_environment_variables(self, tmp_project):
        """Test env vars set in script."""

    def test_hooks_integration(self, tmp_project):
        """Test pre/post hooks called."""

class TestScriptValidation:
    """Test script validation."""

    def test_dry_run_shows_content(self, tmp_project):
        """Test dry-run displays script content."""

    def test_shellcheck_integration(self, tmp_project):
        """Test shellcheck validation if available."""
```

### Integration Tests

```python
# tests/integration/test_bootstrap_workflow.py

def test_full_bootstrap_workflow(tmp_path):
    """Test complete bootstrap workflow."""
    # 1. Initialize project
    # 2. Generate bootstrap scripts
    # 3. Execute bootstrap.sh (in container)
    # 4. Verify toolchain configured
    # 5. Verify CMake ran successfully

def test_bootstrap_with_conan(tmp_path):
    """Test bootstrap with Conan package manager."""

def test_bootstrap_with_vcpkg(tmp_path):
    """Test bootstrap with vcpkg package manager."""

def test_bootstrap_regeneration(tmp_path):
    """Test regenerating scripts updates toolchain."""
```

---

## Documentation Updates

### 1. Update `docs/bootstrap.md`

Add CLI command section:

```markdown
## CLI Command

Generate or regenerate bootstrap scripts for your project:

\`\`\`bash
# Generate bootstrap scripts
tkgen bootstrap

# Regenerate with different toolchain
tkgen bootstrap --force --toolchain gcc-14

# Preview without creating files
tkgen bootstrap --dry-run

# Generate only for specific platform
tkgen bootstrap --platform unix
\`\`\`

### Command Options

- `--force`: Overwrite existing scripts
- `--dry-run`: Preview without creating files
- `--platform`: Choose platform (unix, windows, all)
- `--toolchain`: Override toolchain
- `--build-type`: Override build type
```

### 2. Update `docs/cli.md`

Add bootstrap command documentation with full reference.

### 3. Update `README.md`

Add bootstrap to quick start:

```markdown
## Quick Start

\`\`\`bash
# Initialize new project
tkgen init --toolchain llvm-18

# Generate bootstrap scripts
tkgen bootstrap

# Run bootstrap
./bootstrap.sh  # Linux/macOS
bootstrap.bat   # Windows
\`\`\`
```

---

## Migration Path

### For Existing Users

No breaking changes. Existing functionality through Python API remains identical:

```python
# This still works in v0.2.0+
from toolchainkit.bootstrap import BootstrapGenerator

generator = BootstrapGenerator(project_root, config)
generator.generate_all()
```

New CLI command is additive:

```bash
# New in v0.2.0
tkgen bootstrap
```

### Deprecation Strategy

No deprecations planned. All existing APIs remain stable.

---

## Risk Assessment

### Low Risk Items
- ✅ CLI command addition (standard pattern)
- ✅ Dry-run mode (read-only)
- ✅ Documentation updates

### Medium Risk Items
- ⚠️ Template system (new dependency: Jinja2)
- ⚠️ Shellcheck integration (external tool dependency)
- ⚠️ Hook system (security consideration for executing user scripts)

### Mitigation Strategies

1. **Template System**: Make Jinja2 optional, fall back to f-strings
2. **Shellcheck**: Make optional, skip if not installed
3. **Hooks**: Validate hook paths, warn about security, use sandboxing if possible

---

## Dependencies

### New Dependencies (Optional)

```toml
# pyproject.toml

[project.optional-dependencies]
bootstrap-templates = [
    "jinja2>=3.1.0",
]
validation = [
    "shellcheck-py>=0.9.0",  # Python wrapper for shellcheck
]
```

### Development Dependencies

No new development dependencies required.

---

## Conclusion

The Bootstrap Script Generation feature is **mostly complete** in v0.1.0. The core `BootstrapGenerator` class is fully functional, well-tested, and documented.

**The main gap is the standalone CLI command**, which is critical for usability and consistency with other ToolchainKit commands.

**Recommended Priority**:
1. 🔴 **High Priority**: Phase 1 (CLI Command) - Essential for v0.2.0
2. 🟡 **Medium Priority**: Phase 2 (Advanced Config) + Phase 3 (Validation) - Nice to have for v0.3.0
3. 🟢 **Low Priority**: Phase 4 (Templates) + Phase 5 (PowerShell) - Future enhancements

**Total Implementation Effort**:
- **v0.2.0** (Must-Have): ~11 hours
- **v0.3.0** (Nice-to-Have): ~19 hours
- **v0.4.0+** (Future): ~6+ hours

The feature can be considered **production-ready for v0.2.0** once the CLI command is added.
