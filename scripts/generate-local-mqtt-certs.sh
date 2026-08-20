#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/certs}"
mkdir -p "$OUT"

openssl genrsa -out "$OUT/ca.key" 2048 >/dev/null 2>&1
openssl req -x509 -new -nodes -key "$OUT/ca.key" -sha256 -days 3650 \
  -out "$OUT/ca.crt" -subj "/CN=MeteorCloud Local MQTT CA" >/dev/null 2>&1

openssl genrsa -out "$OUT/server.key" 2048 >/dev/null 2>&1
openssl req -new -key "$OUT/server.key" -out "$OUT/server.csr" \
  -subj "/CN=localhost" >/dev/null 2>&1

cat > "$OUT/server.ext" <<'EOF'
subjectAltName=DNS:localhost,DNS:emqx,IP:127.0.0.1
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl x509 -req -in "$OUT/server.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
  -CAcreateserial -out "$OUT/server.crt" -days 3650 -sha256 \
  -extfile "$OUT/server.ext" >/dev/null 2>&1

# EMQX in Docker must be able to read the server key from the bind mount.
chmod 600 "$OUT/ca.key"
chmod 644 "$OUT/server.key" "$OUT/ca.crt" "$OUT/server.crt"

echo "Wrote MQTT development certificates to $OUT"
echo "  CA:     $OUT/ca.crt"
echo "  Server: $OUT/server.crt (SAN DNS:localhost, DNS:emqx, IP:127.0.0.1)"
