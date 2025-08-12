"""
Test/import safety shim to ensure local src/ takes precedence over any installed package.
Python automatically imports sitecustomize if present on sys.path.
This guarantees we use the workspace code even if an older openchronicle is installed.
"""
from __future__ import annotations

import os
import sys
import shutil
import importlib
import importlib.abc
import importlib.util

# Compute absolute path to the workspace src directory
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")

# Disable bytecode writes globally to avoid stale caches across rapid edits
try:
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
except Exception:
    pass

# Prepend local src to sys.path to ensure it wins import resolution
if os.path.isdir(SRC) and (len(sys.path) == 0 or sys.path[0] != SRC):
    try:
        sys.path.insert(0, SRC)
    except Exception:
        # Best-effort; never crash import due to path manipulation
        pass

# Proactively purge __pycache__ and .pyc under the workspace root and src
def _purge_py_caches(root: str) -> None:
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == "__pycache__":
                shutil.rmtree(dirpath, ignore_errors=True)
                # skip descending into removed dir
                continue
            for fn in filenames:
                if fn.endswith(".pyc"):
                    try:
                        os.remove(os.path.join(dirpath, fn))
                    except Exception:
                        pass
    except Exception:
        pass

try:
    _purge_py_caches(ROOT)
    _purge_py_caches(SRC)
except Exception:
    pass

# Proactively purge any preloaded 'openchronicle' modules that are not from our workspace src
try:
    normalized_src = os.path.normcase(os.path.abspath(SRC)) + os.sep
    to_purge = []
    for name, mod in list(sys.modules.items()):
        if not name.startswith("openchronicle"):
            continue
        mod_file = getattr(mod, "__file__", None)
        if not mod_file:
            continue
        mod_path = os.path.normcase(os.path.abspath(mod_file))
        if not mod_path.startswith(normalized_src):
            to_purge.append(name)
    for name in to_purge:
        sys.modules.pop(name, None)
except Exception:
    # Never fail import startup due to hygiene cleanup
    pass

# Enforce that all 'openchronicle' imports resolve from the workspace src only.
try:
    class _SrcOnlyLoader(importlib.abc.Loader):
        def create_module(self, spec):  # type: ignore[override]
            return None

        def exec_module(self, module):  # type: ignore[override]
            # This loader is only used to error if a module isn't in SRC.
            raise ImportError(
                f"Module {module.__name__} not found in workspace src; refusing to load external package"
            )

    class _OpenChronicleSrcOnlyFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):  # type: ignore[override]
            if not fullname.startswith("openchronicle"):
                return None
            # Always constrain search to SRC for openchronicle
            spec = importlib.machinery.PathFinder.find_spec(fullname, [SRC])
            if spec is not None:
                return spec
            # If not found in src, block fallback to installed copies
            return importlib.machinery.ModuleSpec(fullname, _SrcOnlyLoader(), origin="sitecustomize:src-only")

    # Prepend so it runs before default PathFinder
    if not any(isinstance(f, _OpenChronicleSrcOnlyFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _OpenChronicleSrcOnlyFinder())
except Exception:
    # Best-effort; avoid breaking startup
    pass
