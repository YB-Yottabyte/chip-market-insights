# DAX measures

Paste each code block as a separate measure. The company growth measures expect one fiscal year and quarter in the visual point or slicer. A blank result means the comparison period is missing or its denominator is zero. Financial values are USD; market sales retain the source file's documented unit.

### Total Revenue
```DAX
Total Revenue = SUM ( fact_company_financials[revenue] )
```

### Previous-Year Revenue
```DAX
Previous-Year Revenue =
VAR FY = SELECTEDVALUE ( fact_company_financials[fiscal_year] )
VAR FQ = SELECTEDVALUE ( fact_company_financials[fiscal_quarter] )
RETURN IF ( NOT ISBLANK ( FY ) && NOT ISBLANK ( FQ ),
    CALCULATE ( [Total Revenue], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ),
        REMOVEFILTERS ( fact_company_financials[period_end], fact_company_financials[date_id],
                        fact_company_financials[comparison_quarter_end],
                        fact_company_financials[fiscal_year], fact_company_financials[fiscal_quarter] ),
        fact_company_financials[fiscal_year] = FY - 1,
        fact_company_financials[fiscal_quarter] = FQ ) )
```

### Previous-Quarter Revenue
```DAX
Previous-Quarter Revenue =
VAR FY = SELECTEDVALUE ( fact_company_financials[fiscal_year] )
VAR FQ = SELECTEDVALUE ( fact_company_financials[fiscal_quarter] )
RETURN IF ( NOT ISBLANK ( FY ) && NOT ISBLANK ( FQ ),
    CALCULATE ( [Total Revenue], REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ),
        REMOVEFILTERS ( fact_company_financials[period_end], fact_company_financials[date_id],
                        fact_company_financials[comparison_quarter_end],
                        fact_company_financials[fiscal_year], fact_company_financials[fiscal_quarter] ),
        fact_company_financials[fiscal_year] = IF ( FQ = 1, FY - 1, FY ),
        fact_company_financials[fiscal_quarter] = IF ( FQ = 1, 4, FQ - 1 ) ) )
```

### Revenue Change
```DAX
Revenue Change = IF ( ISBLANK ( [Total Revenue] ) || ISBLANK ( [Previous-Year Revenue] ),
    BLANK (), [Total Revenue] - [Previous-Year Revenue] )
```

### YoY Revenue Growth %
```DAX
YoY Revenue Growth % = DIVIDE ( [Revenue Change], [Previous-Year Revenue] )
```

### QoQ Revenue Growth %
```DAX
QoQ Revenue Growth % = IF ( ISBLANK ( [Total Revenue] ) || ISBLANK ( [Previous-Quarter Revenue] ),
    BLANK (), DIVIDE ( [Total Revenue] - [Previous-Quarter Revenue], [Previous-Quarter Revenue] ) )
```

### Gross Margin %
```DAX
Gross Margin % = DIVIDE ( SUM ( fact_company_financials[gross_profit] ), [Total Revenue] )
```

### Operating Margin %
```DAX
Operating Margin % = DIVIDE ( SUM ( fact_company_financials[operating_income] ), [Total Revenue] )
```

### Net Margin %
```DAX
Net Margin % = DIVIDE ( SUM ( fact_company_financials[net_income] ), [Total Revenue] )
```

### R&D Spending
```DAX
R&D Spending = SUM ( fact_company_financials[rd_expense] )
```

### R&D % Revenue
```DAX
R&D % Revenue = DIVIDE ( [R&D Spending], [Total Revenue] )
```

### Total Semiconductor Sales
```DAX
Total Semiconductor Sales =
VAR HasWorld = CALCULATE ( COUNTROWS ( fact_semiconductor_market ),
    REMOVEFILTERS ( dim_region ), dim_region[region_name] = "World" ) > 0
RETURN IF ( ISFILTERED ( dim_region[region_name] ),
    SUM ( fact_semiconductor_market[monthly_sales] ),
    IF ( HasWorld,
        CALCULATE ( SUM ( fact_semiconductor_market[monthly_sales] ),
            REMOVEFILTERS ( dim_region ), dim_region[region_name] = "World" ),
        CALCULATE ( SUM ( fact_semiconductor_market[monthly_sales] ),
            dim_region[region_name] <> "World" ) ) )
```

### Previous-Year Market Sales
```DAX
Previous-Year Market Sales = CALCULATE ( [Total Semiconductor Sales], DATEADD ( Calendar[Date], -1, YEAR ) )
```

### YoY Market Growth %
```DAX
YoY Market Growth % = IF ( ISBLANK ( [Total Semiconductor Sales] ) || ISBLANK ( [Previous-Year Market Sales] ),
    BLANK (), DIVIDE ( [Total Semiconductor Sales] - [Previous-Year Market Sales], [Previous-Year Market Sales] ) )
```

### Previous-Month Market Sales
```DAX
Previous-Month Market Sales = CALCULATE ( [Total Semiconductor Sales], DATEADD ( Calendar[Date], -1, MONTH ) )
```

### MoM Market Growth %
```DAX
MoM Market Growth % = IF ( ISBLANK ( [Total Semiconductor Sales] ) || ISBLANK ( [Previous-Month Market Sales] ),
    BLANK (), DIVIDE ( [Total Semiconductor Sales] - [Previous-Month Market Sales], [Previous-Month Market Sales] ) )
```

