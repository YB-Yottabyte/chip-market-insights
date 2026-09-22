"""Turn SEC Company Facts into one observation per fiscal quarter."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .config import COMPANIES, SEC_GAAP_TAGS


Fact = dict[str, Any]
INCOME_METRICS = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "rd_expense",
)
BALANCE_METRICS = ("assets", "cash")
FINANCIAL_COLUMNS = (
    "ticker",
    "period_end",
    "fiscal_year",
    "fiscal_quarter",
    "filing_date",
    "source_type",
    *SEC_GAAP_TAGS,
)


class FinancialNormalizer:
    """Select current filing facts and derive Q4 from a complete fiscal year."""

    def __init__(self, ticker: str, payload: dict[str, Any]) -> None:
        if ticker not in COMPANIES or payload.get("cik") != COMPANIES[ticker][0]:
            raise ValueError(f"CIK mapping mismatch for {ticker}")
        self.ticker = ticker
        self.payload = payload
        self._facts_by_metric: dict[str, list[Fact]] = {}

    def _facts(self, metric: str) -> list[Fact]:
        """Use tag priority when a filing reports equivalent GAAP concepts."""
        if metric not in self._facts_by_metric:
            gaap = self.payload.get("facts", {}).get("us-gaap", {})
            facts = []
            for rank, tag in enumerate(SEC_GAAP_TAGS[metric]):
                for item in gaap.get(tag, {}).get("units", {}).get("USD", []):
                    facts.append({**item, "_tag_rank": rank})
            self._facts_by_metric[metric] = facts
        return self._facts_by_metric[metric]

    @staticmethod
    def _duration_days(item: Fact) -> int | None:
        if "start" not in item:
            return None
        start = date.fromisoformat(item["start"])
        end = date.fromisoformat(item["end"])
        return (end - start).days + 1

    @staticmethod
    def _is_current_period(item: Fact) -> bool:
        """Ignore old comparison columns included with a newer filing."""
        days_after_period = (
            date.fromisoformat(item["filed"]) - date.fromisoformat(item["end"])
        ).days
        return 0 <= days_after_period <= 180

    def _select_fact(
        self,
        metric: str,
        fiscal_year: int,
        fiscal_period: str,
        period_end: str,
        kind: str,
    ) -> Fact | None:
        candidates = []
        for item in self._facts(metric):
            if item.get("form") not in {"10-Q", "10-K"}:
                continue
            if (item.get("fy"), item.get("fp"), item.get("end")) != (
                fiscal_year,
                fiscal_period,
                period_end,
            ):
                continue
            if not self._is_current_period(item):
                continue
            if self._valid_duration(item, kind):
                candidates.append(item)

        if not candidates:
            return None
        return min(candidates, key=self._fact_priority)

    def _valid_duration(self, item: Fact, kind: str) -> bool:
        duration = self._duration_days(item)
        if kind == "instant":
            return duration is None
        if duration is None:
            return False
        if kind == "quarter":
            return 60 <= duration <= 120
        if kind == "annual":
            return 330 <= duration <= 380
        raise ValueError(f"Unknown SEC fact period kind: {kind}")

    @staticmethod
    def _fact_priority(item: Fact) -> tuple[int, int, str]:
        return (
            item.get("_tag_rank", 0),
            -date.fromisoformat(item["filed"]).toordinal(),
            item.get("accn", ""),
        )

    def _reported_periods(self) -> list[tuple[int, str, str]]:
        latest_end: dict[tuple[int, str], str] = {}
        for item in self._facts("revenue"):
            if item.get("fp") not in {"Q1", "Q2", "Q3", "FY"}:
                continue
            if item.get("form") not in {"10-Q", "10-K"}:
                continue
            if not self._is_current_period(item):
                continue
            key = (int(item["fy"]), item["fp"])
            latest_end[key] = max(latest_end.get(key, ""), item["end"])

        periods = [(year, period, end) for (year, period), end in latest_end.items()]
        return sorted(
            periods,
            key=lambda value: (
                value[0],
                4 if value[1] == "FY" else int(value[1][1]),
                value[2],
            ),
        )

    def _base_row(
        self,
        fiscal_year: int,
        quarter: int,
        period_end: str,
        filing_date: str,
        source: str,
    ) -> Fact:
        return {
            "ticker": self.ticker,
            "period_end": period_end,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": quarter,
            "filing_date": filing_date,
            "source_type": source,
        }

    def _balance_values(
        self, fiscal_year: int, period: str, end: str
    ) -> dict[str, Any]:
        values = {}
        for metric in BALANCE_METRICS:
            item = self._select_fact(metric, fiscal_year, period, end, "instant")
            values[metric] = item["val"] if item else None
        return values

    def _reported_quarter(
        self, year: int, period: str, end: str, revenue: Fact
    ) -> Fact:
        row = self._base_row(year, int(period[1]), end, revenue["filed"], "SEC API")
        row["revenue"] = revenue["val"]
        for metric in INCOME_METRICS[1:]:
            item = self._select_fact(metric, year, period, end, "quarter")
            row[metric] = item["val"] if item else None
        row.update(self._balance_values(year, period, end))
        return row

    def _derived_fourth_quarter(
        self, year: int, end: str, annual_revenue: Fact, prior_rows: list[Fact]
    ) -> Fact | None:
        first_three = [
            row
            for row in prior_rows
            if row["fiscal_year"] == year and row["fiscal_quarter"] in (1, 2, 3)
        ]
        if {row["fiscal_quarter"] for row in first_three} != {1, 2, 3}:
            return None

        row = self._base_row(
            year, 4, end, annual_revenue["filed"], "SEC API + derived Q4"
        )
        for metric in INCOME_METRICS:
            annual_fact = (
                annual_revenue
                if metric == "revenue"
                else self._select_fact(metric, year, "FY", end, "annual")
            )
            reported_values = [quarter.get(metric) for quarter in first_three]
            if annual_fact is not None and all(
                value is not None for value in reported_values
            ):
                row[metric] = annual_fact["val"] - sum(reported_values)
            else:
                row[metric] = None
        row.update(self._balance_values(year, "FY", end))
        return row

    def normalize(self) -> pd.DataFrame:
        """Return USD values, preserving missing concepts as nulls."""
        rows: list[Fact] = []
        for year, period, end in self._reported_periods():
            kind = "annual" if period == "FY" else "quarter"
            revenue = self._select_fact("revenue", year, period, end, kind)
            if revenue is None:
                continue
            if period == "FY":
                row = self._derived_fourth_quarter(year, end, revenue, rows)
                if row is not None:
                    rows.append(row)
            else:
                rows.append(self._reported_quarter(year, period, end, revenue))

        frame = pd.DataFrame(rows, columns=FINANCIAL_COLUMNS)
        return frame.drop_duplicates(["ticker", "period_end"], keep="last")


def normalize_company(ticker: str, payload: dict[str, Any]) -> pd.DataFrame:
    """Normalize one company with the reusable SEC fact selector."""
    return FinancialNormalizer(ticker, payload).normalize()


def normalize_all(payloads: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Combine normalized quarters for every fetched company."""
    frames = [
        normalize_company(ticker, payload) for ticker, payload in payloads.items()
    ]
    if not frames:
        return pd.DataFrame(columns=FINANCIAL_COLUMNS)
    return pd.concat(frames, ignore_index=True)
