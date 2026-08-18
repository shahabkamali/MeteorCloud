# Edge Agent (reference)

A small, dependency-free reference agent that registers a Linux device with the
Edge Platform control plane and sends periodic heartbeats. It uses only the
Python standard library so it runs on minimal devices, and it is intentionally
simple to serve as a starting point for a production agent in any language.

## Install

```bash
cd agent-example
python -m pip install -e ".[dev]"
```

This installs the `edge-agent` command.

## Register a device

Create a registration token in the dashboard (Fleet → Registration tokens). The
plaintext token is shown **once**. Prefer passing it via a file so it does not
appear in shell history or the process list:

```bash
printf '%s' "reg_..." > /etc/edge-agent/registration-token
sudo edge-agent register \
  --server https://platform.example.com \
  --token-file /etc/edge-agent/registration-token \
  --name edge-01
```

Or pass it inline (less secure):

```bash
sudo edge-agent register --server https://platform.example.com --token reg_...
```

On success the agent:

- collects best-effort inventory (machine ID, serial, MAC addresses, OS, CPU,
  memory), tolerating anything that is unavailable;
- stores the device credential atomically at `/etc/edge-agent/device-token`
  with `0600` permissions;
- writes non-secret configuration to `/etc/edge-agent/config.json`;
- removes the registration-token file (only after a successful registration).

## Send heartbeats

```bash
edge-agent run           # loop forever using the configured interval
edge-agent run --once    # send a single heartbeat and exit
```

The loop uses bounded exponential backoff on transient errors and stops if the
credential is rejected (so the device can be re-registered).

## Inspect configuration

```bash
edge-agent info
```

Shows the server, device ID, organization, name, heartbeat interval, and whether
a credential is present. **Credentials are never printed by any command.**

## Testing

```bash
python -m pytest -q
```

Paths are injectable via `--config-dir`, so tests and local runs never touch the
real `/etc/edge-agent` location.

## Notes

- The agent talks plain JSON over HTTP(S); nothing is specific to Python on the
  server side.
- Use HTTPS in production. Registration over plain HTTP is allowed for now but
  logged as a warning by the server; the server can be configured to require
  HTTPS.
