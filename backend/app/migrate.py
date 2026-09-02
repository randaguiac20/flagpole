"""Bring the schema up to date, exactly once. Spec: 005-platform-delivery FR-012 (research E6).

Runs as an init container on flagpole-api, so the container that serves never starts against an old
schema. Several replicas start together, so the upgrade is wrapped in a PostgreSQL advisory lock:
Alembic has none of its own, and two concurrent `upgrade head` runs against one database is how a
migration ends up half-applied.

The lock is the *blocking* form on purpose. `pg_try_advisory_lock` would let the second replica skip
the migration and start serving against a schema that is still being changed.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# One fixed key for the whole schema. It must be identical in every replica, so it cannot be derived
# from the host, the pod or the clock. The value is arbitrary; only its stability matters.
LOCK_KEY = 8_311_051_970_004_005

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@contextmanager
def _advisory_lock(connection: Any, dialect: str) -> Iterator[None]:
    """Hold the migration lock for the duration of the body, on databases that have one.

    SQLite is one file used by one process in development; there is no lock to take and pretending
    otherwise would be a lie the tests would have to encode.
    """
    supported = dialect == "postgresql"
    if supported:
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK_KEY})
    try:
        yield
    finally:
        # Released explicitly as well as by the connection closing: an ordinary failure must not
        # leave the next replica waiting on a connection that is still alive.
        if supported:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})


def _upgrade() -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    command.upgrade(config, "head")


def run(database_url: str | None = None) -> None:
    url = database_url or os.environ.get("FLAGPOLE_DATABASE_URL", "sqlite:///./flagpole.db")
    engine = create_engine(url)
    logger.info("bringing the schema up to date (%s)", engine.dialect.name)
    with engine.connect() as connection, _advisory_lock(connection, engine.dialect.name):
        _upgrade()
    engine.dispose()
    logger.info("schema is up to date")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
