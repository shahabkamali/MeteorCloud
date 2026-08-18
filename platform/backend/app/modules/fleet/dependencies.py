"""FastAPI dependencies for the fleet and agent APIs."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import AppError, UnauthorizedError
from app.modules.fleet.models import Device
from app.modules.fleet.rate_limit import (
    InMemoryRateLimiter,
    RateLimiter,
    RedisRateLimiter,
)
from app.modules.fleet.registration import RegistrationService
from app.modules.fleet.repository import DeviceRepository
from app.modules.fleet.service import FleetService
from app.modules.fleet.tokens import DEVICE_TOKEN_PREFIX, hash_token

device_bearer_scheme = HTTPBearer(auto_error=False)


class RegistrationRateLimitError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "rate_limited",
            "Too many registration attempts. Please try again later.",
            status_code=429,
        )


def get_fleet_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FleetService:
    return FleetService(session, settings=settings)


def get_registration_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RegistrationService:
    return RegistrationService(session, settings=settings)


@lru_cache
def _build_rate_limiter() -> RateLimiter:
    settings = get_settings()
    try:
        import redis  # type: ignore[import-not-found]

        client = redis.Redis.from_url(settings.redis_url)
        return RedisRateLimiter(
            client,
            limit=settings.registration_rate_limit_requests,
            window_seconds=settings.registration_rate_limit_window_seconds,
        )
    except Exception:
        # Redis client library unavailable; use an in-process limiter instead.
        return InMemoryRateLimiter(
            limit=settings.registration_rate_limit_requests,
            window_seconds=settings.registration_rate_limit_window_seconds,
        )


def get_rate_limiter() -> RateLimiter:
    return _build_rate_limiter()


def enforce_registration_rate_limit(
    request: Request,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    client_host = request.client.host if request.client else "unknown"
    if not limiter.allow(client_host):
        raise RegistrationRateLimitError()


def get_current_device(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(device_bearer_scheme)
    ],
    session: Annotated[Session, Depends(get_db)],
) -> Device:
    """Resolve the authenticated device from its ``dev_`` bearer credential.

    User JWTs are rejected because only ``dev_``-prefixed credentials are
    accepted, and disabled or credential-revoked devices are rejected.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("invalid_device_credentials", "Not authenticated.")

    token = credentials.credentials
    if not token.startswith(DEVICE_TOKEN_PREFIX):
        raise UnauthorizedError(
            "invalid_device_credentials",
            "A device credential is required.",
        )

    devices = DeviceRepository(session)
    device = devices.get_by_credential_hash(hash_token(token))
    if device is None or device.credential_hash is None:
        raise UnauthorizedError(
            "invalid_device_credentials",
            "The device credential is invalid.",
        )
    if not device.is_enabled:
        raise UnauthorizedError(
            "device_disabled",
            "This device has been disabled.",
        )
    return device


FleetSvc = Annotated[FleetService, Depends(get_fleet_service)]
RegistrationSvc = Annotated[RegistrationService, Depends(get_registration_service)]
CurrentDevice = Annotated[Device, Depends(get_current_device)]
