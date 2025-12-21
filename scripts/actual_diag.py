#!/usr/bin/env python3
"""
Quick diagnostic tool for Actual Budget server connectivity.

Usage:
  python scripts/actual_diag.py --url https://actual.example.com --password YOUR_PASSWORD [--no-verify]
"""
import argparse
import json
import logging
import os
import sys
from urllib.parse import urlparse

# Ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.actual_client import ActualClient  # noqa: E402
from config import SETTINGS_DIR, ensure_app_dir  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True, help='Base URL of Actual server, e.g., https://host:port')
    ap.add_argument('--password', required=True, help='Server password')
    ap.add_argument('--no-verify', action='store_true', help='Disable SSL verification for self-signed certs')
    ap.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = ap.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    if args.no_verify:
        os.environ['ACTUAL_VERIFY_SSL'] = 'false'

    parsed = urlparse(args.url)
    if parsed.scheme.lower() == "http":
        host = (parsed.hostname or "").lower()
        if host not in ("localhost", "127.0.0.1", "::1"):
            print("WARNING: Using insecure http:// for a remote server.", file=sys.stderr)

    print('== Creating client ==')
    ensure_app_dir()
    data_dir = SETTINGS_DIR / "actual-data"
    client = ActualClient(args.url, args.password, data_dir=str(data_dir))

    print('== Fetching budgets ==')
    try:
        budgets = client.get_budgets()
        print(f'Budgets ({len(budgets)}):')
        print(json.dumps(budgets, indent=2))
    except Exception as e:
        print('Error fetching budgets:', e)
        return 1

    if budgets:
        first = budgets[0]['id']
        print(f'== Fetching accounts for budget {first} ==')
        try:
            accounts = client.get_accounts(first)
            print(f'Accounts ({len(accounts)}):')
            print(json.dumps(accounts, indent=2))
        except Exception as e:
            print('Error fetching accounts:', e)
            return 1

        if accounts:
            acc = accounts[0]['id']
            print(f'== Fetching transactions for budget {first} account {acc} ==')
            try:
                tx = client.get_transactions(first, acc, count=5)
                print(f'Transactions ({len(tx)} shown):')
                print(json.dumps(tx, indent=2))
            except Exception as e:
                print('Error fetching transactions:', e)
                return 1

    print('Diagnosis complete.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
