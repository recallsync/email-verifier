#!/usr/bin/env bash
# Pull latest images and restart an existing Email Verifier install.
# Run from the install directory (where docker-compose.yml and .env live).

set -euo pipefail

if [[ ! -f docker-compose.yml || ! -f .env ]]; then
  printf 'Error: run this from your Email Verifier install directory.\n' >&2
  exit 1
fi

compose_args=(compose -f docker-compose.yml)
if grep -qE '^NGROK_AUTHTOKEN=.+' .env 2>/dev/null; then
  compose_args+=(-f docker-compose.ngrok.yml)
fi

docker "${compose_args[@]}" pull
docker "${compose_args[@]}" up -d

printf 'Update complete. App: http://localhost:%s\n' "${APP_PORT:-5050}"
