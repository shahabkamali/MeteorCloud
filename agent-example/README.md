# meteorcli (device agent)

`meteorcli` is the MeteorCloud device command. It runs on managed Linux devices,
registers them with the control plane, and sends periodic heartbeats. It uses
only the Python standard library so it runs on minimal devices.

There are **two ways** to enroll a device:

1. An administrator creates a registration token; the device runs `meteorcli register`.
2. The device is configured with an organization API key and runs
   `meteorcli request`; an administrator approves the pending request; the CLI
   polls and then stores the device credential.

## Install

On a Linux device, from this directory:

```bash
sudo ./installcli.sh
meteorcli --help
```

That creates a virtualenv in `/opt/meteorcli`, puts `meteorcli` on `PATH` via
`/usr/local/bin`, and creates `/etc/meteorcli`. Re-run the script to upgrade.
Uninstall with `sudo ./installcli.sh --uninstall` (credentials in
`/etc/meteorcli` are kept).

For local development:

```bash
python -m pip install -e ".[dev]"
```

This also installs the `edge-agent` internal alias.

## Usage

```bash
meteorcli --help
meteorcli <command> --help
meteorcli --version
```

| Command    | Purpose                                                          |
| ---------- | ---------------------------------------------------------------- |
| `config`   | Store the control-plane domain and API key.                      |
| `test`     | Check that the server is reachable and the API key is valid.     |
| `register` | Enroll with a one-time registration token (admin-initiated).     |
| `request`  | Ask to join; wait for admin approval; save the device credential.|
| `run`      | Send heartbeats (loop, or `--once`).                             |
| `status`   | Show persisted, non-secret configuration.                        |

Environment variables: `METEORCLI_DOMAIN`, `METEORCLI_SERVER`, `METEORCLI_API_KEY`,
`METEORCLI_TOKEN`, `METEORCLI_CONFIG_DIR` (default: `/etc/meteorcli`).

Given a domain such as `meteorxx.com`, the CLI calls `https://api.meteorxx.com`
unless `--api-base` / `METEORCLI_SERVER` overrides it.

## Configure the CLI

```bash
sudo meteorcli config --domain meteorxx.com --api-key key_...
sudo meteorcli test
meteorcli config --show
```

The API key is stored at `/etc/meteorcli/api-key` with `0600` permissions and is
never printed by `status` or `--show`.

## Path 1 — register with a token

Create a token in the dashboard (**Devices → Add device**). Prefer a token file:

```bash
printf '%s' "reg_..." > /run/meteorcli.token
sudo meteorcli register --token-file /run/meteorcli.token --name edge-01
```

Or pass `--server` / `--token` explicitly if the CLI is not yet configured.

## Path 2 — request enrollment

```bash
sudo meteorcli request --name edge-01
```

The command submits inventory, then polls until an administrator approves or
rejects the request. On approval it stores the `dev_` credential (once) and
exits. Use `meteorcli run` afterwards.

## Send heartbeats

```bash
meteorcli run
meteorcli run --once
```

## Testing

```bash
python -m pytest -q
```

Paths are injectable via `--config-dir`, so tests never touch `/etc/meteorcli`.
