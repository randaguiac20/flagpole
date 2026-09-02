"""Evaluation endpoint. Spec: 001-flagpole-api FR-008..010."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import Caller, get_caller
from app.db import get_session
from app.evaluation import evaluate
from app.metrics import EVALUATIONS
from app.models import FlagEnvironment
from app.schemas import ErrorOut, EvaluateRequest, EvaluateResponse, Reason

router = APIRouter(tags=["evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}},
)
def evaluate_flag(
    body: EvaluateRequest,
    _: Caller = Depends(get_caller),
    session: Session = Depends(get_session),
):
    state = session.get(FlagEnvironment, (body.flag_key, body.env.value))
    if state is None:
        enabled, reason = False, Reason.unknown_flag  # fail safe, never 404 (FR-010)
    else:
        enabled, reason = evaluate(
            state.enabled, state.rollout_percent, body.flag_key, body.user_id
        )
    EVALUATIONS.labels(env=body.env.value, reason=reason.value).inc()
    return EvaluateResponse(enabled=enabled, reason=reason)
