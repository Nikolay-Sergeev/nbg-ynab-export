import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional
from config import get_logger

logger = get_logger(__name__)


class ActualBridgeRunner:
    """
    Thin wrapper to talk to the Node-based Actual bridge via stdin/stdout.
    """

    RESPONSE_TIMEOUT_SECONDS = 30.0
    MAX_COMMAND_BYTES = 25 * 1024 * 1024
    _CHILD_ENV_ALLOWLIST = (
        "HOME",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LANG",
        "LC_ALL",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PATH",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TEMP",
        "TMP",
        "TMPDIR",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    )

    @classmethod
    def _child_environment(cls) -> Dict[str, str]:
        child_env = {
            name: os.environ[name]
            for name in cls._CHILD_ENV_ALLOWLIST
            if name in os.environ
        }
        child_env["NODE_ENV"] = "production"
        return child_env

    def __init__(self, project_root: Optional[Path] = None):
        root = project_root or Path(__file__).resolve().parent.parent
        script_path = root / "scripts" / "actual_bridge.js"
        if not script_path.exists():
            raise FileNotFoundError(f"Actual bridge script missing: {script_path}")
        node_path = shutil.which("node")
        if not node_path:
            raise FileNotFoundError("Node.js executable was not found on PATH")
        child_env = self._child_environment()
        # Ensure data dir exists when bridge writes cache
        self.process = subprocess.Popen(
            [node_path, str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(root),
            env=child_env,
        )
        self._lock = threading.Lock()
        self._stdout_queue: "queue.Queue[str]" = queue.Queue(maxsize=200)
        self._stdout_thread = threading.Thread(target=self._drain_stdout, daemon=True)
        self._stdout_thread.start()
        self._stderr_buffer = deque(maxlen=50)
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stdout(self) -> None:
        """Collect bridge stdout lines so reads can be time-bounded."""
        if not self.process or self.process.stdout is None:
            return
        for line in self.process.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                self._stdout_queue.put_nowait(line)
            except queue.Full:
                # Keep the newest lines if stdout is noisy.
                try:
                    self._stdout_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._stdout_queue.put_nowait(line)
                except queue.Full:
                    pass

    def _drain_stderr(self) -> None:
        """Log stderr from the bridge to aid debugging."""
        if not self.process or self.process.stderr is None:
            return
        for line in self.process.stderr:
            line = line.rstrip()
            if not line:
                continue
            self._stderr_buffer.append(line)
            logger.debug("[ActualBridge] %s", line)

    def _read_json_line(self, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Read lines until we get a valid JSON response, skipping noisy stdout logs that the
        Actual API occasionally emits (e.g., "Loading fresh spreadsheet").
        """
        timeout = (
            self.RESPONSE_TIMEOUT_SECONDS
            if timeout_seconds is None
            else float(timeout_seconds)
        )
        deadline = time.monotonic() + max(timeout, 0.1)
        max_attempts = 100
        for _ in range(max_attempts):
            if hasattr(self, "_stdout_queue"):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Timed out waiting for Actual bridge response")
                try:
                    resp_line = self._stdout_queue.get(timeout=remaining)
                except queue.Empty as exc:
                    raise TimeoutError("Timed out waiting for Actual bridge response") from exc
            else:
                # Compatibility fallback for tests that bypass __init__.
                if not self.process or self.process.stdout is None:
                    raise RuntimeError("Actual bridge stdout is unavailable")
                resp_line = self.process.stdout.readline()
            if not resp_line:
                break
            try:
                response = json.loads(resp_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON bridge output: %s", resp_line.strip())
                continue
            if not isinstance(response, dict):
                logger.debug("Skipping non-object bridge response")
                continue
            return response
        raise RuntimeError("No valid JSON response from Actual bridge")

    def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if not self.process or self.process.poll() is not None:
                raise RuntimeError("Actual bridge process is not running")
            line = json.dumps(payload) + "\n"
            if len(line.encode('utf-8')) > self.MAX_COMMAND_BYTES:
                raise ValueError("Actual bridge command exceeds the safe size limit")
            if self.process.stdin is None:
                raise RuntimeError("Actual bridge stdin is unavailable")
            self.process.stdin.write(line)
            self.process.stdin.flush()
            try:
                resp_obj = self._read_json_line(timeout_seconds=self.RESPONSE_TIMEOUT_SECONDS)
            except TimeoutError as exc:
                self.close()
                raise RuntimeError("Timed out waiting for Actual bridge response") from exc
        return resp_obj

    def recent_stderr(self, limit: int = 10) -> str:
        if limit <= 0 or not self._stderr_buffer:
            return ""
        lines = list(self._stderr_buffer)[-limit:]
        return "\n".join(lines)

    def init(self, server_url: str, password: str, data_dir: Optional[str] = None) -> Dict[str, Any]:
        return self._send({"cmd": "init", "serverURL": server_url, "password": password, "dataDir": data_dir})

    def list_budgets(self) -> Dict[str, Any]:
        return self._send({"cmd": "listBudgets"})

    def list_accounts(self, budget_id: str, budget_password: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"cmd": "listAccounts", "budgetId": budget_id}
        if budget_password:
            payload["budgetPassword"] = budget_password
        return self._send(payload)

    def list_transactions(
        self,
        budget_id: str,
        account_id: str,
        count: Optional[int] = None,
        budget_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"cmd": "listTransactions", "budgetId": budget_id, "accountId": account_id}
        if count is not None:
            payload["count"] = count
        if budget_password:
            payload["budgetPassword"] = budget_password
        return self._send(payload)

    def upload_transactions(
        self,
        budget_id: str,
        account_id: str,
        transactions: list,
        budget_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "cmd": "uploadTransactions",
            "budgetId": budget_id,
            "accountId": account_id,
            "transactions": transactions,
        }
        if budget_password:
            payload["budgetPassword"] = budget_password
        return self._send(payload)

    def close(self):
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.debug("Failed to stop Actual bridge cleanly: %s", exc)


__all__ = ["ActualBridgeRunner"]
