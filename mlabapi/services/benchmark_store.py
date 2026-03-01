"""Benchmark store — loads pre-computed benchmarks.csv into a DataFrame.

The CSV is produced by scripts/fetch_benchmarks.py which pulls from the
public GitHub-hosted M-Lab parquet files (no credentials needed).

Expected CSV columns
--------------------
    city, asn, as_name, country_code, subdivision1_name,
    download_p50, upload_p50, latency_p50, loss_p50,
    sample_count, iqb_score

Lookup key: (city, asn) — ASN is the stable, unambiguous ISP identifier.
`as_name` is kept for display purposes only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd

_DEFAULT_CSV = Path(__file__).parent.parent / "data" / "benchmarks.csv"
CSV_PATH = Path(os.environ.get("BENCHMARK_CSV_PATH", str(_DEFAULT_CSV)))

_df: Optional[pd.DataFrame] = None


def _load() -> None:
    global _df
    if CSV_PATH.exists():
        try:
            raw = pd.read_csv(CSV_PATH, dtype=str)
            raw["city"] = raw["city"].str.strip().str.lower()
            raw["asn"]  = pd.to_numeric(raw["asn"], errors="coerce").astype("Int64")
            for col in ["download_p50", "upload_p50", "latency_p50", "loss_p50", "iqb_score"]:
                raw[col] = pd.to_numeric(raw[col], errors="coerce")
            raw["sample_count"] = pd.to_numeric(raw["sample_count"],
                                                 errors="coerce").fillna(0).astype(int)
            _df = raw
            print(f"[benchmark_store] Loaded {len(_df):,} rows from {CSV_PATH}")
        except Exception as exc:
            print(f"[benchmark_store] WARNING: could not load {CSV_PATH}: {exc}")
            _df = pd.DataFrame()
    else:
        print(f"[benchmark_store] No benchmarks.csv found at {CSV_PATH} — "
              "run: uv run python mlabapi/scripts/fetch_benchmarks.py")
        _df = pd.DataFrame()


def query(city: Optional[str] = None, asn: Optional[int] = None) -> pd.DataFrame:
    """Return rows matching city and/or ASN. Empty DF if no data."""
    if _df is None or _df.empty:
        return pd.DataFrame()
    mask = pd.Series([True] * len(_df), index=_df.index)
    if city:
        mask &= _df["city"] == city.strip().lower()
    if asn is not None:
        mask &= _df["asn"] == asn
    return _df[mask].copy()


def reload() -> None:
    """Re-read CSV from disk without restarting the server."""
    global _df
    _df = None
    _load()


_load()
