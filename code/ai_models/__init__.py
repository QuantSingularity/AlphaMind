"""
AlphaMind AI Models package.

Heavy dependencies (torch, tensorflow, gym/gymnasium, pymc) are imported
lazily so that lightweight backend deployments do not fail on startup
if a full ML environment is not installed.
"""

from __future__ import annotations

__version__ = "1.0.0"

# Lazy-import helpers — avoids ImportError in environments that install
# only the inference subset of requirements.


def _optional(module: str):
    """Return the module if available, else None — never raises."""
    try:
        import importlib

        return importlib.import_module(module)
    except ImportError:
        return None


# Expose sub-packages (import errors surface only when the sub-package is used)

try:
    pass
except ImportError:
    pass

try:
    pass
except ImportError:
    pass

try:
    pass
except ImportError:
    pass

try:
    pass
except ImportError:
    pass
