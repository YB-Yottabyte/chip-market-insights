# Source validation snapshot

Checked on 2026-09-21 after the earlier local pipeline run. Generated data and the quality summary are excluded from this repository. Rerun the pipeline after restoring the public source files to verify these values against the current data.

| Check | Pipeline output | Primary source |
|---|---:|---|
| onsemi revenue, quarter ended 2026-07-03 | $1,603.5 million | [SEC Form 10-Q](https://www.sec.gov/Archives/edgar/data/1097864/000109786426000017/on-20260703.htm) |
| onsemi R&D, same quarter | $140.8 million | [SEC Form 10-Q](https://www.sec.gov/Archives/edgar/data/1097864/000109786426000017/on-20260703.htm) |
| WSTS worldwide July 2026 three-month average | $146.803 billion, displayed as $146.8 billion | [SIA release based on WSTS](https://www.semiconductors.org/global-semiconductor-sales-increase-6-4-month-to-month-in-july/) |
| onsemi 2025 estimated end-market mix | Automotive 51%, Industrial 28%, Other 21% | [SEC Form 10-K](https://www.sec.gov/Archives/edgar/data/1097864/000109786426000006/on-20251231.htm) |

The WSTS raw workbook says amounts are in thousands of US dollars. The loader multiplies these values by 1,000. World rows reconcile to the four region rows within the documented tolerance. The quarter-ended revenue and R&D values above match the SEC filing's income statement. The end-market mix is an annual company estimate, while Q2 2026 end-market revenue in the reference CSV is rounded investor-presentation data.
