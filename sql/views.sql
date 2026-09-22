DROP VIEW IF EXISTS vw_company_financials;

CREATE VIEW vw_company_financials AS
SELECT
    company.ticker,
    company.company_name,
    financials.period_end,
    financials.fiscal_year,
    financials.fiscal_quarter,
    financials.filing_date,
    financials.comparison_quarter_end,
    financials.revenue,
    financials.gross_profit,
    financials.operating_income,
    financials.net_income,
    financials.rd_expense,
    financials.assets,
    financials.cash,
    financials.source_type
FROM fact_company_financials AS financials
JOIN dim_company AS company
    ON financials.company_id = company.company_id;

DROP VIEW IF EXISTS vw_market_sales;

CREATE VIEW vw_market_sales AS
SELECT
    calendar.date,
    region.region_name AS region,
    market.monthly_sales,
    market.three_month_average,
    market.reported_yoy_growth,
    market.source_file,
    market.source_type
FROM fact_semiconductor_market AS market
JOIN dim_date AS calendar
    ON market.date_id = calendar.date_id
JOIN dim_region AS region
    ON market.region_id = region.region_id;
