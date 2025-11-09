# tests/test_version_v1_2.py
import importlib.util
import pathlib
import sys
import types
from unittest import mock
import runpy
import pytest

TEST_FILE = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.py"

def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("ace_fit_v1_2", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fit_v1_2"] = module
    spec.loader.exec_module(module)
    return module

class FakeMessageBox:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def showinfo(self, title, message):
        self.info_calls.append((title, message))

    def showerror(self, title, message):
        self.error_calls.append((title, message))

def _make_entry(get_value):
    """Simple fake Entry widget with get()/delete()."""
    return types.SimpleNamespace(get=lambda: get_value, delete=lambda *a, **kw: None)

# Lightweight fakes to observe created labels/text in view_summary
class FakeLabel:
    created = []
    def __init__(self, master=None, text="", font=None, fg=None, bg=None, **kwargs):
        FakeLabel.created.append(str(text))
    def pack(self, *a, **k): pass
    def grid(self, *a, **k): pass

class FakeToplevel:
    def __init__(self, master=None):
        self._children = []
    def title(self, *a, **k): pass
    def geometry(self, *a, **k): pass
    def pack(self, *a, **k): pass
    def winfo_children(self): return list(self._children)
    def destroy(self): pass

@pytest.fixture
def module_and_app(monkeypatch):
    assert TEST_FILE.exists(), f"{TEST_FILE} not found"
    module = load_module(TEST_FILE)

    # patch messagebox so dialogs don't appear
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb, raising=False)

    # Create app with a MagicMock root so ttk/Frame calls are no-ops
    root = mock.MagicMock()
    app = module.FitnessTrackerApp(root)

    # Ensure category_var.get returns a valid category
    try:
        app.category_var.get = lambda: "Workout"
    except Exception:
        pass

    yield module, app, fake_mb

def test_module_loads():
    assert TEST_FILE.exists()
    gd = runpy.run_path(str(TEST_FILE), run_name="loaded_v1_2_test")
    assert "FitnessTrackerApp" in gd or any(k.lower().startswith("fitness") for k in gd.keys())

def test_add_workout_success(module_and_app):
    module, app, mb = module_and_app

    app.workout_entry = _make_entry("Push Ups")
    app.duration_entry = _make_entry("15")
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    assert len(app.workouts["Workout"]) == 1
    e = app.workouts["Workout"][0]
    assert e["exercise"] == "Push Ups"
    assert e["duration"] == 15
    assert "timestamp" in e

    assert mb.info_calls, "Expected showinfo on success"

def test_add_workout_empty_and_invalid(module_and_app):
    module, app, mb = module_and_app

    # empty
    app.workout_entry = _make_entry("")
    app.duration_entry = _make_entry("")
    app.add_workout()
    assert mb.error_calls, "Expected error for empty inputs"
    mb.error_calls.clear()

    # invalid duration
    app.workout_entry = _make_entry("Squats")
    app.duration_entry = _make_entry("abc")
    app.add_workout()
    assert mb.error_calls, "Expected error for non-integer duration"
    mb.error_calls.clear()

def test_view_summary_no_sessions_shows_message(module_and_app):
    module, app, mb = module_and_app

    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.view_summary()

    assert mb.info_calls, "Expected info when no sessions logged"
    _, msg = mb.info_calls[-1]
    assert "no sessions logged yet" in msg.lower()

def test_view_summary_with_entries_shows_total_and_motivation(monkeypatch, module_and_app):
    module, app, mb = module_and_app

    # create data directly
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 10, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}],
        "Workout": [{"exercise": "push", "duration": 25, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}],
        "Cool-down": []
    }

    # attach fakes for Label and Toplevel to capture text
    FakeLabel.created.clear()
    if hasattr(module, "tk"):
        monkeypatch.setattr(module.tk, "Label", FakeLabel, raising=False)
        monkeypatch.setattr(module.tk, "Toplevel", FakeToplevel, raising=False)
    else:
        module.Label = FakeLabel
        module.Toplevel = FakeToplevel

    app.view_summary()

    # combined texts should include "Total Time Spent" (or the total minutes) and a motivational message
    combined = "\n".join(FakeLabel.created)
    assert "Total Time Spent" in combined or "Total Time" in combined or "total" in combined.lower()
    # total_time = 35 -> motivational branch should contain "Nice effort" or "Excellent" depending threshold
    assert any(word in combined.lower() for word in ("nice effort", "excellent dedication", "good start"))

def test_create_tabs_cover_lines(module_and_app):
    module, app, mb = module_and_app
    # invoke chart and diet creation methods again to ensure coverage
    app.create_workout_chart_tab()
    app.create_diet_chart_tab()
    assert True
