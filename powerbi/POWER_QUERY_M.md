# Power Query steps

The Python loader cleans the source files before export. Power Query is still useful for repeatable report-side typing and audit columns. Create a **Text parameter** named `ExportFolder` with the absolute path to `data/exports/` on your own computer, including the final slash or backslash. In Power BI Desktop, choose **Get data → Blank query → Advanced Editor** and paste the following M. Rename the query `fact_company_financials`.

```powerquery
let
    Source = Csv.Document(
        File.Contents(ExportFolder & "fact_company_financials.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"company_id", Int64.Type}, {"date_id", Int64.Type},
        {"period_end", type date}, {"filing_date", type date},
        {"comparison_quarter_end", type date},
        {"fiscal_year", Int64.Type}, {"fiscal_quarter", Int64.Type},
        {"revenue", type number}, {"gross_profit", type number},
        {"operating_income", type number}, {"net_income", type number},
        {"rd_expense", type number}, {"assets", type number}, {"cash", type number},
        {"source_type", type text}
    }, "en-US")
in
    Typed
```

For `fact_semiconductor_market`, import the CSV through the same Text/CSV dialog and set `date_id` and `region_id` to Whole Number; sales fields to Decimal Number. Keep `source_file` and `source_type` visible for audit. If the WSTS workbook uses a wide layout, unpivot its region columns in Power Query before saving the tidy CSV described in [the input guide](../data/raw/industry/README.md). Do not convert null sales to zero. A refresh reruns these Power Query steps after the Python pipeline replaces the exports.
