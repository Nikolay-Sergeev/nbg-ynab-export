# Project Dependencies

This project relies on several Python packages listed in `requirements.txt`.
The major runtime dependencies are:

- **pandas** – data processing and CSV/XLSX handling
- **openpyxl** – Excel file support for `pandas`
- **PyQt5** (>=5.15) – GUI wizard implementation
- **requests** – used by the YNAB API client, though not pinned in `requirements.txt`
- **cryptography** – secure storage of the YNAB token

For development and testing the following tools are used:

- **flake8** – code style checking
- **pytest** – optional testing framework (in addition to the included `unittest` suite)

Python 3.6 or newer is required. Install all packages with:

```bash
pip install -r requirements.txt
```
