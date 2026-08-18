# Device-initiated enrollment

A device can request to join an organization. The request sits in **pending**
until an administrator approves or rejects it. After approval the device polls
and receives its `dev_` credential **once**.

This is the second enrollment path. The first path (a registration token) is
documented in [device-registration.md](device-registration.md).

## Flow

1. An administrator creates an [API key](enrollment-api-keys.md) under **Fleet → API keys**.
2. The device is configured (`meteorcli config --domain … --api-key …`) and runs
   `meteorcli request`.
3. `POST /api/v1/agent/enroll/request` (Bearer `key_…`) creates a pending
   request and returns a one-time `claim_secret` (`clm_…`).
4. The administrator reviews the request on **Fleet → API keys** and approves or rejects it.
5. The device polls `POST /api/v1/agent/enroll/poll` with `request_id` and
   `claim_secret`. On first poll after approval the server issues a `dev_`
   credential, creates/updates the device (same identity matching as token
   registration), and returns the token once.

## Device endpoints

```
GET /api/v1/agent/enroll/check
Authorization: Bearer key_...
```

Returns the organization and key label if the key is valid. Used by
`meteorcli test`. Does not create an enrollment request.

```
POST /api/v1/agent/enroll/request
Authorization: Bearer key_...
```

Request body is inventory (all fields optional). Response:

```json
{
  "request_id": "…",
  "claim_secret": "clm_…",
  "status": "pending",
  "poll_interval_seconds": 10,
  "expires_at": "…"
}
```

```
POST /api/v1/agent/enroll/poll
```

```json
{
  "request_id": "…",
  "claim_secret": "clm_…"
}
```

Statuses: `pending`, `approved`, `rejected`, `expired`. `device_token` is
present only on the first successful claim after approval.

## Admin endpoints

| Method | Path |
|--------|------|
| `GET` | `/api/v1/organizations/{org}/enrollment-requests?status=pending` |
| `POST` | `/api/v1/organizations/{org}/enrollment-requests/{id}/approve` |
| `POST` | `/api/v1/organizations/{org}/enrollment-requests/{id}/reject` |

Approve body (all optional): `{ "name", "device_type_id", "device_group_id" }`.
Reject body (optional): `{ "reason" }`. Mutation requires **owner** or **admin**.

## Rate limiting and security

- Submit: fixed-window limiter keyed by source IP + API key (default 5 / 60s).
- Poll: fixed-window limiter keyed by source IP (default 30 / 60s).
- Claim secrets are hashed (SHA-256); plaintext is never listed.
- A wrong `claim_secret` returns `401 invalid_enrollment_request`.
- Duplicate identity matching matches token registration (same org upsert,
  cross-org `409 device_registered_elsewhere`).
- Pending requests expire after `ENROLLMENT_REQUEST_TTL_SECONDS` (default 3600).
- HTTP is allowed but warned; `REGISTRATION_REQUIRE_HTTPS=true` rejects it.

## Using meteorcli

```bash
meteorcli config --domain meteorxx.com --api-key key_...
meteorcli test
meteorcli request --name edge-01
meteorcli run
```
