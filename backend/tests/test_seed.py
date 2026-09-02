"""FR-015 — idempotent seed. Spec: 001-flagpole-api."""

from sqlalchemy import func, select

from app.models import AuditEntry, Flag
from app.seed import ensure_seed


def test_seed_is_idempotent_and_silent(app):
    with app.state.sessionmaker() as s:
        assert ensure_seed(s) is True
        assert ensure_seed(s) is False
        s.commit()
        assert s.scalar(select(func.count()).select_from(Flag)) == 1
        assert s.scalar(select(func.count()).select_from(AuditEntry)) == 0
        flag = s.get(Flag, "new_banner")
        assert flag is not None
        assert {(e.env, e.enabled, e.rollout_percent) for e in flag.environments} == {
            ("dev", False, 0),
            ("prod", False, 0),
        }
