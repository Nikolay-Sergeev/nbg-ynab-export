import logging
from typing import Optional
from pathlib import Path
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

    def __init__(self, base_url: str, password: str, data_dir: Optional[str] = None, bridge: Optional[ActualBridgeRunner] = None):
        # Bridge-based client using @actual-app/api via Node
        self.base_url = base_url.rstrip('/')
        self.password = password
        # Bridge can be injected for testing
        self.bridge = bridge or ActualBridgeRunner(project_root=Path(__file__).resolve().parent.parent)
        init_resp = self.bridge.init(self.base_url, self.password, data_dir)
        if not init_resp.get("ok"):
            raise RuntimeError(init_resp.get("error") or "Failed to init Actual bridge")

    def get_budgets(self) -> list:
        """Return list of budgets with keys id and name."""
        logger.info("[ActualClient] Fetching budgets via bridge")
        resp = self.bridge.list_budgets()
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error") or "Failed to list budgets")
        budgets = resp.get("budgets") or []
        normalized = []
        seen_ids = set()
        seen_names = set()
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
            if bid in seen_ids or name in seen_names:
                continue
            normalized.append({"id": bid, "name": name})
            seen_ids.add(bid)
            seen_names.add(name)
        return normalized

    def get_accounts(self, budget_id: str) -> list:
        """Return list of accounts for a budget with keys id and name."""
        logger.info("[ActualClient] Fetching accounts for budget=%s via bridge", budget_id)
        resp = self.bridge.list_accounts(budget_id)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error") or "Failed to list accounts")
        return resp.get("accounts") or []

    def get_transactions(self, budget_id: str, account_id: str, count: int = None, page: int = None, since_date: str = None) -> list:
        """Return recent transactions in a YNAB-like shape for display: date, payee_name, amount, memo."""
        logger.info("[ActualClient] Fetching transactions for budget=%s account=%s via bridge", budget_id, account_id)
        resp = self.bridge.list_transactions(budget_id, account_id, count=count)
        if not resp.get("ok"):
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
        resp = self.bridge.upload_transactions(budget_id, account_id, transactions)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error") or "Failed to upload transactions")
        uploaded = resp.get("uploaded", 0)
        return {'data': {'transaction_ids': [str(i) for i in range(uploaded)], 'transactions': [{}] * uploaded}}
