#!/usr/bin/env python3
# cli.py
import argparse
import sys
from pathlib import Path

from config import get_logger
from services.conversion_service import ConversionService

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
    try:
        previous = str(args.previous) if args.previous else None
        out_df = ConversionService.convert_to_ynab(str(args.input_file), previous_ynab=previous)
        logger.info("Wrote %d rows", len(out_df))
        return 0
    except Exception as exc:
        logger.error("Processing failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
