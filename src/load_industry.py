"""Read public monthly semiconductor market files into one tidy format."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .config import (
    INDUSTRY_COLUMN_ALIASES,
    REGION_ALIASES,
    WSTS_SHEETS,
    WSTS_USD_MULTIPLIER,
)


LOG = logging.getLogger(__name__)
INDUSTRY_COLUMNS = (
    "date",
    "region",
    "monthly_sales",
    "three_month_average",
    "reported_yoy_growth",
    "source_file",
    "source_type",
)


class IndustryDataLoader:
    """Import native WSTS workbooks or user-supplied tidy CSV/XLSX files."""

    def load_directory(self, directory: Path) -> pd.DataFrame:
        """Combine supported files and reject duplicate region-month records."""
        if not directory.exists():
            LOG.warning("Industry directory does not exist: %s", directory)
            return pd.DataFrame(columns=INDUSTRY_COLUMNS)

        files = sorted(
            path
            for path in directory.iterdir()
            if path.name != "onsemi_end_markets.csv"
            and path.suffix.lower() in {".csv", ".xlsx", ".xlsm"}
        )
        if not files:
            LOG.warning(
                "No industry file found in %s; market tables will be empty", directory
            )
            return pd.DataFrame(columns=INDUSTRY_COLUMNS)

        frame = pd.concat([self.load_file(path) for path in files], ignore_index=True)
        if frame.duplicated(["date", "region"]).any():
            raise ValueError(
                "Duplicate region-month observations across industry files"
            )
        return frame

    def load_file(self, path: Path) -> pd.DataFrame:
        """Read one file without changing its documented units."""
        suffix = path.suffix.lower()
        try:
            if suffix == ".csv":
                frame = pd.read_csv(path)
            elif suffix in {".xlsx", ".xlsm"}:
                if self._is_wsts_workbook(path):
                    return self.load_wsts_workbook(path)
                frame = pd.read_excel(path)
            else:
                raise ValueError(f"Unsupported industry file: {path.name}")
        except (OSError, ImportError) as error:
            raise RuntimeError(
                f"Could not read industry file {path}: {error}"
            ) from error
        return self._standardize_tidy_file(frame, path)

    @staticmethod
    def _is_wsts_workbook(path: Path) -> bool:
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            return set(WSTS_SHEETS).issubset(workbook.sheetnames)
        finally:
            workbook.close()

    def load_wsts_workbook(self, path: Path) -> pd.DataFrame:
        """Convert official WSTS thousands-of-USD values to USD."""
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            if not set(WSTS_SHEETS).issubset(workbook.sheetnames):
                raise ValueError(f"{path.name}: expected Monthly Data and 3MMA sheets")
            monthly = self._read_wsts_sheet(workbook["Monthly Data"], path)
            average = self._read_wsts_sheet(workbook["3MMA"], path)
        finally:
            workbook.close()

        if not monthly:
            raise ValueError(f"{path.name}: no monthly WSTS values found")

        rows = []
        for (period_end, region), sales in sorted(monthly.items()):
            rows.append(
                {
                    "date": period_end,
                    "region": region,
                    "monthly_sales": sales,
                    "three_month_average": average.get((period_end, region)),
                    "reported_yoy_growth": pd.NA,
                    "source_file": path.name,
                    "source_type": "WSTS official workbook",
                }
            )
        return pd.DataFrame(rows, columns=INDUSTRY_COLUMNS)

    @staticmethod
    def _read_wsts_sheet(sheet: Worksheet, path: Path) -> dict[tuple[str, str], float]:
        unit = str(sheet.cell(3, 1).value).lower().replace(",", "")
        if "1000 us$" not in unit:
            raise ValueError(
                f"{path.name}: unknown WSTS amount unit in {sheet.title}: {unit}"
            )

        months = [str(sheet.cell(4, column).value).strip() for column in range(2, 14)]
        expected = [
            pd.Timestamp(2000, month, 1).strftime("%B") for month in range(1, 13)
        ]
        if months != expected:
            raise ValueError(f"{path.name}: unexpected month headers in {sheet.title}")

        observations: dict[tuple[str, str], float] = {}
        year: int | None = None
        for row in sheet.iter_rows(min_row=5, values_only=True):
            label = row[0]
            if isinstance(label, int) and 1980 <= label <= 2100:
                year = label
                continue

            region = REGION_ALIASES.get(str(label).strip().lower())
            if year is None or region is None:
                continue
            for month in range(1, 13):
                value = row[month] if len(row) > month else None
                if isinstance(value, (int, float)) and value > 0:
                    end = pd.Timestamp(year, month, 1).to_period("M").to_timestamp("M")
                    observations[(end.strftime("%Y-%m-%d"), region)] = (
                        float(value) * WSTS_USD_MULTIPLIER
                    )
        return observations

    @staticmethod
    def _standardize_tidy_file(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
        renamed = {}
        for column in frame.columns:
            words = str(column).lower().replace("_", " ").replace("-", " ").split()
            normalized = " ".join(words)
            renamed[column] = INDUSTRY_COLUMN_ALIASES.get(normalized, normalized)
        frame = frame.rename(columns=renamed)

        required = {"date", "region"}
        sales_columns = {"monthly_sales", "three_month_average"}
        if not required.issubset(frame) or not sales_columns.intersection(frame):
            raise ValueError(
                f"{path.name}: need Date, Region and Monthly Sales or Three-Month Moving Average"
            )

        frame["date"] = (
            pd.to_datetime(frame["date"], errors="raise")
            .dt.to_period("M")
            .dt.to_timestamp("M")
            .dt.strftime("%Y-%m-%d")
        )
        frame["region"] = (
            frame["region"]
            .astype(str)
            .str.strip()
            .map(lambda region: REGION_ALIASES.get(region.lower(), region))
        )
        for column in ("monthly_sales", "three_month_average", "reported_yoy_growth"):
            if column not in frame:
                frame[column] = pd.NA
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        if frame.duplicated(["date", "region"]).any():
            raise ValueError(f"{path.name}: duplicate region-month rows")
        if frame[["monthly_sales", "three_month_average"]].lt(0).any().any():
            raise ValueError(f"{path.name}: negative sales")

        frame["source_file"] = path.name
        frame["source_type"] = "manual public dataset"
        return frame[list(INDUSTRY_COLUMNS)]


def load_wsts_workbook(path: Path) -> pd.DataFrame:
    """Compatibility entry point for official WSTS workbooks."""
    return IndustryDataLoader().load_wsts_workbook(path)


def load_file(path: Path) -> pd.DataFrame:
    """Compatibility entry point for one market file."""
    return IndustryDataLoader().load_file(path)


def load_directory(directory: Path) -> pd.DataFrame:
    """Compatibility entry point for a directory of market files."""
    return IndustryDataLoader().load_directory(directory)
