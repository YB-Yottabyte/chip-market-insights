"""Stage typed SQL export rows for the optional Power BI Service XLSX upload."""

from __future__ import annotations

import json

import pandas as pd

from src.config import POWER_BI_IMPORT_TABLE_NAMES, Settings


def main() -> None:
    settings = Settings()
    sheets = []
    for name in POWER_BI_IMPORT_TABLE_NAMES:
        source = settings.exports / f"{name}.csv"
        if not source.exists():
            raise FileNotFoundError(f"Run the ETL first: {source}")
        frame = pd.read_csv(source, keep_default_na=True)
        frame = frame.astype(object).where(pd.notna(frame), None)
        sheets.append(
            {
                "name": name,
                "columns": list(frame.columns),
                "rows": frame.values.tolist(),
            }
        )
    output = settings.powerbi_import
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sheets, ensure_ascii=False, allow_nan=False))
    print(output)


if __name__ == "__main__":
    main()
