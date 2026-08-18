"""Fleet domain models: device types, groups, registration tokens, devices.

All fleet resources are strictly organization-scoped. PostgreSQL JSONB is used
only for free-form structures (capabilities, labels, MAC address arrays, and
custom metadata); every other attribute is an explicit column.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A named class of Linux device within an organization."""

    __tablename__ = "device_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_device_types_org_name"),
        Index("ix_device_types_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form list/dict of declared capabilities.
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


class DeviceGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A logical grouping of devices within an organization."""

    __tablename__ = "device_groups"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_device_groups_org_name"),
        Index("ix_device_groups_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


class RegistrationToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A secret used by a device to self-register into an organization.

    Only the SHA-256 lookup hash is stored. The plaintext value is returned once
    at creation time and never persisted or logged.
    """

    __tablename__ = "registration_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_registration_tokens_token_hash"),
        Index("ix_registration_tokens_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Deterministic SHA-256 hash of the plaintext token, used for lookup.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Short non-secret prefix (e.g. "reg_ab12cd") for display/identification.
    token_prefix: Mapped[str] = mapped_column(String(32), nullable=False)

    device_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    device_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_groups.id", ondelete="RESTRICT"),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )


class Device(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A registered Linux device belonging to an organization."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint(
            "credential_hash",
            name="uq_devices_credential_hash",
        ),
        Index("ix_devices_organization_id", "organization_id"),
        Index("ix_devices_org_machine_id", "organization_id", "machine_id"),
        Index("ix_devices_org_serial_number", "organization_id", "serial_number"),
        Index("ix_devices_org_last_seen_at", "organization_id", "last_seen_at"),
        Index("ix_devices_org_device_type_id", "organization_id", "device_type_id"),
        Index("ix_devices_org_device_group_id", "organization_id", "device_group_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    device_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    device_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_groups.id", ondelete="RESTRICT"),
        nullable=True,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Hardware / OS identity used for duplicate detection.
    machine_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mac_addresses: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    # Inventory (all optional; agents tolerate missing values).
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kernel_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    architecture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cpu_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    labels: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    # Free-form custom metadata. The DB column is named ``metadata`` but the
    # Python attribute is ``metadata_`` to avoid clashing with SQLAlchemy's
    # reserved ``Base.metadata``.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Per-device credential (only the SHA-256 hash is stored).
    credential_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    credential_prefix: Mapped[str | None] = mapped_column(String(32), nullable=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    registered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    registration_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("registration_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
