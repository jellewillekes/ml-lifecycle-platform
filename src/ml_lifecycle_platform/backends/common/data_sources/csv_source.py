"""`DataSource` adapter for local CSV files declared by a CSV model spec."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class CsvSource:
    """Read a labeled dataset straight from a CSV file."""

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path

    def fetch(self) -> pd.DataFrame:
        return pd.read_csv(self._csv_path)
