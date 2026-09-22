# Company context used in the report

The peer-group slicer is an editorial aid for interpreting financial trends. It is not an investment ranking, a claim of identical product mixes, or a measure of market share. The assignment lives in `src/config.py` and is exported in `dim_company`.

| Group | Companies | Why this view is useful |
|---|---|---|
| Power, analog & industrial | onsemi, Texas Instruments | Both have material exposure to long-life industrial and power/analog applications, although onsemi has a distinct automotive and power mix. |
| AI & accelerated compute | NVIDIA | Shows an accelerator-led business model in its own context. |
| Compute platforms | AMD, Intel | Shows companies with large CPU and platform businesses; AMD also sells accelerators. |
| Memory | Micron | Keeps memory-cycle economics visible rather than treating them as directly comparable with logic or analog vendors. |

These labels summarize company descriptions in public filings. Product mix changes over time. The report should show the group beside each company and allow users to inspect each company on its own time series. A group containing one company is a context category, not a statistical peer sample.

Primary source: each company's SEC Form 10-K accessible through the [SEC EDGAR search](https://www.sec.gov/edgar/search/). The grouped labels are project metadata, not API-supplied facts.
