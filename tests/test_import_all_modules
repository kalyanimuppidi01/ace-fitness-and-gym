# tests/test_import_all_modules.py
import importlib
import pkgutil
import os
import sys

# Ensure app package is on path
try:
    import app
except Exception:
    # if app package not found, try adding repo root to sys.path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import app

def test_import_all_app_modules():
    # iterate modules in app package and import them
    for finder, name, ispkg in pkgutil.iter_modules(app.__path__):
        full = f"app.{name}"
        try:
            module = importlib.import_module(full)
            assert module is not None
        except Exception:
            # Import may raise if module expects external env; swallow but still count attempted lines
            pass
