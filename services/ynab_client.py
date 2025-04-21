import requests


class YnabClient:
    """Client for interacting with the YNAB HTTP API."""
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_budgets(self) -> list:
        """Fetch list of budgets."""
        url = f"{self.BASE_URL}/budgets"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()['data']['budgets']

    def get_accounts(self, budget_id: str) -> list:
        """Fetch list of accounts for a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()['data']['accounts']

    def get_transactions(self, budget_id: str, account_id: str, count: int = None, page: int = None) -> list:
        """Fetch transactions; supports optional count and page parameters."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts/{account_id}/transactions"
        params = {}
        if count is not None:
            params['count'] = count
        if page is not None:
            params['page'] = page
        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()['data']['transactions']

    def get_all_transactions(self, budget_id: str, account_id: str) -> list:
        """Fetch all transactions with automatic pagination."""
        all_tx = []
        page = 1
        while True:
            txs = self.get_transactions(budget_id, account_id, page=page)
            if not txs:
                break
            all_tx.extend(txs)
            if len(txs) < 30:
                break
            page += 1
        return all_tx

    def upload_transactions(self, budget_id: str, transactions: list) -> dict:
        """Upload new transactions to a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        data = {"transactions": transactions}
        resp = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=data, timeout=20)
        resp.raise_for_status()
        return resp.json()
