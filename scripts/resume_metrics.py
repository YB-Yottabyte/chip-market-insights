"""Write resume facts supported by code and the latest successful ETL run."""

from __future__ import annotations

import json

import pandas as pd

from src.config import COMPANIES, Settings


def successful_run(settings: Settings) -> dict | None:
    """Read counts only when the saved quality report says the ETL passed."""
    path = settings.quality_summary
    if not path.exists():
        return None
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("status") != "passed":
        return None
    return summary


def _read_export(settings: Settings, name: str) -> pd.DataFrame:
    path = settings.exports / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_report(settings: Settings) -> str:
    """Build a short report without claiming unverified dashboard work."""
    lines = [
        "# Resume metrics",
        "",
        "Counts below come from this repository and its latest successful ETL run.",
        "",
        f"- Companies configured for SEC ingestion: **{len(COMPANIES)}**.",
    ]

    run = successful_run(settings)
    if run is None:
        lines.extend(
            [
                "",
                "No successful local ETL run is available. Data coverage and row counts are omitted.",
            ]
        )
        return "\n".join(lines) + "\n"

    sources = run["source_counts"]
    database_rows = run["database_rows"]
    fact_tables = (
        "fact_company_financials",
        "fact_semiconductor_market",
        "fact_onsemi_segments",
    )
    total_facts = sum(database_rows[table] for table in fact_tables)
    lines.extend(
        [
            f"- Raw SEC company responses processed: **{sources['sec_companies']}**.",
            f"- Raw SEC fact observations processed: **{sources['raw_sec_fact_observations']:,}**.",
            f"- Normalized company quarters: **{sources['sec_financial_rows']:,}**.",
            f"- Imported industry region-month rows: **{sources['industry_rows']:,}**.",
            f"- Imported onsemi end-market rows: **{sources['onsemi_end_market_rows']:,}**.",
            f"- Database fact rows: **{total_facts:,}**.",
            f"- Matched onsemi-industry growth comparisons: **{database_rows['onsemi_industry_comparison']:,}**.",
        ]
    )

    financials = _read_export(settings, "vw_company_financials")
    markets = _read_export(settings, "vw_market_sales")
    if not financials.empty:
        fiscal_periods = financials[["fiscal_year", "fiscal_quarter"]].drop_duplicates()
        lines.extend(
            [
                f"- Companies with financial rows: **{financials['ticker'].nunique()}**.",
                f"- Fiscal-year labels represented: **{financials['fiscal_year'].min()}–{financials['fiscal_year'].max()}** (company fiscal calendars differ).",
                f"- Company quarter-end dates: **{financials['period_end'].min()} to {financials['period_end'].max()}**.",
                f"- Distinct fiscal year-quarter labels: **{len(fiscal_periods)}**.",
            ]
        )
    if not markets.empty:
        lines.extend(
            [
                f"- Industry regions represented: **{markets['region'].nunique()}**.",
                f"- Industry months represented: **{markets['date'].nunique()}**.",
            ]
        )

    lines.extend(
        [
            "",
            "## Resume bullets based on measured results",
            "",
            f"- Built a Python and SQL pipeline for {sources['sec_companies']} semiconductor companies, normalizing {sources['sec_financial_rows']:,} quarterly financial records from SEC Company Facts.",
            f"- Loaded {sources['industry_rows']:,} industry region-month records and produced {database_rows['onsemi_industry_comparison']:,} matched onsemi-to-market growth comparisons.",
            f"- Validated {total_facts:,} SQL fact rows with automated data-quality checks and exported the results for reporting.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    settings = Settings()
    output = settings.resume_metrics_report
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report(settings), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
