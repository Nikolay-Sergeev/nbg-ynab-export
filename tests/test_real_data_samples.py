"""Integration-style tests based on anonymized snapshots of real bank exports."""
from pathlib import Path

import pandas as pd

from services.conversion_service import ConversionService


def _write_account_xlsx(path: Path) -> None:
    """Create a minimal NBG account export, shaped like real statementexport11-12-2025.xlsx."""
    df = pd.DataFrame(
        {
            "Valeur": ["11/12/2025", "10/12/2025"],
            "Ονοματεπώνυμο αντισυμβαλλόμενου": ["ACME MARKET", None],
            "Περιγραφή": ["GROCERY POS", "PAYROLL"],
            "Ποσό συναλλαγής": ["-23,50", "1200,00"],
            "Χρέωση / Πίστωση": ["Χρέωση", "Πίστωση"],
        }
    )
    df.to_excel(path, index=False)


def _write_card_xlsx(path: Path) -> None:
    """Create a minimal NBG card export, shaped like CardStatementExport.xlsx."""
    df = pd.DataFrame(
        {
            "Ημερομηνία/Ώρα Συναλλαγής": ["11/12/2025 14:22", "10/12/2025 09:15"],
            "Περιγραφή Κίνησης": [
                "3D SECURE E-COMMERCE ΑΓΟΡΑ - ONLINE SHOP",
                "POS PURCHASE CAFE ATHENS",
            ],
            "Χ/Π": ["Χ", "Π"],
            "Ποσό": ["18,75", "4,20"],
        }
    )
    df.to_excel(path, index=False)


def _write_revolut_csv(path: Path) -> None:
    """Create a minimal Revolut export shaped like account-statement_2025-12-01_2025-12-11_en-us_034b09.csv."""
    df = pd.DataFrame(
        {
            "Type": ["CARD_PAYMENT", "TRANSFER"],
            "Product": ["Current", "Current"],
            "Started Date": ["2025-12-09 08:45:10", "2025-12-10 11:05:00"],
            "Completed Date": ["2025-12-09 08:45:15", "2025-12-10 11:05:05"],
            "Description": ["COFFEE SPOT", "FROM PARTNER"],
            "Amount": ["-3.50", "250.00"],
            "Fee": ["0.00", "0.00"],
            "Currency": ["EUR", "EUR"],
            "State": ["COMPLETED", "COMPLETED"],
            "Balance": ["100.00", "350.00"],
        }
    )
    df.to_csv(path, index=False)


def test_convert_account_sample(tmp_path: Path):
    input_path = tmp_path / "statementexport11-12-2025.xlsx"
    _write_account_xlsx(input_path)

    df = ConversionService.convert_to_ynab(
        str(input_path),
        write_output=False,
    )

    assert list(df.columns) == ["Date", "Payee", "Memo", "Amount"]
    assert df.iloc[0]["Date"] == "2025-12-11"
    assert df.iloc[0]["Payee"] == "ACME MARKET"
    assert df.iloc[0]["Memo"] == "GROCERY POS"
    assert df.iloc[0]["Amount"] == -23.50
    # Payee should fall back to memo when missing
    assert df.iloc[1]["Payee"] == "PAYROLL"
    assert df.iloc[1]["Amount"] == 1200.00


def test_convert_card_sample(tmp_path: Path):
    input_path = tmp_path / "CardStatementExport.xlsx"
    _write_card_xlsx(input_path)

    df = ConversionService.convert_to_ynab(
        str(input_path),
        write_output=False,
    )

    assert list(df.columns) == ["Date", "Payee", "Memo", "Amount"]
    assert df.iloc[0]["Date"] == "2025-12-11"
    # Ecommerce prefixes should be stripped
    assert df.iloc[0]["Payee"] == "ONLINE SHOP"
    assert df.iloc[0]["Amount"] == -18.75
    # Income row handled via Χ/Π indicator
    assert df.iloc[1]["Amount"] == 4.20


def test_convert_revolut_sample(tmp_path: Path):
    input_path = tmp_path / "account-statement_2025-12-01_2025-12-11_en-us_034b09.csv"
    _write_revolut_csv(input_path)

    df = ConversionService.convert_to_ynab(
        str(input_path),
        write_output=False,
    )

    assert list(df.columns) == ["Date", "Payee", "Memo", "Amount"]
    assert df.iloc[0]["Date"] == "2025-12-09"
    assert df.iloc[0]["Payee"] == "COFFEE SPOT"
    assert df.iloc[0]["Amount"] == -3.50
    assert df.iloc[1]["Payee"] == "FROM PARTNER"
    assert df.iloc[1]["Amount"] == 250.00
