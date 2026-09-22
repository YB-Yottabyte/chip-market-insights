"""Configuration shared by ingestion, validation, and reporting exports."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# CIKs identify SEC filers. Names are labels for the public report.
COMPANIES = {
    "ON": (1097864, "onsemi"),
    "NVDA": (1045810, "NVIDIA"),
    "AMD": (2488, "Advanced Micro Devices"),
    "INTC": (50863, "Intel"),
    "TXN": (97476, "Texas Instruments"),
    "MU": (723125, "Micron Technology"),
}

# These groups provide business context. They are not performance rankings.
COMPANY_CONTEXT = {
    "ON": ("Power, analog & industrial", "Automotive and industrial power and sensing"),
    "TXN": ("Power, analog & industrial", "Analog and embedded processing"),
    "NVDA": ("AI & accelerated compute", "Accelerated computing and graphics"),
    "AMD": ("Compute platforms", "CPUs and compute accelerators"),
    "INTC": ("Compute platforms", "CPUs and platform products"),
    "MU": ("Memory", "Memory and storage"),
}

SEC_GAAP_TAGS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "rd_expense": (
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ),
    "assets": ("Assets",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
}

INDUSTRY_COLUMN_ALIASES = {
    "date": "date",
    "month": "date",
    "period": "date",
    "region": "region",
    "geography": "region",
    "monthly sales": "monthly_sales",
    "sales": "monthly_sales",
    "three month moving average": "three_month_average",
    "3 month moving average": "three_month_average",
    "three month average": "three_month_average",
    "3mma": "three_month_average",
    "yoy growth": "reported_yoy_growth",
    "year over year growth": "reported_yoy_growth",
}

REGION_ALIASES = {
    "asia pacific": "Asia Pacific",
    "asia-pacific": "Asia Pacific",
    "apac": "Asia Pacific",
    "china": "China",
    "americas": "Americas",
    "europe": "Europe",
    "japan": "Japan",
    "world": "World",
    "worldwide": "World",
    "global": "World",
}

MARKET_COMPONENT_REGIONS = frozenset({"Americas", "Europe", "Japan", "Asia Pacific"})

WSTS_SHEETS = ("Monthly Data", "3MMA")
WSTS_USD_MULTIPLIER = 1000

SEGMENT_COLUMNS = (
    "period_end",
    "period_type",
    "end_market",
    "revenue",
    "revenue_percentage",
    "source_document",
    "source_type",
)

EXPORT_TABLE_NAMES = (
    "dim_company",
    "dim_date",
    "dim_region",
    "fact_company_financials",
    "fact_semiconductor_market",
    "fact_onsemi_segments",
    "vw_company_financials",
    "vw_market_sales",
)

POWER_BI_IMPORT_TABLE_NAMES = EXPORT_TABLE_NAMES[:6] + ("onsemi_industry_comparison",)


@dataclass(frozen=True)
class Settings:
    """Runtime options and paths, with environment values read at creation time."""

    user_agent: str = field(
        default_factory=lambda: os.getenv("SEC_USER_AGENT", "").strip()
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///data/processed/semiconductor.db"
        )
    )
    cache_days: int = field(
        default_factory=lambda: int(os.getenv("SEC_CACHE_DAYS", "7"))
    )
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("SEC_TIMEOUT_SECONDS", "30"))
    )
    sec_base_url: str = "https://data.sec.gov/api/xbrl/companyfacts"
    sec_request_interval_seconds: float = 0.2
    sec_retry_attempts: int = 4
    sec_retry_backoff: float = 1.0

    @property
    def raw_sec(self) -> Path:
        return ROOT / "data/raw/sec"

    @property
    def raw_industry(self) -> Path:
        return ROOT / "data/raw/industry"

    @property
    def reference_segments(self) -> Path:
        return ROOT / "data/reference/onsemi_end_markets.csv"

    @property
    def quality_summary(self) -> Path:
        return ROOT / "data/processed/quality_summary.json"

    @property
    def sql_views(self) -> Path:
        return ROOT / "sql/views.sql"

    @property
    def exports(self) -> Path:
        return ROOT / "data/exports"

    @property
    def powerbi_import(self) -> Path:
        return ROOT / "data/processed/powerbi_import.json"

    @property
    def resume_metrics_report(self) -> Path:
        return ROOT / "docs/RESUME_METRICS.md"
