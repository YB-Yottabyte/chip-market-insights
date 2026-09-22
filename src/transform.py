"""Data-quality checks applied before records enter the SQL database."""

from __future__ import annotations

import pandas as pd

from .config import COMPANIES, MARKET_COMPONENT_REGIONS


class DataQualityValidator:
    """Check source keys, values, and cross-region consistency."""

    def validate_financials(self, frame: pd.DataFrame) -> dict[str, int]:
        required = ("ticker", "period_end", "fiscal_year", "fiscal_quarter")
        self._require_columns(frame, (*required, "revenue"), "financial")
        return {
            "duplicate_company_period": int(
                frame.duplicated(["ticker", "period_end"]).sum()
            ),
            "missing_required_keys": int(
                frame[list(required)].isna().any(axis=1).sum()
            ),
            "negative_revenue": int(frame["revenue"].lt(0).sum()),
            "invalid_fiscal_quarter": int(
                (~frame["fiscal_quarter"].isin([1, 2, 3, 4])).sum()
            ),
            "broken_company_mapping": int((~frame["ticker"].isin(COMPANIES)).sum()),
        }

    def validate_market(self, frame: pd.DataFrame) -> dict[str, int]:
        if frame.empty:
            return {
                "duplicate_region_date": 0,
                "missing_market_keys": 0,
                "negative_market_sales": 0,
                "invalid_reported_percentage": 0,
                "world_region_reconciliation_failures": 0,
            }
        self._require_columns(
            frame,
            (
                "region",
                "date",
                "monthly_sales",
                "three_month_average",
                "reported_yoy_growth",
            ),
            "market",
        )
        return {
            "duplicate_region_date": int(frame.duplicated(["region", "date"]).sum()),
            "missing_market_keys": int(
                frame[["region", "date"]].isna().any(axis=1).sum()
            ),
            "negative_market_sales": int(
                frame[["monthly_sales", "three_month_average"]].lt(0).any(axis=1).sum()
            ),
            # Growth above 100% is possible; growth below -100% is not.
            "invalid_reported_percentage": int(
                frame["reported_yoy_growth"].lt(-100).sum()
            ),
            "world_region_reconciliation_failures": self._world_region_mismatches(
                frame
            ),
        }

    def _world_region_mismatches(self, frame: pd.DataFrame) -> int:
        world_sales = frame.loc[
            frame["region"].eq("World"), ["date", "monthly_sales"]
        ].set_index("date")["monthly_sales"]
        regional = frame.loc[frame["region"].isin(MARKET_COMPONENT_REGIONS)]
        totals = regional.groupby("date").agg(
            sales=("monthly_sales", "sum"), regions=("region", "nunique")
        )
        complete = totals.loc[totals["regions"].eq(len(MARKET_COMPONENT_REGIONS))]
        matched = complete.join(world_sales.rename("world"), how="inner").dropna()
        tolerance = matched["world"].abs().mul(0.0001).clip(lower=100000)
        return int(matched["sales"].sub(matched["world"]).abs().gt(tolerance).sum())

    def validate_segments(self, frame: pd.DataFrame) -> dict[str, int]:
        if frame.empty:
            return {
                "duplicate_segment_period": 0,
                "missing_segment_keys": 0,
                "negative_segment_revenue": 0,
                "invalid_segment_percentage": 0,
            }
        required = ("period_end", "period_type", "end_market", "source_document")
        self._require_columns(
            frame, (*required, "revenue", "revenue_percentage"), "segment"
        )
        percentages = frame["revenue_percentage"]
        return {
            "duplicate_segment_period": int(
                frame.duplicated(["period_end", "period_type", "end_market"]).sum()
            ),
            "missing_segment_keys": int(frame[list(required)].isna().any(axis=1).sum()),
            "negative_segment_revenue": int(frame["revenue"].lt(0).sum()),
            "invalid_segment_percentage": int(
                (percentages.lt(0) | percentages.gt(100)).sum()
            ),
        }

    def validate_all(
        self, financials: pd.DataFrame, markets: pd.DataFrame, segments: pd.DataFrame
    ) -> dict[str, int]:
        """Return one combined quality summary for a pipeline run."""
        checks = {}
        checks.update(self.validate_financials(financials))
        checks.update(self.validate_market(markets))
        checks.update(self.validate_segments(segments))
        return checks

    @staticmethod
    def assert_valid(checks: dict[str, int]) -> None:
        failures = {name: count for name, count in checks.items() if count}
        if failures:
            raise ValueError(f"Data quality checks failed: {failures}")

    @staticmethod
    def _require_columns(
        frame: pd.DataFrame, columns: tuple[str, ...], label: str
    ) -> None:
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"Missing {label} columns: {sorted(missing)}")


def validate_financials(frame: pd.DataFrame) -> dict[str, int]:
    return DataQualityValidator().validate_financials(frame)


def validate_market(frame: pd.DataFrame) -> dict[str, int]:
    return DataQualityValidator().validate_market(frame)


def validate_segments(frame: pd.DataFrame) -> dict[str, int]:
    return DataQualityValidator().validate_segments(frame)


def assert_quality(checks: dict[str, int]) -> None:
    DataQualityValidator.assert_valid(checks)
