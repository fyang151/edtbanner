#!/bin/sh
# Reads .env and generates config.js for the browser
set -e

ENV_FILE="$(dirname "$0")/.env"
OUT_FILE="$(dirname "$0")/config.js"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env not found. Copy .env.example and fill it in."
  exit 1
fi

. "$ENV_FILE"

cat > "$OUT_FILE" <<EOF
window.CONFIG = {
  API: '${api_url}'
};
EOF

echo "Generated config.js"
