import requests
import logging
import os

# Setup YNAB API debug logging
# Prefer a writable path inside the project to avoid sandbox issues.
api_logger = logging.getLogger('ynab_api')
api_logger.setLevel(logging.DEBUG)

try:
    # Allow overriding via env var
    base_dir = os.getenv('YNAB_LOG_DIR')
    if not base_dir:
        # Default to project root /.nbg-ynab-export (services/.. = project root)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_dir = os.path.join(project_root, '.nbg-ynab-export')
    os.makedirs(base_dir, exist_ok=True)
    ynab_log_file = os.path.join(base_dir, 'ynab_api.log')

    api_file_handler = logging.FileHandler(ynab_log_file, mode='a')
    api_file_handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    )
    api_logger.addHandler(api_file_handler)
except Exception as _e:
    # Fall back to a null handler if we cannot write logs
    api_logger.addHandler(logging.NullHandler())

# Root logger for general application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='a'
)


class YnabClient:
    """Client for interacting with the YNAB HTTP API."""
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}
        # Cache accounts per budget to avoid repeated API calls
        self._accounts_cache = {}

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

    def get_transactions(
        self,
        budget_id: str,
        account_id: str,
        count: int = None,
        page: int = None,
        since_date: str = None,
    ) -> list:
        """Fetch transactions; supports optional count and page parameters."""
        url = (
            f"{self.BASE_URL}/budgets/{budget_id}/accounts/"
            f"{account_id}/transactions"
        )
        params = {}
        if count is not None:
            params['count'] = count
        if page is not None:
            params['page'] = page
        if since_date is not None:
            params['since_date'] = since_date
        resp = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=15,
        )
        self._log_api('GET', url, resp, params)
        resp.raise_for_status()
        return resp.json()['data']['transactions']

    def get_account_name(self, budget_id: str, account_id: str) -> str:
        # Use cached accounts list if available
        if budget_id not in self._accounts_cache:
            self._accounts_cache[budget_id] = self.get_accounts(budget_id)
        accounts = self._accounts_cache[budget_id]
        for acc in accounts:
            if acc['id'] == account_id:
                return acc['name']
        return "Unknown Account"

    def upload_transactions(self, budget_id: str, transactions: list) -> dict:
        """Upload new transactions to a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        data = {"transactions": transactions}
        resp = requests.post(
            url,
            headers={**self.headers, "Content-Type": "application/json"},
            json=data,
            timeout=20,
        )
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
            api_logger.debug('[YNAB API] %s', log_entry)
        except Exception as e:
            logging.error('Failed to log YNAB API call: %s', e)
