"""Idempotent seed: the demo flag new_banner. Spec: 001-flagpole-api FR-015."""

import logging

from sqlalchemy.orm import Session

from app.models import ENVS, Flag, FlagEnvironment

log = logging.getLogger(__name__)
SEED_KEY = "new_banner"


def ensure_seed(session: Session) -> bool:
    """Create new_banner (both envs disabled) if absent; True when created. No audit entry."""
    if session.get(Flag, SEED_KEY) is not None:
        return False
    flag = Flag(key=SEED_KEY, description="Demo banner used by the walkthrough")
    flag.environments = [FlagEnvironment(env=env) for env in ENVS]
    session.add(flag)
    session.flush()
    log.info("seeded flag %s", SEED_KEY)
    return True


def main() -> None:
    from app.config import get_settings
    from app.db import make_engine, make_sessionmaker

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with make_sessionmaker(make_engine(get_settings().database_url))() as session:
        created = ensure_seed(session)
        session.commit()
    log.info("seeded new_banner" if created else "seed already present")


if __name__ == "__main__":
    main()
