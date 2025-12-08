"""
Compiler strategies package.

Standard compiler strategies (Clang, GCC, MSVC) are available but not
auto-registered. They should be registered explicitly through the plugin
system or by the application at startup.
"""

from toolchainkit.toolchain.strategies.standard import (
    ClangStrategy,
    GccStrategy,
    MsvcStrategy,
)

__all__ = ["ClangStrategy", "GccStrategy", "MsvcStrategy"]
