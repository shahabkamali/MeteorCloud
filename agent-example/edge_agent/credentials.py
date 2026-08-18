"""Secure persistence of the per-device credential.

The device token is written atomically with ``0600`` permissions and is never
logged or printed. Paths are injectable for tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_device_token(path: Path, token: str) -> None:
    """Atomically write the device token with owner-only (0600) permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-token-")
    try:
        os.chmod(tmp_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_device_token(path: Path) -> str | None:
    """Return the stored device token, or None when absent."""
    try:
        token = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return token or None


def read_registration_token_file(path: Path) -> str:
    """Read a registration token from a file, stripping whitespace."""
    return path.read_text(encoding="utf-8").strip()


def remove_file(path: Path) -> None:
    """Remove a file if it exists (used to consume a registration-token file)."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass
