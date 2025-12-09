import requests
import logging
from config import get_logger


logger = get_logger(__name__)


class ActualClient:
    """
    Minimal Actual Budget API client exposing a YNAB-like interface so the UI can reuse workers.

    Note: Actual server deployments can vary. Endpoints and payloads below follow the public
    API docs at a high level. If your server uses different routes, adjust the URL paths
    in this client accordingly.
    """

    def __init__(self, base_url: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        # Allow opting out of SSL verification for self-signed servers via env var
        import os as _os
        verify_ssl = (_os.getenv('ACTUAL_VERIFY_SSL', 'true').lower() not in ('0', 'false', 'no'))
        self.session.verify = verify_ssl
        logger.info("[ActualClient] verify_ssl=%s", verify_ssl)

        # Attempt login to obtain a session/token if the server supports it; otherwise rely on password per call
        try:
            login_url = f"{self.base_url}/api/login"
            logger.info("[ActualClient] POST %s (login)", login_url)
            resp = self.session.post(login_url, json={"password": self.password}, timeout=10)
            logger.info("[ActualClient] login status=%s", resp.status_code)
            if resp.ok and 'token' in resp.json():
                token = resp.json()['token']
                self.session.headers.update({'Authorization': f"Bearer {token}"})
        except Exception:
            # Some servers don't require an explicit login; continue without token
            logger.info("[ActualClient] Login endpoint not available or not required; continuing without token")

    def _auth_params(self):
        """Build auth object if server expects password in body/query instead of bearer token."""
        return {"password": self.password}

    def get_budgets(self) -> list:
        """Return list of budgets with keys id and name."""
        try:
            # Prefer bearer header, fallback to password param
            url = f"{self.base_url}/api/budgets"
            logger.info("[ActualClient] GET %s (budgets)", url)
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 401:
                logger.info("[ActualClient] 401 on GET; trying POST %s with auth body", url)
                resp = self.session.post(url, json=self._auth_params(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info("[ActualClient] Budgets response keys=%s", list(data.keys()) if isinstance(data, dict) else type(data))
            budgets = data.get('budgets') or data.get('data') or data
            out = []
            for b in budgets:
                if isinstance(b, dict):
                    out.append({'id': b.get('id') or b.get('uuid') or b.get('budgetId'), 'name': b.get('name')})
            return out
        except Exception as e:
            logger.error("[ActualClient] get_budgets failed: %s", e)
            raise

    def get_accounts(self, budget_id: str) -> list:
        """Return list of accounts for a budget with keys id and name."""
        try:
            url = f"{self.base_url}/api/budgets/{budget_id}/accounts"
            logger.info("[ActualClient] GET %s (accounts)", url)
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 401:
                logger.info("[ActualClient] 401 on GET; trying POST %s with auth body", url)
                resp = self.session.post(url, json=self._auth_params(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info("[ActualClient] Accounts response keys=%s", list(data.keys()) if isinstance(data, dict) else type(data))
            accounts = data.get('accounts') or data.get('data') or data
            out = []
            for a in accounts:
                if isinstance(a, dict):
                    out.append({'id': a.get('id') or a.get('uuid') or a.get('accountId'), 'name': a.get('name')})
            return out
        except Exception as e:
            logger.error("[ActualClient] get_accounts failed: %s", e)
            raise

    def get_transactions(self, budget_id: str, account_id: str, count: int = None, page: int = None, since_date: str = None) -> list:
        """Return recent transactions in a YNAB-like shape for display: date, payee_name, amount, memo.

        Amount is returned in milliunits to match existing UI formatting.
        """
        try:
            params = {"limit": count or 50}
            if since_date:
                params["since_date"] = since_date
            url = f"{self.base_url}/api/budgets/{budget_id}/accounts/{account_id}/transactions"
            logger.info("[ActualClient] GET %s (transactions) params=%s", url, params)
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 401:
                logger.info("[ActualClient] 401 on GET; trying POST %s with auth body+params", url)
                resp = self.session.post(url, json={**self._auth_params(), **params}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            txs = data.get('transactions') or data.get('data') or data
            out = []
            for t in txs:
                if not isinstance(t, dict):
                    continue
                # Try to normalize fields
                date = t.get('date') or t.get('transactionDate')
                payee = t.get('payee') or t.get('payee_name') or t.get('payeeName')
                memo = t.get('notes') or t.get('memo')
                amt = t.get('amount')
                # If amount comes as decimal, convert to milliunits; if already int assume milliunits
                try:
                    if isinstance(amt, (int, float)):
                        amount_milli = int(round(float(amt) * 1000)) if abs(amt) < 100000 else int(amt)
                    elif isinstance(amt, str):
                        amount_milli = int(round(float(amt) * 1000))
                    else:
                        amount_milli = 0
                except Exception:
                    amount_milli = 0
                out.append({
                    'date': date,
                    'payee_name': payee,
                    'amount': amount_milli,
                    'memo': memo,
                })
            return out
        except Exception as e:
            logger.error("[ActualClient] get_transactions failed: %s", e)
            raise

    def upload_transactions(self, budget_id: str, transactions: list) -> dict:
        """Upload transactions; expects transactions similar to YNAB formatting from the UI.

        Returns a dict with 'data' containing 'transactions' or 'transaction_ids' length for UI count.
        """
        try:
            # Map YNAB-like payload to Actual's expected shape
            mapped = []
            for tx in transactions:
                amount_mu = tx.get('amount', 0)  # milliunits
                # Actual commonly uses integer in milliunits as well; if server expects decimal, it can convert
                mapped.append({
                    'date': tx.get('date'),
                    'amount': amount_mu,
                    'payee_name': tx.get('payee_name') or tx.get('payee'),
                    'notes': tx.get('memo', ''),
                    'account_id': tx.get('account_id'),
                })

            url = f"{self.base_url}/api/budgets/{budget_id}/transactions/batch"
            body = {'password': self.password, 'transactions': mapped}
            logger.info("[ActualClient] POST %s (upload) count=%d", url, len(mapped))
            resp = self.session.post(url, json=body, timeout=20)
            if resp.status_code == 401:
                logger.info("[ActualClient] 401 on POST; retrying with same body")
                resp = self.session.post(url, json=body, timeout=20)
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            # Normalize to a YNAB-like response shape for the UI
            tx_ids = []
            tx_list = data.get('transactions') or data.get('data') or []
            for i, t in enumerate(tx_list):
                tx_ids.append(t.get('id') or t.get('uuid') or str(i))
            return {'data': {'transaction_ids': tx_ids, 'transactions': tx_list}}
        except Exception as e:
            logger.error("[ActualClient] upload_transactions failed: %s", e)
            raise
