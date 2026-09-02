"""Audit log: newest first, cursor-paged, optional flag filter. Spec: 001-flagpole-api FR-007."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Caller, get_caller
from app.db import get_session
from app.models import AuditEntry
from app.schemas import AuditEntryOut, AuditPage, ErrorOut

router = APIRouter(tags=["audit"])


@router.get(
    "/audit",
    response_model=AuditPage,
    responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}},
)
def read_audit(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: Annotated[int | None, Query(description="return entries with id < before")] = None,
    flag_key: Annotated[str | None, Query()] = None,
    _: Caller = Depends(get_caller),
    session: Session = Depends(get_session),
):
    stmt = select(AuditEntry).order_by(AuditEntry.id.desc()).limit(limit)
    if before is not None:
        stmt = stmt.where(AuditEntry.id < before)
    if flag_key is not None:
        stmt = stmt.where(AuditEntry.flag_key == flag_key)
    items = list(session.scalars(stmt))
    next_before = items[-1].id if len(items) == limit else None
    return AuditPage(
        items=[AuditEntryOut.model_validate(i) for i in items], next_before=next_before
    )
