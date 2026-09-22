"""Financial and market metrics calculated from observed periods."""

from __future__ import annotations

import pandas as pd

from .config import MARKET_COMPONENT_REGIONS


def nearest_calendar_quarter_end(value: str | pd.Timestamp) -> str | None:
    """Return the closest calendar quarter end if it is within 45 days."""
    fiscal_end = pd.Timestamp(value)
    candidates = [
        pd.Timestamp(year, month, 1) + pd.offsets.MonthEnd(0)
        for year in (fiscal_end.year - 1, fiscal_end.year, fiscal_end.year + 1)
        for month in (3, 6, 9, 12)
    ]
    nearest = min(candidates, key=lambda date: abs((date - fiscal_end).days))
    if abs((nearest - fiscal_end).days) > 45:
        return None
    return nearest.date().isoformat()


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide without turning zero denominators into misleading values."""
    return numerator.div(denominator.where(denominator.ne(0)))


def revenue_cagr(first: float | None, last: float | None, years: float) -> float | None:
    """Calculate annualized growth when both endpoints and duration are valid."""
    if pd.isna(first) or pd.isna(last) or pd.isna(years):
        return None
    if first <= 0 or last < 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def _add_period_growth(
    frame: pd.DataFrame,
    group_column: str,
    period_number: pd.Series,
    value_column: str,
    growth_periods: tuple[tuple[str, int], ...],
) -> None:
    """Match prior observations by actual period key, allowing gaps."""
    lookup = frame.assign(_period_number=period_number).set_index(
        [group_column, "_period_number"]
    )[value_column]
    if not lookup.index.is_unique:
        raise ValueError(f"Duplicate {group_column} and period")

    for output_column, period_offset in growth_periods:
        prior_keys = pd.MultiIndex.from_arrays(
            [frame[group_column], period_number - period_offset]
        )
        previous = pd.Series(lookup.reindex(prior_keys).to_numpy(), index=frame.index)
        frame[output_column] = safe_ratio(frame[value_column] - previous, previous)


def _add_company_margins(frame: pd.DataFrame) -> None:
    numerator_columns = {
        "gross_margin": "gross_profit",
        "operating_margin": "operating_income",
        "net_margin": "net_income",
        "rd_revenue_ratio": "rd_expense",
    }
    for output_column, numerator_column in numerator_columns.items():
        frame[output_column] = safe_ratio(frame[numerator_column], frame["revenue"])


def _add_company_cagr(frame: pd.DataFrame) -> None:
    frame["revenue_cagr"] = pd.NA
    for _, same_quarter in frame.groupby(["ticker", "fiscal_quarter"]):
        first = same_quarter.sort_values("fiscal_year").iloc[0]
        for row_index, row in same_quarter.iterrows():
            years = int(row.fiscal_year) - int(first.fiscal_year)
            frame.at[row_index, "revenue_cagr"] = revenue_cagr(
                first.revenue, row.revenue, years
            )
    frame["revenue_cagr"] = pd.to_numeric(frame["revenue_cagr"])


def company_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Add growth, margins, R&D intensity, and same-quarter CAGR."""
    result = frame.sort_values(["ticker", "fiscal_year", "fiscal_quarter"]).copy()
    if result.empty:
        return result

    if "comparison_quarter_end" not in result and "period_end" in result:
        result["comparison_quarter_end"] = result["period_end"].map(
            nearest_calendar_quarter_end
        )

    fiscal_period = result["fiscal_year"] * 4 + result["fiscal_quarter"]
    _add_period_growth(
        result,
        group_column="ticker",
        period_number=fiscal_period,
        value_column="revenue",
        growth_periods=(("qoq_revenue_growth", 1), ("yoy_revenue_growth", 4)),
    )
    _add_company_margins(result)
    _add_company_cagr(result)
    return result


def _add_rolling_market_average(frame: pd.DataFrame) -> None:
    regions = frame.groupby("region", sort=False)
    rolling_mean = regions["monthly_sales"].transform(
        lambda sales: sales.rolling(3, min_periods=3).mean()
    )
    consecutive_months = regions["date"].transform(
        lambda dates: (dates.dt.year * 12 + dates.dt.month).diff(2).eq(2)
    )
    frame["calculated_three_month_average"] = rolling_mean.where(consecutive_months)


def _add_regional_contribution(frame: pd.DataFrame) -> None:
    frame["region_share"] = pd.NA
    frame["regional_growth_contribution"] = pd.NA
    component_rows = frame.loc[frame["region"].isin(MARKET_COMPONENT_REGIONS)]

    for month, current in component_rows.groupby("date"):
        if set(current["region"]) != MARKET_COMPONENT_REGIONS:
            continue
        if current["monthly_sales"].isna().any():
            continue

        current_total = current["monthly_sales"].sum()
        if current_total > 0:
            frame.loc[current.index, "region_share"] = (
                current["monthly_sales"] / current_total
            )

        previous_month = month - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)
        previous = component_rows.loc[component_rows["date"].eq(previous_month)]
        if set(previous["region"]) != MARKET_COMPONENT_REGIONS:
            continue
        if previous["monthly_sales"].isna().any():
            continue

        previous_total = previous["monthly_sales"].sum()
        if previous_total <= 0:
            continue
        previous_by_region = previous.set_index("region")["monthly_sales"]
        contributions = [
            (row.monthly_sales - previous_by_region[row.region]) / previous_total
            for row in current.itertuples()
        ]
        frame.loc[current.index, "regional_growth_contribution"] = contributions

    frame["region_share"] = pd.to_numeric(frame["region_share"])
    frame["regional_growth_contribution"] = pd.to_numeric(
        frame["regional_growth_contribution"]
    )


def market_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Add exact-period growth, rolling sales, and regional contribution."""
    result = frame.sort_values(["region", "date"]).copy()
    if result.empty:
        return result

    result["date"] = pd.to_datetime(result["date"])
    month_number = result["date"].dt.year * 12 + result["date"].dt.month
    _add_period_growth(
        result,
        group_column="region",
        period_number=month_number,
        value_column="monthly_sales",
        growth_periods=(("mom_sales_growth", 1), ("yoy_sales_growth", 12)),
    )
    _add_rolling_market_average(result)
    _add_regional_contribution(result)
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result
