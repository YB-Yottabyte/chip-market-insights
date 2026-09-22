import pandas as pd

from src.metrics import (
    company_metrics,
    market_metrics,
    nearest_calendar_quarter_end,
    revenue_cagr,
)


def test_growth_requires_actual_prior_fiscal_period():
    frame = pd.DataFrame(
        {
            "ticker": ["ON", "ON"],
            "fiscal_year": [2024, 2024],
            "fiscal_quarter": [1, 3],
            "revenue": [100, 150],
            "gross_profit": [40, 60],
            "operating_income": [20, 30],
            "net_income": [10, 15],
            "rd_expense": [5, 7],
        }
    )
    result = company_metrics(frame)
    assert pd.isna(result.iloc[1].qoq_revenue_growth)
    assert result.iloc[0].gross_margin == 0.4


def test_market_growth_requires_12_month_match():
    frame = pd.DataFrame(
        {
            "region": ["World", "World"],
            "date": ["2024-01-31", "2025-01-31"],
            "monthly_sales": [100, 120],
        }
    )
    result = market_metrics(frame)
    assert pd.isna(result.iloc[1].mom_sales_growth)
    assert abs(result.iloc[1].yoy_sales_growth - 0.2) < 1e-10


def test_cagr_guards_invalid_inputs():
    assert abs(revenue_cagr(100, 121, 2) - 0.1) < 1e-10
    assert revenue_cagr(0, 121, 2) is None
    assert revenue_cagr(pd.NA, 121, 2) is None


def test_cagr_uses_same_fiscal_quarter_across_years():
    frame = pd.DataFrame(
        {
            "ticker": ["ON", "ON"],
            "fiscal_year": [2023, 2025],
            "fiscal_quarter": [1, 1],
            "revenue": [100, 121],
            "gross_profit": [40, 50],
            "operating_income": [20, 25],
            "net_income": [10, 15],
            "rd_expense": [5, 6],
        }
    )
    result = company_metrics(frame)
    assert abs(result.iloc[1].revenue_cagr - 0.1) < 1e-10
    assert pd.isna(result.iloc[1].yoy_revenue_growth)


def test_regional_share_and_growth_contribution_need_complete_four_regions():
    regions = ["Americas", "Europe", "Japan", "Asia Pacific"]
    frame = pd.DataFrame(
        {
            "region": regions * 2,
            "date": ["2024-01-31"] * 4 + ["2025-01-31"] * 4,
            "monthly_sales": [10] * 4 + [20, 10, 10, 10],
        }
    )
    result = market_metrics(frame)
    america = result.loc[
        result.region.eq("Americas") & result.date.eq("2025-01-31")
    ].iloc[0]
    assert abs(america.region_share - 0.4) < 1e-10
    assert abs(america.regional_growth_contribution - 0.25) < 1e-10


def test_peer_quarters_align_by_nearest_calendar_end():
    assert nearest_calendar_quarter_end("2026-07-03") == "2026-06-30"
    assert nearest_calendar_quarter_end("2026-07-26") == "2026-06-30"
