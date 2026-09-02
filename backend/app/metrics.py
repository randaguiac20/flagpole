"""Domain metrics. Spec: 001-flagpole-api FR-013 (research R4)."""

from prometheus_client import Counter

# registry=None: each app registers this collector in its own registry (main.create_app).
EVALUATIONS = Counter(
    "flagpole_evaluations_total",
    "Flag evaluations by env and reason",
    ["env", "reason"],
    registry=None,
)
