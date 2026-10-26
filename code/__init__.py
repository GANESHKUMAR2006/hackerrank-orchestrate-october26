"""Ghost Data Still Exists package root.

Bridges standard library 'code' module attributes so tools like pdb, pytest,
and inspect that import stdlib 'code' continue to function seamlessly.
"""

import importlib.machinery
import importlib.util
import os
import sys

# Bridge stdlib code attributes to prevent shadowing collisions with pdb/pytest
for p in sys.path:
    target = os.path.join(p, "code.py")
    if os.path.exists(target) and "site-packages" not in p.lower():
        try:
            loader = importlib.machinery.SourceFileLoader("_stdlib_code", target)
            spec = importlib.util.spec_from_loader("_stdlib_code", loader)
            if spec and loader:
                mod = importlib.util.module_from_spec(spec)
                loader.exec_module(mod)
                for attr in dir(mod):
                    if not attr.startswith("__"):
                        globals()[attr] = getattr(mod, attr)
                break
        except Exception:
            pass
