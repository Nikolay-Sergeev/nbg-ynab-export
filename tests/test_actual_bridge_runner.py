import os
import queue
import threading
from unittest.mock import patch

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


class RecordingStdin:
    def __init__(self):
        self.value = ""

    def write(self, value):
        self.value += value

    def flush(self):
        pass


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


def test_read_json_line_skips_non_object_json():
    runner = ActualBridgeRunner.__new__(ActualBridgeRunner)
    runner.process = FakeProcess(['["not", "an", "object"]\n', '{"ok":true}\n'])

    assert runner._read_json_line() == {"ok": True}


def test_child_environment_excludes_unrelated_secrets_and_node_options():
    with patch.dict(
        os.environ,
        {
            "YNAB_TOKEN": "secret-token",
            "ACTUAL_VERIFY_SSL": "false",
            "NODE_OPTIONS": "--require=/tmp/untrusted.js",
            "HTTPS_PROXY": "https://proxy.example",
            "PATH": "/usr/bin",
        },
        clear=True,
    ):
        child_env = ActualBridgeRunner._child_environment()

    assert child_env["NODE_ENV"] == "production"
    assert child_env["HTTPS_PROXY"] == "https://proxy.example"
    assert child_env["PATH"] == "/usr/bin"
    assert "YNAB_TOKEN" not in child_env
    assert "ACTUAL_VERIFY_SSL" not in child_env
    assert "NODE_OPTIONS" not in child_env


def test_send_rejects_oversized_command_before_writing_to_bridge():
    runner = ActualBridgeRunner.__new__(ActualBridgeRunner)
    runner._lock = threading.Lock()
    runner.MAX_COMMAND_BYTES = 20
    runner.process = FakeProcess([])
    runner.process.stdin = RecordingStdin()

    with pytest.raises(ValueError, match="safe size limit"):
        runner._send({"cmd": "uploadTransactions", "transactions": ["sensitive-data"]})

    assert runner.process.stdin.value == ""
