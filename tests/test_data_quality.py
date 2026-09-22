import pandas as pd
import pytest

from src.transform import assert_quality, validate_financials, validate_market
from src.segments import load_segments


def test_financial_quality_detects_duplicate_and_bad_revenue():
    frame = pd.DataFrame(
        {
            "ticker": ["ON", "ON"],
            "period_end": ["2024-03-31"] * 2,
            "fiscal_year": [2024] * 2,
            "fiscal_quarter": [1, 5],
            "revenue": [10, -1],
        }
    )
    checks = validate_financials(frame)
    assert checks["duplicate_company_period"] == 1
    assert checks["negative_revenue"] == 1
    with pytest.raises(ValueError):
        assert_quality(checks)


def test_market_quality_handles_empty_file():
    assert all(value == 0 for value in validate_market(pd.DataFrame()).values())


def test_market_quality_reconciles_world_to_four_regions():
    frame = pd.DataFrame(
        {
            "date": ["2025-01-31"] * 5,
            "region": ["Americas", "Europe", "Japan", "Asia Pacific", "World"],
            "monthly_sales": [
                10_000_000,
                10_000_000,
                10_000_000,
                10_000_000,
                50_000_000,
            ],
            "three_month_average": [None] * 5,
            "reported_yoy_growth": [None] * 5,
        }
    )
    assert validate_market(frame)["world_region_reconciliation_failures"] == 1


def test_segment_percentage_validation(tmp_path):
    file = tmp_path / "onsemi_end_markets.csv"
    file.write_text(
        "period_end,period_type,end_market,revenue,revenue_percentage,source_document,source_type\n2024-12-31,annual,Automotive,10,101,filing,manual\n"
    )
    with pytest.raises(ValueError):
        load_segments(file)
