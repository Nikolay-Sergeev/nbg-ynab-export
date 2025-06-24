import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from converter import utils


def test_read_input_csv(tmp_path):
    df = pd.DataFrame({'A': [1, 2]})
    csv_path = tmp_path / 'data.csv'
    df.to_csv(csv_path, index=False)
    result = utils.read_input(csv_path)
    assert result.equals(df)


def test_read_input_excel(tmp_path):
    df = pd.DataFrame({'A': [1]})
    xls_path = tmp_path / 'data.xlsx'
    # Patch pandas.read_excel so we don't depend on openpyxl internals
    with patch('pandas.read_excel', return_value=df) as mock_read:
        result = utils.read_input(xls_path)
        mock_read.assert_called_once_with(xls_path)
    assert result.equals(df)


def test_write_output(tmp_path):
    df = pd.DataFrame({'A': [3]})
    in_path = tmp_path / 'input.xlsx'
    in_path.touch()
    fixed_date = datetime(2025, 2, 25)
    with patch.object(utils, 'datetime') as mock_dt:
        mock_dt.now.return_value = fixed_date
        mock_dt.strftime = datetime.strftime
        out_path = utils.write_output(in_path, df)
    expected_name = f"input_{fixed_date.strftime(utils.DATE_FMT_YNAB)}_ynab.csv"
    assert out_path.name == expected_name
    written = pd.read_csv(out_path)
    assert written.equals(df)


def test_exclude_existing():
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
    assert len(result) == 1
    assert result.iloc[0]['Payee'] == 'B'


def test_normalize_column_name():
    assert utils.normalize_column_name('  Foo   Bar  ') == 'Foo Bar'


def test_extract_date_from_filename():
    assert utils.extract_date_from_filename('file_2025-02-25.csv') == '2025-02-25'
    assert utils.extract_date_from_filename('25-02-2025_file.csv') == '2025-02-25'
    assert utils.extract_date_from_filename('nodate') == ''


def test_generate_output_filename_date(tmp_path):
    file_path = tmp_path / 'statement_2025-02-25.xlsx'
    expected = tmp_path / 'statement_2025-02-25_ynab.csv'
    assert utils.generate_output_filename(str(file_path)) == str(expected)


def test_generate_output_filename_current_date(tmp_path):
    file_path = tmp_path / 'file.xlsx'
    fixed_date = datetime(2025, 2, 25)
    with patch.object(utils, 'datetime') as mock_dt:
        mock_dt.now.return_value = fixed_date
        mock_dt.strftime = datetime.strftime
        out = utils.generate_output_filename(str(file_path))
    expected = tmp_path / f"file_{fixed_date.strftime(utils.DATE_FMT_YNAB)}_ynab.csv"
    assert out == str(expected)
