"""Descriptive comparisons and insight text grounded in loaded observations."""

from __future__ import annotations

import pandas as pd

from .config import MARKET_COMPONENT_REGIONS
from .metrics import company_metrics


COMPARISON_COLUMNS = (
    "onsemi_period_end",
    "market_window_end",
    "onsemi_yoy_growth",
    "industry_yoy_growth",
    "growth_gap",
    "market_source",
)


def _monthly_world_sales(markets: pd.DataFrame) -> pd.DataFrame:
    """Use reported World values, or four complete regional values."""
    frame = markets.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp("M")
    world = frame.loc[
        frame["region"].eq("World"), ["date", "monthly_sales", "source_file"]
    ]
    if not world.empty:
        return world.set_index("date").sort_index().dropna(subset=["monthly_sales"])

    regional = frame.loc[frame["region"].isin(MARKET_COMPONENT_REGIONS)]
    region_counts = regional.groupby("date")["region"].nunique()
    complete_dates = region_counts.loc[
        region_counts.eq(len(MARKET_COMPONENT_REGIONS))
    ].index
    totals = regional.groupby("date")["monthly_sales"].sum(
        min_count=len(MARKET_COMPONENT_REGIONS)
    )
    monthly = totals.loc[complete_dates].to_frame()
    monthly["source_file"] = "sum of four reported regions"
    return monthly.dropna(subset=["monthly_sales"])


def _closest_month_end(period_end: str) -> pd.Timestamp | None:
    end = pd.Timestamp(period_end)
    candidates = [
        end.to_period("M").to_timestamp("M"),
        (end - pd.offsets.MonthEnd(1)).to_period("M").to_timestamp("M"),
    ]
    closest = min(candidates, key=lambda candidate: abs((end - candidate).days))
    return closest if abs((end - closest).days) <= 7 else None


def _three_month_window(end: pd.Timestamp) -> list[pd.Timestamp]:
    return [end - pd.offsets.MonthEnd(months_back) for months_back in (0, 1, 2)]


def build_onsemi_industry_comparison(
    companies: pd.DataFrame, markets: pd.DataFrame
) -> pd.DataFrame:
    """Match onsemi fiscal quarters to complete three-month market windows."""
    if companies.empty or markets.empty or "monthly_sales" not in markets:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)

    monthly = _monthly_world_sales(markets)
    if monthly.empty:
        return pd.DataFrame(columns=COMPARISON_COLUMNS)
    sales_by_month = monthly["monthly_sales"].to_dict()
    onsemi = company_metrics(companies).loc[lambda frame: frame["ticker"].eq("ON")]

    rows = []
    for observation in onsemi.itertuples(index=False):
        end = _closest_month_end(observation.period_end)
        if end is None or pd.isna(observation.yoy_revenue_growth):
            continue

        current_months = _three_month_window(end)
        prior_months = [
            month - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)
            for month in current_months
        ]
        if not all(month in sales_by_month for month in current_months + prior_months):
            continue

        prior_sales = sum(sales_by_month[month] for month in prior_months)
        if prior_sales == 0:
            continue
        current_sales = sum(sales_by_month[month] for month in current_months)
        market_growth = current_sales / prior_sales - 1
        rows.append(
            {
                "onsemi_period_end": observation.period_end,
                "market_window_end": end.date().isoformat(),
                "onsemi_yoy_growth": observation.yoy_revenue_growth,
                "industry_yoy_growth": market_growth,
                "growth_gap": observation.yoy_revenue_growth - market_growth,
                "market_source": str(monthly.loc[end, "source_file"]),
            }
        )
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


def build_insights(
    companies: pd.DataFrame,
    markets: pd.DataFrame,
    segments: pd.DataFrame | None = None,
) -> list[dict]:
    """Write descriptive statements only when the supporting rows exist."""
    if companies.empty:
        return []

    measured = company_metrics(companies)
    onsemi = measured.loc[measured["ticker"].eq("ON")]
    onsemi = onsemi.sort_values(["fiscal_year", "fiscal_quarter"])
    if onsemi.empty:
        return []

    latest = onsemi.iloc[-1]
    insights = []
    financial_labels = (
        ("yoy_revenue_growth", "YoY revenue growth"),
        ("gross_margin", "gross margin"),
        ("operating_margin", "operating margin"),
    )
    for column, label in financial_labels:
        value = latest[column]
        if pd.notna(value):
            insights.append(
                {
                    "period_end": latest.period_end,
                    "metric": label,
                    "value": round(float(value), 4),
                    "unit": "fraction",
                    "text": (
                        f"onsemi {label} was {value:.1%} for the quarter "
                        f"ended {latest.period_end}."
                    ),
                    "source": "SEC API; calculated from financial statements",
                }
            )

    comparison = build_onsemi_industry_comparison(companies, markets)
    if not comparison.empty:
        matched = comparison.sort_values("onsemi_period_end").iloc[-1]
        insights.append(
            {
                "period_end": matched.onsemi_period_end,
                "metric": "onsemi versus industry YoY growth gap",
                "value": round(float(matched.growth_gap), 4),
                "unit": "percentage points / 100",
                "text": (
                    f"onsemi quarterly YoY growth was {matched.onsemi_yoy_growth:.1%} "
                    f"versus {matched.industry_yoy_growth:.1%} for the three-month "
                    f"global market window ending {matched.market_window_end}."
                ),
                "source": (
                    f"SEC API and {matched.market_source}; matched three-month window"
                ),
            }
        )

    if segments is not None and not segments.empty:
        annual = segments.loc[
            segments["period_type"].eq("annual")
            & segments["end_market"].isin(["Automotive", "Industrial"])
        ]
        if not annual.empty:
            latest_year = annual["period_end"].max()
            for row in annual.loc[annual["period_end"].eq(latest_year)].itertuples():
                if pd.notna(row.revenue_percentage):
                    insights.append(
                        {
                            "period_end": row.period_end,
                            "metric": f"{row.end_market} annual exposure",
                            "value": float(row.revenue_percentage) / 100,
                            "unit": "fraction",
                            "text": (
                                f"onsemi estimated {row.end_market} at "
                                f"{row.revenue_percentage:g}% of revenue for the year "
                                f"ended {row.period_end}."
                            ),
                            "source": row.source_document,
                        }
                    )
    return insights
