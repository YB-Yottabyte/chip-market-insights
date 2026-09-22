"""Small synthetic fixtures test mechanics only; they are never dashboard data."""

import pandas as pd
from sqlalchemy import create_engine, text

from src.database import load_database
from src.export_powerbi import export_tables


def test_database_and_csv_export_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    financial = pd.DataFrame(
        [
            {
                "ticker": "ON",
                "period_end": "2024-03-31",
                "fiscal_year": 2024,
                "fiscal_quarter": 1,
                "filing_date": "2024-05-01",
                "revenue": 100.0,
                "gross_profit": 40.0,
                "operating_income": 20.0,
                "net_income": 10.0,
                "rd_expense": 5.0,
                "assets": None,
                "cash": None,
                "source_type": "test fixture",
            }
        ]
    )
    market = pd.DataFrame(
        columns=[
            "date",
            "region",
            "monthly_sales",
            "three_month_average",
            "reported_yoy_growth",
            "source_file",
            "source_type",
        ]
    )
    load_database(engine, financial, market)
    counts = export_tables(engine, tmp_path / "exports")
    assert counts["fact_company_financials"] == 1
    assert counts["fact_semiconductor_market"] == 0
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT revenue FROM vw_company_financials")).scalar_one()
            == 100.0
        )
        assert (
            conn.execute(
                text("SELECT COUNT(*) = COUNT(DISTINCT date) FROM dim_date")
            ).scalar_one()
            == 1
        )
    assert (tmp_path / "exports" / "business_insights.json").exists()
