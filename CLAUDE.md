# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Git Workflow
- Commit and push after every change
- Use clear and concise commit messages
- Don't include generation mention in commit messages (no "Generated with Claude" or "Co-Authored-By: Claude")
- Don't batch multiple changes - commit each significant change separately
- ALWAYS run tests and the linter before committing and ensure ALL tests pass
- NEVER introduce failing tests or code that breaks existing tests

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Install dependencies
python3 -m pip install -r requirements.txt
```

## Project Dependencies

This project relies on several Python packages listed in `requirements.txt`.
The major runtime dependencies are:

- **pandas** – data processing and CSV/XLSX handling
- **openpyxl** – Excel file support for `pandas`
- **PyQt5** (>=5.15) – GUI wizard implementation
- **requests** – used by the YNAB API client
- **cryptography** – secure storage of the YNAB token

For development and testing the following tools are used:

- **flake8** – code style checking
- **pytest** – test runner (some tests use pytest fixtures; `unittest` is also used)

Python 3.6 or newer is required. Install all packages with:

```bash
pip install -r requirements.txt
```

Actual API mode uses a Node bridge (`scripts/actual_bridge.js`) and requires:

```bash
npm install
```

### Running the Application
```bash
# CLI Mode - Convert file to YNAB format
python3 cli.py path/to/statement.[xlsx|csv]

# CLI Mode - Convert excluding previously imported transactions
python3 cli.py path/to/statement.[xlsx|csv] --previous path/to/previous_ynab.csv

# GUI Wizard Mode
python3 ui/wizard.py
```

### Development Commands
```bash
# Run all tests - ALL tests must pass
python3 -m unittest discover -s tests -v

# Run tests using pytest - ALL tests must pass
python3 -m pytest

# Check code style
python3 -m flake8 .
```

### Testing Guidelines
- Tests are a critical part of this codebase - ALL tests must pass at all times
- If you're making changes, you MUST ensure all tests continue to pass
- Never delete or comment out tests to make them pass
- Always fix the implementation to match the test expectations
- Add new tests for any new functionality

## Code Architecture

The application is structured with the following components:

### Core Components
1. **Main Module** (`main.py`): Entry point for CLI mode, containing high-level functions for converting bank statements.

2. **Converter Modules**: Specialized modules for each bank format
   - `converter/account.py`: Handles NBG account statements
   - `converter/card.py`: Handles NBG card statements
   - `converter/revolut.py`: Handles Revolut CSV exports
   - `converter/utils.py`: Common utilities for all converters

3. **GUI Wizard** (`ui/wizard.py`): PyQt5-based wizard interface with step-by-step guidance
   - Multiple pages for file selection, authentication, account selection, etc.
   - Uses QThread workers for non-blocking operations
   - Custom RobustWizard class extends QWizard with thread cleanup capabilities
   - SidebarWizardWindow provides a modern UI with navigation sidebar
   - Pages are organized in a logical flow with styled components

4. **Controller** (`ui/controller.py`): Manages interaction between UI and backend services
   - Contains worker classes for background processing in separate QThreads
   - Handles signals between UI components and backend services
   - Uses PyQt signals/slots pattern for asynchronous communication
   - Worker classes: BudgetFetchWorker, AccountFetchWorker, TransactionFetchWorker, DuplicateCheckWorker, UploadWorker
   - WizardController class orchestrates the wizard workflow

5. **Services**:
   - `services/ynab_client.py`: API client for YNAB integration with request caching
   - `services/conversion_service.py`: Business logic for converting between formats

### Data Flow
1. Bank statements (XLSX/CSV) are loaded as pandas DataFrames
2. Format is detected automatically (NBG Account, NBG Card, or Revolut)
3. Specialized converter processes the data based on format
4. Output is generated as a YNAB-compatible CSV file
5. Optional: Data is uploaded to YNAB via API (GUI mode only)

### Configuration and Settings
- User settings stored under `~/.nbg-ynab-export/`:
  - `settings.txt`: encrypted YNAB token and last-used folder
  - `settings.key`: Fernet key used for encryption
  - `actual_settings.txt`: encrypted Actual server URL/password
  - `ynab_api.log`: YNAB API debug log

### UI Architecture

#### Wizard Structure
- **Main Window Class** (`SidebarWizardWindow`): Houses the wizard with a modern sidebar navigation
- **Custom Wizard Class** (`RobustWizard`): Extends QWizard with thread safety features
- **Page Flow**: Import File → Authorization → Account Selection → Transactions → Review & Upload → Finish

#### UI Pages
1. **ImportFilePage**: File selection with drag-and-drop support and validation
2. **YNABAuthPage**: YNAB API token entry with secure storage
3. **AccountSelectionPage**: Budget and account selection using YNAB API data
4. **TransactionsPage**: Displays and manages transaction data with duplicate detection
5. **ReviewAndUploadPage**: Final review and upload transactions to YNAB
6. **FinishPage**: Confirmation and success information

#### Controller Logic
- **WizardController**: Central coordinator connecting UI and services
- **Worker Pattern**: Background tasks run in QThreads to prevent UI freezing
- **Signal/Slot Communication**: Asynchronous data flow between components
- **Error Handling**: Comprehensive error reporting throughout the UI
