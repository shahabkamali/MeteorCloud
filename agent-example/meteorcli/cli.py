"""``meteorcli`` command-line interface.

Subcommands
-----------
  config     Store the control-plane domain and API key.
  test       Check that the server is reachable and the API key is valid.
  register   Register this device with a registration token (path 1).
  request    Ask to join; wait for admin approval; save the device credential.
  run        Send periodic heartbeats.
  status     Show persisted (non-secret) configuration.

Secrets are never printed by any command except when the user explicitly
passes them on the command line.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from edge_agent.client import AgentApiError, EdgeClient
from edge_agent.config import AgentConfig, load_config, save_config
from edge_agent.credentials import read_device_token, read_registration_token_file
from edge_agent.heartbeat import run_loop, send_heartbeat
from edge_agent.inventory import collect_inventory
from edge_agent.registration import register
from meteorcli import __version__
from meteorcli.config import (
    CliPaths,
    default_config_dir,
    derive_api_base,
    persist_connection,
    resolve_server_url,
)
from meteorcli.credentials import read_secret, remove_secret, write_secret

logger = logging.getLogger("meteorcli")

PROG = "meteorcli"

ENV_SERVER = "METEORCLI_SERVER"
ENV_DOMAIN = "METEORCLI_DOMAIN"
ENV_TOKEN = "METEORCLI_TOKEN"
ENV_API_KEY = "METEORCLI_API_KEY"
ENV_CONFIG_DIR = "METEORCLI_CONFIG_DIR"


def _paths_from_args(args: argparse.Namespace) -> CliPaths:
    config_dir = args.config_dir or os.environ.get(ENV_CONFIG_DIR)
    if config_dir:
        return CliPaths.from_dir(Path(config_dir).expanduser())
    return CliPaths.from_dir(default_config_dir())


def _load(paths: CliPaths) -> AgentConfig | None:
    return load_config(paths.agent_paths())


def _resolve_server(args: argparse.Namespace, config: AgentConfig | None) -> str | None:
    override = getattr(args, "server", None) or os.environ.get(ENV_SERVER)
    return resolve_server_url(config, override=override)


def _resolve_token(args: argparse.Namespace) -> tuple[str | None, Path | None]:
    if args.token:
        return args.token, None
    if args.token_file:
        token_file = Path(args.token_file)
        return read_registration_token_file(token_file), token_file
    env_token = os.environ.get(ENV_TOKEN)
    if env_token:
        return env_token, None
    return None, None


def _resolve_api_key(args: argparse.Namespace, paths: CliPaths) -> str | None:
    flag = getattr(args, "api_key", None)
    if flag:
        return flag
    env_key = os.environ.get(ENV_API_KEY)
    if env_key:
        return env_key
    return read_secret(paths.api_key_path)


def _cmd_config(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    domain = args.domain or os.environ.get(ENV_DOMAIN)
    api_base = args.api_base
    api_key = args.api_key or os.environ.get(ENV_API_KEY)

    if args.show:
        config = _load(paths)
        server = resolve_server_url(config)
        has_key = read_secret(paths.api_key_path) is not None
        has_device = read_device_token(paths.token_path) is not None
        print(f"Domain:         {config.domain if config else '—'}")
        print(f"API base:       {server or '—'}")
        print(f"API key:        {'present' if has_key else 'MISSING'}")
        print(f"Device ID:      {config.device_id if config and config.device_id else '—'}")
        print(f"Credential:     {'present' if has_device else 'MISSING'}")
        return 0 if config is not None or has_key else 1

    if not domain and not api_base and not api_key:
        print(
            f"error: provide --domain, --api-base, and/or --api-key "
            f"(or {ENV_DOMAIN}/{ENV_API_KEY}).",
            file=sys.stderr,
        )
        return 2

    persist_connection(paths, domain=domain, api_base=api_base, http=args.http)
    if api_key:
        write_secret(paths.api_key_path, api_key)
    print(f"Configuration saved under {paths.config_path.parent}")
    print(f"Next: verify with '{PROG} test'.")
    return 0


def _cmd_register(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    config = _load(paths)
    server = _resolve_server(args, config)
    if not server:
        print(
            f"error: a server URL is required "
            f"(use --server, {ENV_SERVER}, or '{PROG} config --domain').",
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
            f"error: a registration token is required (use --token, --token-file, or {ENV_TOKEN}).",
            file=sys.stderr,
        )
        return 2

    client = EdgeClient(server)
    try:
        result = register(
            client=client,
            paths=paths.agent_paths(),
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


def _persist_claimed_device(
    paths: CliPaths,
    client: EdgeClient,
    poll: dict,
) -> None:
    from edge_agent.credentials import write_device_token

    write_device_token(paths.token_path, poll["device_token"])
    existing = _load(paths) or AgentConfig(server_url=client.server_url)
    existing.server_url = client.server_url
    existing.device_id = str(poll["device_id"])
    existing.organization_id = str(poll["organization_id"])
    existing.name = str(poll.get("name") or existing.name)
    existing.heartbeat_interval_seconds = int(poll.get("heartbeat_interval_seconds") or 60)
    save_config(paths.agent_paths(), existing)
    remove_secret(paths.claim_secret_path)


def _cmd_request(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    config = _load(paths)
    server = _resolve_server(args, config)
    if not server:
        print(
            f"error: a server URL is required "
            f"(use --server, {ENV_SERVER}, or '{PROG} config --domain').",
            file=sys.stderr,
        )
        return 2

    api_key = _resolve_api_key(args, paths)
    if not api_key:
        print(
            f"error: an API key is required "
            f"(use --api-key, {ENV_API_KEY}, or '{PROG} config --api-key').",
            file=sys.stderr,
        )
        return 2

    client = EdgeClient(server)
    inventory = collect_inventory()
    try:
        submitted = client.enroll_request(api_key=api_key, inventory=inventory, name=args.name)
    except AgentApiError as error:
        print(f"error: enrollment request failed: {error.message}", file=sys.stderr)
        return 1

    request_id = str(submitted["request_id"])
    claim_secret = str(submitted["claim_secret"])
    write_secret(
        paths.claim_secret_path,
        json.dumps({"request_id": request_id, "claim_secret": claim_secret}),
    )
    interval = int(submitted.get("poll_interval_seconds") or 10)
    print(f"Enrollment request {request_id} submitted.")
    print("Waiting for an administrator to approve this device…")

    sleep = args._sleep if hasattr(args, "_sleep") else time.sleep
    max_polls = args._max_polls if hasattr(args, "_max_polls") else None
    polls = 0
    while True:
        try:
            polled = client.enroll_poll(request_id=request_id, claim_secret=claim_secret)
        except AgentApiError as error:
            print(f"error: poll failed: {error.message}", file=sys.stderr)
            return 1

        status = polled.get("status")
        if status == "pending":
            polls += 1
            if max_polls is not None and polls >= max_polls:
                print("Still pending approval.")
                return 0
            sleep(int(polled.get("poll_interval_seconds") or interval))
            continue
        if status == "rejected":
            reason = polled.get("rejection_reason") or "no reason given"
            print(f"Enrollment rejected: {reason}", file=sys.stderr)
            remove_secret(paths.claim_secret_path)
            return 1
        if status == "expired":
            print("Enrollment request expired. Submit a new request.", file=sys.stderr)
            remove_secret(paths.claim_secret_path)
            return 1
        if status == "approved" and polled.get("device_token"):
            _persist_claimed_device(paths, client, polled)
            print(f"Registered device {polled['device_id']}")
            print(f"Name:           {polled.get('name')}")
            print(f"Credential:     stored at {paths.token_path}")
            print()
            print(f"Next: start sending heartbeats with '{PROG} run'.")
            return 0
        if status == "approved":
            print("Approved, but the device credential was already claimed.", file=sys.stderr)
            return 1
        print(f"error: unexpected enrollment status: {status}", file=sys.stderr)
        return 1


def _cmd_test(args: argparse.Namespace) -> int:
    paths = _paths_from_args(args)
    config = _load(paths)
    server = _resolve_server(args, config)
    if not server:
        print(
            f"error: a server URL is required "
            f"(use --server, {ENV_SERVER}, or '{PROG} config --domain').",
            file=sys.stderr,
        )
        return 2

    if args.http:
        server = derive_api_base(server, http=True)

    client = EdgeClient(server)
    try:
        health = client.health()
    except AgentApiError as error:
        print(f"error: cannot reach {server}: {error.message}", file=sys.stderr)
        return 1

    print(f"API base:       {server}")
    print(f"Server:         {health.get('status', 'ok')}")

    api_key = _resolve_api_key(args, paths)
    if not api_key:
        print("API key:        MISSING")
        print(
            f"error: an API key is required "
            f"(use --api-key, {ENV_API_KEY}, or '{PROG} config --api-key').",
            file=sys.stderr,
        )
        return 1

    try:
        checked = client.check_api_key(api_key=api_key)
    except AgentApiError as error:
        print(f"API key:        rejected ({error.message})", file=sys.stderr)
        return 1

    print("API key:        ok")
    print(f"Organization:   {checked.get('organization_name') or checked.get('organization_id')}")
    print(f"Key name:       {checked.get('key_name') or '—'}")
    prefix = checked.get("key_prefix")
    if prefix:
        print(f"Key prefix:     {prefix}…")
    return 0


def _load_or_fail(paths: CliPaths) -> tuple[AgentConfig, str] | None:
    config = _load(paths)
    if config is None or not config.device_id:
        print(
            f"error: this device is not registered. "
            f"Run '{PROG} register' or '{PROG} request' first.",
            file=sys.stderr,
        )
        return None
    device_token = read_device_token(paths.token_path)
    if device_token is None:
        print(
            f"error: device credential is missing. "
            f"Re-register with '{PROG} register' or '{PROG} request'.",
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
    config = _load(paths)
    has_credential = read_device_token(paths.token_path) is not None
    has_key = read_secret(paths.api_key_path) is not None
    if config is None and not has_key:
        print(f"Not configured. Run '{PROG} config --domain … --api-key …' first.")
        return 1
    server = resolve_server_url(config)
    print(f"Domain:         {config.domain if config else '—'}")
    print(f"API base:       {server or '—'}")
    print(f"API key:        {'present' if has_key else 'MISSING'}")
    print(f"Device ID:      {config.device_id if config and config.device_id else '—'}")
    print(f"Organization:   {config.organization_id if config and config.organization_id else '—'}")
    print(f"Name:           {config.name if config and config.name else '—'}")
    print(f"Heartbeat:      every {config.heartbeat_interval_seconds if config else 60}s")
    print(f"Credential:     {'present' if has_credential else 'MISSING'}")
    return 0 if config and config.device_id else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="MeteorCloud device agent.",
        epilog=(
            "Examples:\n"
            f"  {PROG} config --domain meteorxx.com --api-key key_XXXX\n"
            f"  {PROG} config --domain 192.168.0.107:8000 --api-key key_XXXX\n"
            f"  {PROG} test\n"
            f"  {PROG} request --name edge-01\n"
            f"  {PROG} register --token reg_XXXX\n"
            f"  {PROG} run\n"
            f"  {PROG} status\n"
            "\n"
            "Environment variables:\n"
            f"  {ENV_DOMAIN}       Server host or IP (used as-is; HTTP for IPs).\n"
            f"  {ENV_SERVER}       Override the API base URL (http:// is allowed).\n"
            f"  {ENV_API_KEY}      API key.\n"
            f"  {ENV_TOKEN}        Registration token (used if --token is omitted).\n"
            f"  {ENV_CONFIG_DIR}   Config/credential directory "
            f"(default: /etc/meteorcli as root, ~/.config/meteorcli otherwise).\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")
    parser.add_argument(
        "--config-dir",
        default=None,
        metavar="DIR",
        help=(
            "Directory for device config and credentials "
            "(default: /etc/meteorcli as root, ~/.config/meteorcli otherwise)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    config_parser = subparsers.add_parser(
        "config",
        help="Store the control-plane domain and API key.",
        description="Persist the server domain (and optional API key) used by later commands.",
    )
    config_parser.add_argument(
        "--domain",
        default=None,
        metavar="HOST",
        help=f"Server host or IP (meteorxx.com or 192.168.0.107:8000; or set {ENV_DOMAIN}).",
    )
    config_parser.add_argument(
        "--api-base",
        default=None,
        metavar="URL",
        help="Override the derived API origin (http:// is allowed for local testing).",
    )
    config_parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP instead of HTTPS (for local testing).",
    )
    config_parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help=f"API key (or set {ENV_API_KEY}). Stored with 0600 permissions.",
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Print the persisted configuration (never prints secrets).",
    )
    config_parser.set_defaults(func=_cmd_config)

    test_parser = subparsers.add_parser(
        "test",
        help="Check that the server is reachable and the API key is valid.",
        description=(
            "Reach the control plane and authenticate with the stored API key. "
            "Does not create an enrollment request."
        ),
    )
    test_parser.add_argument(
        "--server",
        default=None,
        metavar="URL",
        help=f"Control-plane base URL (or set {ENV_SERVER}).",
    )
    test_parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help=f"API key (or set {ENV_API_KEY} / stored key).",
    )
    test_parser.add_argument(
        "--http",
        action="store_true",
        help="Force HTTP when probing the server (for local testing).",
    )
    test_parser.set_defaults(func=_cmd_test)

    register_parser = subparsers.add_parser(
        "register",
        help="Register this device using a registration token.",
        description="Register this device with a one-time registration token.",
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
        help="Read the registration token from a file (recommended).",
    )
    register_parser.add_argument(
        "--name",
        default=None,
        metavar="NAME",
        help="Optional device name.",
    )
    register_parser.set_defaults(func=_cmd_register)

    request_parser = subparsers.add_parser(
        "request",
        help="Request enrollment and wait for admin approval.",
        description=(
            "Submit a device-initiated enrollment request using the stored API key, "
            "then poll until an administrator approves or rejects it."
        ),
    )
    request_parser.add_argument(
        "--server",
        default=None,
        metavar="URL",
        help=f"Control-plane base URL (or set {ENV_SERVER}).",
    )
    request_parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help=f"API key (or set {ENV_API_KEY} / stored key).",
    )
    request_parser.add_argument(
        "--name",
        default=None,
        metavar="NAME",
        help="Optional requested device name.",
    )
    request_parser.set_defaults(func=_cmd_request)

    run_parser = subparsers.add_parser(
        "run",
        help="Send heartbeats to the control plane.",
        description="Send periodic heartbeats so the device reports as online.",
    )
    run_parser.add_argument("--once", action="store_true", help="Send a single heartbeat and exit.")
    run_parser.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Override the heartbeat interval.",
    )
    run_parser.set_defaults(func=_cmd_run)

    status_parser = subparsers.add_parser(
        "status",
        help="Show the persisted (non-secret) configuration.",
        description="Show persisted configuration. Never prints credentials.",
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
