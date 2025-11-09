# tests/test_version_v1_3.py (corrected)
import importlib.util
import pathlib
import sys
import types
from unittest import mock
import runpy
import pytest

TEST_FILE = pathlib.Path(__file__).parents[1] / "app" / "ACEest_Fitness-V1.3.py"

# --------- Fakes / Helpers --------- #
class FakeMessageBox:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def showinfo(self, title, message):
        self.info_calls.append((title, message))

    def showerror(self, title, message):
        self.error_calls.append((title, message))

def _make_entry(value):
    return types.SimpleNamespace(get=lambda: value, delete=lambda *a, **k: None, pack=lambda *a, **k: None)

# Fake matplotlib pieces used when update_progress_charts runs
class DummyAxes:
    def __init__(self):
        self._bars = []
        self._pies = []

    def bar(self, *a, **k): self._bars.append((a, k))
    def set_title(self, *a, **k): pass
    def set_ylabel(self, *a, **k): pass
    def tick_params(self, *a, **k): pass
    def grid(self, *a, **k): pass
    def set_facecolor(self, *a, **k): pass
    def pie(self, *a, **k): self._pies.append((a, k))
    def axis(self, *a, **k): pass
    @property
    def spines(self):
        return {"right": mock.MagicMock(), "top": mock.MagicMock()}

class DummyFigure:
    def __init__(self, *a, **k): self._axes = []
    def add_subplot(self, *a, **k):
        ax = DummyAxes(); self._axes.append(ax); return ax
    def tight_layout(self, *a, **k): pass

class FakeCanvasWidget:
    def __init__(self): self.packed = False; self.destroyed = False
    def pack(self, *a, **k): self.packed = True
    def destroy(self): self.destroyed = True

class FakeCanvas:
    def __init__(self, fig, master=None):
        self.fig = fig; self.master = master; self._widget = FakeCanvasWidget(); self.draw_called = False
    def draw(self): self.draw_called = True
    def get_tk_widget(self): return self._widget

# Fake PDF Canvas used by export_weekly_report
class FakePDFCanvas:
    def __init__(self, filename, pagesize=None):
        self.filename = filename
        self.saved = False
        self.drawn = []
    def setFont(self, *a, **k): pass
    def drawString(self, *a, **k): self.drawn.append(("text", a))
    def save(self): self.saved = True
    def __getattr__(self, name):
        return lambda *a, **k: None

# Capture labels/texts created in view_summary by monkeypatching tk.Text.insert
class DummyTextRecorder:
    def __init__(self):
        self.inserted = []
    def insert(self, *args, **kwargs):
        if len(args) >= 2:
            self.inserted.append(args[1])
    def tag_config(self, *a, **k): pass
    def pack(self, *a, **k): pass
    def config(self, *a, **k): pass
    def yview(self, *a, **k): pass
    def __getattr__(self, _): return lambda *a, **k: None

# Proper fake Scrollbar factory with set/config/pack
def _fake_scrollbar_factory(*a, **k):
    return types.SimpleNamespace(
        pack=lambda *a, **k: None,
        config=lambda *a, **k: None,
        set=lambda *a, **k: None
    )

# --------- Fixtures --------- #
@pytest.fixture
def module_and_app(monkeypatch):
    assert TEST_FILE.exists(), f"{TEST_FILE} not found"
    spec = importlib.util.spec_from_file_location("ace_fit_v1_3", str(TEST_FILE))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fit_v1_3"] = module
    spec.loader.exec_module(module)

    # Patch messagebox so no modal dialogs appear
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb, raising=False)

    # Patch plotting classes
    monkeypatch.setattr(module, "Figure", DummyFigure, raising=False)
    monkeypatch.setattr(module, "FigureCanvasTkAgg", FakeCanvas, raising=False)

    # Patch PDF canvas class
    monkeypatch.setattr(module.pdf_canvas, "Canvas", FakePDFCanvas, raising=False)

    # **Ensure a real A4 page-size tuple exists on the module so code can unpack it**
    monkeypatch.setattr(module, "A4", (595.27, 841.89), raising=False)

    # Create app with MagicMock root (ttk.Style calls are no-ops on MagicMock)
    root = mock.MagicMock()
    app = module.FitnessTrackerApp(root)

    # Ensure category_var.get returns valid key
    try:
        app.category_var.get = lambda: "Workout"
    except Exception:
        pass

    # Replace chart_container with simple object safe for tests (some envs mock tk.Frame)
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])

    # make sure ttk.Scrollbar factory is safe for tests
    monkeypatch.setattr(module.ttk, "Scrollbar", _fake_scrollbar_factory, raising=False)

    yield module, app, fake_mb

# --------- Tests --------- #
def test_module_loads():
    gd = runpy.run_path(str(TEST_FILE), run_name="loaded_v1_3")
    assert "FitnessTrackerApp" in gd

