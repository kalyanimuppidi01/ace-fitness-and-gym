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
    # other libs possibly used in v1.3
    sys.modules['matplotlib'] = mock.MagicMock()
    sys.modules['reportlab'] = mock.MagicMock()

def test_load_v1_3():
    _mocks()
    p = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.3.py"
    assert p.exists()
    gd = runpy.run_path(str(p), run_name="loaded_v1_3")
    assert isinstance(gd, dict)
    # instantiate class if present (signature-only check)
    if "FitnessTrackerApp" in gd:
        cls = gd["FitnessTrackerApp"]
        # call constructor with a mock master
        cls(mock.MagicMock())
