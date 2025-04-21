# UI and YNAB API Integration Plan

## TODO Tasks (in order)

1. **Add UI using Python**
   - [x] Choose a Python UI framework (PyQt5)
   - [x] Scaffold the main window and layout for file import and controls (wizard style)

2. **Implement File Import in UI**
   - [x] Add a file picker to allow users to select a statement file (CSV/XLSX)
   - [x] Display basic file info/preview in the UI (file path shown)

3. **Process and Modify CSV**
   - Integrate existing CSV conversion logic with the UI
   - Allow user to trigger conversion and display results/output filename

4. **Account Selection via Dropdown**
   - Fetch and display available YNAB accounts in a dropdown menu
   - On account selection, show last transaction(s) for that account

5. **Fetch Last 5 Transactions from YNAB API**
   - Integrate with https://api.ynab.com/ (requires user API key)
   - Add UI section to display last 5 transactions from selected YNAB account

6. **Add Missed Transactions from Imported File**
   - Compare imported transactions with those fetched from YNAB
   - Identify and display transactions not present in YNAB
   - Allow user to confirm and upload missed transactions to YNAB via API

---

- Each step should include error handling and user feedback in the UI
- API key management (secure input/storage) should be considered for YNAB access
- Ensure code is modular for easy testing and maintenance
