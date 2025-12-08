"""
Bootstrap script generator.

Generates platform-specific bootstrap scripts (bootstrap.sh, bootstrap.bat)
for automating project setup.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BootstrapGeneratorError(Exception):
    """Base exception for bootstrap generator errors."""

    pass


class BootstrapGenerator:
    """
    Generate platform-specific bootstrap scripts.

    Creates bootstrap.sh for Unix (Linux/macOS) and bootstrap.bat for Windows
    that automate project setup including:
    - Python availability check
    - ToolchainKit installation
    - Toolchain configuration
    - Dependency installation
    - CMake configuration
    """

    def __init__(self, project_root: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize bootstrap generator.

        Args:
            project_root: Project root directory
            config: Project configuration dict with keys:
                   - toolchain: Toolchain name (e.g., 'llvm-18')
                   - build_type: Build type (e.g., 'Release')
                   - build_dir: Build directory name (default: 'build')
                   - package_manager: Package manager name or None
                   - cmake_args: List of additional CMake arguments
                   - env: Dictionary of environment variables to set
                   - hooks: Dictionary of hook scripts (pre_configure, post_configure)
        """
        self.project_root = Path(project_root)
        self.config = config or {}

        # Extract configuration with defaults
        self.project_name = self.project_root.name
        self.toolchain = self.config.get("toolchain", "llvm-18")
        self.build_type = self.config.get("build_type", "Release")
        self.build_dir = self.config.get("build_dir", "build")
        self.package_manager = self.config.get("package_manager")
        self.config_file = self.config.get(
            "config_file"
        )  # Path to config file (optional)

        # Phase 2: Advanced configuration
        self.cmake_args = self.config.get("cmake_args", [])
        self.env_vars = self.config.get("env_vars", {}) or self.config.get("env", {})
        self.hooks = self.config.get("hooks", {})

        # Jinja2 template system
        self.template_dir = self.config.get("template_dir")
        self._jinja_env = self._init_jinja2()

    def _init_jinja2(self):
        """
        Initialize Jinja2 template environment.

        Returns:
            Jinja2 Environment instance

        Raises:
            BootstrapGeneratorError: If templates cannot be initialized
        """
        from jinja2 import Environment, FileSystemLoader

        # Determine template directory
        if self.template_dir:
            template_dir = Path(self.template_dir)
        else:
            # Use built-in templates
            template_dir = Path(__file__).parent / "templates"

        if not template_dir.exists():
            raise BootstrapGeneratorError(
                f"Template directory not found: {template_dir}"
            )

        # Create Jinja2 environment
        jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.debug(f"Jinja2 templates initialized from: {template_dir}")
        return jinja_env

    def _render_template(self, template_name: str) -> str:
        """
        Render a Jinja2 template.

        Args:
            template_name: Name of template file

        Returns:
            Rendered template content

        Raises:
            BootstrapGeneratorError: If template rendering fails
        """
        try:
            template = self._jinja_env.get_template(template_name)
            context = {
                "project_name": self.project_name,
                "toolchain": self.toolchain,
                "build_type": self.build_type,
                "build_dir": self.build_dir,
                "package_manager": self.package_manager,
                "config_file": self.config_file,
                "cmake_args": self.cmake_args,
                "env_vars": self.env_vars,
                "hooks": self.hooks,
            }
            return template.render(**context)
        except Exception as e:
            raise BootstrapGeneratorError(
                f"Failed to render template {template_name}: {e}"
            ) from e

    def generate_all(self) -> Dict[str, Path]:
        """
        Generate all bootstrap scripts.

        Returns:
            Dictionary with script paths: {'shell': Path, 'batch': Path, 'powershell': Path}

        Raises:
            BootstrapGeneratorError: If generation fails
        """
        try:
            shell_script = self.generate_shell_script()
            batch_script = self.generate_batch_script()
            powershell_script = self.generate_powershell_script()

            return {
                "shell": shell_script,
                "batch": batch_script,
                "powershell": powershell_script,
            }
        except Exception as e:
            raise BootstrapGeneratorError(
                f"Failed to generate bootstrap scripts: {e}"
            ) from e

    def generate_shell_script(self) -> Path:
        """
        Generate bootstrap.sh for Unix systems (Linux/macOS).

        Returns:
            Path to generated script

        Raises:
            BootstrapGeneratorError: If generation fails
        """
        script_content = self._generate_shell_content()
        script_path = self.project_root / "bootstrap.sh"

        try:
            # Write script
            script_path.write_text(script_content, encoding="utf-8")

            # Make executable (Unix only)
            try:
                script_path.chmod(0o755)
                logger.debug(f"Made script executable: {script_path}")
            except Exception as e:
                logger.warning(f"Could not make script executable: {e}")

            logger.info(f"Generated shell script: {script_path}")
            return script_path

        except Exception as e:
            raise BootstrapGeneratorError(f"Failed to write shell script: {e}") from e

    def generate_batch_script(self) -> Path:
        """
        Generate bootstrap.bat for Windows.

        Returns:
            Path to generated script

        Raises:
            BootstrapGeneratorError: If generation fails
        """
        script_content = self._generate_batch_content()
        script_path = self.project_root / "bootstrap.bat"

        try:
            # Write script with Windows line endings
            # Python 3.9 doesn't support newline parameter in write_text, so use open()
            with open(script_path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(script_content)

            logger.info(f"Generated batch script: {script_path}")
            return script_path

        except Exception as e:
            raise BootstrapGeneratorError(f"Failed to write batch script: {e}") from e

    def generate_powershell_script(self) -> Path:
        """
        Generate bootstrap.ps1 for Windows PowerShell.

        Returns:
            Path to generated script

        Raises:
            BootstrapGeneratorError: If generation fails
        """
        script_content = self._generate_powershell_content()
        script_path = self.project_root / "bootstrap.ps1"

        try:
            # Write script
            script_path.write_text(script_content, encoding="utf-8")

            logger.info(f"Generated PowerShell script: {script_path}")
            return script_path

        except Exception as e:
            raise BootstrapGeneratorError(
                f"Failed to write PowerShell script: {e}"
            ) from e

    def preview_scripts(self) -> Dict[str, str]:
        """
        Generate script content without writing files.

        Returns:
            Dictionary with script content: {'shell': str, 'batch': str, 'powershell': str}

        Example:
            >>> generator = BootstrapGenerator(project_root, config)
            >>> scripts = generator.preview_scripts()
            >>> print(scripts['shell'])
        """
        return {
            "shell": self._generate_shell_content(),
            "batch": self._generate_batch_content(),
            "powershell": self._generate_powershell_content(),
        }

    def generate_readme_section(self) -> str:
        """
        Generate README section explaining bootstrap process.

        Returns:
            Markdown text for README
        """
        toolchain_note = ""
        if self.toolchain and (
            "llvm" in self.toolchain.lower() or "clang" in self.toolchain.lower()
        ):
            toolchain_note = f"""
**Note:** This project uses `{self.toolchain}`. Make sure LLVM/Clang is installed and available in your PATH:
- **Linux:** `sudo apt install clang-18` (or appropriate package manager)
- **macOS:** `brew install llvm@18`
- **Windows:** Download from [LLVM Releases](https://github.com/llvm/llvm-project/releases)

If the toolchain is not available, the bootstrap script will fall back to the system default compiler.
"""

        return f"""## Getting Started
{toolchain_note}
To set up the development environment:

**Linux/macOS:**
```bash
./bootstrap.sh
```

**Windows:**
```batch
bootstrap.bat
```

This will:
1. Check Python 3 is installed
2. Install ToolchainKit if not already installed
3. Download and configure the {self.toolchain} toolchain
4. Install project dependencies{' ('+self.package_manager+')' if self.package_manager else ''}
5. Configure CMake

Then build with:
```bash
cmake --build {self.build_dir} --config {self.build_type}
```
"""

    def validate_shell_script(self, script_path: Path) -> tuple[bool, list[str]]:
        """
        Validate shell script using shellcheck and bash -n.

        Args:
            script_path: Path to shell script

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        import shutil
        import subprocess

        errors = []

        # Check if bash is available for syntax checking
        if shutil.which("bash"):
            try:
                result = subprocess.run(
                    ["bash", "-n", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"Bash syntax error: {result.stderr.strip()}")
                else:
                    logger.debug(f"Bash syntax check passed: {script_path}")
            except subprocess.TimeoutExpired:
                errors.append("Bash syntax check timed out")
            except Exception as e:
                logger.warning(f"Could not run bash syntax check: {e}")
        else:
            logger.debug("bash not found, skipping syntax check")

        # Check if shellcheck is available
        if shutil.which("shellcheck"):
            try:
                result = subprocess.run(
                    ["shellcheck", "--severity=warning", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    errors.append(f"Shellcheck warnings:\n{result.stdout.strip()}")
                else:
                    logger.debug(f"Shellcheck passed: {script_path}")
            except subprocess.TimeoutExpired:
                errors.append("Shellcheck timed out")
            except Exception as e:
                logger.warning(f"Could not run shellcheck: {e}")
        else:
            logger.debug("shellcheck not found, skipping validation")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_batch_script(self, script_path: Path) -> tuple[bool, list[str]]:
        """
        Validate batch script syntax (basic validation).

        Args:
            script_path: Path to batch script

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Basic validation: check if file is readable and valid text
        try:
            _ = script_path.read_text(encoding="utf-8")
            # Basic validation passed
            logger.debug(f"Basic batch validation passed: {script_path}")

        except Exception as e:
            errors.append(f"Could not read batch script: {e}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_powershell_script(self, script_path: Path) -> tuple[bool, list[str]]:
        """
        Validate PowerShell script syntax.

        Args:
            script_path: Path to PowerShell script

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        import shutil
        import subprocess

        errors = []

        # Check if PowerShell is available
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            try:
                # Use PowerShell's built-in syntax checking
                result = subprocess.run(
                    [
                        powershell,
                        "-NoProfile",
                        "-Command",
                        f"$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content '{script_path}' -Raw), [ref]$null)",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    errors.append(f"PowerShell syntax error: {result.stderr.strip()}")
                else:
                    logger.debug(f"PowerShell syntax check passed: {script_path}")
            except subprocess.TimeoutExpired:
                errors.append("PowerShell syntax check timed out")
            except Exception as e:
                logger.warning(f"Could not run PowerShell syntax check: {e}")
        else:
            logger.debug("PowerShell not found, skipping validation")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _generate_shell_content(self) -> str:
        """Generate shell script content using Jinja2 template."""
        return self._render_template("bootstrap.sh.j2")

    def _generate_batch_content(self) -> str:
        """Generate batch script content using Jinja2 template."""
        return self._render_template("bootstrap.bat.j2")

    def _generate_powershell_content(self) -> str:
        """Generate PowerShell script content using Jinja2 template."""
        return self._render_template("bootstrap.ps1.j2")
