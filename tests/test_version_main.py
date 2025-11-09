# tests/test_version_main.py
import runpy, sys, pathlib
from unittest import mock

def _mocks():
    m = mock.MagicMock()

    # A small Entry-like object compatible with code that calls grid/pack/place/config
    class SimpleEntry:
        def __init__(self):
            self._v = ""
        def get(self):
            return self._v
        def delete(self, a, b=None):
            # support delete(0, tk.END) or delete(0, 1)
            self._v = ""
        def insert(self, i, v):
            self._v = v
        # UI layout stubs (no-op)
        def grid(self, *a, **k): return None
        def pack(self, *a, **k): return None
        def place(self, *a, **k): return None
        def config(self, *a, **k): return None
        def __repr__(self):
            return f"<SimpleEntry val={self._v!r}>"

    # Provide minimal API for tkinter used by the app
    m.Tk = mock.MagicMock()
    m.Entry = lambda *a, **k: SimpleEntry()
    m.Label = mock.MagicMock(return_value=mock.MagicMock())
    m.Button = mock.MagicMock(return_value=mock.MagicMock())
    m.END = "end"
    sys.modules['tkinter'] = m
    sys.modules['tkinter.messagebox'] = mock.MagicMock()

    # Mock optional heavy libs to prevent import failures
    sys.modules['matplotlib'] = mock.MagicMock()
    sys.modules['reportlab'] = mock.MagicMock()

def test_load_main_version():
    # Inject mocks before importing/running the module
    _mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness.py"
    assert p.exists(), f"expected file {p} to exist"
    # Run module as a non-main module so its if __name__ == "__main__" won't execute
    gd = runpy.run_path(str(p), run_name="loaded_main")
    # Expect a main app class or functions
    assert any(k for k in gd.keys() if "Fitness" in k or "add_workout" in k.lower())
    # if FitnessTrackerApp present, instantiate (no GUI will show)
    if "FitnessTrackerApp" in gd:
        cls = gd["FitnessTrackerApp"]
        # call constructor with a mock master (no real window)
        cls(mock.MagicMock())
