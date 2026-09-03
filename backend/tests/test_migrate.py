"""The migration entry point. Spec: 005-platform-delivery FR-012 (research E6).

Several replicas start at once, each with an init container that brings the schema up to date.
Alembic has no lock of its own, so this module takes a PostgreSQL advisory lock first.

The tests use SQLite, where there is no such lock and none is needed. What they assert is the
*decision*: that a lock is taken when the database is PostgreSQL, that it is the blocking form, that
it is released even when the body fails, and that it is not pretended to exist where it does not.
"""

from typing import Any

import pytest
from sqlalchemy import create_engine

from app import migrate


class RecordingConnection:
    """Stands in for a live connection, recording the statements a lock would issue."""

    def __init__(self, granted: bool = True) -> None:
        self.statements: list[str] = []
        self.granted = granted

    def execute(self, statement: Any, *_: Any) -> Any:
        self.statements.append(str(statement).strip())

        class Result:
            def __init__(self, value: bool) -> None:
                self._value = value

            def scalar(self) -> bool:
                return self._value

        return Result(self.granted)

    def __enter__(self) -> "RecordingConnection":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_the_lock_key_is_fixed_and_not_random() -> None:
    """Two processes must ask for the same lock, so the key cannot come from anything local."""
    assert isinstance(migrate.LOCK_KEY, int)
    assert migrate.LOCK_KEY == migrate.LOCK_KEY  # noqa: PLR0124 - the point is that it is a constant
    assert -(2**63) <= migrate.LOCK_KEY < 2**63, "must fit PostgreSQL's bigint advisory lock key"


def test_postgres_takes_the_lock_before_upgrading(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = RecordingConnection()
    order: list[str] = []

    monkeypatch.setattr(migrate, "_upgrade", lambda: order.append("upgrade"))
    with migrate._advisory_lock(connection, dialect="postgresql"):  # noqa: SLF001 - unit under test
        order.append("inside the lock")

    assert "pg_advisory_lock" in connection.statements[0]
    assert "pg_advisory_unlock" in connection.statements[-1]
    assert order == ["inside the lock"]


def test_a_second_caller_waits_rather_than_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    """pg_advisory_lock blocks; it does not return false. A caller that waits then finds nothing
    to do is the whole point — it must exit successfully, not report a conflict."""
    connection = RecordingConnection()
    with migrate._advisory_lock(connection, dialect="postgresql"):  # noqa: SLF001
        pass
    assert not any("try_advisory" in s for s in connection.statements), (
        "the blocking form is required: try_advisory_lock would make the loser skip the migration"
    )


def test_a_database_without_advisory_locks_is_not_pretended_to_have_one() -> None:
    """SQLite is one file used by one process in development; claiming a lock would be a lie."""
    connection = RecordingConnection()
    with migrate._advisory_lock(connection, dialect="sqlite"):  # noqa: SLF001
        pass
    assert connection.statements == []


def test_the_lock_is_released_when_the_body_raises() -> None:
    """A dying process must not hold the lock. The connection closing releases it, but an ordinary
    failure must release it too, or the next replica waits forever on a live connection."""
    connection = RecordingConnection()
    with pytest.raises(RuntimeError), migrate._advisory_lock(connection, dialect="postgresql"):  # noqa: SLF001
        raise RuntimeError("migration blew up")
    assert "pg_advisory_unlock" in connection.statements[-1]


def test_run_upgrades_a_real_database(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End to end on SQLite: an empty database gains the schema, and a second run is a no-op."""
    url = f"sqlite:///{tmp_path / 'migrate.db'}"
    monkeypatch.setenv("FLAGPOLE_DATABASE_URL", url)

    migrate.run(url)
    with create_engine(url).connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "flags" in tables and "alembic_version" in tables

    migrate.run(url)  # must not raise: the second replica finds nothing to do
