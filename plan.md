# NBG/Revolut to YNAB Wizard: Development Plan

## Next Steps / Ideas
- **Code Architecture & Refactoring**
  - ~~Extract and modularize conversion logic into a dedicated service (e.g., `ConversionService`) for reuse in UI.  # In Progress~~ (Completed 2025-04-21)
  - ~~Move core conversion logic (`process_*_operations`, `validate_dataframe`, constants) from `main.py` to the services layer.~~ (Completed 2025-04-21)
  - ~~Integrate `YnabClient` service into UI pages, replacing inline `requests` calls.  # In Progress~~ (Completed 2025-04-22)
  - ~~Refactor token encryption/decryption in `YNABAuthPage` to reuse utility functions.  # In Progress~~ (Completed 2025-04-23)
  - ~~Replace dynamic `importlib` loads with direct module imports.  # In Progress~~ (Completed 2025-04-24)
  - ~~Verify and potentially fix session cache implementation (`NBGYNABWizard.cached_ynab_transactions`).  # In Progress~~ (Completed 2025-04-25)
  - ~~Address potentially incorrect `get_selected_budget_account` in `TransactionsPage`.  # In Progress~~ (Completed 2025-04-26)
  - ~~Ensure hidden settings directory (`~/.nbg-ynab-export`) is created at startup.  # In Progress~~ (Completed 2025-04-27)
  - ~~Remove unused imports (e.g., `tempfile`).~~ (Completed 2025-04-21)
- ~~**Error Handling & Logging**~~ (Completed 2025-04-28)
  - ~~Centralize logging configuration at the application entry point (`ui_wizard.py`'s main block).~~
  - ~~Centralize logging to a file for diagnostics (e.g., `~/.nbg-ynab-export/app.log`).~~
  - ~~Improve exception granularity and user messages for different error scenarios.~~
  - ~~Improve amount comparison in UI deduplication (`tx_equal`) to handle floating-point inaccuracies.~~
  - ~~Provide UI feedback (e.g., table status update) for transactions skipped due to formatting errors.~~
- **Performance & Responsiveness**
  - Optimize `YnabClient.get_account_name` by caching fetched accounts per budget.  # In Progress
  - Use YNAB API `per_page` parameter to fetch larger batches and reduce pagination calls (e.g., 200 for `get_all_transactions`).  # In Progress
  - Offload file processing and API calls to background threads (QThread/QRunnable) to avoid UI blocking.  # In Progress
- **Settings & Config Management**
  - Validate and create settings directory before read/write operations.
  - Consider using `QSettings` or `configparser` for persistent settings storage.
- **User Experience (UX)**
  - Enhance feedback during deduplication in `ReviewAndUploadPage` (e.g., status label updates).
  - Consider making the `since_date` lookback for deduplication configurable or clearer.
- **Testing & CI**
  - Add unit tests for conversion utilities, API client, and spinner widget.
  - Add integration tests simulating wizard workflows.
- **Packaging & Distribution**
  - Provide a `setup.py` or `pyproject.toml` for pip-installable package.
  - Build standalone executables (PyInstaller) for Windows, macOS, and Linux.
- **Command-Line Interface (CLI)**
  - Consider using `argparse` in `main.py` for better CLI argument handling.
  - Clarify or align differences between CLI (file-based) and UI (API-based) deduplication logic.

---
_**, existing ideas below:__
- Add warning if user is near API rate limit (e.g., after 180 requests)
- Add live countdown if rate limit is hit (using Retry-After)
- Further reduce requests by caching transactions in Step 4
- Add more SVG icons or color cues for other steps
- Optional: allow user to manually refresh cached data

_Last updated: 2025-04-28_
