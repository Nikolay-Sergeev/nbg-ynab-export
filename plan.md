# NBG/Revolut to YNAB Wizard: Development Plan

## Current Features
- Wizard-style PyQt5 app for importing NBG/Revolut exports and uploading to YNAB
- Secure token management (encrypted, always saved on token entry)
- Step 1: Drag-and-drop or browse for file (large, icon-enhanced, filename only)
- Step 2: Enter YNAB Personal Access Token
- Step 3: Select YNAB budget/account
- Step 4: View last 5 transactions (API errors with SVG icons, word-wrapped)
- Step 5: Review & upload transactions (status column, SVG icons for success/error)
- Step 6: Finish/confirmation
- All API errors are user-friendly and visually clear

## API Rate Limit Optimization (NEW)
- Session-level cache for fetched YNAB transactions
- Only fetches all transactions once per account per session
- Navigating back/forth or re-reviewing does not trigger extra API requests
- Cache is invalidated if budget/account selection changes
- All uploads use batch API endpoint

## UI/UX Improvements (NEW)
- SVG icons for error, success, upload, info
- No unnecessary left margins in drag/drop or error areas
- Only filename shown in file input
- Error messages wrap and are never cut off
- Tooltips for all icons

## Next Steps / Ideas
- **Code Architecture & Refactoring**
  - Extract YNAB API client and file conversion logic into separate modules/services.  # 
  - Replace dynamic `importlib` loads with direct module imports.  # 
  - Ensure hidden settings directory (`~/.nbg-ynab-export`) is created at startup.  # 
  - Integrate `YnabClient` service into UI pages, replacing inline `requests` calls.  # In Progress
  - Extract and modularize conversion logic into a dedicated service (e.g., `ConversionService`) for reuse in UI.  # In Progress
  - Move core conversion logic (`process_*_operations`, `validate_dataframe`, constants) from main.py to the services layer.
  - Refactor token encryption/decryption in YNABAuthPage to reuse utility functions.
  - Verify and potentially fix session cache implementation (`NBGYNABWizard.cached_ynab_transactions`).
  - Address potentially incorrect `get_selected_budget_account` in TransactionsPage.
  - Remove unused imports (e.g., `tempfile`).
- **Performance & Responsiveness**
  - Offload file processing and API calls to background threads (QThread/QRunnable) to avoid UI blocking.
  - Use YNAB API `per_page` parameter to fetch larger batches and reduce pagination calls.
  - Optimize `YnabClient.get_account_name` by caching fetched accounts per budget.
- **Settings & Config Management**
  - Consider using `QSettings` or `configparser` for persistent settings storage.
  - Validate and create settings directory before read/write operations.
- **Error Handling & Logging**
  - Centralize logging to a file for diagnostics (e.g., `~/.nbg-ynab-export/app.log`).
  - Centralize logging configuration at the application entry point (ui_wizard.py's main block).
  - Improve exception granularity and user messages for different error scenarios.
  - Improve amount comparison in UI deduplication (`tx_equal`) to handle floating-point inaccuracies.
  - Provide UI feedback (e.g., table status update) for transactions skipped due to formatting errors.
- **Testing & CI**
  - Add unit tests for conversion utilities, API client, and spinner widget.
  - Add integration tests simulating wizard workflows.
  - Integrate tests into a CI pipeline (GitHub Actions, TravisCI).
- **Packaging & Distribution**
  - Provide a `setup.py` or `pyproject.toml` for pip-installable package.
  - Build standalone executables (PyInstaller) for Windows, macOS, and Linux.
- **User Experience (UX)**
  - Enhance feedback during deduplication in ReviewAndUploadPage (e.g., status label updates).
  - Consider making the `since_date` lookback for deduplication configurable or clearer.
- **Command-Line Interface (CLI)**
  - Consider using `argparse` in main.py for better CLI argument handling.
  - Clarify or align differences between CLI (file-based) and UI (API-based) deduplication logic.

---
_**, existing ideas below:__
- Add warning if user is near API rate limit (e.g., after 180 requests)
- Add live countdown if rate limit is hit (using Retry-After)
- Further reduce requests by caching transactions in Step 4
- Add more SVG icons or color cues for other steps
- Optional: allow user to manually refresh cached data

_Last updated: 2025-04-21_
