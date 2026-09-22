# Industry and onsemi disclosure inputs

## Official WSTS data

1. Open the [WSTS Historical Billings Report](https://www.wsts.org/67/Historical-Billings-Report).
2. Download its XLSX workbook. WSTS describes it as a free historical report with monthly billings and three-month moving averages by Americas, Europe, Japan, and Asia Pacific. Respect the copyright terms on the page. Keep the original workbook outside Git.
3. Place the downloaded original workbook in this folder and rerun `python -m src.pipeline`. The loader reads its `Monthly Data` and `3MMA` sheets directly, converts the workbook's stated “1000 US$” amount unit to USD, and skips future zero placeholders. Do not place a second copy of the same region-month data here.

The loader also accepts other tidy CSV/XLSX sources with columns `Date`, `Region`, and `Monthly Sales`. Add `Three-Month Moving Average` and `YoY Growth` if provided. Each row must be one month and one region. For these other files, record the amount unit in your local notes: the loader preserves numerical values and does not guess whether a table uses USD, USD millions, or USD billions. For a file containing only a three-month moving average, leave `Monthly Sales` empty rather than copying averaged values into it.

Minimal accepted file:

```csv
Date,Region,Monthly Sales,Three-Month Moving Average,YoY Growth
```

The header above is a format example, not data. Accepted region names include Americas, Europe, Japan, Asia Pacific, China, and World. The loader rejects duplicate region-month observations and negative sales. WSTS copyright is why this repository does not include or republish its workbook.

## Optional onsemi end-market data

Official [onsemi investor relations](https://investor.onsemi.com/) provides quarterly revenue breakout files when available. If you can verify Automotive, Industrial, or Other values for a period, create `onsemi_end_markets.csv` here with:

```csv
period_end,period_type,end_market,revenue,revenue_percentage,source_document,source_type
```

The required columns are `period_end,period_type,end_market,revenue,revenue_percentage,source_document,source_type`. `period_type` is `annual` or `quarterly`. `revenue` must be USD, matching SEC financial facts. `revenue_percentage` is a 0–100 percentage, not a fraction. Put the exact investor presentation or filing URL in `source_document`, and describe the extraction in `source_type`. Leave a numeric field empty when the source lacks it. The loader does not infer exposure from a company description or mix of product segments. Do not duplicate the six verified rows already bundled in `data/reference/onsemi_end_markets.csv`.
