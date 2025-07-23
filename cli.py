#!/usr/bin/env python3
# cli.py
import argparse
import sys
from pathlib import Path

from config import get_logger, SUPPORTED_EXT
from converter.utils import read_input, exclude_existing, write_output
from converter.account import process_account, REQUIRED as ACCOUNT_REQUIRED
from converter.card import process_card, REQUIRED as CARD_REQUIRED
from converter.revolut import process_revolut, REQUIRED as REVOLUT_REQUIRED

logger = get_logger(__name__)


def parse_args():
    p = argparse.ArgumentParser(
        prog="nbg-ynab-export",
        description="Convert NBG/Revolut statements into YNAB CSV"
    )
    p.add_argument("input_file", type=Path, help="Path to bank statement (.csv/.xls/.xlsx)")
    p.add_argument(
        "--previous", "-p",
        type=Path,
        default=None,
        help="Optional path to previous YNAB export CSV for de-duplication"
    )
    return p.parse_args()


def main():
    args = parse_args()
    in_path = args.input_file
    if not in_path.exists() or in_path.suffix.lower() not in SUPPORTED_EXT:
        logger.error("Invalid input: %s", in_path)
        return 1
    try:
        df = read_input(in_path)
        if set(REVOLUT_REQUIRED).issubset(df.columns):
            logger.info("Detected Revolut export")
            out_df = process_revolut(df)
        elif set(ACCOUNT_REQUIRED).issubset(df.columns):
            logger.info("Detected NBG Account export")
            out_df = process_account(df)
        elif set(CARD_REQUIRED).issubset(df.columns):
            logger.info("Detected NBG Card export")
            out_df = process_card(df)
        else:
            logger.error("Unrecognized format: columns %s", list(df.columns))
            return 1
        if args.previous:
            prev_df = read_input(args.previous)
            out_df = exclude_existing(out_df, prev_df)
        out_path = write_output(in_path, out_df)
        logger.info("Wrote %d rows to %s", len(out_df), out_path)
        return 0
    except Exception as e:
        logger.error("Processing failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
