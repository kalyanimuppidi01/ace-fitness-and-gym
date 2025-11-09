# tests/test_version_v1_2_2.py
import importlib.util
import pathlib
import sys
import types
from unittest import mock
import runpy
import pytest

TEST_FILE = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.2.py"

def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("ace_fit_v1_2_2", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fit_v1_2_2"] = module
    spec.loader.exec_module(module)
    return module

# --- Lightweight fakes for matplotlib objects used by the module --- #
class DummyAxes:
    def __init__(self):
        self._bars = []
        self._pies = []

    def bar(self, *args, **kwargs):
        self._bars.append((args, kwargs))

    def set_title(self, title, **kwargs):
        self._title = title

    def set_ylabel(self, lbl, **kwargs):
        self._ylabel = lbl

    def tick_params(self, *a, **k):
        pass

    def grid(self, *a, **k):
        pass

    def pie(self, *args, **kwargs):
        self._pies.append((args, kwargs))

    def set_title(self, *a, **k):
        pass

    def axis(self, *a, **k):
        pass

class DummyFigure:
    def __init__(self, *args, **kwargs):
        self._axes = []

    def add_subplot(self, *args, **kwargs):
        ax = DummyAxes()
        self._axes.append(ax)
        return ax

    def tight_layout(self, *a, **k):
        pass

class FakeCanvasWidget:
    def __init__(self):
        self.packed = False
        self.destroyed = False

    def pack(self, *a, **k):
        self.packed = True

    def destroy(self):
        self.destroyed = True

class FakeCanvas:
    def __init__(self, fig, master=None):
        self.fig = fig
        self.master = master
        self._widget = FakeCanvasWidget()
        self.draw_called = False

    def draw(self):
        self.draw_called = True

    def get_tk_widget(self):
        return self._widget

# --- Simple entry-like object used in tests to avoid shared MagicMock entries --- #
def _make_entry(get_value):
    return types.SimpleNamespace(get=lambda: get_value, delete=lambda *a, **kw: None)

class FakeMessageBox:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def showinfo(self, title, message):
        self.info_calls.append((title, message))

    def showerror(self, title, message):
        self.error_calls.append((title, message))

@pytest.fixture
def app_module_and_app(monkeypatch):
    assert TEST_FILE.exists(), f"{TEST_FILE} not found"
    module = load_module(TEST_FILE)

    # Replace messagebox with a fake
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb, raising=False)

    # Replace plotting objects to safe fakes
    monkeypatch.setattr(module, "Figure", DummyFigure, raising=False)
    monkeypatch.setattr(module, "FigureCanvasTkAgg", FakeCanvas, raising=False)

    # Create the app with a MagicMock root (ttk.Style calls etc. will be no-ops on MagicMock)
    root = mock.MagicMock()
    app = module.FitnessTrackerApp(root)

    # Ensure category_var.get returns a valid category
    try:
        app.category_var.get = lambda: "Workout"
    except Exception:
        pass

    # Replace chart_container with a simple container that has winfo_children and can accept labels
    # Some test environments will have chart_container as a MagicMock; override to be safe
    app.chart_container = types.SimpleNamespace(
        _children=[],
        winfo_children=lambda: [],
    )

    yield module, app, fake_mb

def test_module_loads_and_has_class():
    assert TEST_FILE.exists()
    gd = runpy.run_path(str(TEST_FILE), run_name="loaded_v1_2_2")
    assert "FitnessTrackerApp" in gd or any(k.lower().startswith("fitness") for k in gd.keys())

def test_add_workout_success(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Use distinct entry-like objects to avoid shared MagicMock issues
    app.workout_entry = _make_entry("Burpees")
    app.duration_entry = _make_entry("30")
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    # verify internal data
    assert len(app.workouts["Workout"]) == 1
    entry = app.workouts["Workout"][0]
    assert entry["exercise"] == "Burpees"
    assert entry["duration"] == 30
    assert "timestamp" in entry

    # messagebox info should not be empty
    assert fake_mb.info_calls, "Expected a success showinfo call"

    # progress chart should have been updated to a FakeCanvas
    assert isinstance(app.chart_canvas, FakeCanvas)

def test_add_workout_empty_fields_shows_error(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    app.workout_entry = _make_entry("")
    app.duration_entry = _make_entry("")

    app.add_workout()

    # no entries added
    assert all(len(v) == 0 for v in app.workouts.values())
    assert fake_mb.error_calls, "Expected an error showerror call for empty inputs"
    _, msg = fake_mb.error_calls[-1]
    assert "please enter both exercise and duration" in msg.lower()

def test_add_workout_invalid_or_negative_duration(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # non-integer duration
    app.workout_entry = _make_entry("Squat")
    app.duration_entry = _make_entry("not-a-number")
    app.category_var.get = lambda: "Workout"
    app.add_workout()
    assert fake_mb.error_calls, "Expected error for non-integer duration"
    fake_mb.error_calls.clear()

    # negative or zero duration
    app.workout_entry = _make_entry("Squat")
    app.duration_entry = _make_entry("0")
    app.add_workout()
    assert fake_mb.error_calls, "Expected error for non-positive duration"

def test_view_summary_empty_shows_message(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.view_summary()
    assert fake_mb.info_calls, "Expected info show for empty summary"
    _, msg = fake_mb.info_calls[-1]
    assert "no sessions logged yet" in msg.lower()

def test_update_progress_charts_no_data_and_with_data(app_module_and_app):
    module, app, fake_mb = app_module_and_app

    # Case: no data -> should early-return after placing a label (chart_container mocked)
    # Make chart_container return no children
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.update_progress_charts()
    # Since no data, no canvas was created
    assert app.chart_canvas is None

    # Case: with data -> create DummyFigure/FakeCanvas and draw called
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 5, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "lift", "duration": 45, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }
    # Provide chart_container that supports winfo_children and reception of widgets
    # (actual tk.Label calls will be MagicMocks in many test setups; this suffices)
    def fake_winfo_children():
        return []
    app.chart_container = types.SimpleNamespace(winfo_children=fake_winfo_children)

    # Ensure module.Figure and FigureCanvasTkAgg are the fakes
    module.Figure = DummyFigure
    module.FigureCanvasTkAgg = FakeCanvas

    app.update_progress_charts()

    assert isinstance(app.chart_canvas, FakeCanvas)
    assert app.chart_canvas.draw_called is True

def test_on_tab_change_triggers_update(app_module_and_app, monkeypatch):
    module, app, fake_mb = app_module_and_app

    # Prepare notebook.select and tab to simulate selecting the Progress Tracker tab
    app.notebook.select = lambda: "sel-id"
    app.notebook.tab = lambda sel, key: "📈 Progress Tracker"  # must include 'Progress Tracker' substring

    # Patch update_progress_charts to record calls
    called = {"count": 0}
    def fake_update():
        called["count"] += 1
    app.update_progress_charts = fake_update

    # Simulate event object (content not used)
    app.on_tab_change(event=types.SimpleNamespace())
    assert called["count"] == 1
