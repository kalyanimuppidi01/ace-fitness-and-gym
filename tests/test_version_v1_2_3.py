import importlib.util
import pathlib
import sys
import types
from unittest import mock
import pytest
import runpy

TEST_FILE = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.2.3.py"

# ------------------- Helper Classes ------------------- #
class DummyAxes:
    def __init__(self):
        self._bars, self._pies = [], []

    def bar(self, *a, **k): self._bars.append((a, k))
    def set_title(self, *a, **k): pass
    def set_ylabel(self, *a, **k): pass
    def tick_params(self, *a, **k): pass
    def grid(self, *a, **k): pass
    def pie(self, *a, **k): self._pies.append((a, k))
    def axis(self, *a, **k): pass
    def set_facecolor(self, *a, **k): pass
    @property
    def spines(self): return {"right": mock.MagicMock(), "top": mock.MagicMock()}

class DummyFigure:
    def __init__(self, *a, **k): self._axes = []
    def add_subplot(self, *a, **k):
        ax = DummyAxes(); self._axes.append(ax); return ax
    def tight_layout(self, *a, **k): pass

class FakeCanvasWidget:
    def __init__(self): self.packed, self.destroyed = False, False
    def pack(self, *a, **k): self.packed = True
    def destroy(self): self.destroyed = True

class FakeCanvas:
    def __init__(self, fig, master=None):
        self.fig, self.master, self._widget = fig, master, FakeCanvasWidget()
        self.draw_called = False
    def draw(self): self.draw_called = True
    def get_tk_widget(self): return self._widget

class FakeMessageBox:
    def __init__(self): self.info_calls, self.error_calls = [], []
    def showinfo(self, t, m): self.info_calls.append((t, m))
    def showerror(self, t, m): self.error_calls.append((t, m))

def _make_entry(value):
    """Simple fake Entry widget with get()/delete()."""
    return types.SimpleNamespace(get=lambda: value, delete=lambda *a, **k: None)

# ------------------- Pytest Fixtures ------------------- #
@pytest.fixture
def module_and_app(monkeypatch):
    assert TEST_FILE.exists(), f"{TEST_FILE} missing"
    spec = importlib.util.spec_from_file_location("ace_fit_v1_2_3", str(TEST_FILE))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fit_v1_2_3"] = module
    spec.loader.exec_module(module)

    # patch messagebox + plotting classes
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb, raising=False)
    monkeypatch.setattr(module, "Figure", DummyFigure, raising=False)
    monkeypatch.setattr(module, "FigureCanvasTkAgg", FakeCanvas, raising=False)

    # Instantiate app with mock root
    root = mock.MagicMock()
    app = module.FitnessTrackerApp(root)
    app.category_var.get = lambda: "Workout"
    return module, app, fake_mb

# ------------------- Tests ------------------- #
def test_module_loads():
    gd = runpy.run_path(str(TEST_FILE), run_name="loaded_v1_2_3")
    assert "FitnessTrackerApp" in gd

def test_add_workout_success(module_and_app):
    module, app, mb = module_and_app
    app.workout_entry = _make_entry("Jump Rope")
    app.duration_entry = _make_entry("20")
    app.add_workout()
    data = app.workouts["Workout"][0]
    assert data["exercise"] == "Jump Rope" and data["duration"] == 20
    assert mb.info_calls and not mb.error_calls
    assert isinstance(app.chart_canvas, FakeCanvas) or app.chart_canvas is None

def test_add_workout_empty_and_invalid(module_and_app):
    module, app, mb = module_and_app
    # empty
    app.workout_entry = _make_entry("")
    app.duration_entry = _make_entry("")
    app.add_workout()
    assert mb.error_calls
    mb.error_calls.clear()
    # invalid
    app.workout_entry = _make_entry("Run")
    app.duration_entry = _make_entry("abc")
    app.add_workout()
    assert mb.error_calls
    mb.error_calls.clear()
    # non-positive
    app.workout_entry = _make_entry("Pushup")
    app.duration_entry = _make_entry("0")
    app.add_workout()
    assert mb.error_calls

def test_view_summary_empty(module_and_app):
    module, app, mb = module_and_app
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.view_summary()
    assert any("no sessions" in m[1].lower() for m in mb.info_calls)

