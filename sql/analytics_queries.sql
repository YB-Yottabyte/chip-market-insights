-- Fiscal quarter company comparison (USD). Fiscal calendars can differ.
SELECT
    financials.fiscal_year,
    financials.fiscal_quarter,
    financials.ticker,
    financials.revenue,
    CASE
        WHEN financials.revenue <> 0
        THEN financials.gross_profit / financials.revenue
    END AS gross_margin,
    CASE
        WHEN financials.revenue <> 0
        THEN financials.operating_income / financials.revenue
    END AS operating_margin,
    CASE
        WHEN financials.revenue <> 0
        THEN financials.rd_expense / financials.revenue
    END AS rd_intensity
FROM vw_company_financials AS financials
ORDER BY
    financials.fiscal_year DESC,
    financials.fiscal_quarter DESC,
    financials.ticker;

-- Industry time series. Sales units follow the imported source file.
SELECT
    market.date,
    market.region,
    market.monthly_sales,
    market.three_month_average,
    market.source_file
FROM vw_market_sales AS market
ORDER BY market.date, market.region;

-- onsemi end-market disclosure coverage, when cited data is supplied.
SELECT
    calendar.date AS period_end,
    segments.period_type,
    segments.end_market,
    segments.revenue,
    segments.revenue_percentage,
    segments.source_document,
    segments.source_type
FROM fact_onsemi_segments AS segments
JOIN dim_date AS calendar
    ON segments.date_id = calendar.date_id
ORDER BY calendar.date, segments.end_market;
