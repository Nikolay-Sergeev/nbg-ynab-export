import requests
import logging
import os

# Setup YNAB API debug logging
ynab_log_file = os.path.expanduser('~/.nbg-ynab-export/ynab_api.log')
logging.basicConfig(
    filename=ynab_log_file,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='a'
)


class YnabClient:
    """Client for interacting with the YNAB HTTP API."""
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_budgets(self) -> list:
        """Fetch list of budgets."""
        url = f"{self.BASE_URL}/budgets"
        resp = requests.get(url, headers=self.headers, timeout=10)
        self._log_api('GET', url, resp)
        resp.raise_for_status()
        return resp.json()['data']['budgets']

    def get_accounts(self, budget_id: str) -> list:
        """Fetch list of accounts for a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts"
        resp = requests.get(url, headers=self.headers, timeout=10)
        self._log_api('GET', url, resp)
        resp.raise_for_status()
        return resp.json()['data']['accounts']

    def get_transactions(self, budget_id: str, account_id: str, count: int = None, page: int = None, since_date: str = None) -> list:
        """Fetch transactions; supports optional count and page parameters."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts/{account_id}/transactions"
        params = {}
        if count is not None:
            params['count'] = count
        if page is not None:
            params['page'] = page
        if since_date is not None:
            params['since_date'] = since_date
        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        self._log_api('GET', url, resp, params)
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

    def get_account_name(self, budget_id: str, account_id: str) -> str:
        accounts = self.get_accounts(budget_id)
        for acc in accounts:
            if acc['id'] == account_id:
                return acc['name']
        return "Unknown Account"

    def upload_transactions(self, budget_id: str, transactions: list) -> dict:
        """Upload new transactions to a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        data = {"transactions": transactions}
        resp = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=data, timeout=20)
        self._log_api('POST', url, resp, json=data)
        resp.raise_for_status()
        return resp.json()

    def _log_api(self, method, url, resp, params=None, json=None):
        try:
            log_entry = {
                'method': method,
                'url': url,
                'status_code': resp.status_code,
                'params': params,
                'json': json,
                'response': resp.text[:10000]  # Avoid logging huge responses
            }
            logging.debug('[YNAB API] %s', log_entry)
        except Exception as e:
            logging.error('Failed to log YNAB API call: %s', e)
