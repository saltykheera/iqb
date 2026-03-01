"""Fetch M-Lab benchmark data from the GitHub-hosted parquet cache.

No BigQuery credentials needed — data comes from the public GitHub release
files listed in the manifest at:
  https://raw.githubusercontent.com/m-lab/iqb/main/data/state/ghremote/manifest.json

What this script does
---------------------
1. Reads the manifest to find all available city+ASN parquet files
2. Filters to the latest N months (default: last 3 months)
3. Downloads downloads_by_country_city_asn + uploads_by_country_city_asn
4. Joins on (country_code, city, as_name), aggregates across months using
   a weighted median (weights = sample_count)
5. Computes the IQB score for each city+ISP row using p50 values
6. Writes mlabapi/data/benchmarks.csv

Usage
-----
    # From repo root:
    uv run python mlabapi/scripts/fetch_benchmarks.py

    # With options:
    uv run python mlabapi/scripts/fetch_benchmarks.py --months 6 --out mlabapi/data/benchmarks.csv
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

# Make library importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))           # mlabapi/
sys.path.insert(0, str(Path(__file__).parent.parent.parent      # repo root
                        / "library" / "src"))

from iqb import IQB

MANIFEST_URL = (
    "https://raw.githubusercontent.com/m-lab/iqb/main"
    "/data/state/ghremote/manifest.json"
)
JOIN_KEY = ["country_code", "city", "asn", "as_name"]


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def fetch_manifest() -> dict:
    print("[manifest] Fetching manifest …")
    r = requests.get(MANIFEST_URL, timeout=30)
    r.raise_for_status()
    return r.json()


def latest_months(manifest: dict, n: int) -> list[str]:
    """Return the N most recent period prefixes that actually have city_asn data."""
    prefixes: set[str] = set()
    for key in manifest["files"]:
        # Only keep periods that have the city_asn downloads parquet
        if "downloads_by_country_city_asn/data.parquet" not in key:
            continue
        parts = key.split("/")
        if len(parts) >= 4:
            prefixes.add(f"{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}")
    return sorted(prefixes)[-n:]


def get_parquet(manifest: dict, prefix: str, dataset: str) -> pd.DataFrame:
    key = f"{prefix}/{dataset}/data.parquet"
    if key not in manifest["files"]:
        return pd.DataFrame()
    url = manifest["files"][key]["url"]
    print(f"  [GET] {key.split('/')[2][:8]} {dataset} …", end=" ", flush=True)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    df = pd.read_parquet(io.BytesIO(r.content))
    print(f"{len(df):,} rows")
    return df


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def weighted_p50(df: pd.DataFrame, col: str) -> float:
    """
    Approximate a weighted median: sort by value, find the cumulative-weight
    midpoint.  This gives a sample-count-weighted aggregate across months.
    """
    if df.empty or col not in df.columns:
        return float("nan")
    s = df[[col, "sample_count"]].dropna().sort_values(col)
    cum = s["sample_count"].cumsum()
    midpoint = s["sample_count"].sum() / 2
    idx = (cum >= midpoint).idxmax()
    return float(s.loc[idx, col])


def aggregate_months(frames: list[pd.DataFrame], metric_cols: list[str]) -> pd.DataFrame:
    """
    Concatenate monthly frames and compute weighted p50 per city+ISP group.
    """
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=JOIN_KEY)

    results = []
    for key_vals, grp in combined.groupby(JOIN_KEY, sort=False):
        row = dict(zip(JOIN_KEY, key_vals))
        row["sample_count"] = int(grp["sample_count"].sum())
        for col in metric_cols:
            if col in grp.columns:
                row[col] = weighted_p50(grp, col)
        # Keep the subdivision1_name from the first row
        if "subdivision1_name" in grp.columns:
            row["subdivision1_name"] = grp["subdivision1_name"].iloc[0]
        results.append(row)

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# IQB scoring
# ---------------------------------------------------------------------------

def compute_iqb(df: pd.DataFrame) -> pd.DataFrame:
    calc = IQB()
    scores = []
    for _, row in df.iterrows():
        data = {
            "m-lab": {
                "download_throughput_mbps": row.get("download_p50", 0) or 0,
                "upload_throughput_mbps":   row.get("upload_p50",   0) or 0,
                "latency_ms":               row.get("latency_p50",  0) or 0,
                "packet_loss":              row.get("loss_p50",     0) or 0,
            },
            "cloudflare": {"download_throughput_mbps": 0, "upload_throughput_mbps": 0,
                           "latency_ms": 0, "packet_loss": 0},
            "ookla":      {"download_throughput_mbps": 0, "upload_throughput_mbps": 0,
                           "latency_ms": 0, "packet_loss": 0},
        }
        scores.append(
            round(calc.calculate_iqb_score(data=data, print_details=False), 6)
        )
    df = df.copy()
    df["iqb_score"] = scores
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build benchmarks.csv from GitHub-hosted M-Lab parquet files"
    )
    parser.add_argument("--months", type=int, default=1,
                        help="Number of most-recent months to aggregate (default: 1)")
    parser.add_argument("--limit", type=int, default=2000,
                        help="Keep only the top N rows by sample_count (default: 2000, 0 = all)")
    parser.add_argument("--out", default="mlabapi/data/benchmarks.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    manifest = fetch_manifest()
    periods = latest_months(manifest, args.months)
    print(f"[fetch] Using {len(periods)} period(s): {[p.split('/')[2][:8] for p in periods]}")

    dl_frames, ul_frames = [], []
    for period in periods:
        dl_frames.append(get_parquet(manifest, period, "downloads_by_country_city_asn"))
        ul_frames.append(get_parquet(manifest, period, "uploads_by_country_city_asn"))

    print("[agg] Aggregating downloads …")
    dl_agg = aggregate_months(dl_frames,
                               ["download_p50", "latency_p50", "loss_p50"])
    print(f"      {len(dl_agg):,} city+ISP rows")

    print("[agg] Aggregating uploads …")
    ul_agg = aggregate_months(ul_frames, ["upload_p50"])
    print(f"      {len(ul_agg):,} city+ISP rows")

    print("[join] Merging downloads + uploads …")
    merged = dl_agg.merge(
        ul_agg[JOIN_KEY + ["upload_p50"]],
        on=JOIN_KEY, how="inner"
    )
    print(f"       {len(merged):,} rows after join")

    print("[iqb] Computing IQB scores …")
    merged = compute_iqb(merged)

    # Keep only the most-sampled rows for the test dataset
    if args.limit > 0:
        merged = merged.sort_values("sample_count", ascending=False).head(args.limit)
        print(f"[limit] Keeping top {len(merged):,} rows by sample_count")

    # Final columns — asn is the stable lookup key, as_name is display label
    out_cols = [
        "city", "asn", "as_name", "country_code", "subdivision1_name",
        "download_p50", "upload_p50", "latency_p50", "loss_p50",
        "sample_count", "iqb_score",
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged[out_cols].to_csv(out_path, index=False)
    print(f"[done] Written {len(merged):,} rows → {out_path}")


if __name__ == "__main__":
    main()
