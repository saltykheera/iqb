"""Services (business logic layer).

This module wraps the mlab-iqb library and exposes clean functions
that the controllers call. No FastAPI/HTTP concerns live here.
"""

from iqb import IQB, IQB_CONFIG

from models.schemas import MLabOnlyRequest, ScoreRequest

# Single shared calculator instance
_calculator = IQB()

# Reusable zero-value dataset (for datasets with no data / zero weight)
_ZERO_DATASET: dict[str, float] = {
    "download_throughput_mbps": 0.0,
    "upload_throughput_mbps": 0.0,
    "latency_ms": 0.0,
    "packet_loss": 0.0,
}


def get_config() -> dict:
    """Return the full IQB configuration dict."""
    return IQB_CONFIG


def calculate_score(req: ScoreRequest) -> float:
    """
    Calculate an IQB score from measurements across all three datasets.

    Cloudflare and Ookla default to zero when not provided (they have
    zero weight in the current config anyway).
    """
    data = {
        "m-lab": req.mlab.model_dump(),
        "cloudflare": req.cloudflare.model_dump() if req.cloudflare else _ZERO_DATASET,
        "ookla": req.ookla.model_dump() if req.ookla else _ZERO_DATASET,
    }
    return round(_calculator.calculate_iqb_score(data=data, print_details=False), 6)


def calculate_score_mlab_only(req: MLabOnlyRequest) -> float:
    """
    Calculate an IQB score using only M-Lab measurements.

    Cloudflare and Ookla are automatically set to zero.
    """
    data = {
        "m-lab": req.model_dump(),
        "cloudflare": _ZERO_DATASET,
        "ookla": _ZERO_DATASET,
    }
    return round(_calculator.calculate_iqb_score(data=data, print_details=False), 6)


def calculate_use_case_scores(req: MLabOnlyRequest) -> dict:
    """
    Calculate an individual IQB score for EACH use case separately.

    The library only exposes one aggregated score, so we re-implement
    the per-use-case breakdown here using the same formula from IQBCalculator.

    For each use case:
      1. For each network requirement, compute a binary score (0 or 1):
           - throughput: 1 if measurement > threshold, else 0
           - latency / packet_loss: 1 if measurement < threshold, else 0
      2. Weighted-average the binary scores → use case score (0.0 – 1.0)
      3. Mark the use case as "supported" if score == 1.0 (all requirements met)

    Returns a dict with:
      - use_case_scores:   {use_case: score}   — score per use case
      - supported:         [use_case, ...]      — use cases fully supported (score = 1.0)
      - not_supported:     [use_case, ...]      — use cases not fully supported
      - best_use_case:     str                  — use case with the highest score
      - iqb_score:         float                — overall IQB score (weighted average)
    """
    data = {
        "m-lab": req.model_dump(),
        "cloudflare": _ZERO_DATASET,
        "ookla": _ZERO_DATASET,
    }

    config = _calculator.config
    use_case_scores: dict[str, float] = {}

    for uc_name, uc_config in config["use cases"].items():
        nr_scores = []
        nr_weights = []

        for nr_name, nr_config in uc_config["network requirements"].items():
            nr_w = nr_config["w"]
            nr_th = nr_config["threshold min"]

            # Collect binary scores for each dataset that has non-zero weight
            ds_binary_scores = []
            for ds_name, ds_config in nr_config["datasets"].items():
                if ds_config["w"] > 0 and ds_name in data:
                    brs = _calculator.calculate_binary_requirement_score(
                        nr_name, data[ds_name][nr_name], nr_th
                    )
                    ds_binary_scores.append(brs)

            if ds_binary_scores:
                # Agreement score = average of dataset binary scores
                agreement_score = sum(ds_binary_scores) / len(ds_binary_scores)
                nr_scores.append(agreement_score * nr_w)
                nr_weights.append(nr_w)

        # Use case score = weighted average of requirement scores
        uc_score = sum(nr_scores) / sum(nr_weights) if nr_weights else 0.0
        use_case_scores[uc_name] = round(uc_score, 6)

    # Derive summary fields
    supported = [uc for uc, s in use_case_scores.items() if s == 1.0]
    not_supported = [uc for uc, s in use_case_scores.items() if s < 1.0]
    best_use_case = max(use_case_scores, key=use_case_scores.__getitem__)

    # Overall IQB score = weighted average of use case scores
    uc_weights = [config["use cases"][uc]["w"] for uc in use_case_scores]
    uc_values = [use_case_scores[uc] * config["use cases"][uc]["w"] for uc in use_case_scores]
    iqb_score = round(sum(uc_values) / sum(uc_weights), 6) if uc_weights else 0.0

    return {
        "iqb_score": iqb_score,
        "use_case_scores": use_case_scores,
        "supported": supported,
        "not_supported": not_supported,
        "best_use_case": best_use_case,
    }
