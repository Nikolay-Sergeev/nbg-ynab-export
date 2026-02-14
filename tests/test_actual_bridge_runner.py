import json
import queue
import pytest
from services.actual_bridge_runner import ActualBridgeRunner


class FakeStdout:
    def __init__(self, lines):
        self._lines = lines

    def readline(self):
        if not self._lines:
            return ""
        return self._lines.pop(0)


class FakeProcess:
    def __init__(self, lines):
        self.stdout = FakeStdout(lines)
        self.stdin = None

    def poll(self):
        return None


def test_read_json_line_skips_noise_and_returns_first_valid_json():
    runner = ActualBridgeRunner.__new__(ActualBridgeRunner)  # bypass __init__
    runner.process = FakeProcess(["Loading fresh spreadsheet\n", '{"ok":true}\n'])
    resp = runner._read_json_line()
    assert resp == {"ok": True}


def test_read_json_line_times_out_when_no_stdout_data():
    runner = ActualBridgeRunner.__new__(ActualBridgeRunner)  # bypass __init__
    runner._stdout_queue = queue.Queue()
    with pytest.raises(TimeoutError):
        runner._read_json_line(timeout_seconds=0.01)
