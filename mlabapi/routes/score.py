"""Score controller — handles POST /score and POST /score/mlab"""

from fastapi import APIRouter

from models.schemas import MLabOnlyRequest, ScoreRequest, ScoreResponse, UseCaseBreakdownResponse
import services.iqb_service as iqb_service

router = APIRouter(tags=["Score"])


@router.post("/score", response_model=ScoreResponse, summary="Calculate IQB score")
def calculate_score(req: ScoreRequest) -> ScoreResponse:
    """
    Calculate an IQB score from measurements across all three datasets
    (m-lab, cloudflare, ookla).

    Only **m-lab** has non-zero weights in the current config, so
    `cloudflare` and `ookla` are optional — they default to zeros when omitted.

    **Example request body:**
    ```json
    {
      "mlab": {
        "download_throughput_mbps": 100,
        "upload_throughput_mbps": 50,
        "latency_ms": 20,
        "packet_loss": 0.001
      }
    }
    ```
    """
    score = iqb_service.calculate_score(req)
    return ScoreResponse(iqb_score=score)


@router.post(
    "/score/mlab",
    response_model=ScoreResponse,
    summary="Calculate IQB score (M-Lab only)",
)
def calculate_score_mlab(req: MLabOnlyRequest) -> ScoreResponse:
    """
    Convenience endpoint — supply only the four M-Lab measurements.
    Cloudflare and Ookla are automatically set to zero.

    **Example request body:**
    ```json
    {
      "download_throughput_mbps": 100,
      "upload_throughput_mbps": 50,
      "latency_ms": 20,
      "packet_loss": 0.001
    }
    ```
    """
    score = iqb_service.calculate_score_mlab_only(req)
    return ScoreResponse(iqb_score=score)


@router.post(
    "/score/use-cases",
    response_model=UseCaseBreakdownResponse,
    summary="Per-use-case IQB score breakdown",
)
def calculate_use_case_scores(req: MLabOnlyRequest) -> UseCaseBreakdownResponse:
    """
    Calculate an individual IQB score for **each use case** separately and
    determine which use cases your connection fully supports.

    Use cases: `web browsing`, `video streaming`, `audio streaming`,
    `video conferencing`, `online backup`, `gaming`

    A use case is **supported** (score = 1.0) when every network requirement
    (download, upload, latency, packet loss) meets its threshold.

    **Example request body:**
    ```json
    {
      "download_throughput_mbps": 50,
      "upload_throughput_mbps": 20,
      "latency_ms": 30,
      "packet_loss": 0.002
    }
    ```

    **Example response:**
    ```json
    {
      "iqb_score": 0.916,
      "use_case_scores": {
        "web browsing": 1.0,
        "video streaming": 1.0,
        "audio streaming": 1.0,
        "video conferencing": 1.0,
        "online backup": 0.75,
        "gaming": 0.692
      },
      "supported": ["web browsing", "video streaming", "audio streaming", "video conferencing"],
      "not_supported": ["online backup", "gaming"],
      "best_use_case": "web browsing"
    }
    ```
    """
    result = iqb_service.calculate_use_case_scores(req)
    return UseCaseBreakdownResponse(**result)