### Rolling 3-Month Sales
```DAX
Rolling 3-Month Sales =
VAR EndDate = MAX ( Calendar[Date] )
VAR WindowSales = CALCULATE ( [Total Semiconductor Sales],
    DATESBETWEEN ( Calendar[Date], EOMONTH ( EndDate, -3 ) + 1, EndDate ) )
VAR MonthsPresent = CALCULATE ( DISTINCTCOUNT ( fact_semiconductor_market[date_id] ),
    DATESBETWEEN ( Calendar[Date], EOMONTH ( EndDate, -3 ) + 1, EndDate ),
    NOT ISBLANK ( fact_semiconductor_market[monthly_sales] ) )
RETURN IF ( MonthsPresent = 3, DIVIDE ( WindowSales, 3 ) )
```

Use this measure at a monthly point. The three-month window cannot span three observations unless the imported data covers each month.

### Reported 3-Month Average
```DAX
Reported 3-Month Average = SUM ( fact_semiconductor_market[three_month_average] )
```

### Region Share %
```DAX
Region Share % =
VAR RegionSales = SUM ( fact_semiconductor_market[monthly_sales] )
VAR AllRegions = CALCULATE ( SUM ( fact_semiconductor_market[monthly_sales] ),
    REMOVEFILTERS ( dim_region ), dim_region[region_name] <> "World" )
RETURN IF ( SELECTEDVALUE ( dim_region[region_name] ) <> "World",
    DIVIDE ( RegionSales, AllRegions ) )
```

Only use region share when the source supplies all component regions for the selected months. This is share of reported regional sales, not a company's semiconductor market share.

### Top Region
```DAX
Top Region =
VAR Ranked = TOPN ( 1,
    FILTER ( ALL ( dim_region[region_name] ), dim_region[region_name] <> "World"
        && NOT ISBLANK ( CALCULATE ( SUM ( fact_semiconductor_market[monthly_sales] ) ) ) ),
    CALCULATE ( SUM ( fact_semiconductor_market[monthly_sales] ) ), DESC )
RETURN CONCATENATEX ( Ranked, dim_region[region_name], ", " )
```

### Selected Period
```DAX
Selected Period = FORMAT ( MAX ( Calendar[Date] ), "MMM yyyy" )
```

### Selected Company Revenue
```DAX
Selected Company Revenue = IF ( HASONEVALUE ( dim_company[ticker] ), [Total Revenue] )
```

### onsemi Revenue
```DAX
onsemi Revenue = CALCULATE ( [Total Revenue], REMOVEFILTERS ( dim_company ), dim_company[ticker] = "ON" )
```

### Competitor Median Growth %
```DAX
Competitor Median Growth % =
VAR Anchor = SELECTEDVALUE ( fact_company_financials[comparison_quarter_end] )
RETURN IF ( NOT ISBLANK ( Anchor ),
    MEDIANX (
        FILTER ( ALL ( dim_company ), dim_company[ticker] <> "ON" ),
        VAR Peer = dim_company[ticker]
        RETURN CALCULATE ( [YoY Revenue Growth %],
            REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ),
            REMOVEFILTERS ( fact_company_financials[period_end], fact_company_financials[date_id],
                            fact_company_financials[comparison_quarter_end],
                            fact_company_financials[fiscal_year], fact_company_financials[fiscal_quarter] ),
            fact_company_financials[comparison_quarter_end] = Anchor,
            dim_company[ticker] = Peer ) ) )
```

### onsemi Growth Gap vs Peers
```DAX
onsemi Growth Gap vs Peers =
CALCULATE ( [YoY Revenue Growth %], REMOVEFILTERS ( dim_company ), dim_company[ticker] = "ON" )
    - [Competitor Median Growth %]
```

### Automotive Exposure %
```DAX
Automotive Exposure % =
VAR LatestAnnual = CALCULATE ( MAX ( fact_onsemi_segments[date_id] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[period_type] = "annual" )
RETURN DIVIDE ( CALCULATE ( SUM ( fact_onsemi_segments[revenue_percentage] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[date_id] = LatestAnnual,
    fact_onsemi_segments[end_market] = "Automotive" ), 100 )
```

### Industrial Exposure %
```DAX
Industrial Exposure % =
VAR LatestAnnual = CALCULATE ( MAX ( fact_onsemi_segments[date_id] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[period_type] = "annual" )
RETURN DIVIDE ( CALCULATE ( SUM ( fact_onsemi_segments[revenue_percentage] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[date_id] = LatestAnnual,
    fact_onsemi_segments[end_market] = "Industrial" ), 100 )
```

### Other Exposure %
```DAX
Other Exposure % =
VAR LatestAnnual = CALCULATE ( MAX ( fact_onsemi_segments[date_id] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[period_type] = "annual" )
RETURN DIVIDE ( CALCULATE ( SUM ( fact_onsemi_segments[revenue_percentage] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[date_id] = LatestAnnual,
    fact_onsemi_segments[end_market] = "Other" ), 100 )
```

### Latest Exposure Period
```DAX
Latest Exposure Period =
VAR LatestAnnual = CALCULATE ( MAX ( fact_onsemi_segments[date_id] ),
    REMOVEFILTERS ( Calendar ), REMOVEFILTERS ( dim_date ), REMOVEFILTERS ( fact_onsemi_segments ),
    fact_onsemi_segments[period_type] = "annual" )
RETURN FORMAT ( LOOKUPVALUE ( dim_date[date], dim_date[date_id], LatestAnnual ), "yyyy" )
```

These exposure cards show the latest annual reported estimates, ignoring the quarterly date slicer. Display `Latest Exposure Period` beside them. The bundled 2025 estimates are annual; the Q2 2026 presentation gives rounded quarterly revenue amounts but no exact percentages. Reported percentages are entered on a 0–100 scale. Do not total percentages across quarters.
