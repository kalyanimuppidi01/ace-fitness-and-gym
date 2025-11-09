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

def test_load_v1_2_3():
    _mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.3.py"
    assert p.exists()
    gd = runpy.run_path(str(p), run_name="loaded_v1_2_3")
    # smoke validate
    assert "FitnessTrackerApp" in gd.keys() or any(n.lower().startswith("add") for n in gd.keys())
