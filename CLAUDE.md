# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Git Workflow
- Commit and push after every change
- Use clear and concise commit messages
- Don't include generation mention in commit messages (no "Generated with Claude" or "Co-Authored-By: Claude")
- Don't batch multiple changes - commit each significant change separately

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Install dependencies
python3 -m pip install -r requirements.txt
```

### Running the Application
```bash
# CLI Mode - Convert file to YNAB format
python3 main.py path/to/statement.[xlsx|csv]

# CLI Mode - Convert excluding previously imported transactions
python3 main.py path/to/statement.[xlsx|csv] path/to/previous_ynab.csv

# GUI Wizard Mode
python3 ui/wizard.py
```

### Development Commands
```bash
# Run tests (unittest)
python3 -m unittest discover -s test -v

# Run tests (pytest)
python3 -m pytest

# Check code style
python3 -m flake8 main.py test
```

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

4. **Controller** (`ui/controller.py`): Manages interaction between UI and backend services
   - Contains worker classes for background processing
   - Handles signals between UI components

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
- User settings stored in `~/.nbg-ynab-export/nbg_ynab_settings.txt`
- YNAB token securely stored using cryptography
- API logs in `~/.nbg-ynab-export/ynab_api.log`