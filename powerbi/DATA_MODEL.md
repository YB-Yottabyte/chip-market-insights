# Power BI data model

Import the six base CSV tables in `data/exports/`. The two `vw_` files are convenient flat analysis tables, but do not relate them to the base facts in the same report or you will count records twice.

| One side | Many side | Join | Direction |
|---|---|---|---|
| `dim_company` | `fact_company_financials` | `company_id` | Single |
| `dim_date` | `fact_company_financials` | `date_id` | Single |
| `dim_date` | `fact_semiconductor_market` | `date_id` | Single |
| `dim_region` | `fact_semiconductor_market` | `region_id` | Single |
| `dim_date` | `fact_onsemi_segments` | `date_id` | Single |

`fact_company_financials` has one company and period-end row per fiscal quarter. USD values are unscaled. `fact_semiconductor_market` has one region and month row. The native WSTS XLSX loader converts its stated thousands-of-USD unit to USD; other tidy files retain their stated source unit. Check the source type before dollar comparisons. A World aggregate and component regions must never be summed together.

`comparison_quarter_end` assigns each company's fiscal end date to the nearest calendar quarter end within 45 days. Use it for peer growth comparisons; use the actual `period_end` in tooltips. Fiscal year and quarter labels alone are not a common peer time axis.

`dim_date` contains observed period ends. A continuous calendar can support time intelligence in Power BI. Fiscal quarters differ among companies, so label comparisons by fiscal year and quarter and inspect period-end dates when comparing with calendar industry months. `fact_onsemi_segments` contains six curated, cited onsemi observations: annual 2025 percentage estimates and rounded Q2 2026 revenue by end market. Its `period_type` and `source_type` columns must be visible in end-market visuals. Annual exposure and quarterly revenue are different grains and should not be added together.

Lineage: SEC API → `fact_company_financials`; manually supplied public file → `fact_semiconductor_market`; cited SEC filing or investor presentation extraction → `fact_onsemi_segments`; Python/DAX formulas → calculated metrics.
