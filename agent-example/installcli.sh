#!/usr/bin/env bash
# Install meteorcli from this directory onto a Linux device.
#
#   sudo ./installcli.sh
#   sudo ./installcli.sh --uninstall
#
# Override locations with --prefix / --bin-dir, or PREFIX / BIN_DIR.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/opt/meteorcli}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
UNINSTALL=0

usage() {
  cat <<EOF
Install meteorcli from ${SCRIPT_DIR}

Usage:
  sudo $0                 Install to ${PREFIX} and ${BIN_DIR}/meteorcli
  sudo $0 --uninstall     Remove the install (keeps /etc/meteorcli)
  $0 --prefix DIR         Install the venv elsewhere (no root if DIR is writable)

Options:
  --prefix DIR    Virtualenv location (default: ${PREFIX})
  --bin-dir DIR   Directory for the meteorcli symlink (default: ${BIN_DIR})
  --uninstall     Remove the venv and symlink
  -h, --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      PREFIX="${2:?--prefix requires a directory}"
      shift 2
      ;;
    --bin-dir)
      BIN_DIR="${2:?--bin-dir requires a directory}"
      shift 2
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

need_writable() {
  local path="$1"
  local parent
  parent="$(dirname "${path}")"
  if [[ -e "${path}" ]]; then
    [[ -w "${path}" ]]
  else
    [[ -w "${parent}" ]]
  fi
}

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
        command -v "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

uninstall() {
  local link="${BIN_DIR}/meteorcli"
  if [[ -L "${link}" || -f "${link}" ]]; then
    rm -f "${link}"
    echo "Removed ${link}"
  fi
  if [[ -d "${PREFIX}" ]]; then
    rm -rf "${PREFIX}"
    echo "Removed ${PREFIX}"
  fi
  echo "Left /etc/meteorcli in place (device credentials)."
}

install() {
  local python
  python="$(find_python)" || {
    echo "error: Python 3.11+ is required (python3, python3.11, python3.12, or python3.13)." >&2
    echo "On Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip" >&2
    exit 1
  }

  if ! "${python}" -c 'import venv, ensurepip' >/dev/null 2>&1; then
    echo "error: the venv module is missing for ${python}." >&2
    echo "On Debian/Ubuntu: sudo apt install python3-venv" >&2
    exit 1
  fi

  echo "Using ${python} ($("${python}" --version 2>&1))"
  echo "Installing meteorcli into ${PREFIX}"

  mkdir -p "${PREFIX}" "${BIN_DIR}"
  "${python}" -m venv "${PREFIX}"
  "${PREFIX}/bin/python" -m pip install --upgrade pip
  "${PREFIX}/bin/python" -m pip install "${SCRIPT_DIR}"

  ln -sfn "${PREFIX}/bin/meteorcli" "${BIN_DIR}/meteorcli"
  if [[ "${BIN_DIR}" == "/usr/local/bin" ]]; then
    mkdir -p /etc/meteorcli
    chmod 0755 /etc/meteorcli
  fi

  echo
  "${BIN_DIR}/meteorcli" --version
  echo "Installed ${BIN_DIR}/meteorcli"
  echo "Next: sudo meteorcli config --domain <host> --api-key key_..."
  echo "      sudo meteorcli test"
}

if [[ "${UNINSTALL}" -eq 1 ]]; then
  if ! need_writable "${PREFIX}" || ! need_writable "${BIN_DIR}"; then
    echo "error: ${PREFIX} or ${BIN_DIR} is not writable; re-run with sudo." >&2
    exit 1
  fi
  uninstall
  exit 0
fi

if ! need_writable "${PREFIX}" || ! need_writable "${BIN_DIR}"; then
  echo "error: ${PREFIX} or ${BIN_DIR} is not writable; re-run with sudo." >&2
  exit 1
fi

install
