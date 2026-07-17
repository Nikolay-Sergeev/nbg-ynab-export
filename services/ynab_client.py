import requests
import logging
import os
import re
from config import SETTINGS_DIR, ensure_app_dir

# Setup YNAB API logging
# Prefer a writable path inside the project to avoid sandbox issues.
api_logger = logging.getLogger('ynab_api')
_log_verbose = os.getenv('YNAB_API_DEBUG', '').lower() in ('1', 'true', 'yes') \
    or os.getenv('YNAB_LOG_VERBOSE', '').lower() in ('1', 'true', 'yes')
_log_level = logging.DEBUG if _log_verbose else logging.WARNING
api_logger.setLevel(_log_level)

try:
    # Allow overriding via env var
    base_dir = os.getenv('YNAB_LOG_DIR')
    if not base_dir:
        # Default to user settings dir (~/.nbg-ynab-export), fallback to project-local if needed.
        try:
            ensure_app_dir()
            base_dir = str(SETTINGS_DIR)
        except Exception:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, '.nbg-ynab-export')
    os.makedirs(base_dir, exist_ok=True)
    ynab_log_file = os.path.join(base_dir, 'ynab_api.log')

    api_file_handler = logging.FileHandler(ynab_log_file, mode='a')
    api_file_handler.setLevel(_log_level)
    api_file_handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    )
    api_logger.addHandler(api_file_handler)
    try:
        os.chmod(ynab_log_file, 0o600)
    except OSError:
        pass
except Exception:
    # Fall back to a null handler if we cannot write logs
    api_logger.addHandler(logging.NullHandler())

# Root logger for general application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='a'
)


def _redact_resource_ids(url: str) -> str:
    redacted = re.sub(r'(/budgets/)[^/]+', r'\1<budget-id>', url)
    return re.sub(r'(/accounts/)[^/]+', r'\1<account-id>', redacted)


def _payload_shape(payload):
    """Describe a request without persisting financial transaction contents."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        shape = {}
        for key, value in payload.items():
            if isinstance(value, (list, tuple)):
                shape[key] = {'type': 'list', 'count': len(value)}
            elif isinstance(value, dict):
                shape[key] = {'type': 'object', 'keys': sorted(value.keys())}
            else:
                shape[key] = {'type': type(value).__name__}
        return shape
    return {'type': type(payload).__name__}


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
                'url': _redact_resource_ids(url),
                'status_code': resp.status_code,
                'params': params,
            }
            if _log_verbose:
                log_entry['request_shape'] = _payload_shape(json)
                response_content = getattr(resp, 'content', b'') or b''
                log_entry['response_bytes'] = len(response_content)
            if resp.status_code >= 400:
                api_logger.warning('[YNAB API] %s', log_entry)
            else:
                api_logger.debug('[YNAB API] %s', log_entry)
        except Exception as e:
            logging.error('Failed to log YNAB API call: %s', e)
