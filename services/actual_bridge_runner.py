import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from config import get_logger

logger = get_logger(__name__)


class ActualBridgeRunner:
    """
    Thin wrapper to talk to the Node-based Actual bridge via stdin/stdout.
    """

    def __init__(self, project_root: Optional[Path] = None):
        root = project_root or Path(__file__).resolve().parent.parent
        script_path = root / "scripts" / "actual_bridge.js"
        if not script_path.exists():
            raise FileNotFoundError(f"Actual bridge script missing: {script_path}")
        # Ensure data dir exists when bridge writes cache
        self.process = subprocess.Popen(
            ["node", str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._lock = threading.Lock()

    def _read_json_line(self) -> Dict[str, Any]:
        """
        Read lines until we get a valid JSON response, skipping noisy stdout logs that the
        Actual API occasionally emits (e.g., "Loading fresh spreadsheet").
        """
        assert self.process and self.process.stdout is not None
        max_attempts = 100
        for _ in range(max_attempts):
            resp_line = self.process.stdout.readline()
            if not resp_line:
                break
            try:
                return json.loads(resp_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON bridge output: %s", resp_line.strip())
                continue
        raise RuntimeError("No valid JSON response from Actual bridge")

    def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if not self.process or self.process.poll() is not None:
                raise RuntimeError("Actual bridge process is not running")
            line = json.dumps(payload) + "\n"
            assert self.process.stdin is not None
            self.process.stdin.write(line)
            self.process.stdin.flush()
            resp_obj = self._read_json_line()
        return resp_obj

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
        except Exception:
            pass


__all__ = ["ActualBridgeRunner"]
