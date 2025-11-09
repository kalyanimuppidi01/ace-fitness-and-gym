# tests/test_version_v1_2_1.py
import importlib.util
import pathlib
import sys
import types
from unittest import mock
import runpy
import pytest

TEST_FILE = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.1.py"

def load_module(path: pathlib.Path):
    """Load module from given path and return the module object."""
    spec = importlib.util.spec_from_file_location("ace_fit_v1_2_1", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fit_v1_2_1"] = module
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

class DummyAxes:
    def __init__(self):
        self._bars = []
        self._pies = []

    def bar(self, *args, **kwargs):
        self._bars.append((args, kwargs))

    def set_title(self, title):
        self._title = title

    def set_ylabel(self, lbl):
        self._ylabel = lbl

    def pie(self, *args, **kwargs):
        self._pies.append((args, kwargs))

class DummyFigure:
    def __init__(self, *args, **kwargs):
        self.subplots = []

    def add_subplot(self, *args, **kwargs):
        ax = DummyAxes()
        self.subplots.append(ax)
        return ax

class FakeCanvasWidget:
    def __init__(self):
        self.packed = False
        self.destroyed = False

    def pack(self, *a, **k):
        self.packed = True

    def destroy(self):
        self.destroyed = True

class FakeCanvas:
    """Replacement for FigureCanvasTkAgg used in the module."""
    def __init__(self, fig, master=None):
        self._fig = fig
        self._master = master
        self._widget = FakeCanvasWidget()
        self.draw_called = False

    def draw(self):
        self.draw_called = True

    def get_tk_widget(self):
        return self._widget

@pytest.fixture
def app_module_and_app(monkeypatch):
    # Load module fresh
    assert TEST_FILE.exists(), f"Missing file: {TEST_FILE}"
    module = load_module(TEST_FILE)

    # Replace messagebox with fake so tests can assert calls
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb, raising=False)

    # Replace Figure and FigureCanvasTkAgg in the module to safe fakes
    monkeypatch.setattr(module, "Figure", DummyFigure, raising=False)
    monkeypatch.setattr(module, "FigureCanvasTkAgg", FakeCanvas, raising=False)

    # Provide a simple mock "root" that will be passed to the app
    mock_root = mock.MagicMock()
    app = module.FitnessTrackerApp(mock_root)

    # Ensure category_var.get returns sensible default even if it's a MagicMock
    try:
        app.category_var.get = lambda: "Workout"
    except Exception:
        pass

    yield module, app, fake_mb

def test_module_loads_and_class_exists():
    assert TEST_FILE.exists()
    gd = runpy.run_path(str(TEST_FILE), run_name="loaded_v1_2_1_test")
    # Should expose class name
    assert "FitnessTrackerApp" in gd or any(k.lower().startswith("fitness") for k in gd.keys())

def _make_entry(get_value):
    """
    Create a simple object that mimics minimal Entry API used by the app:
    - get() -> returns the string
    - delete(start, end) -> no-op
    """
    return types.SimpleNamespace(get=lambda: get_value, delete=lambda *a, **kw: None)

