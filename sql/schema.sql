-- PostgreSQL reference schema. The Python loader creates the equivalent
-- tables in PostgreSQL or SQLite through SQLAlchemy metadata.

CREATE TABLE dim_company (
    company_id INTEGER PRIMARY KEY,
    ticker VARCHAR(12) NOT NULL UNIQUE,
    company_name VARCHAR(100) NOT NULL,
    cik INTEGER NOT NULL UNIQUE,
    peer_group VARCHAR(60) NOT NULL,
    business_focus VARCHAR(120) NOT NULL
);

CREATE TABLE dim_date (
    date_id INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(12) NOT NULL
);

CREATE TABLE dim_region (
    region_id INTEGER PRIMARY KEY,
    region_name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE fact_company_financials (
    company_id INTEGER NOT NULL REFERENCES dim_company(company_id),
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    period_end DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER NOT NULL,
    filing_date DATE,
    comparison_quarter_end DATE,
    revenue DOUBLE PRECISION,
    gross_profit DOUBLE PRECISION,
    operating_income DOUBLE PRECISION,
    net_income DOUBLE PRECISION,
    rd_expense DOUBLE PRECISION,
    assets DOUBLE PRECISION,
    cash DOUBLE PRECISION,
    source_type VARCHAR(40) NOT NULL,
    UNIQUE (company_id, period_end)
);

CREATE TABLE fact_semiconductor_market (
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    region_id INTEGER NOT NULL REFERENCES dim_region(region_id),
    monthly_sales DOUBLE PRECISION,
    three_month_average DOUBLE PRECISION,
    reported_yoy_growth DOUBLE PRECISION,
    source_file VARCHAR(255),
    source_type VARCHAR(40) NOT NULL,
    UNIQUE (date_id, region_id)
);

CREATE TABLE fact_onsemi_segments (
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    period_type VARCHAR(12) NOT NULL,
    end_market VARCHAR(50) NOT NULL,
    revenue DOUBLE PRECISION,
    revenue_percentage DOUBLE PRECISION,
    source_document VARCHAR(255) NOT NULL,
    source_type VARCHAR(60) NOT NULL,
    UNIQUE (date_id, period_type, end_market)
);
