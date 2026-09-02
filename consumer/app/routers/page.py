"""The page. Spec: 003-flagpole-consumer FR-001, FR-004, FR-005."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.client import FlagServiceClient, get_client

router = APIRouter(tags=["page"])


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    user: str | None = None,
    client: FlagServiceClient = Depends(get_client),
) -> HTMLResponse:
    settings = request.app.state.settings
    # Blank or whitespace-only is the same as absent (spec, edge cases).
    chosen_user = (user or "").strip() or settings.default_user
    decision = await client.evaluate(chosen_user)
    return request.app.state.templates.TemplateResponse(
        request=request, name="page.html", context={"decision": decision}
    )
