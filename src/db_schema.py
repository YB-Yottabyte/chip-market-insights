"""SQLAlchemy tables for the reporting database."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)


metadata = MetaData()

company = Table(
    "dim_company",
    metadata,
    Column("company_id", Integer, primary_key=True),
    Column("ticker", String(12), nullable=False, unique=True),
    Column("company_name", String(100), nullable=False),
    Column("cik", Integer, nullable=False, unique=True),
    Column("peer_group", String(60), nullable=False),
    Column("business_focus", String(120), nullable=False),
)

date_dim = Table(
    "dim_date",
    metadata,
    Column("date_id", Integer, primary_key=True),
    Column("date", Date, nullable=False, unique=True),
    Column("year", Integer, nullable=False),
    Column("quarter", Integer, nullable=False),
    Column("month", Integer, nullable=False),
    Column("month_name", String(12), nullable=False),
)

region = Table(
    "dim_region",
    metadata,
    Column("region_id", Integer, primary_key=True),
    Column("region_name", String(60), nullable=False, unique=True),
)

financial = Table(
    "fact_company_financials",
    metadata,
    Column("company_id", Integer, ForeignKey("dim_company.company_id"), nullable=False),
    Column("date_id", Integer, ForeignKey("dim_date.date_id"), nullable=False),
    Column("period_end", Date, nullable=False),
    Column("fiscal_year", Integer, nullable=False),
    Column("fiscal_quarter", Integer, nullable=False),
    Column("filing_date", Date),
    Column("comparison_quarter_end", Date),
    Column("revenue", Float),
    Column("gross_profit", Float),
    Column("operating_income", Float),
    Column("net_income", Float),
    Column("rd_expense", Float),
    Column("assets", Float),
    Column("cash", Float),
    Column("source_type", String(40), nullable=False),
    UniqueConstraint("company_id", "period_end", name="uq_company_period"),
)

market = Table(
    "fact_semiconductor_market",
    metadata,
    Column("date_id", Integer, ForeignKey("dim_date.date_id"), nullable=False),
    Column("region_id", Integer, ForeignKey("dim_region.region_id"), nullable=False),
    Column("monthly_sales", Float),
    Column("three_month_average", Float),
    Column("reported_yoy_growth", Float),
    Column("source_file", String(255)),
    Column("source_type", String(40), nullable=False),
    UniqueConstraint("date_id", "region_id", name="uq_market_date_region"),
)

segment = Table(
    "fact_onsemi_segments",
    metadata,
    Column("date_id", Integer, ForeignKey("dim_date.date_id"), nullable=False),
    Column("period_type", String(12), nullable=False),
    Column("end_market", String(50), nullable=False),
    Column("revenue", Float),
    Column("revenue_percentage", Float),
    Column("source_document", String(255), nullable=False),
    Column("source_type", String(60), nullable=False),
    UniqueConstraint(
        "date_id", "period_type", "end_market", name="uq_segment_date_market"
    ),
)
