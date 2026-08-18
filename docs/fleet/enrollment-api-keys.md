# API keys

An API key lets a device *ask* to join an organization without a
registration token. Keys are organization-scoped and managed under **Fleet →
API keys**.

## Security model

- Keys are generated with `secrets.token_urlsafe` and carry a `key_` prefix.
- Only a deterministic **SHA-256 hash** and a short non-secret **prefix** are
  stored. The plaintext is returned **once** at creation.
- List responses never include the plaintext.
- Revoked or expired keys are rejected with `401 invalid_api_key`.
- Submitting a request is rate-limited per source IP and key (default 5 / 60s).

## Options

When creating a key you may set:

- `name` — required label.
- `device_type_id` / `device_group_id` — optional defaults applied to devices
  enrolled with this key.
- `expires_at` — optional expiry (must be in the future).

## API

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/api/v1/organizations/{org}/enrollment-keys` | never includes plaintext |
| `POST` | `/api/v1/organizations/{org}/enrollment-keys` | response includes one-time `api_key` |
| `POST` | `/api/v1/organizations/{org}/enrollment-keys/{id}/revoke` | immediate |

Create and revoke require **owner** or **admin**. Any member may list keys.

## Using meteorcli

```bash
meteorcli config --domain meteorxx.com --api-key key_...
meteorcli test
meteorcli request --name edge-01
```

See [device-request-enrollment.md](device-request-enrollment.md).
