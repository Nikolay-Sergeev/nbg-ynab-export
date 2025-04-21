# UI and YNAB API Integration Plan

## TODO Tasks (in order)

1. **Add UI using Python**
   - Choose a Python UI framework (e.g., Tkinter, PyQt, or Streamlit)
   - Scaffold the main window and layout for file import and controls

2. **Implement File Import in UI**
   - Add a file picker to allow users to select a statement file (CSV/XLSX)
   - Display basic file info/preview in the UI

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