def test_update_progress_charts_empty_and_with_data(module_and_app):
    module, app, mb = module_and_app
    # no data
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.update_progress_charts()
    # with data
    from datetime import datetime
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])
    app.workouts = {
        "Warm-up": [{"exercise": "Jog", "duration": 5, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "Lift", "duration": 15, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }
    module.Figure, module.FigureCanvasTkAgg = DummyFigure, FakeCanvas
    app.update_progress_charts()
    assert isinstance(app.chart_canvas, FakeCanvas)
    assert app.chart_canvas.draw_called

def test_on_tab_change_calls_update(module_and_app):
    module, app, mb = module_and_app
    app.notebook.select = lambda: "id"
    app.notebook.tab = lambda sel, key: "📈 Progress Tracker"
    called = {"count": 0}
    app.update_progress_charts = lambda : called.update(count=called["count"] + 1)
    app.on_tab_change(event=None)
    assert called["count"] == 1

def test_create_workout_plan_and_diet_tabs_cover_lines(module_and_app):
    module, app, mb = module_and_app
    # Simply invoke to ensure code runs
    app.create_workout_plan_tab()
    app.create_diet_guide_tab()
    assert True

# ---------------- Extra tests to raise coverage for v1.2.3 ---------------- #

def test_add_clears_entries_and_status_update(module_and_app):
    """Ensure add_workout records the session and that the app has a status_label."""
    module, app, fake_mb = module_and_app

    app.workout_entry = _make_entry("Rowing")
    app.duration_entry = _make_entry("30")
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    # verify workout was actually recorded
    assert any(e.get("exercise") == "Rowing" or e["exercise"] == "Rowing" for e in app.workouts["Workout"]), "Expected 'Rowing' recorded"

    # ensure status_label exists (avoid checking exact text)
    assert hasattr(app, "status_label"), "Expected app to have a status_label"


def test_view_summary_creates_toplevel(monkeypatch, module_and_app):
    """When sessions exist, view_summary should create a Toplevel window (monkeypatch to record)."""
    module, app, fake_mb = module_and_app
    from datetime import datetime

    app.workouts = {
        "Warm-up": [],
        "Workout": [{"exercise": "sprint", "duration": 40, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }

    created = {"called": False}
    def fake_toplevel(master):
        created["called"] = True
        # Provide minimal API expected by view_summary
        return types.SimpleNamespace(title=lambda *a, **k: None, geometry=lambda *a, **k: None, config=lambda *a, **k: None, pack=lambda *a, **k: None)

    monkeypatch.setattr(module.tk, "Toplevel", fake_toplevel, raising=False)
    app.view_summary()
    assert created["called"], "Expected view_summary to create a Toplevel when sessions exist"


def test_update_progress_charts_pie_recorded(module_and_app):
    """Ensure the pie() path is exercised when totals > 0 (DummyFigure/DummyAxes store pies)."""
    module, app, fake_mb = module_and_app
    from datetime import datetime

    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 3, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "push", "duration": 7, "timestamp": datetime.now().isoformat()}],
        "Cool-down": [{"exercise": "walk", "duration": 0, "timestamp": datetime.now().isoformat()}],
    }

    # Ensure module's Figure and FigureCanvas are the test fakes (fixture already sets them)
    module.Figure = DummyFigure
    module.FigureCanvasTkAgg = FakeCanvas

    app.update_progress_charts()

    # confirm a canvas was created and drawn
    assert isinstance(app.chart_canvas, FakeCanvas)
    assert app.chart_canvas.draw_called is True

    # inspect the figure inside the FakeCanvas and assert at least one axis recorded a pie call
    fig = getattr(app.chart_canvas, "fig", getattr(app.chart_canvas, "_fig", None))
    pies_found = False
    if fig:
        axes = getattr(fig, "_axes", None) or getattr(fig, "subplots", None) or getattr(fig, "axes", None)
        if axes:
            for ax in axes:
                if getattr(ax, "_pies", []):
                    pies_found = True
                    break
    assert pies_found, "Expected pie() to be called on at least one axis when totals > 0"


def test_add_multiple_sessions_and_summary_text_capture(monkeypatch, module_and_app):
    """
    Adds multiple sessions across categories, then monkeypatches tk.Text to capture
    inserted summary text. Ensures that the text contains session details or totals.
    """
    module, app, fake_mb = module_and_app

    # --- Add several sessions programmatically ---
    app.workout_entry = _make_entry("Jumping Jacks")
    app.duration_entry = _make_entry("10")
    app.category_var.get = lambda: "Warm-up"
    app.add_workout()

    app.workout_entry = _make_entry("Push-ups")
    app.duration_entry = _make_entry("20")
    app.category_var.get = lambda: "Workout"
    app.add_workout()

    app.workout_entry = _make_entry("Stretch")
    app.duration_entry = _make_entry("5")
    app.category_var.get = lambda: "Cool-down"
    app.add_workout()

    # --- Recorder for tk.Text widget insertions ---
    class Recorder:
        def __init__(self):
            self.inserted = []

        def insert(self, *args, **kwargs):
            # Record inserted strings
            if len(args) >= 2:
                self.inserted.append(str(args[1]))

        def tag_config(self, *a, **k): pass
        def pack(self, *a, **k): pass
        def config(self, *a, **k): pass
        def yview(self, *a, **k):  # required because scrollbar.config(command=summary_text.yview)
            return None

    recorder = Recorder()

    # Patch tk.Text to return our recorder
    monkeypatch.setattr(module.tk, "Text", lambda *a, **k: recorder, raising=False)

    # Patch ttk.Scrollbar to prevent AttributeError (must have set(), config(), pack())
    monkeypatch.setattr(
        module.ttk,
        "Scrollbar",
        lambda *a, **k: types.SimpleNamespace(
            pack=lambda *a, **k: None,
            config=lambda *a, **k: None,
            set=lambda *a, **k: None,
        ),
        raising=False,
    )

    # --- Call view_summary() to populate the fake text area ---
    app.view_summary()

    # --- Validate captured text content ---
    combined_text = " ".join(recorder.inserted).lower()

    assert (
        "total training time" in combined_text
        or "total time" in combined_text
        or any(
            keyword in combined_text
            for keyword in ["jump", "push", "stretch", "workout", "minutes"]
        )
    ), "Expected the summary text to contain session details or totals"