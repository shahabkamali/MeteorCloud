# meteor (device agent)

`meteor` is the MeteorCloud device command. It runs on managed Linux devices,
registers them with the control plane using a registration token, and sends
periodic heartbeats. It uses only the Python standard library so it runs on
minimal devices, and it is intentionally simple to serve as a starting point
for a production agent in any language.

It is structured like a normal Linux tool: a top-level command with
subcommands, `--help` at every level, `--version`, and environment-variable
fallbacks for scripting.

## Install

```bash
cd agent-example
python -m pip install -e ".[dev]"
```

This installs the `meteor` command (the `edge-agent` alias remains available for
the reference internals).

## Usage

```bash
meteor --help              # top-level help and examples
meteor <command> --help    # help for a specific command
meteor --version
```

| Command    | Purpose                                        |
| ---------- | ---------------------------------------------- |
| `register` | Enroll this device with a registration token.  |
| `run`      | Send heartbeats (loop, or `--once`).           |
| `status`   | Show persisted, non-secret configuration.      |

Environment variables: `METEOR_SERVER`, `METEOR_TOKEN`, `METEOR_CONFIG_DIR`
(default config directory: `/etc/meteor`).

## Register a device

Create a token in the dashboard (**Fleet → Devices → Add device**). The
plaintext token is shown **once**. Prefer passing it via a file so it does not
appear in shell history or the process list:

```bash
printf '%s' "reg_..." > /run/meteor.token
sudo meteor register \
  --server https://cloud.example.com \
  --token-file /run/meteor.token \
  --name edge-01
```

Or pass it inline (less secure):

```bash
sudo meteor register --server https://cloud.example.com --token reg_...
```

You can also rely on environment variables:

```bash
export METEOR_SERVER=https://cloud.example.com
export METEOR_TOKEN=reg_...
sudo -E meteor register
```

On success the command:

- collects best-effort inventory (machine ID, serial, MAC addresses, OS, CPU,
  memory), tolerating anything that is unavailable;
- stores the device credential atomically at `/etc/meteor/device-token` with
  `0600` permissions;
- writes non-secret configuration to `/etc/meteor/config.json`;
- removes the registration-token file (only after a successful registration).

## Send heartbeats

```bash
meteor run                 # loop forever using the configured interval
meteor run --once          # send a single heartbeat and exit
meteor run --interval 30   # override the interval (seconds)
```

The loop uses bounded exponential backoff on transient errors and stops if the
credential is rejected (so the device can be re-registered).

## Inspect configuration

```bash
meteor status
```

Shows the server, device ID, organization, name, heartbeat interval, and whether
a credential is present. **Credentials are never printed by any command.**

## Testing

```bash
python -m pytest -q
```

Paths are injectable via `--config-dir`, so tests and local runs never touch the
real `/etc/meteor` location.

## Notes

- The agent talks plain JSON over HTTP(S); nothing is specific to Python on the
  server side.
- Use HTTPS in production. Registration over plain HTTP is allowed for now but
  logged as a warning by the server; the server can be configured to require
  HTTPS.
