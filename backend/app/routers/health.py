"""Liveness and readiness. Spec: 001-flagpole-api FR-013 (/metrics: instrumentator in main)."""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import ErrorOut, StatusOut

log = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=StatusOut)
def healthz():
    return StatusOut()


@router.get("/readyz", response_model=StatusOut, responses={503: {"model": ErrorOut}})
def readyz(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        log.warning("readiness check failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "database unreachable"},
        )
    return StatusOut()
