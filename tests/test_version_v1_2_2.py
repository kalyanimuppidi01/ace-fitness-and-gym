import runpy, sys, pathlib
from unittest import mock

def _mocks():
    m = mock.MagicMock()
    m.Tk = mock.MagicMock()
    m.Entry = mock.MagicMock(return_value=mock.MagicMock())
    m.Label = mock.MagicMock(return_value=mock.MagicMock())
    m.Button = mock.MagicMock(return_value=mock.MagicMock())
    m.END = "end"
    sys.modules['tkinter'] = m
    sys.modules['tkinter.messagebox'] = mock.MagicMock()
    sys.modules['matplotlib'] = mock.MagicMock()

def test_load_v1_2_2():
    _mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.2.py"
    assert p.exists()
    gd = runpy.run_path(str(p), run_name="loaded_v1_2_2")
    assert isinstance(gd, dict)
    assert any(k for k in gd.keys() if "Fitness" in k or "workout" in k.lower())
