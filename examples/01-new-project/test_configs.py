import argparse
import glob
import os
import platform
import subprocess
import re


def main():
    parser = argparse.ArgumentParser(description="Test toolchainkit configurations.")
    parser.add_argument(
        "--path", default=".", help="Path to the directory containing .yaml files"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show bootstrap script output in real-time",
    )
    args = parser.parse_args()

    search_path = os.path.join(args.path, "*.yaml")
    yaml_files = glob.glob(search_path)

    if not yaml_files:
        print(f"No .yaml files found in {args.path}")
        return

    print(f"Found {len(yaml_files)} yaml files in {args.path}")

    results = []

    for yaml_file in yaml_files:
        print(f"\n--- Processing {yaml_file} ---")

        # 1. Run toolchainkit bootstrap --force
        cmd = ["toolchainkit", "--config", yaml_file, "bootstrap", "--force"]
        print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            print(
                "Error: 'toolchainkit' command not found. Ensure it is installed and in your PATH."
            )
            return

        # 2. Check for "Use one of the supported compilers"
        if (
            "Use one of the supported compilers" in result.stdout
            or "Use one of the supported compilers" in result.stderr
        ):
            print(f"Skipping {yaml_file}: Unsupported compiler detected.")
            results.append((yaml_file, "SKIPPED", "Unsupported compiler"))
            continue

        if result.returncode != 0:
            print(f"Error running bootstrap for {yaml_file}:")
            print(result.stdout)
            print(result.stderr)
            results.append((yaml_file, "FAILED", "Bootstrap command failed"))
            continue

        print("Bootstrap successful.")

        # 3. Determine bootstrap script to run
        system_platform = platform.system()
        bootstrap_script = None

        # Look for bootstrap script in the current working directory
        current_dir = os.getcwd()

        if system_platform == "Windows":
            # Prefer ps1, then bat
            if os.path.exists(os.path.join(current_dir, "bootstrap.ps1")):
                bootstrap_script = [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    os.path.join(current_dir, "bootstrap.ps1"),
                ]
            elif os.path.exists(os.path.join(current_dir, "bootstrap.bat")):
                bootstrap_script = [os.path.join(current_dir, "bootstrap.bat")]
        else:
            if os.path.exists(os.path.join(current_dir, "bootstrap.sh")):
                bootstrap_script = ["bash", os.path.join(current_dir, "bootstrap.sh")]

        if not bootstrap_script:
            print("Error: No suitable bootstrap script found in current directory.")
            results.append((yaml_file, "FAILED", "No bootstrap script found"))
            continue

        print(f"Running bootstrap script: {' '.join(bootstrap_script)}")

        # 4. Run bootstrap script and capture output
        try:
            # Run in the current directory
            if args.verbose:
                # Show output in real-time - don't capture stdout/stderr
                print(f"\n{'='*60}")
                print("BOOTSTRAP SCRIPT OUTPUT:")
                print(f"{'='*60}")
                bs_result = subprocess.run(
                    bootstrap_script, cwd=current_dir, check=False, text=True
                )
                print(f"{'='*60}\n")
                # Run again to capture output for parsing build command
                bs_result_capture = subprocess.run(
                    bootstrap_script,
                    capture_output=True,
                    text=True,
                    cwd=current_dir,
                    check=False,
                )
                output = bs_result_capture.stdout
            else:
                # Capture output silently
                bs_result = subprocess.run(
                    bootstrap_script,
                    capture_output=True,
                    text=True,
                    cwd=current_dir,
                    check=False,
                )
                output = bs_result.stdout
        except Exception as e:
            print(f"Failed to execute bootstrap script: {e}")
            results.append((yaml_file, "FAILED", f"Bootstrap execution exception: {e}"))
            continue

        if bs_result.returncode != 0:
            print(f"Bootstrap script failed for {yaml_file}:")
            print(bs_result.stdout)
            print(bs_result.stderr)
            results.append((yaml_file, "FAILED", "Bootstrap script failed"))
            continue

        print("Bootstrap script executed successfully.")

        # 5. Find build command in output
        # Look for "To build the project:\n  <command>"
        # The prompt says:
        # To build the project:
        #   cmake --build build --config Release

        match = re.search(r"To build the project:\s+([^\r\n]+)", output)

        if match:
            build_cmd_str = match.group(1).strip()
            print(f"Found build command: {build_cmd_str}")

            # 6. Run the build command
            print(f"Executing build command: {build_cmd_str}")
            try:
                if args.verbose:
                    # Show build output in real-time
                    print(f"\n{'='*60}")
                    print("BUILD OUTPUT:")
                    print(f"{'='*60}")
                    build_result = subprocess.run(
                        build_cmd_str, shell=True, cwd=current_dir, check=False
                    )
                    print(f"{'='*60}\n")
                else:
                    # Capture build output silently
                    build_result = subprocess.run(
                        build_cmd_str,
                        shell=True,
                        cwd=current_dir,
                        check=False,
                        capture_output=True,
                    )
                if build_result.returncode == 0:
                    print(f"Build successful for {yaml_file}")
                    results.append((yaml_file, "PASSED", "Build successful"))
                else:
                    print(f"Build failed for {yaml_file}")
                    results.append((yaml_file, "FAILED", "Build command failed"))
            except Exception as e:
                print(f"Failed to execute build command: {e}")
                results.append((yaml_file, "FAILED", f"Build execution exception: {e}"))

        else:
            print("Could not find build command in bootstrap script output.")
            print("Output was:")
            print(output)
            results.append((yaml_file, "FAILED", "Build command not found"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'File':<40} | {'Result':<10} | {'Message'}")
    print("-" * 80)
    for filename, status, message in results:
        # Use relative path for cleaner output
        rel_filename = os.path.basename(filename)
        print(f"{rel_filename:<40} | {status:<10} | {message}")
    print("-" * 80)

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    skipped = sum(1 for _, status, _ in results if status == "SKIPPED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")

    print(
        f"Total: {len(results)}, Passed: {passed}, Skipped: {skipped}, Failed: {failed}"
    )


if __name__ == "__main__":
    main()
