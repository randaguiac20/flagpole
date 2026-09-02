"""FR-016 — data survives restarts; schema is versioned. Spec: 001-flagpole-api."""

from sqlalchemy import func, select

from app.config import Settings
from app.main import create_app
from app.models import AuditEntry, Flag
from tests.conftest import migrate


def test_data_survives_a_new_app_over_the_same_store(tmp_path):
    url = f"sqlite:///{tmp_path / 'persist.db'}"
    migrate(url)
    first = create_app(Settings(database_url=url))
    with first.state.sessionmaker() as s:
        s.add(Flag(key="kept_flag", description="survives"))
        s.flush()
        s.add(AuditEntry(who="t", flag_key="kept_flag", env=None, before=None, after={}))
        s.commit()
    first.state.engine.dispose()

    migrate(url)  # idempotent: already at head
    second = create_app(Settings(database_url=url))
    with second.state.sessionmaker() as s:
        assert s.get(Flag, "kept_flag").description == "survives"
        assert s.scalar(select(func.count()).select_from(AuditEntry)) == 1
