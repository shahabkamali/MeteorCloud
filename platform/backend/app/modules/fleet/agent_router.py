"""Device-facing agent HTTP routes: registration and heartbeat."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.modules.fleet.dependencies import (
    CurrentDevice,
    RegistrationSvc,
    enforce_registration_rate_limit,
)
from app.modules.fleet.schemas import (
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegisterRequest,
    AgentRegisterResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=201,
    dependencies=[Depends(enforce_registration_rate_limit)],
)
def register_device(
    payload: AgentRegisterRequest,
    request: Request,
    service: RegistrationSvc,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentRegisterResponse:
    # HTTP registration remains allowed for now but is flagged as a known
    # limitation. A setting is available to require HTTPS later.
    if request.url.scheme != "https":
        if settings.registration_require_https:
            from app.core.exceptions import ForbiddenError

            raise ForbiddenError(
                "https_required",
                "Device registration requires a secure (HTTPS) connection.",
            )
        logger.warning(
            "Device registration received over insecure transport (%s). "
            "Enable REGISTRATION_REQUIRE_HTTPS in production.",
            request.url.scheme,
        )
    return service.register(payload)


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
def device_heartbeat(
    payload: AgentHeartbeatRequest,
    device: CurrentDevice,
    service: RegistrationSvc,
) -> AgentHeartbeatResponse:
    return service.heartbeat(device=device, payload=payload)
