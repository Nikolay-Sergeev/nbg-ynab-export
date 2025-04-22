# NBG/Revolut to YNAB Wizard: Development Plan

## Next Steps / Ideas
- **Code Architecture & Refactoring (Senior‑Level Overhaul) # In Progress**
  - Clear separation of concerns:
    - `cli.py` for CLI & logging setup
    - `config.py` for constants and QSettings-backed prefs
    - `converter/` for pure data-transforms with type hints & tests
    - `services/` for I/O clients (YnabClient, ConversionService)
    - `ui/` for Qt pages emitting signals; `controller.py` orchestrates logic
  - Modern Python practices: `argparse`, `pathlib`, `dataclasses`, full type hints
  - Robust logging: per-module loggers via `get_logger`, catch only at top-level
  - Testability: pure functions in `converter/` with pytest suites in `tests/`
  - Proposed structure:
    ```
    .
    ├── cli.py
    ├── config.py
    ├── converter/
    ├── services/
    ├── ui/
    ├── tests/
    └── requirements.txt
    ```
  - **Next**: scaffold directories/files & migrate existing code into modules
- ~~**Error Handling & Logging**~~ (Completed 2025-04-28)
  - ~~Centralize logging configuration at the application entry point (`ui_wizard.py`'s main block).~~
  - ~~Centralize logging to a file for diagnostics (e.g., `~/.nbg-ynab-export/app.log`).~~
  - ~~Improve exception granularity and user messages for different error scenarios.~~
  - ~~Improve amount comparison in UI deduplication (`tx_equal`) to handle floating-point inaccuracies.~~
  - ~~Provide UI feedback (e.g., table status update) for transactions skipped due to formatting errors.~~
- ~~**Performance & Responsiveness**~~ (Completed 2025-04-21)
  - ~~Optimize `YnabClient.get_account_name` by caching fetched accounts per budget.~~
  - ~~Use YNAB API `per_page` parameter to fetch larger batches and reduce pagination calls (e.g., 200 for `get_all_transactions`).~~
  - ~~Offload file processing and API calls to background threads (QThread/QRunnable) to avoid UI blocking.~~
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
