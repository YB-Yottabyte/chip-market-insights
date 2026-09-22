"""Run collection, cleaning, validation, SQL loading, and CSV exports."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone

import pandas as pd

from .clean_financials import normalize_all
from .config import SEGMENT_COLUMNS, Settings
from .database import DatabaseLoader, engine_for
from .export_powerbi import PowerBIExporter
from .fetch_sec import SecCompanyFactsClient
from .load_industry import IndustryDataLoader
from .segments import load_segments
from .transform import DataQualityValidator


LOG = logging.getLogger(__name__)


class SemiconductorPipeline:
    """Coordinate the ETL steps and write a quality summary for each run."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.industry_loader = IndustryDataLoader()
        self.validator = DataQualityValidator()

    def _load_segments(self) -> pd.DataFrame:
        locations = (
            self.settings.reference_segments,
            self.settings.raw_industry / "onsemi_end_markets.csv",
        )
        frames = [load_segments(path) for path in locations]
        nonempty = [frame for frame in frames if not frame.empty]
        if not nonempty:
            return pd.DataFrame(columns=SEGMENT_COLUMNS)

        segments = pd.concat(nonempty, ignore_index=True)
        keys = ["period_end", "period_type", "end_market"]
        if segments.duplicated(keys).any():
            raise ValueError(
                "Duplicate onsemi end-market rows between reference and user files"
            )
        return segments

    @staticmethod
    def _count_raw_sec_observations(payloads: dict[str, dict]) -> int:
        count = 0
        for payload in payloads.values():
            for taxonomy in payload.get("facts", {}).values():
                for fact in taxonomy.values():
                    for observations in fact.get("units", {}).values():
                        count += len(observations)
        return count

    def _quality_summary(
        self,
        payloads: dict[str, dict],
        financials: pd.DataFrame,
        markets: pd.DataFrame,
        segments: pd.DataFrame,
        checks: dict[str, int],
    ) -> dict:
        return {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "quality_checks": checks,
            "source_counts": {
                "sec_companies": len(payloads),
                "sec_financial_rows": len(financials),
                "raw_sec_fact_observations": self._count_raw_sec_observations(payloads),
                "industry_rows": len(markets),
                "onsemi_end_market_rows": len(segments),
            },
            "status": "failed" if any(checks.values()) else "passed",
        }

    def _write_summary(self, summary: dict) -> None:
        path = self.settings.quality_summary
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        LOG.info("Quality summary written to %s", path)

    def run(self, refresh: bool = False) -> dict:
        """Run ETL and return counts from source files and exported SQL tables."""
        with SecCompanyFactsClient(self.settings) as client:
            payloads = client.fetch_all(refresh=refresh)
        LOG.info("Collected Company Facts for %s companies", len(payloads))

        financials = normalize_all(payloads)
        markets = self.industry_loader.load_directory(self.settings.raw_industry)
        segments = self._load_segments()
        checks = self.validator.validate_all(financials, markets, segments)
        summary = self._quality_summary(payloads, financials, markets, segments, checks)

        if summary["status"] == "failed":
            self._write_summary(summary)
        self.validator.assert_valid(checks)

        engine = engine_for(self.settings.database_url)
        DatabaseLoader(engine, self.settings).load(financials, markets, segments)
        summary["database_rows"] = PowerBIExporter(engine).export(self.settings.exports)
        self._write_summary(summary)
        return summary


def run(refresh: bool = False) -> dict:
    """Compatibility entry point for running the pipeline with environment settings."""
    return SemiconductorPipeline().run(refresh=refresh)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Ignore fresh SEC cache")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(json.dumps(run(refresh=args.refresh), indent=2))


if __name__ == "__main__":
    main()
