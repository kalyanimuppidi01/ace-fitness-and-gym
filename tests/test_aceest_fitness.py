# tests/test_aceest_fitness.py
import pytest
from unittest import mock

# -------------------------
# Mock tkinter and messagebox so GUI won't open
# -------------------------
mock_tk = mock.MagicMock()
mock_messagebox = mock.MagicMock()

modules_to_patch = {
    "tkinter": mock_tk,
    "tkinter.messagebox": mock_messagebox
}

with mock.patch.dict("sys.modules", modules_to_patch):
    import app.ACEest_Fitness as fitness


@pytest.fixture
def app_instance():
    """Provide a FitnessTrackerApp instance with mocked tkinter widgets."""

    # Generic widget mock with grid() no-op
    class BaseWidget:
        def grid(self, *a, **kw):  # tkinter layout call
            return self

    # Entry mock: behaves like tkinter.Entry but stores value in memory
    class MockEntry(BaseWidget):
        def __init__(self):
            self._value = ""
        def get(self): return self._value
        def delete(self, start, end): self._value = ""
        def insert(self, index, value): self._value = value

    # Label/Button mocks (just accept .grid())
    class MockLabel(BaseWidget): pass
    class MockButton(BaseWidget): pass

    # Replace tkinter classes with mocks
    mock_tk.Entry.side_effect = lambda *a, **k: MockEntry()
    mock_tk.Label.side_effect = lambda *a, **k: MockLabel()
    mock_tk.Button.side_effect = lambda *a, **k: MockButton()
    mock_tk.END = "end"

    master = mock.MagicMock()
    return fitness.FitnessTrackerApp(master)


# ---------------------------------------------------------------------
# ✅ TESTS
# ---------------------------------------------------------------------

def test_add_workout_success(app_instance):
    app = app_instance
    app.workout_entry.insert(0, "Pushups")
    app.duration_entry.insert(0, "30")

    fitness.messagebox.showinfo = mock.MagicMock()
    fitness.messagebox.showerror = mock.MagicMock()

    app.add_workout()

    assert len(app.workouts) == 1
    assert app.workouts[0]["workout"] == "Pushups"
    assert app.workouts[0]["duration"] == 30
    fitness.messagebox.showinfo.assert_called_once()
    # Inputs cleared
    assert app.workout_entry.get() == ""
    assert app.duration_entry.get() == ""


def test_add_workout_missing_fields(app_instance):
    app = app_instance
    app.workout_entry.insert(0, "")
    app.duration_entry.insert(0, "45")

    fitness.messagebox.showerror = mock.MagicMock()
    app.add_workout()

    fitness.messagebox.showerror.assert_called_once_with(
        "Error", "Please enter both workout and duration."
    )
    assert len(app.workouts) == 0


def test_add_workout_invalid_duration(app_instance):
    app = app_instance
    app.workout_entry.insert(0, "Jogging")
    app.duration_entry.insert(0, "abc")

    fitness.messagebox.showerror = mock.MagicMock()
    app.add_workout()

    fitness.messagebox.showerror.assert_called_once_with(
        "Error", "Duration must be a number."
    )
    assert len(app.workouts) == 0


def test_view_workouts_empty(app_instance):
    app = app_instance
    fitness.messagebox.showinfo = mock.MagicMock()
    app.view_workouts()
    fitness.messagebox.showinfo.assert_called_once_with(
        "Workouts", "No workouts logged yet."
    )


def test_view_workouts_with_entries(app_instance):
    app = app_instance
    app.workouts = [
        {"workout": "Yoga", "duration": 60},
        {"workout": "Run", "duration": 20},
    ]

    fitness.messagebox.showinfo = mock.MagicMock()
    app.view_workouts()

    args, _ = fitness.messagebox.showinfo.call_args
    assert args[0] == "Workouts"
    assert "Yoga" in args[1]
    assert "Run" in args[1]
    assert "minutes" in args[1]
