"""``meteor`` command-line interface.

Structured like a standard Linux tool: a top-level command with subcommands,
``--help`` at every level, ``--version``, and environment-variable fallbacks so
it works well in scripts and provisioning tools.

Subcommands
-----------
  register   Register this device with a registration token.
  run        Send periodic heartbeats to the control plane.
  status     Show the persisted (non-secret) configuration.

The device credential is stored with owner-only permissions and is never
printed by any command.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from edge_agent.client import AgentApiError, EdgeClient
from edge_agent.config import AgentConfig, AgentPaths, load_config
from edge_agent.credentials import read_device_token, read_registration_token_file
from edge_agent.heartbeat import run_loop, send_heartbeat
from edge_agent.registration import register
from meteor import __version__

logger = logging.getLogger("meteor")

PROG = "meteor"

# Default on-device locations. Overridable with --config-dir or METEOR_CONFIG_DIR
# so the command can be tested and run without root.
DEFAULT_CONFIG_DIR = Path("/etc/meteor")

ENV_SERVER = "METEOR_SERVER"
ENV_TOKEN = "METEOR_TOKEN"
ENV_CONFIG_DIR = "METEOR_CONFIG_DIR"


def _paths_from_args(args: argparse.Namespace) -> AgentPaths:
    config_dir = args.config_dir or os.environ.get(ENV_CONFIG_DIR)
    base = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    return AgentPaths(config_path=base / "config.json", token_path=base / "device-token")


def _resolve_server(args: argparse.Namespace) -> str | None:
    return args.server or os.environ.get(ENV_SERVER)


def _resolve_token(args: argparse.Namespace) -> tuple[str | None, Path | None]:
    """Resolve the registration token and its source file (if any).

    Precedence: --token, then --token-file, then the METEOR_TOKEN env var.
    """
    if args.token:
        return args.token, None
    if args.token_file:
        token_file = Path(args.token_file)
        return read_registration_token_file(token_file), token_file
    env_token = os.environ.get(ENV_TOKEN)
    if env_token:
        return env_token, None
    return None, None


def _cmd_register(args: argparse.Namespace) -> int:
    server = _resolve_server(args)
    if not server:
        print(
            f"error: a server URL is required (use --server or {ENV_SERVER}).",
            file=sys.stderr,
        )
        return 2

    try:
        token, token_file = _resolve_token(args)
    except FileNotFoundError:
        print(f"error: token file not found: {args.token_file}", file=sys.stderr)
        return 2
    if not token:
        print(
            f"error: a registration token is required "
            f"(use --token, --token-file, or {ENV_TOKEN}).",
            file=sys.stderr,
        )
        return 2

    paths = _paths_from_args(args)
    client = EdgeClient(server)
    try:
        result = register(
            client=client,
            paths=paths,
            token=token,
            name=args.name,
            token_file=token_file,
        )
    except AgentApiError as error:
        logger.error("Registration failed: %s", error.code)
        print(f"error: registration failed: {error.message}", file=sys.stderr)
        return 1

    print(f"Registered device {result.device_id}")
    print(f"Organization:   {result.organization_id}")
    print(f"Name:           {result.name}")
    print(f"Heartbeat:      every {result.heartbeat_interval_seconds}s")
    print(f"Credential:     stored at {paths.token_path}")
    print()
    print(f"Next: start sending heartbeats with '{PROG} run'.")
    return 0


def _load_or_fail(paths: AgentPaths) -> tuple[AgentConfig, str] | None:
    config = load_config(paths)
    if config is None:
        print(
            f"error: this device is not registered. Run '{PROG} register' first.",
            file=sys.stderr,
        )
        return None
    device_token = read_device_token(paths.token_path)
    if device_token is None:
        print(
            f"error: device credential is missing. Re-register with '{PROG} register'.",
            file=sys.stderr,
        )
        return None
    return config, device_token


def _cmd_run(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    loaded = _load_or_fail(paths)
    if loaded is None:
        return 1
    config, device_token = loaded
    client = EdgeClient(config.server_url)

    if args.once:
        try:
            response = send_heartbeat(client, device_token)
        except AgentApiError as error:
            print(f"error: heartbeat failed: {error.message}", file=sys.stderr)
            return 1
        print(f"Heartbeat ok; status: {response.get('status', 'unknown')}")
        return 0

    interval = args.interval or config.heartbeat_interval_seconds
    logger.info("Starting heartbeat loop every %ss", interval)
    try:
        run_loop(
            client,
            device_token,
            interval_seconds=interval,
            sleep=time.sleep,
            should_continue=lambda: True,
        )
    except AgentApiError:
        return 1
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        logger.info("Stopping heartbeat loop.")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    config = load_config(paths)
    if config is None:
        print(f"Not registered. Run '{PROG} register' to enroll this device.")
        return 1
    has_credential = read_device_token(paths.token_path) is not None
    print(f"Server:         {config.server_url}")
    print(f"Device ID:      {config.device_id}")
    print(f"Organization:   {config.organization_id}")
    print(f"Name:           {config.name}")
    print(f"Heartbeat:      every {config.heartbeat_interval_seconds}s")
    print(f"Credential:     {'present' if has_credential else 'MISSING'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="MeteorCloud device agent.",
        epilog=(
            "Examples:\n"
            f"  {PROG} register --server https://cloud.example.com --token reg_XXXX\n"
            f"  {PROG} register --server https://cloud.example.com --token-file /run/meteor.token\n"
            f"  {PROG} run\n"
            f"  {PROG} status\n"
            "\n"
            "Environment variables:\n"
            f"  {ENV_SERVER}       Default control-plane URL.\n"
            f"  {ENV_TOKEN}        Registration token (used if --token is omitted).\n"
            f"  {ENV_CONFIG_DIR}   Config/credential directory (default: /etc/meteor).\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        metavar="DIR",
        help="Directory for device config and credential (default: /etc/meteor).",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    register_parser = subparsers.add_parser(
        "register",
        help="Register this device using a registration token.",
        description="Register this device with the control plane using a registration token.",
    )
    register_parser.add_argument(
        "--server",
        default=None,
        metavar="URL",
        help=f"Control-plane base URL (or set {ENV_SERVER}).",
    )
    register_parser.add_argument(
        "--token",
        default=None,
        metavar="TOKEN",
        help=f"Registration token value (or set {ENV_TOKEN}).",
    )
    register_parser.add_argument(
        "--token-file",
        default=None,
        metavar="PATH",
        help="Read the registration token from a file (recommended; keeps it out of history).",
    )
    register_parser.add_argument(
        "--name",
        default=None,
        metavar="NAME",
        help="Optional device name (defaults to the hostname on the server).",
    )
    register_parser.set_defaults(func=_cmd_register)

    run_parser = subparsers.add_parser(
        "run",
        help="Send heartbeats to the control plane.",
        description="Send periodic heartbeats so the device reports as online.",
    )
    run_parser.add_argument(
        "--once",
        action="store_true",
        help="Send a single heartbeat and exit.",
    )
    run_parser.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Override the heartbeat interval (default: value chosen at registration).",
    )
    run_parser.set_defaults(func=_cmd_run)

    status_parser = subparsers.add_parser(
        "status",
        help="Show the persisted (non-secret) configuration.",
        description="Show the persisted device configuration. Never prints the credential.",
    )
    status_parser.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