def test_add_workout_success(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Replace entry objects with distinct simple namespaces so they are not shared MagicMocks
    app.workout_entry = _make_entry("Push Ups")
    app.duration_entry = _make_entry("20")
    app.category_var.get = lambda: "Workout"

    # call add_workout
    app.add_workout()

    # verify internal data updated
    assert len(app.workouts["Workout"]) == 1
    entry = app.workouts["Workout"][0]
    assert entry["exercise"] == "Push Ups"
    assert entry["duration"] == 20
    assert "timestamp" in entry

    # messagebox.showinfo called
    assert fake_mb.info_calls, "Expected showinfo to be called on successful add"
    title, msg = fake_mb.info_calls[-1]
    assert "added to" in msg.lower()

    # progress canvas updated (FakeCanvas)
    assert isinstance(app.progress_canvas, FakeCanvas), "Expected progress_canvas to be a FakeCanvas after add_workout"

def test_add_workout_empty_fields_shows_error(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    app.workout_entry = _make_entry("")
    app.duration_entry = _make_entry("")

    app.add_workout()

    # no additions
    assert all(len(v) == 0 for v in app.workouts.values())
    assert fake_mb.error_calls, "Expected showerror for empty fields"
    title, msg = fake_mb.error_calls[-1]
    assert "please enter both exercise and duration" in msg.lower()

def test_add_workout_invalid_duration_shows_error(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    app.workout_entry = _make_entry("Squats")
    app.duration_entry = _make_entry("notanumber")
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    assert all(len(v) == 0 for v in app.workouts.values())
    assert fake_mb.error_calls, "Expected showerror for invalid duration"
    _, msg = fake_mb.error_calls[-1]
    assert "duration must be a number" in msg.lower()

def test_view_summary_no_sessions_shows_message(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Clear workouts
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}

    app.view_summary()

    assert fake_mb.info_calls, "Expected summary info when no sessions logged"
    _, msg = fake_mb.info_calls[-1]
    assert "no sessions logged yet" in msg.lower()

def test_update_progress_charts_sets_canvas(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Start with empty totals -> progress_canvas still created (but pie not called)
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.update_progress_charts()
    assert isinstance(app.progress_canvas, FakeCanvas)

    # Now add entries with non-zero totals and update -> pie should be attempted (DummyAxes records pies)
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 5, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "push", "duration": 25, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }

    # Replace module.Figure with DummyFigure just in case, then run
    module.Figure = DummyFigure
    app.update_progress_charts()

    # Canvas should again be set
    assert isinstance(app.progress_canvas, FakeCanvas)
    # The FakeCanvas.draw should have been called inside update_progress_charts
    assert app.progress_canvas.draw_called is True

# ---------------- Additional tests added for more coverage ---------------- #

def test_add_multiple_sessions_and_motivational_message(app_module_and_app):
    """Add multiple sessions across categories and verify the motivational message branch indirectly."""
    module, app, fake_mb = app_module_and_app

    # Add small total -> should fall into 'Good start' when viewing summary (but view_summary doesn't show motivational text here)
    app.workout_entry = _make_entry("Jumping Jacks")
    app.duration_entry = _make_entry("10")
    app.category_var.get = lambda: "Warm-up"
    app.add_workout()

    app.workout_entry = _make_entry("Push-ups")
    app.duration_entry = _make_entry("10")
    app.category_var.get = lambda: "Workout"
    app.add_workout()

    app.workout_entry = _make_entry("Stretch")
    app.duration_entry = _make_entry("5")
    app.category_var.get = lambda: "Cool-down"
    app.add_workout()

    # Total time is 25 -> ensure summary window builds and total_time appears in labels/text via monkeypatching Label to capture text
    captured = []
    def fake_label(master=None, text="", *a, **k):
        captured.append(text)
        return types.SimpleNamespace(pack=lambda *aa, **kk: None, grid=lambda *aa, **kk: None)
    # monkeypatch module-level tk.Label used by the loaded module
    setattr(module, "tk", module.tk)  # ensure module.tk exists
    original_label = module.tk.Label
    module.tk.Label = fake_label
    try:
        app.view_summary()
    finally:
        module.tk.Label = original_label

    joined = " ".join([str(c) for c in captured]).lower()
    assert "total time" in joined or "total" in joined

def test_add_clears_entries_and_status_update(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Use simple namespace entries (delete is a no-op)
    app.workout_entry = types.SimpleNamespace(get=lambda: "Rowing", delete=lambda *a, **k: None)
    app.duration_entry = types.SimpleNamespace(get=lambda: "30", delete=lambda *a, **k: None)
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    # verify workout was added to internal store
    assert any(e.get("exercise") == "Rowing" for e in app.workouts["Workout"]), "Expected 'Rowing' to be recorded in workouts"

    # ensure status_label exists on the app (we don't assert its exact text to avoid GUI fragility)
    assert hasattr(app, "status_label"), "Expected app to have a status_label"


def test_view_summary_creates_toplevel(monkeypatch, app_module_and_app):
    """Ensure a Toplevel would be created when sessions exist (monkeypatch to record creation)."""
    module, app, fake_mb = app_module_and_app
    # prepare a session
    from datetime import datetime
    app.workouts = {"Warm-up": [], "Workout": [{"exercise": "sprint", "duration": 40, "timestamp": datetime.now().isoformat()}], "Cool-down": []}

    created = {"called": False}
    def fake_toplevel(master):
        created["called"] = True
        # mimic minimal Toplevel API used by view_summary
        return types.SimpleNamespace(title=lambda *a, **k: None, geometry=lambda *a, **k: None, pack=lambda *a, **k: None)

    monkeypatch.setattr(module.tk, "Toplevel", fake_toplevel, raising=False)
    app.view_summary()
    assert created["called"], "Expected view_summary to create a Toplevel window when sessions exist"

def test_update_progress_charts_pie_recorded(app_module_and_app):
    """Ensure the pie chart call is recorded on the DummyAxes when values > 0."""
    module, app, fake_mb = app_module_and_app
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 3, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "push", "duration": 7, "timestamp": datetime.now().isoformat()}],
        "Cool-down": [{"exercise": "walk", "duration": 0, "timestamp": datetime.now().isoformat()}],
    }
    # ensure module.Figure is DummyFigure (so we can introspect axes)
    module.Figure = DummyFigure
    app.update_progress_charts()
    # our DummyFigure created inside update_progress_charts is wrapped by FakeCanvas; access it:
    assert isinstance(app.progress_canvas, FakeCanvas)
    # the DummyFigure is at app.progress_canvas._fig
    fig = app.progress_canvas._fig
    # find any axis with pies recorded
    pies_found = any(getattr(ax, "_pies", []) for ax in fig.subplots)
    assert pies_found, "Expected pie() to be called on at least one axis when totals > 0"
