"""Deterministic flag evaluation. Spec: 001-flagpole-api FR-009, FR-010 (research R3)."""

import hashlib

from app.schemas import Reason


def bucket(flag_key: str, user_id: str) -> int:
    """0–99 bucket for (flag, user): SHA-256 of "<flag_key>:<user_id>", big-endian int mod 100."""
    digest = hashlib.sha256(f"{flag_key}:{user_id}".encode()).digest()
    return int.from_bytes(digest, "big") % 100


def evaluate(
    enabled: bool, rollout_percent: int, flag_key: str, user_id: str
) -> tuple[bool, Reason]:
    if not enabled:
        return False, Reason.env_disabled
    if bucket(flag_key, user_id) < rollout_percent:
        return True, Reason.rollout_hit
    return False, Reason.rollout_miss
