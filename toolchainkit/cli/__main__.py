"""
Entry point for running ToolchainKit CLI as a module.

Usage: python -m toolchainkit.cli [command] [options]
"""

from .parser import main

if __name__ == "__main__":
    main()
