from pathlib import Path

from src.config import COMPANIES, COMPANY_CONTEXT, ROOT
from src.segments import load_segments


def test_curated_onsemi_rows_have_sources_and_separate_grains():
    frame = load_segments(ROOT / "data/reference/onsemi_end_markets.csv")
    assert len(frame) == 6
    assert set(frame.period_type) == {"annual", "quarterly"}
    assert frame.source_document.str.startswith("https://").all()
    annual = frame.loc[frame.period_type.eq("annual")]
    assert annual.revenue_percentage.sum() == 100
    assert (
        frame.loc[frame.period_type.eq("quarterly"), "revenue_percentage"].isna().all()
    )


def test_every_sec_company_has_a_business_context():
    assert set(COMPANIES) == set(COMPANY_CONTEXT)
    assert all(group and focus for group, focus in COMPANY_CONTEXT.values())
    assert COMPANY_CONTEXT["ON"][0] == COMPANY_CONTEXT["TXN"][0]