def test_save_user_info_success_and_invalid(module_and_app):
    module, app, mb = module_and_app

    # Valid inputs
    app.name_entry = _make_entry("Alice")
    app.regn_entry = _make_entry("REG123")
    app.age_entry = _make_entry("30")
    app.gender_entry = _make_entry("F")
    app.height_entry = _make_entry("165")
    app.weight_entry = _make_entry("60")
    app.save_user_info()
    assert app.user_info, "user_info should be populated"
    assert "bmi" in app.user_info and "bmr" in app.user_info
    assert mb.info_calls, "Expected showinfo on valid save"

    # Invalid input (age non-integer) -> should call showerror
    mb.info_calls.clear(); mb.error_calls.clear()
    app.name_entry = _make_entry("Bob")
    app.regn_entry = _make_entry("REG2")
    app.age_entry = _make_entry("notanint")
    app.gender_entry = _make_entry("M")
    app.height_entry = _make_entry("170")
    app.weight_entry = _make_entry("70")
    app.save_user_info()
    assert mb.error_calls, "Expected showerror on invalid save"

def test_add_workout_success_and_daily_tracking(module_and_app):
    module, app, mb = module_and_app

    # prepare user_info so calorie calc uses provided weight
    app.user_info = {"weight": 80}

    # distinct entry-like objects
    app.workout_entry = _make_entry("Cycling")
    app.duration_entry = _make_entry("30")
    app.category_var.get = lambda: "Workout"

    # run add_workout
    app.add_workout()

    # check workouts updated
    assert len(app.workouts["Workout"]) == 1
    e = app.workouts["Workout"][0]
    assert e["exercise"] == "Cycling"
    assert e["duration"] == 30
    assert "calories" in e

    # check daily_workouts updated for today's date
    today = __import__("datetime").date.today().isoformat()
    assert today in app.daily_workouts
    assert len(app.daily_workouts[today]["Workout"]) >= 1
    assert mb.info_calls, "Expected showinfo after successful add"

def test_add_workout_invalid_and_zero_duration(module_and_app):
    module, app, mb = module_and_app

    # invalid non-int
    app.workout_entry = _make_entry("Run")
    app.duration_entry = _make_entry("abc")
    app.add_workout()
    assert mb.error_calls, "Expected error for non-integer duration"
    mb.error_calls.clear()

    # zero/negative
    app.workout_entry = _make_entry("Run")
    app.duration_entry = _make_entry("0")
    app.add_workout()
    assert mb.error_calls, "Expected error for non-positive duration"

def test_view_summary_empty_and_populated(monkeypatch, module_and_app):
    module, app, mb = module_and_app

    # empty case -> showinfo
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.view_summary()
    assert mb.info_calls, "Expected info when no sessions"

    # populated case -> replace Text widget with recorder to capture inserted text
    mb.info_calls.clear()
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 10, "calories": 10.0, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}],
        "Workout": [{"exercise": "lift", "duration": 20, "calories": 50.0, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}],
        "Cool-down": []
    }

    recorder = DummyTextRecorder()
    # monkeypatch module.tk.Text to our recorder factory
    monkeypatch.setattr(module.tk, "Text", lambda *a, **k: recorder, raising=False)
    # monkeypatch ttk.Scrollbar to proper fake (with set)
    monkeypatch.setattr(module.ttk, "Scrollbar", _fake_scrollbar_factory, raising=False)

    app.view_summary()

    # recorder should have some inserted text fragments including totals
    combined_text = "".join(recorder.inserted).lower()
    assert "total training time" in combined_text or "total" in combined_text

def test_update_progress_charts_no_data_and_with_data(module_and_app):
    module, app, mb = module_and_app

    # no data
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    app.update_progress_charts()
    # chart_canvas should remain None if no data
    assert app.chart_canvas is None

    # with data
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "jog", "duration": 5, "calories": 5.0, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "push", "duration": 25, "calories": 50.0, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }
    module = sys.modules["ace_fit_v1_3"]
    module.Figure = DummyFigure
    module.FigureCanvasTkAgg = FakeCanvas
    app.chart_container = types.SimpleNamespace(winfo_children=lambda: [])
    app.update_progress_charts()
    assert isinstance(app.chart_canvas, FakeCanvas)
    assert app.chart_canvas.draw_called

def test_export_weekly_report_generates_pdf(monkeypatch, module_and_app):
    module, app, mb = module_and_app

    # ensure user_info exists
    app.user_info = {"name": "Test User", "regn_id": "R1", "age": 30, "gender": "M", "height": 170, "weight": 70, "bmi": 24.2, "bmr": 1600}
    # add some workouts so table is non-empty
    from datetime import datetime
    app.workouts = {
        "Warm-up": [{"exercise": "j", "duration": 5, "calories": 5.0, "timestamp": datetime.now().isoformat()}],
        "Workout": [{"exercise": "p", "duration": 25, "calories": 60.0, "timestamp": datetime.now().isoformat()}],
        "Cool-down": []
    }

    # Our module's pdf_canvas.Canvas is already monkeypatched to FakePDFCanvas in fixture.
    # call export and verify messagebox showinfo and that fake PDF saved
    app.export_weekly_report()
    assert mb.info_calls, "Expected showinfo after PDF export"
    _, msg = mb.info_calls[-1]
    assert ".pdf" in msg.lower()
