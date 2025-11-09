import runpy, sys, pathlib
from unittest import mock

def _inject_basic_mocks():
    mock_tk = mock.MagicMock()
    mock_tk.Tk = mock.MagicMock()
    mock_tk.Entry = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Label = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.Button = mock.MagicMock(return_value=mock.MagicMock())
    mock_tk.END = "end"
    sys.modules['tkinter'] = mock_tk
    sys.modules['tkinter.messagebox'] = mock.MagicMock()
    sys.modules['matplotlib'] = mock.MagicMock()
    sys.modules['reportlab'] = mock.MagicMock()

def test_load_v1_2():
    _inject_basic_mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.py"
    assert p.exists()
    gd = runpy.run_path(str(p), run_name="loaded_v1_2")
    # sanity checks
    assert isinstance(gd, dict)
    # expect either a class or some module-level helpers
    assert any(k for k in gd.keys() if "Fitness" in k or "add_workout" in k.lower() or "view_workouts" in k.lower())
