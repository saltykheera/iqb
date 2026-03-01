"""Models — Pydantic schemas for request and response validation."""

from typing import Dict, List

from pydantic import BaseModel, Field


class DatasetMeasurements(BaseModel):
    """Network measurements for a single dataset (m-lab, cloudflare, or ookla)."""

    download_throughput_mbps: float = Field(
        ..., ge=0, description="Download speed in Mbps"
    )
    upload_throughput_mbps: float = Field(
        ..., ge=0, description="Upload speed in Mbps"
    )
    latency_ms: float = Field(
        ..., ge=0, description="Latency in milliseconds"
    )
    packet_loss: float = Field(
        ..., ge=0, le=1,
        description="Packet loss as a decimal 0–1 (e.g. 0.007 = 0.7%)"
    )


class ScoreRequest(BaseModel):
    """Full score request — one measurement block per dataset."""

    mlab: DatasetMeasurements
    cloudflare: DatasetMeasurements | None = None
    ookla: DatasetMeasurements | None = None


class MLabOnlyRequest(BaseModel):
    """Convenience request — only M-Lab measurements required."""

    download_throughput_mbps: float = Field(
        ..., ge=0, description="Download speed in Mbps"
    )
    upload_throughput_mbps: float = Field(
        ..., ge=0, description="Upload speed in Mbps"
    )
    latency_ms: float = Field(
        ..., ge=0, description="Latency in milliseconds"
    )
    packet_loss: float = Field(
        ..., ge=0, le=1,
        description="Packet loss as a decimal 0–1 (e.g. 0.007 = 0.7%)"
    )


class ScoreResponse(BaseModel):
    """IQB score response."""

    iqb_score: float = Field(
        ..., description="IQB score between 0.0 (worst) and 1.0 (best)"
    )


class UseCaseBreakdownResponse(BaseModel):
    """Per-use-case IQB score breakdown."""

    iqb_score: float = Field(
        ..., description="Overall IQB score (weighted average of all use cases)"
    )
    use_case_scores: Dict[str, float] = Field(
        ..., description="Individual score (0.0–1.0) for each use case"
    )
    supported: List[str] = Field(
        ..., description="Use cases where ALL network requirements are fully met (score = 1.0)"
    )
    not_supported: List[str] = Field(
        ..., description="Use cases where at least one requirement is not met (score < 1.0)"
    )
    best_use_case: str = Field(
        ..., description="The use case with the highest score"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str


# ---------------------------------------------------------------------------
# Benchmark schemas
# ---------------------------------------------------------------------------

class BenchmarkStats(BaseModel):
    """Median stats for one comparison group (ISP or regional)."""

    median_iqb_score: float | None = Field(
        None, description="Median IQB score. None when sample size is too small."
    )
    sample_size: int = Field(..., description="Number of M-Lab tests in this group")
    delta: float | None = Field(
        None, description="User score minus median (positive = above average)"
    )
    verdict: str | None = Field(
        None, description="'above average' | 'below average' | 'at average'"
    )
    insufficient_reason: str | None = Field(
        None, description="Why median is unavailable (null when data is sufficient)"
    )


class BenchmarkCompareRequest(BaseModel):
    """Request: compare a score against city ISP and regional medians."""

    iqb_score: float = Field(..., ge=0, le=1, description="The user's IQB score (0.0–1.0)")
    city: str = Field(..., min_length=1, description="City name (e.g. 'Delhi')")
    asn: int = Field(..., gt=0, description="AS Number of the user's ISP (e.g. 24560 for Airtel Telemedia)")
    window_days: int = Field(
        30, ge=1, le=365,
        description="Informational: the fetch script window used. Does not filter live."
    )


class BenchmarkCompareResponse(BaseModel):
    """Full ISP vs regional comparison result."""

    user_iqb_score: float
    city: str
    asn: int
    isp_name: str | None = Field(None, description="Human-readable AS name from M-Lab data")
    window_days: int
    isp_benchmark: BenchmarkStats = Field(
        ..., description="Median IQB for same ASN in same city"
    )
    regional_benchmark: BenchmarkStats = Field(
        ..., description="Median IQB across all qualifying ASNs in same city"
    )
