"""Authentication and user identity business logic."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository
from app.modules.identity.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserPublic,
    UserRegisterRequest,
)


class AuthenticationService:
    """Register users, authenticate credentials, and issue access tokens."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)

    def register_user(self, payload: UserRegisterRequest) -> UserPublic:
        if self.users.get_by_email(payload.email) is not None:
            raise ConflictError(
                "email_already_registered",
                "An account with this email address already exists.",
            )

        user = self.users.create(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        self.session.commit()
        self.session.refresh(user)
        return UserPublic.model_validate(user)

    def authenticate(self, payload: UserLoginRequest) -> User:
        user = self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError(
                "invalid_credentials",
                "Invalid email or password.",
            )
        if not user.is_active:
            raise UnauthorizedError(
                "invalid_credentials",
                "Invalid email or password.",
            )
        return user

    def issue_access_token(self, user: User) -> TokenResponse:
        expires = timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        token = create_access_token(
            str(user.id),
            settings=self.settings,
            expires_delta=expires,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires.total_seconds()),
        )

    def login(self, payload: UserLoginRequest) -> TokenResponse:
        user = self.authenticate(payload)
        return self.issue_access_token(user)

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get_by_id(user_id)

    def require_active_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(
                "invalid_credentials",
                "Could not validate credentials.",
            )
        return user
