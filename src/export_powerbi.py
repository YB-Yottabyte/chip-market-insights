"""Export the SQL model and calculated analysis tables as CSV files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import Date, MetaData, Table, select
from sqlalchemy.engine import Engine

from .analysis import build_insights, build_onsemi_industry_comparison
from .config import EXPORT_TABLE_NAMES
from .db_schema import date_dim, segment
from .metrics import company_metrics, market_metrics


LOG = logging.getLogger(__name__)


class PowerBIExporter:
    """Write stable, explicitly selected tables for reporting and review."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def _read_table(self, name: str) -> pd.DataFrame:
        if name not in EXPORT_TABLE_NAMES:
            raise ValueError(f"Table is not approved for export: {name}")
        table = Table(name, MetaData(), autoload_with=self.engine)
        query = select(*table.columns)
        frame = pd.read_sql_query(query, self.engine)
        for column in table.columns:
            if isinstance(column.type, Date):
                frame[column.name] = pd.to_datetime(frame[column.name]).dt.strftime(
                    "%Y-%m-%d"
                )
        return frame

    def _read_segments(self) -> pd.DataFrame:
        query = select(
            date_dim.c.date.label("period_end"),
            segment.c.period_type,
            segment.c.end_market,
            segment.c.revenue,
            segment.c.revenue_percentage,
            segment.c.source_document,
        ).join(segment, segment.c.date_id == date_dim.c.date_id)
        frame = pd.read_sql_query(query, self.engine)
        if not frame.empty:
            frame["period_end"] = pd.to_datetime(frame["period_end"]).dt.strftime(
                "%Y-%m-%d"
            )
        return frame

    @staticmethod
    def _write_insights(destination: Path, insights: list[dict]) -> None:
        json_path = destination / "business_insights.json"
        json_path.write_text(json.dumps(insights, indent=2), encoding="utf-8")

        lines = ["# Calculated business insights", ""]
        if insights:
            lines.extend(
                f"- {item['text']} Source: {item['source']}" for item in insights
            )
        else:
            lines.append(
                "No supported insights yet; load source data and rerun the pipeline."
            )
        (destination / "business_insights.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def export(self, destination: Path) -> dict[str, int]:
        """Export SQL tables, derived metrics, and supported insight text."""
        destination.mkdir(parents=True, exist_ok=True)
        table_counts = {}
        for name in EXPORT_TABLE_NAMES:
            frame = self._read_table(name)
            frame.to_csv(destination / f"{name}.csv", index=False)
            table_counts[name] = len(frame)

        companies = self._read_table("vw_company_financials")
        markets = self._read_table("vw_market_sales")
        segments = self._read_segments()

        company_metrics(companies).to_csv(
            destination / "company_metrics.csv", index=False
        )
        market_metrics(markets).to_csv(destination / "market_metrics.csv", index=False)
        comparison = build_onsemi_industry_comparison(companies, markets)
        comparison.to_csv(destination / "onsemi_industry_comparison.csv", index=False)
        table_counts["onsemi_industry_comparison"] = len(comparison)

        insights = build_insights(companies, markets, segments)
        self._write_insights(destination, insights)
        LOG.info("Exported %s SQL tables to %s", len(EXPORT_TABLE_NAMES), destination)
        return table_counts


def export_tables(engine: Engine, destination: Path) -> dict[str, int]:
    """Compatibility entry point for the Power BI CSV exports."""
    return PowerBIExporter(engine).export(destination)
