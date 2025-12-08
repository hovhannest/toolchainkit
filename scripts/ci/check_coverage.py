"""
Check code coverage and enforce thresholds.

Usage:
    python scripts/ci/check_coverage.py [threshold]

Example:
    python scripts/ci/check_coverage.py 80.0
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def check_coverage(coverage_file: Path, threshold: float = 80.0) -> bool:
    """
    Check if coverage meets threshold.

    Args:
        coverage_file: Path to coverage.xml
        threshold: Minimum coverage percentage required

    Returns:
        True if coverage meets threshold
    """
    if not coverage_file.exists():
        print(f"ERROR: Coverage file not found: {coverage_file}")
        return False

    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()

        # Get overall coverage (line-rate is a fraction 0.0-1.0)
        line_rate = float(root.attrib.get("line-rate", 0))
        coverage = line_rate * 100

        print(f"Code coverage: {coverage:.2f}%")
        print(f"Required threshold: {threshold:.2f}%")

        if coverage < threshold:
            print(
                f"ERROR: Coverage {coverage:.2f}% is below threshold {threshold:.2f}%"
            )
            return False

        print("✓ Coverage meets threshold")
        return True

    except ET.ParseError as e:
        print(f"ERROR: Failed to parse coverage file: {e}")
        return False
    except (KeyError, ValueError) as e:
        print(f"ERROR: Invalid coverage data: {e}")
        return False


def main():
    """Main entry point."""
    coverage_file = Path("coverage.xml")
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 80.0

    success = check_coverage(coverage_file, threshold)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
