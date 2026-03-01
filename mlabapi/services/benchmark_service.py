"""Benchmark service — ISP and regional comparison against M-Lab medians.

Data comes from benchmarks.csv (pre-computed from GitHub parquet files).
Each CSV row is one city+ASN combination with p50 values already computed
by BigQuery APPROX_QUANTILES — these ARE the medians.

ISP comparison:   the single row matching city + ASN (exact, no name fuzzing)
Regional:         median of all ASN-level IQB scores for the same city
Min sample size:  30 — rows below this are excluded as unreliable
"""

from __future__ import annotations

import statistics
from typing import Optional

import services.benchmark_store as store

MIN_SAMPLE_SIZE = 30


def _verdict(delta: Optional[float]) -> Optional[str]:
    if delta is None:
        return None
    return "above average" if delta > 0 else ("below average" if delta < 0 else "at average")


def compare(iqb_score: float, city: str, asn: int, window_days: int = 30) -> dict:
    """
    Compare user's IQB score against ISP median and regional median.

    Lookup is by ASN (integer) — stable and unambiguous.
    Returns a dict matching BenchmarkCompareResponse schema.
    """
    city_norm = city.strip().lower()

    # ------------------------------------------------------------------ ISP --
    isp_rows = store.query(city=city_norm, asn=asn)

    if isp_rows.empty:
        isp_median, isp_n, isp_name, isp_reason = None, 0, None, (
            f"No data found for ASN {asn} in '{city}' — "
            "use GET /benchmark/isps?city=<city> to find valid ASNs"
        )
    else:
        isp_n    = int(isp_rows["sample_count"].sum())
        isp_name = str(isp_rows["as_name"].iloc[0])
        if isp_n < MIN_SAMPLE_SIZE:
            isp_median, isp_reason = None, (
                f"Insufficient data: {isp_n} sample(s) "
                f"(minimum {MIN_SAMPLE_SIZE} required)"
            )
        else:
            isp_median = round(float(isp_rows["iqb_score"].iloc[0]), 6)
            isp_reason = None

    isp_delta = round(iqb_score - isp_median, 6) if isp_median is not None else None

    # -------------------------------------------------------------- Regional --
    regional_rows = store.query(city=city_norm)
    qualified     = regional_rows[regional_rows["sample_count"] >= MIN_SAMPLE_SIZE]

    if qualified.empty:
        regional_n = len(regional_rows)
        regional_median, regional_reason = None, (
            f"No qualifying ASNs in '{city}' "
            f"(need ≥{MIN_SAMPLE_SIZE} samples per ASN)"
            if regional_n > 0 else
            f"No data found for city '{city}'"
        )
    else:
        scores          = qualified["iqb_score"].tolist()
        regional_median = round(statistics.median(scores), 6)
        regional_n      = int(qualified["sample_count"].sum())
        regional_reason = None

    regional_delta = (
        round(iqb_score - regional_median, 6) if regional_median is not None else None
    )

    return {
        "user_iqb_score": iqb_score,
        "city":        city_norm,
        "asn":         asn,
        "isp_name":    isp_name,
        "window_days": window_days,
        "isp_benchmark": {
            "median_iqb_score":    isp_median,
            "sample_size":         isp_n,
            "delta":               isp_delta,
            "verdict":             _verdict(isp_delta),
            "insufficient_reason": isp_reason,
        },
        "regional_benchmark": {
            "median_iqb_score":    regional_median,
            "sample_size":         regional_n,
            "delta":               regional_delta,
            "verdict":             _verdict(regional_delta),
            "insufficient_reason": regional_reason,
        },
    }
