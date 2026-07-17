import ipaddress
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from config import get_logger
from services.actual_bridge_runner import ActualBridgeRunner


logger = get_logger(__name__)


def _is_loopback_host(hostname: str) -> bool:
    if hostname.lower() == 'localhost':
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_actual_server_url(base_url: str) -> str:
    """Return a normalized Actual URL after enforcing safe transport rules."""
    if not isinstance(base_url, str) or not base_url or base_url != base_url.strip():
        raise ValueError("Actual server URL must be a non-empty URL without surrounding whitespace")
    if any(ord(character) < 32 for character in base_url):
        raise ValueError("Actual server URL contains invalid control characters")

    parsed = urlsplit(base_url)
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError("Actual server URL must be an absolute http:// or https:// URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Actual server URL must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Actual server URL must not contain a query string or fragment")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Actual server URL contains an invalid port") from exc
    if scheme == 'http' and not _is_loopback_host(parsed.hostname):
        raise ValueError("Remote Actual servers must use HTTPS")
    return base_url.rstrip('/')


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
        self.base_url = validate_actual_server_url(base_url)
        if not isinstance(password, str) or not password:
            raise ValueError("Actual server password is required")
        # Use explicit encryption password when provided; otherwise fall back to server password.
        self.download_password = encryption_password or password
        self.data_dir = data_dir
        # Bridge can be injected for testing
        self.bridge = bridge or ActualBridgeRunner(
            project_root=self._project_root
        )
        init_resp = self.bridge.init(self.base_url, password, self.data_dir)
        if not init_resp.get("ok"):
            raise RuntimeError(init_resp.get("error") or "Failed to init Actual bridge")

    def _log_bridge_error(self, resp: dict, context: str) -> bool:
        error = str(resp.get("error") or "Unknown bridge error")
        detail = str(resp.get("details") or "")
        logger.error(
            "[ActualClient] Bridge error during %s: %s",
            context,
            error.replace('\n', ' ')[:500],
        )
        recent = ""
        if self.bridge and hasattr(self.bridge, "recent_stderr"):
            try:
                recent = self.bridge.recent_stderr() or ""
            except Exception:
                recent = ""
        out_of_sync = "out-of-sync-migrations" in "\n".join((error, detail, recent))
        if out_of_sync:
            logger.error(
                "[ActualClient] Actual server appears newer than the installed API client. "
                "Install the reviewed dependencies with npm ci and retry."
            )
        return out_of_sync

    def get_budgets(self) -> list:
        """Return list of budgets with keys id and name."""
        logger.info("[ActualClient] Fetching budgets via bridge")
        return self._get_budgets()

    def _get_budgets(self) -> list:
        resp = self.bridge.list_budgets()
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list budgets")
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Run npm ci from a reviewed checkout or install a matching @actual-app/api build."
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

    def _get_accounts(self, budget_id: str) -> list:
        resp = self.bridge.list_accounts(budget_id, self.download_password)
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list accounts")
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Run npm ci from a reviewed checkout or install a matching @actual-app/api build."
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
    ) -> list:
        resp = self.bridge.list_transactions(
            budget_id,
            account_id,
            count=count,
            budget_password=self.download_password,
        )
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "list transactions")
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Run npm ci from a reviewed checkout or install a matching @actual-app/api build."
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
    ) -> dict:
        resp = self.bridge.upload_transactions(
            budget_id,
            account_id,
            transactions,
            budget_password=self.download_password,
        )
        if not resp.get("ok"):
            out_of_sync = self._log_bridge_error(resp, "upload transactions")
            if out_of_sync:
                raise RuntimeError(
                    "Actual server appears newer than the API client. "
                    "Run npm ci from a reviewed checkout or install a matching @actual-app/api build."
                )
            raise RuntimeError(resp.get("error") or "Failed to upload transactions")
        return resp
