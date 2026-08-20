#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/certs}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

openssl genrsa -out "$OUT/ca.key" 2048 >/dev/null 2>&1
openssl req -x509 -new -nodes -key "$OUT/ca.key" -sha256 -days 3650 \
  -out "$OUT/ca.crt" -subj "/CN=MeteorCloud Local MQTT CA" \
  -addext "basicConstraints=critical,CA:true" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" >/dev/null 2>&1

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

# EMQX in Docker runs as UID/GID 1000 and bind-mounts this key.
# chmod while we still own the file, then chown. Do not chmod after a
# docker chown — GitHub Actions (UID 1001) cannot chmod a UID-1000 file.
chmod 0640 "$OUT/server.key"
chmod 600 "$OUT/ca.key"
chmod 644 "$OUT/ca.crt" "$OUT/server.crt"
if ! chown 1000:1000 "$OUT/server.key" 2>/dev/null; then
  if command -v docker >/dev/null 2>&1; then
    docker run --rm --user 0:0 -v "$OUT:/certs" busybox:1.36 \
      chown 1000:1000 /certs/server.key
  else
    echo "error: could not set $OUT/server.key owner to UID/GID 1000 (required so EMQX can read the bind-mounted key)." >&2
    echo "error: rerun as uid 1000, as root, or with Docker available to chown the file." >&2
    exit 1
  fi
fi

echo "Wrote MQTT development certificates to $OUT"
echo "  CA:     $OUT/ca.crt"
echo "  Server: $OUT/server.crt (SAN DNS:localhost, DNS:emqx, IP:127.0.0.1)"
