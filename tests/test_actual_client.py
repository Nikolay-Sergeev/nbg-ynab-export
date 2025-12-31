from services.actual_client import ActualClient


class FakeBridge:
    def __init__(self):
        self.inited = False
        self.init_args = None

    def init(self, server_url, password, data_dir=None):
        self.inited = True
        self.init_args = (server_url, password, data_dir)
        return {"ok": True}

    def list_budgets(self):
        return {
            "ok": True,
            "budgets": [
                {"cloudFileId": "abc123", "groupId": "sync-1", "name": "Remote Budget"},
                {"id": "with-id", "name": "Local Budget"},
                {"groupId": "sync-1", "name": "Remote Budget Duplicate"},
                {"cloudFileId": None, "name": "No id"},
            ],
        }


def test_get_budgets_normalizes_cloud_file_id_and_filters_missing_ids():
    bridge = FakeBridge()
    client = ActualClient("https://example.com", "pw", bridge=bridge)

    budgets = client.get_budgets()

    assert bridge.inited is True
    assert budgets == [
        {"id": "sync-1", "name": "Remote Budget"},
        {"id": "with-id", "name": "Local Budget"},
    ]


def test_get_transactions_uses_bridge_and_filters_since_date():
    class BridgeWithTx(FakeBridge):
        def list_transactions(self, budget_id, account_id, count=None, budget_password=None):
            self.last_args = (budget_id, account_id, count, budget_password)
            return {
                "ok": True,
                "transactions": [
                    {"date": "2024-01-01", "amount": 10},
                    {"date": "2024-02-01", "amount": 20},
                ],
            }

    bridge = BridgeWithTx()
    client = ActualClient("https://example.com", "pw", bridge=bridge)

    txs = client.get_transactions("b1", "a1", since_date="2024-02-01")
    assert txs == [{"date": "2024-02-01", "amount": 20}]
    assert bridge.last_args == ("b1", "a1", None, "pw")


def test_get_accounts_uses_encryption_password_when_provided():
    class BridgeWithAccounts(FakeBridge):
        def __init__(self):
            super().__init__()
            self.last_args = None

        def list_accounts(self, budget_id, budget_password=None):
            self.last_args = (budget_id, budget_password)
            return {"ok": True, "accounts": []}

    bridge = BridgeWithAccounts()
    client = ActualClient("https://example.com", "server-pw", encryption_password="e2e-pw", bridge=bridge)

    accounts = client.get_accounts("budget-1")

    assert accounts == []
    assert bridge.last_args == ("budget-1", "e2e-pw")


def test_get_budgets_prefers_remote_for_duplicate_names():
    class BridgeWithDup(FakeBridge):
        def list_budgets(self):
            return {
                "ok": True,
                "budgets": [
                    {"id": "local-id", "groupId": "old-sync", "name": "Budget A"},
                    {"groupId": "new-sync", "name": "Budget A", "state": "remote", "cloudFileId": "file-1"},
                ],
            }

    bridge = BridgeWithDup()
    client = ActualClient("https://example.com", "pw", bridge=bridge)

    budgets = client.get_budgets()

    assert budgets == [{"id": "new-sync", "name": "Budget A"}]
