"""Load optional, source-attributed onsemi end-market disclosures."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import SEGMENT_COLUMNS


LOG = logging.getLogger(__name__)
REQUIRED_SEGMENT_FIELDS = (
    "period_end",
    "period_type",
    "end_market",
    "source_document",
    "source_type",
)
SEGMENT_KEYS = ("period_end", "period_type", "end_market")


def load_segments(path: Path) -> pd.DataFrame:
    """Read cited segment rows; keep optional values missing when undisclosed."""
    if not path.exists():
        LOG.info("No onsemi end-market source file at %s", path)
        return pd.DataFrame(columns=SEGMENT_COLUMNS)

    frame = pd.read_csv(path)
    missing_columns = set(SEGMENT_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise ValueError(
            f"onsemi segment file missing columns: {sorted(missing_columns)}"
        )

    frame = frame.loc[:, SEGMENT_COLUMNS].copy()
    if frame.loc[:, REQUIRED_SEGMENT_FIELDS].isna().any().any():
        raise ValueError("Segment keys and source document are required")

    frame["period_end"] = pd.to_datetime(
        frame["period_end"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame["period_type"] = frame["period_type"].astype(str).str.strip().str.lower()
    for column in ("end_market", "source_document", "source_type"):
        frame[column] = frame[column].astype(str).str.strip()
    for column in ("revenue", "revenue_percentage"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame.duplicated(list(SEGMENT_KEYS)).any():
        raise ValueError("Duplicate onsemi end-market period")
    if frame.loc[:, REQUIRED_SEGMENT_FIELDS].eq("").any().any():
        raise ValueError("Segment keys and source document are required")
    if not frame["period_type"].isin(("annual", "quarterly")).all():
        raise ValueError("Segment period_type must be annual or quarterly")
    if frame["revenue"].lt(0).any():
        raise ValueError("Segment revenue or percentage outside valid range")
    valid_percentages = frame["revenue_percentage"].dropna().between(0, 100)
    if not valid_percentages.all():
        raise ValueError("Segment revenue or percentage outside valid range")

    LOG.info("Loaded %s cited onsemi end-market records", len(frame))
    return frame
