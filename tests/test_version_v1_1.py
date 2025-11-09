import runpy, sys, pathlib, types
import builtins
import pytest
from unittest import mock

def _inject_basic_mocks():
    # Minimal tkinter mock so imports succeed in CI
    mock_tk = mock.MagicMock()
    mock_tk.Tk = mock.MagicMock()
    mock_tk.Entry = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Label = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Button = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.END = "end"
    sys.modules['tkinter'] = mock_tk
    sys.modules['tkinter.messagebox'] = mock.MagicMock()
    # common optional libs
    sys.modules['matplotlib'] = mock.MagicMock()
    sys.modules['matplotlib.figure'] = mock.MagicMock()
    sys.modules['reportlab'] = mock.MagicMock()
    sys.modules['reportlab.pdfgen'] = mock.MagicMock()

def test_load_v1_1():
    _inject_basic_mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.1.py"
    assert p.exists(), f"expected file {p} to exist"
    gd = runpy.run_path(str(p), run_name="loaded_v1_1")
    # check for a class or functions commonly present
    assert any(name for name in gd if name.lower().startswith("fitness") or name.lower().startswith("add_workout")), "module did not expose expected symbols"
