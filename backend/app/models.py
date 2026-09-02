"""SQLAlchemy models. Spec: 001-flagpole-api FR-001/002/005/016; design in data-model.md."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ENVS = ("dev", "prod")


def utcnow() -> datetime:
    """Naive UTC timestamp (identical storage on SQLite and PostgreSQL)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Flag(Base):
    __tablename__ = "flags"

    key: Mapped[str] = mapped_column(String(63), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    environments: Mapped[list["FlagEnvironment"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan", order_by="FlagEnvironment.env"
    )


class FlagEnvironment(Base):
    __tablename__ = "flag_environments"
    __table_args__ = (
        CheckConstraint("env IN ('dev','prod')", name="ck_flag_environments_env"),
        CheckConstraint("rollout_percent BETWEEN 0 AND 100", name="ck_flag_environments_rollout"),
    )

    flag_key: Mapped[str] = mapped_column(
        ForeignKey("flags.key", ondelete="CASCADE"), primary_key=True
    )
    env: Mapped[str] = mapped_column(String(8), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    flag: Mapped[Flag] = relationship(back_populates="environments")


class AuditEntry(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_flag_key_id", "flag_key", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    who: Mapped[str] = mapped_column(String(320), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    flag_key: Mapped[str] = mapped_column(
        ForeignKey("flags.key", ondelete="CASCADE"), nullable=False
    )
    env: Mapped[str | None] = mapped_column(String(8), nullable=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict] = mapped_column(JSON, nullable=False)
