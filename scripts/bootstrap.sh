#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Edge Platform helper scripts live in ${ROOT_DIR}/scripts"
echo "Prefer Make targets from the repository root (make help)."
