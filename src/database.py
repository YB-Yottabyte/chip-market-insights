"""Load validated observations into SQLite or PostgreSQL."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine

from .config import COMPANIES, COMPANY_CONTEXT, ROOT, Settings
from .db_schema import company, date_dim, financial, market, metadata, region, segment
from .metrics import nearest_calendar_quarter_end


LOG = logging.getLogger(__name__)
FINANCIAL_AMOUNT_COLUMNS = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "rd_expense",
    "assets",
    "cash",
)
MARKET_AMOUNT_COLUMNS = (
    "monthly_sales",
    "three_month_average",
    "reported_yoy_growth",
)


def engine_for(url: str) -> Engine:
    """Resolve a relative SQLite URL inside the project directory."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        database_path = ROOT / url.removeprefix("sqlite:///")
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{database_path}")
    return create_engine(url)


class DatabaseLoader:
    """Replace the reporting tables together after input validation succeeds."""

    def __init__(self, engine: Engine, settings: Settings | None = None) -> None:
        self.engine = engine
        self.settings = settings or Settings()

    @staticmethod
    def _date_rows(values: set[str]) -> list[dict]:
        rows = []
        for date_id, value in enumerate(sorted(values), start=1):
            period = pd.Timestamp(value)
            rows.append(
                {
                    "date_id": date_id,
                    "date": period.date(),
                    "year": period.year,
                    "quarter": period.quarter,
                    "month": period.month,
                    "month_name": period.strftime("%B"),
                }
            )
        return rows

    @staticmethod
    def _number_or_none(value: object) -> float | None:
        return None if pd.isna(value) else float(value)

    @staticmethod
    def _date_or_none(value: object) -> date | None:
        return None if pd.isna(value) else pd.Timestamp(value).date()

    def _upgrade_existing_schema(self) -> None:
        """Add columns introduced after older local databases were created."""
        company_columns = {
            column["name"] for column in inspect(self.engine).get_columns("dim_company")
        }
        financial_columns = {
            column["name"]
            for column in inspect(self.engine).get_columns("fact_company_financials")
        }
        upgrades = []
        if "peer_group" not in company_columns:
            upgrades.append("ALTER TABLE dim_company ADD COLUMN peer_group VARCHAR(60)")
        if "business_focus" not in company_columns:
            upgrades.append(
                "ALTER TABLE dim_company ADD COLUMN business_focus VARCHAR(120)"
            )
        if "comparison_quarter_end" not in financial_columns:
            upgrades.append(
                "ALTER TABLE fact_company_financials ADD COLUMN comparison_quarter_end DATE"
            )
        if upgrades:
            with self.engine.begin() as connection:
                for statement in upgrades:
                    connection.execute(text(statement))

    @staticmethod
    def _company_rows() -> list[dict]:
        rows = []
        for company_id, (ticker, (cik, name)) in enumerate(COMPANIES.items(), start=1):
            peer_group, business_focus = COMPANY_CONTEXT[ticker]
            rows.append(
                {
                    "company_id": company_id,
                    "ticker": ticker,
                    "company_name": name,
                    "cik": cik,
                    "peer_group": peer_group,
                    "business_focus": business_focus,
                }
            )
        return rows

    def _financial_row(
        self, observation: object, company_ids: dict[str, int], date_ids: dict[str, int]
    ) -> dict:
        period_end = pd.Timestamp(observation.period_end).date()
        comparison = nearest_calendar_quarter_end(observation.period_end)
        row = {
            "company_id": company_ids[observation.ticker],
            "date_id": date_ids[observation.period_end],
            "period_end": period_end,
            "fiscal_year": int(observation.fiscal_year),
            "fiscal_quarter": int(observation.fiscal_quarter),
            "filing_date": self._date_or_none(observation.filing_date),
            "comparison_quarter_end": self._date_or_none(comparison),
            "source_type": observation.source_type,
        }
        for column in FINANCIAL_AMOUNT_COLUMNS:
            row[column] = self._number_or_none(getattr(observation, column))
        return row

    def _market_row(
        self, observation: object, date_ids: dict[str, int], region_ids: dict[str, int]
    ) -> dict:
        row = {
            "date_id": date_ids[observation.date],
            "region_id": region_ids[observation.region],
            "source_file": observation.source_file,
            "source_type": observation.source_type,
        }
        for column in MARKET_AMOUNT_COLUMNS:
            row[column] = self._number_or_none(getattr(observation, column))
        return row

    def _segment_row(self, observation: object, date_ids: dict[str, int]) -> dict:
        return {
            "date_id": date_ids[observation.period_end],
            "period_type": observation.period_type,
            "end_market": observation.end_market,
            "revenue": self._number_or_none(observation.revenue),
            "revenue_percentage": self._number_or_none(observation.revenue_percentage),
            "source_document": observation.source_document,
            "source_type": observation.source_type,
        }

    def _create_views(self, connection: Connection) -> None:
        """Execute the checked-in SQL view definitions."""
        view_sql = self.settings.sql_views.read_text(encoding="utf-8")
        for statement in view_sql.split(";"):
            if statement.strip():
                connection.execute(text(statement))

    def load(
        self,
        financials: pd.DataFrame,
        markets: pd.DataFrame,
        segments: pd.DataFrame | None = None,
    ) -> None:
        """Refresh dimensions, facts, and views in one data transaction."""
        segments = segments if segments is not None else pd.DataFrame()
        all_dates = set(financials.period_end) | set(markets.date)
        if not segments.empty:
            all_dates.update(segments.period_end)

        date_rows = self._date_rows(all_dates)
        date_ids = {row["date"].isoformat(): row["date_id"] for row in date_rows}
        region_names = sorted(set(markets.region))
        region_ids = {name: index for index, name in enumerate(region_names, start=1)}
        company_ids = {ticker: index for index, ticker in enumerate(COMPANIES, start=1)}

        metadata.create_all(self.engine)
        self._upgrade_existing_schema()

        with self.engine.begin() as connection:
            for table in (segment, market, financial, region, date_dim, company):
                connection.execute(table.delete())

            connection.execute(company.insert(), self._company_rows())
            if date_rows:
                connection.execute(date_dim.insert(), date_rows)
            if region_ids:
                region_rows = [
                    {"region_id": region_id, "region_name": name}
                    for name, region_id in region_ids.items()
                ]
                connection.execute(region.insert(), region_rows)

            if not financials.empty:
                rows = [
                    self._financial_row(item, company_ids, date_ids)
                    for item in financials.itertuples(index=False)
                ]
                connection.execute(financial.insert(), rows)
            if not markets.empty:
                rows = [
                    self._market_row(item, date_ids, region_ids)
                    for item in markets.itertuples(index=False)
                ]
                connection.execute(market.insert(), rows)
            if not segments.empty:
                rows = [
                    self._segment_row(item, date_ids)
                    for item in segments.itertuples(index=False)
                ]
                connection.execute(segment.insert(), rows)

            self._create_views(connection)
        LOG.info(
            "Loaded %s company and %s market records", len(financials), len(markets)
        )


def load_database(
    engine: Engine,
    financials: pd.DataFrame,
    markets: pd.DataFrame,
    segments: pd.DataFrame | None = None,
) -> None:
    """Compatibility entry point for the reporting database refresh."""
    DatabaseLoader(engine).load(financials, markets, segments)
