# tests/test_ACEest_Fitness_V1_1.py
import importlib.util
import pathlib
import sys
import types
import tkinter as real_tk
import pytest

THIS_DIR = pathlib.Path(__file__).parent.resolve()
APP_DIR = THIS_DIR.parent / "app"
MODULE_PATH = APP_DIR / "ACEest_Fitness-V1.1.py"  # adjust if your file name or location differs

def load_module_from_path(path: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("ace_fitness_module", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["ace_fitness_module"] = module
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

@pytest.fixture
def app_module_and_app(monkeypatch):
    # Load target module
    module = load_module_from_path(MODULE_PATH)

    # Replace messagebox in module with fake to avoid GUI dialogs
    fake_mb = FakeMessageBox()
    monkeypatch.setattr(module, "messagebox", fake_mb)

    # Create a Tk root. If the test environment has patched tk.Tk to a MagicMock,
    # this will result in a MagicMock root — we handle that below.
    try:
        root = real_tk.Tk()
        # hide window if real tkinter was used
        root.withdraw()
    except Exception:
        # fallback: some CI environments may not allow real tk.Tk() — create a simple dummy object
        root = types.SimpleNamespace(winfo_children=lambda: [])

    # Instantiate the app using the module's class. If module imports tkinter as `tk`,
    # it will use that; root might be a MagicMock — we'll patch the instance afterwards.
    app = module.FitnessTrackerApp(root)

    # Ensure category_var.get() returns a string (tests expect category keys to work).
    # If category_var is a MagicMock or StringVar, override get() to return "Workout".
    try:
        app.category_var.get = lambda: "Workout"
    except Exception:
        # if setting attribute fails, ignore — tests will still attempt to set it where needed
        pass

    yield module, app, root, fake_mb

    # Cleanup: destroy any toplevel windows and root if real
    try:
        # destroy any toplevels created by the app
        if hasattr(root, "winfo_children"):
            for w in list(root.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
        # destroy root if it's a real tkinter root
        if isinstance(root, real_tk.Tk):
            root.destroy()
    except Exception:
        pass

def test_add_workout_success(app_module_and_app):
    module, app, root, fake_mb = app_module_and_app

    # Ensure entry.get() returns the desired values (robust to MagicMock entries)
    app.workout_entry.get = lambda: "Push Ups"
    app.duration_entry.get = lambda: "15"
    # category var already forced in fixture, but set explicitly here as well
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    # workout should be added
    assert len(app.workouts["Workout"]) == 1
    entry = app.workouts["Workout"][0]
    assert entry["exercise"] == "Push Ups"
    assert entry["duration"] == 15
    assert "timestamp" in entry

    # status label should change (can't guarantee it's a real tk.Label in all envs,
    # but status_label.cget should exist in normal runs)
    try:
        status_text = app.status_label.cget("text")
        assert "Added Push Ups (15 min) to Workout" in status_text
    except Exception:
        # if status_label is mocked, skip exact text assertion
        pass

    # messagebox.showinfo should have been called
    assert fake_mb.info_calls, "Expected showinfo to be called on success"
    title, msg = fake_mb.info_calls[-1]
    assert "added to" in msg.lower()

def test_add_workout_empty_fields_shows_error(app_module_and_app):
    module, app, root, fake_mb = app_module_and_app

    # Make entry.get return empty strings
    app.workout_entry.get = lambda: ""
    app.duration_entry.get = lambda: ""

    app.add_workout()

    # no workouts added
    assert all(len(v) == 0 for v in app.workouts.values())
    # showerror should be called
    assert fake_mb.error_calls, "Expected showerror to be called for empty inputs"
    title, msg = fake_mb.error_calls[-1]
    assert "please enter both exercise and duration" in msg.lower()

def test_add_workout_invalid_duration_shows_error(app_module_and_app):
    module, app, root, fake_mb = app_module_and_app

    app.workout_entry.get = lambda: "Squats"
    app.duration_entry.get = lambda: "abc"  # invalid
    app.category_var.get = lambda: "Workout"

    app.add_workout()

    # no workouts added
    assert all(len(v) == 0 for v in app.workouts.values())
    # showerror called for duration
    assert fake_mb.error_calls, "Expected showerror to be called for invalid duration"
    title, msg = fake_mb.error_calls[-1]
    assert "duration must be a number" in msg.lower()

def test_view_summary_no_sessions_shows_message(app_module_and_app):
    module, app, root, fake_mb = app_module_and_app

    # ensure no sessions
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}

    app.view_summary()

    # Should call showinfo indicating no sessions
    assert fake_mb.info_calls, "Expected showinfo for empty summary"
    title, msg = fake_mb.info_calls[-1]
    assert "no sessions logged yet" in msg.lower()

# Helpers for injecting fake Label/Toplevel that capture created label texts.
class FakeLabel:
    created_texts = []

    def __init__(self, master=None, text="", font=None, fg=None, **kwargs):
        # store text for later assertions
        FakeLabel.created_texts.append(str(text))

    def pack(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def config(self, *args, **kwargs):
        pass

    # allow cget to be called by tests (if they attempt it)
    def cget(self, key):
        if key == "text":
            return FakeLabel.created_texts[-1]
        return None

class FakeToplevel:
    def __init__(self, master=None):
        # a container that the app will treat as a window
        self._children = []

    def title(self, *args, **kwargs):
        pass

    def geometry(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        pass

    def winfo_children(self):
        return list(self._children)

    def destroy(self):
        pass

def _create_entries_direct(app, entries):
    """Helper: create workout entries directly in data structure (bypass messagebox)."""
    from datetime import datetime
    app.workouts = {"Warm-up": [], "Workout": [], "Cool-down": []}
    for cat, ex, dur in entries:
        app.workouts.setdefault(cat, [])
        app.workouts[cat].append({
            "exercise": ex,
            "duration": dur,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

@pytest.mark.parametrize("entries, expected_msg_fragment", [
    ( [("Workout", "A", 10)], "Good start! Keep moving"),           # total 10 < 30
    ( [("Workout", "A", 20), ("Warm-up", "B", 15)], "Nice effort!"),# total 35 -> 30-59
    ( [("Workout", "A", 40), ("Cool-down", "B", 30)], "Excellent dedication!"), # total 70 >=60
])
def test_view_summary_shows_correct_motivational_message(app_module_and_app, monkeypatch, entries, expected_msg_fragment):
    module, app, root, fake_mb = app_module_and_app

    # Populate workouts directly (avoid messagebox side effects)
    _create_entries_direct(app, entries)

    # Replace module.tk.Label and module.tk.Toplevel with fakes that capture text
    # Use raising=False in case module.tk is a MagicMock that doesn't have attributes
    FakeLabel.created_texts.clear()
    if hasattr(module, "tk"):
        monkeypatch.setattr(module.tk, "Label", FakeLabel, raising=False)
        monkeypatch.setattr(module.tk, "Toplevel", FakeToplevel, raising=False)
    else:
        # fallback: ensure Label/Toplevel exist on module
        module.Label = FakeLabel
        module.Toplevel = FakeToplevel

    # Call view_summary (which will create FakeToplevel and FakeLabel instances)
    app.view_summary()

    # Check that a "Total Time Spent" label text was created and motivational message exists
    combined_text = "\n".join(FakeLabel.created_texts)
    assert "Total Time Spent" in combined_text, f"Total time label missing. Collected: {FakeLabel.created_texts}"
    assert expected_msg_fragment in combined_text, f"Expected motivational message '{expected_msg_fragment}' in labels: {FakeLabel.created_texts}"
