import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import unittest

from converter import utils


class TestUtils(unittest.TestCase):
    def test_read_input_csv(self):
        df = pd.DataFrame({'A': [1, 2]})
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / 'data.csv'
            df.to_csv(csv_path, index=False)
            result = utils.read_input(csv_path)
        self.assertTrue(result.equals(df))

    def test_read_input_excel(self):
        df = pd.DataFrame({'A': [1]})
        with tempfile.TemporaryDirectory() as td:
            xls_path = Path(td) / 'data.xlsx'
            # Patch pandas.read_excel so we don't depend on openpyxl internals
            with patch('pandas.read_excel', return_value=df) as mock_read:
                result = utils.read_input(xls_path)
                mock_read.assert_called_once_with(xls_path)
        self.assertTrue(result.equals(df))

    def test_write_output(self):
        df = pd.DataFrame({'A': [3]})
        with tempfile.TemporaryDirectory() as td:
            in_path = Path(td) / 'input.xlsx'
            in_path.touch()
            fixed_date = datetime(2025, 2, 25)
            with patch.object(utils, 'datetime') as mock_dt:
                mock_dt.now.return_value = fixed_date
                mock_dt.strftime = datetime.strftime
                out_path = utils.write_output(in_path, df)
            expected_name = (
                f"input_{fixed_date.strftime(utils.DATE_FMT_YNAB)}_ynab.csv"
            )
            self.assertEqual(out_path.name, expected_name)
            written = pd.read_csv(out_path)
        self.assertTrue(written.equals(df))

    def test_sanitize_csv_formulas(self):
        df = pd.DataFrame({
            'Payee': ['=HYPERLINK("http://x")', ' Normal'],
            'Memo': ['+SUM(1,1)', None],
            'Amount': [1, 2],
        })
        sanitized = utils.sanitize_csv_formulas(df)
        self.assertEqual(sanitized.loc[0, 'Payee'], "'=HYPERLINK(\"http://x\")")
        self.assertEqual(sanitized.loc[0, 'Memo'], "'+SUM(1,1)")
        self.assertEqual(sanitized.loc[1, 'Payee'], ' Normal')
        self.assertTrue(pd.isna(sanitized.loc[1, 'Memo']))

    def test_exclude_existing(self):
        new_df = pd.DataFrame({
            'Date': ['2025-02-25', '2025-02-26'],
            'Payee': ['A', 'B'],
            'Amount': [1, 2]
        })
        prev_df = pd.DataFrame({
            'Date': ['2025-02-25'],
            'Payee': ['A'],
            'Amount': [1]
        })
        result = utils.exclude_existing(new_df, prev_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Payee'], 'B')

    def test_exclude_existing_with_legacy_date_cutoff(self):
        new_df = pd.DataFrame({
            'Date': ['2025-02-24', '2025-02-25', '2025-02-26'],
            'Payee': ['OLD', 'A', 'B'],
            'Amount': [10, 1, 2],
        })
        prev_df = pd.DataFrame({
            'Date': ['2025-02-25'],
            'Payee': ['A'],
            'Amount': [1],
        })
        result = utils.exclude_existing(
            new_df,
            prev_df,
            drop_older_than_latest_prev=True,
        )
        self.assertEqual(list(result['Payee']), ['B'])

    def test_normalize_column_name(self):
        self.assertEqual(
            utils.normalize_column_name('  Foo   Bar  '),
            'Foo Bar'
        )

    def test_extract_date_from_filename(self):
        self.assertEqual(
            utils.extract_date_from_filename('file_2025-02-25.csv'),
            '2025-02-25'
        )
        self.assertEqual(
            utils.extract_date_from_filename('25-02-2025_file.csv'),
            '2025-02-25'
        )
        self.assertEqual(utils.extract_date_from_filename('nodate'), '')

    def test_generate_output_filename_date(self):
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / 'statement_2025-02-25.xlsx'
            expected = Path(td) / 'statement_2025-02-25_ynab.csv'
            self.assertEqual(
                utils.generate_output_filename(str(file_path)),
                str(expected)
            )

    def test_generate_output_filename_current_date(self):
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / 'file.xlsx'
            fixed_date = datetime(2025, 2, 25)
            with patch.object(utils, 'datetime') as mock_dt:
                mock_dt.now.return_value = fixed_date
                mock_dt.strftime = datetime.strftime
                out = utils.generate_output_filename(str(file_path))
            expected = (
                Path(td)
                / f"file_{fixed_date.strftime(utils.DATE_FMT_YNAB)}_ynab.csv"
            )
            self.assertEqual(out, str(expected))
