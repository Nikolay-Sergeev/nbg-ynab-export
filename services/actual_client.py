from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
import json
import subprocess
import threading
from config import get_logger
from services.actual_bridge_runner import ActualBridgeRunner


logger = get_logger(__name__)


class ActualClient:
    """
    Minimal Actual Budget API client exposing a YNAB-like interface so the UI can reuse workers.

    Note: Actual server deployments can vary. Endpoints and payloads below follow the public
    API docs at a high level. If your server uses different routes, adjust the URL paths
    in this client accordingly.
    """

    def __init__(
        self,
        base_url: str,
        password: str,
        encryption_password: Optional[str] = None,
        data_dir: Optional[str] = None,
        bridge: Optional[ActualBridgeRunner] = None,
    ):
        self._project_root = Path(__file__).resolve().parent.parent
        # Bridge-based client using @actual-app/api via Node
        self.base_url = base_url.rstrip('/')
        self.password = password
        # Use explicit encryption password when provided; otherwise fall back to server password.
        self.download_password = encryption_password or password
        self.data_dir = data_dir
        self._npm_install_attempts = set()
        self._npm_install_lock = threading.Lock()
        self._dist_tags = None
        parsed = urlparse(self.base_url)
        if parsed.scheme.lower() == "http":
            host = (parsed.hostname or "").lower()
            if host not in ("localhost", "127.0.0.1", "::1"):
                logger.warning("[ActualClient] Insecure HTTP URL for remote server: %s", self.base_url)
        elif parsed.scheme and parsed.scheme.lower() != "https":
            logger.warning("[ActualClient] Unrecognized URL scheme for Actual server: %s", self.base_url)
        # Bridge can be injected for testing
        self.bridge = bridge or ActualBridgeRunner(
            project_root=self._project_root
        )
        init_resp = self.bridge.init(self.base_url, self.password, self.data_dir)
        if not init_resp.get("ok"):
            raise RuntimeError(init_resp.get("error") or "Failed to init Actual bridge")

    def _restart_bridge(self) -> bool:
        try:
            if self.bridge:
                self.bridge.close()
        except Exception:
            pass
        try:
            self.bridge = ActualBridgeRunner(project_root=self._project_root)
            init_resp = self.bridge.init(self.base_url, self.password, self.data_dir)
            if not init_resp.get("ok"):
                logger.error("[ActualClient] Bridge re-init failed: %s", init_resp.get("error"))
                return False
            return True
        except Exception as exc:
            logger.error("[ActualClient] Failed to restart Actual bridge: %s", exc)
            return False

    def _attempt_npm_install(self, package_spec: Optional[str] = None) -> bool:
        spec_key = package_spec or "default"
        with self._npm_install_lock:
            if spec_key in self._npm_install_attempts:
                return False
            self._npm_install_attempts.add(spec_key)
        package_json = self._project_root / "package.json"
        if not package_json.exists():
            logger.error("[ActualClient] package.json not found; cannot run npm install")
            return False
        try:
            if package_spec:
                logger.warning(
                    "[ActualClient] Running npm install %s to update Actual API client", package_spec
                )
                cmd = ["npm", "install", package_spec]
            else:
                logger.warning("[ActualClient] Running npm install to update Actual API client")
                cmd = ["npm", "install"]
            result = subprocess.run(
                cmd,
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            logger.error("[ActualClient] npm install failed: %s", exc)
            return False
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            if stderr:
                logger.error("[ActualClient] npm install stderr: %s", stderr)
            if stdout:
                logger.error("[ActualClient] npm install stdout: %s", stdout)
            return False
        if not self._restart_bridge():
            return False
        logger.info("[ActualClient] npm install completed; bridge restarted")
        return True

    def _npm_view_dist_tags(self) -> dict:
        if isinstance(self._dist_tags, dict):
            return self._dist_tags
        try:
            result = subprocess.run(
                ["npm", "view", "@actual-app/api", "dist-tags", "--json"],
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception as exc:
            logger.error("[ActualClient] npm view dist-tags failed: %s", exc)
            self._dist_tags = {}
            return self._dist_tags
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                logger.error("[ActualClient] npm view dist-tags stderr: %s", stderr)
            self._dist_tags = {}
            return self._dist_tags
        try:
            payload = json.loads((result.stdout or "").strip() or "{}")
        except json.JSONDecodeError:
            logger.error("[ActualClient] npm view dist-tags returned invalid JSON")
            self._dist_tags = {}
            return self._dist_tags
        self._dist_tags = payload if isinstance(payload, dict) else {}
        return self._dist_tags

    def _attempt_npm_install_from_tags(self) -> bool:
        tags = self._npm_view_dist_tags()
        if not tags:
            logger.error("[ActualClient] No dist-tags available for @actual-app/api")
            return False
        preferred = ("next", "beta", "canary", "preview", "rc", "nightly", "dev")
        for tag in preferred:
            if tag in tags:
                return self._attempt_npm_install(f"@actual-app/api@{tag}")
        for tag in sorted(tags.keys()):
            if tag == "latest":
                continue
            return self._attempt_npm_install(f"@actual-app/api@{tag}")
        logger.error("[ActualClient] No non-latest dist-tag available for @actual-app/api")
        return False

    def _log_bridge_error(self, resp: dict, context: str) -> bool:
        out_of_sync = False
        detail = resp.get("details")
        if detail:
            logger.error("[ActualClient] Bridge error detail during %s: %s", context, detail)
            if "out-of-sync-migrations" in detail:
                out_of_sync = True
                logger.error(
                    "[ActualClient] Actual server appears newer than the API client. "
                    "Update @actual-app/api (npm install) and retry."
                )
            return out_of_sync
        recent = None
        if self.bridge and hasattr(self.bridge, "recent_stderr"):
            try:
                recent = self.bridge.recent_stderr()
            except Exception:
                recent = None
        if recent:
            logger.error("[ActualClient] Bridge stderr during %s: %s", context, recent)
            if "out-of-sync-migrations" in recent:
                out_of_sync = True
                logger.error(
                    "[ActualClient] Actual server appears newer than the API client. "
                    "Update @actual-app/api (npm install) and retry."
                )
        if "out-of-sync-migrations" in (resp.get("error") or ""):
            out_of_sync = True
        return out_of_sync

    def get_budgets(self) -> list:
        """Return list of budgets with keys id and name."""
        logger.info("[ActualClient] Fetching budgets via bridge")
        return self._get_budgets()

    def _get_budgets(self, retry_stage: int = 0) -> list:
        resp = self.bridge.list_budgets()
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list budgets")
            if out_of_sync and retry_stage < 1 and self._attempt_npm_install():
                logger.info("[ActualClient] Retrying list budgets after npm install")
                return self._get_budgets(retry_stage=1)
            if out_of_sync and retry_stage < 2 and self._attempt_npm_install_from_tags():
                logger.info("[ActualClient] Retrying list budgets after npm install from dist-tags")
                return self._get_budgets(retry_stage=2)
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Automatic npm updates failed; update the server or install a matching @actual-app/api build."
                )
            raise RuntimeError(resp.get("error") or "Failed to list budgets")
        budgets = resp.get("budgets") or []
        seen_ids = set()
        by_name = {}
        for b in budgets:
            # Prefer groupId because Actual's downloadBudget expects the sync id (groupId)
            bid = (
                b.get("groupId")
                or b.get("id")
                or b.get("cloudFileId")
                or b.get("fileId")
                or b.get("syncId")
                or b.get("uuid")
            )
            name = b.get("name") or b.get("budgetName")
            if not bid or not name:
                continue
            if bid in seen_ids:
                continue

            entry = {
                "id": bid,
                "name": name,
                "_state": (b.get("state") or "").lower(),
            }
            if name in by_name:
                existing = by_name[name]
                existing_remote = existing.get("_state") == "remote"
                candidate_remote = entry["_state"] == "remote"
                if candidate_remote and not existing_remote:
                    by_name[name] = entry
            else:
                by_name[name] = entry

            seen_ids.add(bid)
        return [{"id": b["id"], "name": b["name"]} for b in by_name.values()]

    def get_accounts(self, budget_id: str) -> list:
        """Return list of accounts for a budget with keys id and name."""
        logger.info("[ActualClient] Fetching accounts for budget=%s via bridge", budget_id)
        return self._get_accounts(budget_id)

    def _get_accounts(self, budget_id: str, retry_stage: int = 0) -> list:
        resp = self.bridge.list_accounts(budget_id, self.download_password)
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list accounts")
            if out_of_sync and retry_stage < 1 and self._attempt_npm_install():
                logger.info("[ActualClient] Retrying list accounts after npm install")
                return self._get_accounts(budget_id, retry_stage=1)
            if out_of_sync and retry_stage < 2 and self._attempt_npm_install_from_tags():
                logger.info("[ActualClient] Retrying list accounts after npm install from dist-tags")
                return self._get_accounts(budget_id, retry_stage=2)
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Automatic npm updates failed; update the server or install a matching @actual-app/api build."
                )
            raise RuntimeError(resp.get("error") or "Failed to list accounts")
        return resp.get("accounts") or []

    def get_transactions(
        self,
        budget_id: str,
        account_id: str,
        count: int = None,
        page: int = None,
        since_date: str = None,
    ) -> list:
        """Return recent transactions in a YNAB-like shape for display: date, payee_name, amount, memo."""
        logger.info(
            "[ActualClient] Fetching transactions for budget=%s account=%s via bridge",
            budget_id,
            account_id,
        )
        return self._get_transactions(budget_id, account_id, count=count, since_date=since_date)

    def _get_transactions(
        self,
        budget_id: str,
        account_id: str,
        count: int = None,
        since_date: str = None,
        retry_stage: int = 0,
    ) -> list:
        resp = self.bridge.list_transactions(
            budget_id,
            account_id,
            count=count,
            budget_password=self.download_password,
        )
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list transactions")
            if out_of_sync and retry_stage < 1 and self._attempt_npm_install():
                logger.info("[ActualClient] Retrying list transactions after npm install")
                return self._get_transactions(
                    budget_id,
                    account_id,
                    count=count,
                    since_date=since_date,
                    retry_stage=1,
                )
            if out_of_sync and retry_stage < 2 and self._attempt_npm_install_from_tags():
                logger.info("[ActualClient] Retrying list transactions after npm install from dist-tags")
                return self._get_transactions(
                    budget_id,
                    account_id,
                    count=count,
                    since_date=since_date,
                    retry_stage=2,
                )
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Automatic npm updates failed; update the server or install a matching @actual-app/api build."
                )
            raise RuntimeError(resp.get("error") or "Failed to list transactions")
        txs = resp.get("transactions") or []
        # Optional since_date filter (inclusive)
        if since_date:
            txs = [t for t in txs if (t.get("date") or "") >= since_date]
        return txs

    def upload_transactions(self, budget_id: str, account_id: str, transactions: list) -> dict:
        """Upload transactions; expects transactions similar to YNAB formatting from the UI.

        Returns a dict with 'data' containing 'transactions' or 'transaction_ids' length for UI count.
        """
        resp = self._upload_transactions(budget_id, account_id, transactions)
        uploaded = resp.get("uploaded", 0)
        return {
            'data': {
                'transaction_ids': [str(i) for i in range(uploaded)],
                'transactions': [{}] * uploaded,
            }
        }

    def _upload_transactions(
        self,
        budget_id: str,
        account_id: str,
        transactions: list,
        retry_stage: int = 0,
    ) -> dict:
        resp = self.bridge.upload_transactions(
            budget_id,
            account_id,
            transactions,
            budget_password=self.download_password,
        )
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "upload transactions")
            if out_of_sync and retry_stage < 1 and self._attempt_npm_install():
                logger.info("[ActualClient] Retrying upload after npm install")
                return self._upload_transactions(
                    budget_id,
                    account_id,
                    transactions,
                    retry_stage=1,
                )
            if out_of_sync and retry_stage < 2 and self._attempt_npm_install_from_tags():
                logger.info("[ActualClient] Retrying upload after npm install from dist-tags")
                return self._upload_transactions(
                    budget_id,
                    account_id,
                    transactions,
                    retry_stage=2,
                )
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Automatic npm updates failed; update the server or install a matching @actual-app/api build."
                )
            raise RuntimeError(resp.get("error") or "Failed to upload transactions")
        return resp
