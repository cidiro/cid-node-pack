"""Tests for the CidTimerStart / CidTimerStop timer nodes and helpers."""

import importlib.util
import math
import sys
import time
import types
from pathlib import Path

import pytest


def _load_module(module_file, package_name="cid_node_pack_test"):
    root = Path(__file__).resolve().parents[1]

    package = sys.modules.get(package_name)
    if package is None:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root)]
        sys.modules[package_name] = package
    sub = module_file.parent.name
    sub_package = sys.modules.get(f"{package_name}.{sub}")
    if sub_package is None:
        sub_package = types.ModuleType(f"{package_name}.{sub}")
        sub_package.__path__ = [str(root / sub)]
        sys.modules[f"{package_name}.{sub}"] = sub_package

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.{sub}.{module_file.stem}", module_file
    )
    if spec.name in sys.modules:
        return sys.modules[spec.name]
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_nodes_dir = Path(__file__).resolve().parents[1] / "nodes"
_utils_dir = Path(__file__).resolve().parents[1] / "utils"

CidTimerStart = _load_module(_nodes_dir / "cid_timer_start.py").CidTimerStart
CidTimerStop = _load_module(_nodes_dir / "cid_timer_stop.py").CidTimerStop
timers = _load_module(_utils_dir / "timers.py")
duration = _load_module(_utils_dir / "duration.py")


class FakeClock:
    def __init__(self, start=100.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(time, "perf_counter", fake)
    return fake


@pytest.fixture(autouse=True)
def clean_timers():
    timers.clear_timers()
    yield
    timers.clear_timers()


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0.8234, "823.4 ms"),
        (0.0, "0.0 ms"),
        (1.0, "1.00 s"),
        (12.34, "12.34 s"),
        (83.4, "1m 23.4s"),
        (594.5, "9m 54.5s"),
        (3723.4, "1h 02m 03.4s"),
        (-5.0, "0.0 ms"),
    ],
)
def test_format_duration(seconds, expected):
    assert duration.format_duration(seconds) == expected


# ---------------------------------------------------------------------------
# timers utility
# ---------------------------------------------------------------------------


def test_timers_elapsed(clock):
    timers.start_timer("t")
    clock.advance(2.5)
    assert timers.stop_timer("t") == pytest.approx(2.5)


def test_timers_stop_without_start_raises():
    with pytest.raises(ValueError, match="no start timestamp for timer 'missing'"):
        timers.stop_timer("missing")


def test_timers_restart_overwrites(clock):
    timers.start_timer("t")
    clock.advance(1.0)
    timers.start_timer("t")
    clock.advance(2.0)
    assert timers.stop_timer("t") == pytest.approx(2.0)


def test_timers_stamp_persists_for_splits(clock):
    timers.start_timer("t")
    clock.advance(3.0)
    assert timers.stop_timer("t") == pytest.approx(3.0)
    clock.advance(1.0)
    assert timers.stop_timer("t") == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# CidTimerStart
# ---------------------------------------------------------------------------


def test_start_passes_input_through_unchanged(clock):
    sentinel = object()
    ret = CidTimerStart().main("default", sentinel)
    assert ret["result"] == (sentinel,)
    assert ret["result"][0] is sentinel


def test_start_stamps_and_announces(clock):
    ret = CidTimerStart().main("t1")
    assert ret["ui"] == {"timer_started": ["t1"]}
    clock.advance(1.25)
    assert timers.stop_timer("t1") == pytest.approx(1.25)


def test_start_rejects_empty_name():
    with pytest.raises(ValueError, match="timer_name"):
        CidTimerStart().main("")


def test_start_is_changed_always_fires():
    assert math.isnan(CidTimerStart.IS_CHANGED("default"))


def test_start_metadata():
    inputs = CidTimerStart.INPUT_TYPES()
    assert list(inputs["required"].keys()) == ["timer_name"]
    assert inputs["required"]["timer_name"][0] == "STRING"
    assert inputs["optional"]["input"][1]["forceInput"] is True
    assert CidTimerStart.OUTPUT_NODE is True


# ---------------------------------------------------------------------------
# CidTimerStop
# ---------------------------------------------------------------------------


def test_stop_measures_elapsed(clock):
    sentinel = object()
    timers.start_timer("default")
    clock.advance(12.34)
    ret = CidTimerStop().main("default", sentinel)
    out, seconds, text = ret["result"]
    assert out is sentinel
    assert seconds == pytest.approx(12.34)
    assert text == "12.34 s"


def test_stop_ui_payload(clock):
    timers.start_timer("default")
    clock.advance(2.0)
    ret = CidTimerStop().main("default")
    assert ret["ui"]["text"] == ["2.00 s"]
    assert ret["ui"]["elapsed"] == [pytest.approx(2.0)]


def test_stop_prints_to_console(clock, capsys):
    timers.start_timer("default")
    clock.advance(83.4)
    CidTimerStop().main("default")
    out = capsys.readouterr().out
    assert "CidTimerStop [default] 1m 23.4s" in out
    assert "(83.4000 s)" in out


def test_stop_without_start_raises():
    with pytest.raises(ValueError, match="CidTimerStop"):
        CidTimerStop().main("never-started")


def test_stop_rejects_empty_name():
    with pytest.raises(ValueError, match="timer_name"):
        CidTimerStop().main("")


def test_stop_is_changed_always_fires():
    assert math.isnan(CidTimerStop.IS_CHANGED("default"))


def test_stop_metadata():
    inputs = CidTimerStop.INPUT_TYPES()
    assert list(inputs["required"].keys()) == ["timer_name"]
    assert inputs["optional"]["input"][1]["forceInput"] is True
    assert CidTimerStop.RETURN_TYPES == (CidTimerStop.INPUT_TYPES()["optional"]["input"][0], "FLOAT", "STRING")
    assert CidTimerStop.RETURN_NAMES == ("output", "seconds", "text")
    assert CidTimerStop.OUTPUT_NODE is True


# ---------------------------------------------------------------------------
# Pair behavior
# ---------------------------------------------------------------------------


def test_start_stop_pair_end_to_end(clock):
    payload = {"image": [1, 2, 3]}
    CidTimerStart().main("default", payload)
    clock.advance(7.5)
    ret = CidTimerStop().main("default", payload)
    assert ret["result"][0] is payload
    assert ret["result"][1] == pytest.approx(7.5)
    assert ret["result"][2] == "7.50 s"


def test_two_stops_split_one_start(clock):
    CidTimerStart().main("t")
    clock.advance(1.0)
    first = CidTimerStop().main("t")["result"][1]
    clock.advance(2.0)
    second = CidTimerStop().main("t")["result"][1]
    assert first == pytest.approx(1.0)
    assert second == pytest.approx(3.0)
