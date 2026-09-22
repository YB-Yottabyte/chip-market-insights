# Build the Power BI report

Power BI Desktop runs on Windows. This repository produces a database and CSVs, not a `.pbix` file.

## 1. Prepare the data

Run `python -m src.pipeline` from the project root after setting `SEC_USER_AGENT`. For local CSV use, select **Get data → Text/CSV** and import `dim_company.csv`, `dim_date.csv`, `dim_region.csv`, and the three `fact_*.csv` files from `data/exports/`. For SQL use, choose **Get data → SQLite** if your Desktop installation has a connector, or **PostgreSQL database** with your configured server. Import the same six tables. CSV is the most portable route.

In Power Query set all `date`, `period_end`, and `comparison_quarter_end` columns to Date; IDs and fiscal fields to Whole Number; financial and market fields to Decimal Number. Keep nulls as nulls. The native WSTS workbook loader converts thousands of USD to USD; check the `source_type` before any dollar comparison with another imported file. If another source uses millions of USD, create a new explicit USD column by multiplying by 1,000,000; retain the original column for auditing. If it reports only a three-month moving average, do not label it raw monthly sales.

For a repeatable Power Query import and type conversion, use the copy-ready M example in [POWER_QUERY_M.md](POWER_QUERY_M.md).

## 2. Relationships and calendar

In Model view, make the five one-to-many, single-direction relationships in [DATA_MODEL.md](DATA_MODEL.md). Do not connect company and market facts directly. Create a continuous calendar with **New table**:

```DAX
Calendar =
ADDCOLUMNS (
    CALENDAR ( MIN ( dim_date[date] ), MAX ( dim_date[date] ) ),
    "Year", YEAR ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" )
)
```

Mark `Calendar[Date]` as the date table. Relate `Calendar[Date]` one-to-many to `dim_date[date]`, single direction. Use Calendar year/month slicers; use fiscal year and fiscal quarter from the company fact for company pages. Turn off auto date/time if desired. If imported dates are text, fix them in Power Query before relationships.

## 3. Measures

Create a separate empty measure table, then paste measures from [DAX_MEASURES.md](DAX_MEASURES.md) one at a time. Format ratios as Percent and USD measures as currency. Filter company cards to one fiscal quarter or label them as totals across the selected quarters. Use the market measures only when the imported source supplies the corresponding sales column.

## 4. Pages

**Global Semiconductor Market** — Cards: Total Semiconductor Sales, YoY Market Growth, MoM Market Growth, Top Region, Selected Period. Line charts: monthly sales by `Calendar[Date]`, YoY growth, rolling three-month sales. Bar charts: region sales and region share. Slicers: Calendar year and region. Exclude `World` from region bars; use it only for the global total. If no industry file is loaded, show a clear “Industry dataset required” note and leave visuals blank.

**Company Comparison** — Cards: Total Revenue, YoY Revenue Growth, Gross Margin, Operating Margin, R&D % Revenue. Trend charts: revenue, growth, operating margin by company and `comparison_quarter_end`; comparison bars: gross margin and R&D intensity. Matrix: ticker, fiscal year, fiscal quarter, period end, comparison quarter end, revenue, margins, R&D. Slicers: company, fiscal year, fiscal quarter. Clear the fiscal-year slicer when comparing companies in the same calendar window, since their fiscal-year labels differ. Show actual period end in tooltips.

**onsemi Deep Dive** — Apply page filter `dim_company[ticker] = ON`. Cards: onsemi Revenue, YoY growth, Gross Margin, Operating Margin, R&D Spending, Automotive Exposure, Industrial Exposure, Other Exposure. Display `Latest Exposure Period` beside the last three cards. Charts: quarterly revenue, growth, margin, R&D trend. End-market composition uses `fact_onsemi_segments`: label annual estimated percentages separately from rounded Q2 2026 quarterly revenue. Import `onsemi_industry_comparison.csv` as a separate, disconnected chart table for the matched growth comparison. Its two growth columns share a percentage scale even if the underlying WSTS currency unit differs; do not compare their dollar totals. When the file is empty, show an explicit unavailable note. For the Business Insights text box, copy the current sentences from `data/exports/business_insights.json` after each refresh; they are calculated from loaded rows. Do not turn those sentences into timeless claims.

## 5. Final checks

Confirm that Power BI row counts match `data/processed/quality_summary.json`. Check two revenue quarters against the SEC filing links, review currency scale, ensure World is not added to its regions, and verify that a one-quarter slicer changes company cards as expected. Save screenshots under `docs/screenshots/` when the report is built.
