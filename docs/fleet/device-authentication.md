# Device authentication

Devices authenticate separately from users. The two credential systems never
overlap.

## Credentials

- On registration a device receives a **device token** with a `dev_` prefix.
- Only the SHA-256 hash and a short non-secret prefix are stored server-side.
- The device sends it as a bearer token: `Authorization: Bearer dev_...`.

## Separation from user auth

The device authentication dependency:

- accepts **only** `dev_`-prefixed credentials, so a user JWT can never be used
  as a device credential (and vice versa);
- rejects unknown or revoked credentials with `401 invalid_device_credentials`;
- rejects disabled devices with `401 device_disabled`.

## Admin controls

From the device detail page (owner/admin only):

- **Enable / disable** — a disabled device cannot heartbeat until re-enabled.
- **Rotate credential** — issues a new `dev_` token (shown once) and immediately
  invalidates the old one.
- **Revoke credential** — clears the credential entirely; the device must
  re-register to obtain a new one.

| Method | Path |
|--------|------|
| `POST` | `/api/v1/organizations/{org}/devices/{id}/enable` |
| `POST` | `/api/v1/organizations/{org}/devices/{id}/disable` |
| `POST` | `/api/v1/organizations/{org}/devices/{id}/rotate-credential` |
| `POST` | `/api/v1/organizations/{org}/devices/{id}/revoke-credential` |

## Secret handling

Plaintext credentials are returned only at creation/rotation time, are never
logged, and are shown once in the UI with clipboard actions before being cleared
from memory.
