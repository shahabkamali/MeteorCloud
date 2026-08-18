# Heartbeat and connectivity status

Devices report liveness by sending periodic heartbeats. Connectivity status is
derived from the last heartbeat time.

## Endpoint

```
POST /api/v1/agent/heartbeat
Authorization: Bearer dev_...
```

Optional body:

```json
{
  "hostname": "edge-01",
  "os_version": "22.04",
  "kernel_version": "6.2.0",
  "metrics": {}
}
```

Response:

```json
{
  "device_id": "…",
  "status": "online",
  "heartbeat_interval_seconds": 60,
  "server_time": "2026-08-18T10:00:00Z"
}
```

Each heartbeat updates the device's `last_seen_at` and may refresh a few
inventory fields. Disabled or credential-revoked devices are rejected.

## Connectivity status

Status is computed consistently everywhere (list, detail, filters) from
`last_seen_at`:

| Status | Meaning |
|--------|---------|
| `online` | last seen within the offline threshold |
| `offline` | last seen, but longer ago than the threshold |
| `never_seen` | has never sent a heartbeat |

Two settings control the timing (defaults shown):

- `DEVICE_HEARTBEAT_INTERVAL_SECONDS=60` — interval advertised to agents.
- `DEVICE_OFFLINE_THRESHOLD_SECONDS=150` — window before a device is offline.

The threshold is intentionally larger than the interval so a single missed
heartbeat does not immediately flip a device offline.

## Reference agent

```bash
edge-agent run          # loop using the advertised interval
edge-agent run --once   # single heartbeat
```

The loop uses bounded exponential backoff on transient failures and stops if the
credential is rejected so the device can be re-registered.
