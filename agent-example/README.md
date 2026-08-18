# meterocli (device agent)

`meterocli` is the MeteorCloud device command. It runs on managed Linux devices,
registers them with the control plane, and sends periodic heartbeats. It uses
only the Python standard library so it runs on minimal devices.

There are **two ways** to enroll a device:

1. An administrator creates a registration token; the device runs `meterocli register`.
2. The device is configured with an organization API key and runs
   `meterocli request`; an administrator approves the pending request; the CLI
   polls and then stores the device credential.

## Install

```bash
cd agent-example
python -m pip install -e ".[dev]"
```

This installs the `meterocli` command (`edge-agent` remains as an internal alias).

## Usage

```bash
meterocli --help
meterocli <command> --help
meterocli --version
```

| Command    | Purpose                                                          |
| ---------- | ---------------------------------------------------------------- |
| `config`   | Store the control-plane domain and API key.                      |
| `register` | Enroll with a one-time registration token (admin-initiated).     |
| `request`  | Ask to join; wait for admin approval; save the device credential.|
| `run`      | Send heartbeats (loop, or `--once`).                             |
| `status`   | Show persisted, non-secret configuration.                        |

Environment variables: `METEROCLI_DOMAIN`, `METEROCLI_SERVER`, `METEROCLI_API_KEY`,
`METEROCLI_TOKEN`, `METEROCLI_CONFIG_DIR` (default: `/etc/meterocli`).

Given a domain such as `meteorxx.com`, the CLI calls `https://api.meteorxx.com`
unless `--api-base` / `METEROCLI_SERVER` overrides it.

## Configure the CLI

```bash
sudo meterocli config --domain meteorxx.com --api-key key_...
meterocli config --show
```

The API key is stored at `/etc/meterocli/api-key` with `0600` permissions and is
never printed by `status` or `--show`.

## Path 1 — register with a token

Create a token in the dashboard (**Devices → Add device**). Prefer a token file:

```bash
printf '%s' "reg_..." > /run/meterocli.token
sudo meterocli register --token-file /run/meterocli.token --name edge-01
```

Or pass `--server` / `--token` explicitly if the CLI is not yet configured.

## Path 2 — request enrollment

```bash
sudo meterocli request --name edge-01
```

The command submits inventory, then polls until an administrator approves or
rejects the request. On approval it stores the `dev_` credential (once) and
exits. Use `meterocli run` afterwards.

## Send heartbeats

```bash
meterocli run
meterocli run --once
```

## Testing

```bash
python -m pytest -q
```

Paths are injectable via `--config-dir`, so tests never touch `/etc/meterocli`.
