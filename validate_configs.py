import sys
from pathlib import Path
from toolchainkit.config.parser import load_config
from toolchainkit.config.validation import validate_config


def validate_all():
    base_path = Path("examples/01-new-project")
    config_files = sorted(base_path.glob("toolchainkit_*.yaml"))

    if not config_files:
        print("No configuration files found!")
        sys.exit(1)

    print(f"Found {len(config_files)} configuration files.")

    has_errors = False
    for config_file in config_files:
        try:
            # Note: load_config might not be available directly if not in python path
            # But we are running from root so it should be fine if we set PYTHONPATH
            config = load_config(config_file)
            issues = validate_config(config)

            errors = [i for i in issues if i.level == "error"]
            if errors:
                print(f"❌ {config_file.name}: {len(errors)} errors")
                for error in errors:
                    print(f"  - {error.message}")
                has_errors = True
            else:
                print(f"✅ {config_file.name}")

        except Exception as e:
            print(f"❌ {config_file.name}: Exception during validation: {e}")
            has_errors = True

    if has_errors:
        sys.exit(1)
    else:
        print("\nAll configurations valid!")


if __name__ == "__main__":
    validate_all()
