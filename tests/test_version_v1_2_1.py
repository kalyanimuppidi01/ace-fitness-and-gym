import runpy, sys, pathlib
from unittest import mock

def _mocks():
    mock_tk = mock.MagicMock()
    mock_tk.Tk = mock.MagicMock()
    mock_tk.Entry = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Label = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Button = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.END = "end"
    sys.modules['tkinter'] = mock_tk
    sys.modules['tkinter.messagebox'] = mock.MagicMock()
    sys.modules['matplotlib'] = mock.MagicMock()

def test_load_v1_2_1():
    _mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.1.py"
    assert p.exists()
    gd = runpy.run_path(str(p), run_name="loaded_v1_2_1")
    # assert that the module executed and exposed something
    assert len(gd) > 0
    # at least one of these names should be present in typical versions
    assert any(name.lower().startswith("fitness") or name.lower().startswith("add") for name in gd.keys())
