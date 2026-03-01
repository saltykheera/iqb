"""Benchmark controller — GET /benchmark/isps  +  POST /benchmark/compare"""

from fastapi import APIRouter, Query

from models.schemas import (
    BenchmarkCompareRequest,
    BenchmarkCompareResponse,
    BenchmarkStats,
)
import services.benchmark_service as benchmark_service
import services.benchmark_store as benchmark_store

router = APIRouter(tags=["Benchmark"])


@router.get(
    "/benchmark/isps",
    summary="List ISPs (ASNs) available for a city",
)
def list_isps(city: str = Query(..., description="City name, e.g. 'Delhi'")):
    """
    Return all ISPs for which benchmark data exists in the given city,
    sorted by sample count descending.

    Use the `asn` field when calling `POST /benchmark/compare`.

    **Example:** `GET /benchmark/isps?city=Delhi`
    ```json
    [
      { "asn": 55836, "as_name": "Reliance Jio Infocomm Limited", "sample_count": 1093747, "iqb_score": 0.759140 },
      { "asn": 45609, "as_name": "Bharti Airtel Ltd. AS for GPRS Service", "sample_count": 419081, "iqb_score": 0.759140 },
      ...
    ]
    ```
    """
    rows = benchmark_store.query(city=city)
    if rows.empty:
        return []
    cols = ["asn", "as_name", "sample_count", "iqb_score"]
    available = [c for c in cols if c in rows.columns]
    return (
        rows[available]
        .sort_values("sample_count", ascending=False)
        .fillna("")
        .to_dict(orient="records")
    )


@router.post(
    "/benchmark/compare",
    response_model=BenchmarkCompareResponse,
    summary="Compare your IQB score against your ISP and regional medians",
)
def compare_benchmark(req: BenchmarkCompareRequest) -> BenchmarkCompareResponse:
    """
    Compare a user's IQB score against two baselines from real M-Lab data:

    * **ISP median** — p50 IQB of all M-Lab tests for the same **ASN** in the
      same city (pre-aggregated by `scripts/fetch_benchmarks.py`)
    * **Regional median** — Python median of all qualifying ASN scores in the
      same city (each ASN must have ≥ 30 samples to count)

    **Why ASN instead of ISP name?**
    M-Lab records the AS Number from BGP routing — it's exact and stable.
    ISP names like "Airtel" map to multiple ASNs (mobile vs broadband vs
    enterprise). Use `GET /benchmark/isps?city=<city>` to look up the right
    ASN for your connection.

    **Example request:**
    ```json
    {
      "iqb_score": 0.72,
      "city": "Delhi",
      "asn": 24560
    }
    ```

    **Example response:**
    ```json
    {
      "user_iqb_score": 0.72,
      "city": "delhi",
      "asn": 24560,
      "isp_name": "Bharti Airtel Ltd., Telemedia Services",
      "window_days": 30,
      "isp_benchmark": {
        "median_iqb_score": 0.717042,
        "sample_size": 265483,
        "delta": 0.002958,
        "verdict": "above average",
        "insufficient_reason": null
      },
      "regional_benchmark": {
        "median_iqb_score": 0.717042,
        "sample_size": 2857995,
        "delta": 0.002958,
        "verdict": "above average",
        "insufficient_reason": null
      }
    }
    ```
    """
    result = benchmark_service.compare(
        iqb_score=req.iqb_score,
        city=req.city,
        asn=req.asn,
        window_days=req.window_days,
    )
    return BenchmarkCompareResponse(
        user_iqb_score=result["user_iqb_score"],
        city=result["city"],
        asn=result["asn"],
        isp_name=result["isp_name"],
        window_days=result["window_days"],
        isp_benchmark=BenchmarkStats(**result["isp_benchmark"]),
        regional_benchmark=BenchmarkStats(**result["regional_benchmark"]),
    )


@router.post(
    "/benchmark/compare",
    response_model=BenchmarkCompareResponse,
    summary="Compare your IQB score against your ISP and regional medians",
)
def compare_benchmark(req: BenchmarkCompareRequest) -> BenchmarkCompareResponse:
    """
    Compare a user's IQB score against two baselines derived from real
    M-Lab test data (public GitHub parquet cache):

    * **ISP median** — p50 IQB score of all M-Lab tests run by the same ISP
      in the same city (pre-aggregated by `scripts/fetch_benchmarks.py`)
    * **Regional median** — Python median of all qualifying ISP p50 scores
      in the same city

    **Minimum sample size:** an ISP row needs ≥ 30 tests to be trusted.
    Below that, `median_iqb_score` is `null` and `insufficient_reason`
    explains why.

    **ISP name matching:** uses the `as_name` field from M-Lab data
    (e.g. "Airtel Broadband - AS Provider", "Jio", "BSNL").
    Use `GET /benchmark/isps?city=Delhi` to see exact names available.

    **Example request:**
    ```json
    {
      "iqb_score": 0.72,
      "city": "Delhi",
      "isp": "Airtel"
    }
    ```

    **Example response:**
    ```json
    {
      "user_iqb_score": 0.72,
      "city": "delhi",
      "isp": "airtel",
      "window_days": 30,
      "isp_benchmark": {
        "median_iqb_score": 0.68,
        "sample_size": 1420,
        "delta": 0.04,
        "verdict": "above average",
        "insufficient_reason": null
      },
      "regional_benchmark": {
        "median_iqb_score": 0.70,
        "sample_size": 8910,
        "delta": 0.02,
        "verdict": "above average",
        "insufficient_reason": null
      }
    }
    ```
    """
    result = benchmark_service.compare(
        iqb_score=req.iqb_score,
        city=req.city,
        isp=req.isp,
        window_days=req.window_days,
    )
    return BenchmarkCompareResponse(
        user_iqb_score=result["user_iqb_score"],
        city=result["city"],
        isp=result["isp"],
        window_days=result["window_days"],
        isp_benchmark=BenchmarkStats(**result["isp_benchmark"]),
        regional_benchmark=BenchmarkStats(**result["regional_benchmark"]),
    )
