# converter/dispatcher.py
from typing import Callable, Dict, Tuple

import pandas as pd

from constants import (
    ACCOUNT_REQUIRED_COLUMNS,
    CARD_REQUIRED_COLUMNS,
    REVOLUT_REQUIRED_COLUMNS,
)

Processor = Callable[[pd.DataFrame], pd.DataFrame]
ProcessorMap = Dict[str, Processor]


def detect_processor(df: pd.DataFrame, processors: ProcessorMap) -> Tuple[Processor, bool, str]:
    """
    Determine which processor to use based on available columns.

    Returns the matching processor, whether the format is Revolut, and a source label
    ('revolut', 'account', or 'card'). Raises ValueError when no match is found.
    """
    if set(REVOLUT_REQUIRED_COLUMNS).issubset(df.columns):
        return processors['revolut'], True, 'revolut'
    if set(ACCOUNT_REQUIRED_COLUMNS).issubset(df.columns):
        return processors['account'], False, 'account'
    if set(CARD_REQUIRED_COLUMNS).issubset(df.columns):
        return processors['card'], False, 'card'
    raise ValueError("File format not recognized")
