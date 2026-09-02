"""Domain metrics. Spec: 001-flagpole-api FR-013 (research R4)."""

from prometheus_client import Counter

EVALUATIONS = Counter(
    "flagpole_evaluations_total", "Flag evaluations by env and reason", ["env", "reason"]
)
