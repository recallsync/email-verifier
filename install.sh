#!/usr/bin/env bash
# Interactive installer for Email Verifier (Docker Hub images).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh | bash
#   curl -fsSL .../install.sh -o install.sh && bash install.sh
#
# Requires: Docker Compose v2, curl or wget

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/recallsync/email-verifier/main/deploy"
INSTALL_SCRIPT_RAW="https://raw.githubusercontent.com/recallsync/email-verifier/main/install.sh"
DEFAULT_DIR="email-verifier"
HEALTH_TIMEOUT=120
TTY_DEVICE="/dev/tty"

err() { printf 'Error: %s\n' "$*" >&2; }
info() { printf '%s\n' "$*"; }

# curl | bash feeds the script on stdin — read prompts from the terminal explicitly.
prompt() {
  local __var=$1
  local __msg=$2
  local __secret=${3:-0}
  local __val=""

  if [[ ! -r "$TTY_DEVICE" ]]; then
    err "Interactive installer requires a terminal ($TTY_DEVICE)."
    err "Try: curl -fsSL ${INSTALL_SCRIPT_RAW} -o install.sh && bash install.sh"
    exit 1
  fi

  if [[ "$__secret" == "1" ]]; then
    IFS= read -r -s -p "$__msg" __val <"$TTY_DEVICE" || true
    printf '\n' >"$TTY_DEVICE"
  else
    IFS= read -r -p "$__msg" __val <"$TTY_DEVICE" || true
  fi

  printf -v "$__var" '%s' "$__val"
}

download() {
  local url=$1 dest=$2
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dest"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dest" "$url"
  else
    err "curl or wget is required to download install files."
    exit 1
  fi
}

check_prereqs() {
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    err "Docker Compose v2 is required (docker compose). Legacy docker-compose is not supported."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    err "Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
  fi
}

generate_password() {
  local pw=""
  if command -v openssl >/dev/null 2>&1; then
    pw=$(openssl rand -hex 16 2>/dev/null || true)
    [[ -n "$pw" ]] && { printf '%s' "$pw"; return 0; }
  fi
  if command -v python3 >/dev/null 2>&1; then
    pw=$(python3 -c 'import secrets; print(secrets.token_hex(16))' 2>/dev/null || true)
    [[ -n "$pw" ]] && { printf '%s' "$pw"; return 0; }
  fi
  if [[ -r /dev/urandom ]]; then
    if command -v od >/dev/null 2>&1; then
      pw=$(od -An -N16 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n' || true)
      [[ -n "$pw" ]] && { printf '%s' "$pw"; return 0; }
    fi
    if command -v hexdump >/dev/null 2>&1; then
      pw=$(hexdump -vn16 -e '16/1 "%02x"' /dev/urandom 2>/dev/null || true)
      [[ -n "$pw" ]] && { printf '%s' "$pw"; return 0; }
    fi
  fi
  if command -v shasum >/dev/null 2>&1; then
    pw=$(shasum -a 256 /dev/urandom 2>/dev/null | cut -c1-32 || true)
    [[ -n "$pw" ]] && { printf '%s' "$pw"; return 0; }
  fi
  pw="${RANDOM}${RANDOM}$(date +%s)"
  printf '%s' "$pw"
}

escape_env_value() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g"
}

write_env_line() {
  local key=$1 value=$2
  printf "%s='%s'\n" "$key" "$(escape_env_value "$value")"
}

normalize_ngrok_domain() {
  local d="${1// /}"
  d="${d%/}"
  d="${d#https://}"
  d="${d#http://}"
  if [[ -z "$d" ]]; then
    return 1
  fi
  printf 'https://%s' "$d"
}

uses_ngrok() {
  [[ -f .env ]] || return 1
  grep -qE '^NGROK_AUTHTOKEN=.+' .env 2>/dev/null
}

compose_cmd() {
  local -a args=(compose -f docker-compose.yml)
  if uses_ngrok || [[ "${ENABLE_NGROK:-0}" == "1" ]]; then
    args+=(-f docker-compose.ngrok.yml)
  fi
  docker "${args[@]}" "$@"
}

wait_for_health() {
  local port="${APP_PORT:-5050}"
  local url="http://localhost:${port}/health"
  local elapsed=0
  info "Waiting for app to become healthy..."
  while [[ "$elapsed" -lt "$HEALTH_TIMEOUT" ]]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  err "App did not become healthy within ${HEALTH_TIMEOUT}s. Check: docker compose logs app"
  return 1
}

fetch_ngrok_public_url() {
  if ! curl -fsS http://localhost:4040/api/tunnels >/dev/null 2>&1; then
    return 1
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c '
import json, urllib.request
try:
    with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=5) as r:
        data = json.load(r)
    for t in data.get("tunnels", []):
        url = t.get("public_url", "")
        if url.startswith("https://"):
            print(url)
            break
except Exception:
    pass
' 2>/dev/null || true
  fi
}

main() {
  info "Email Verifier — installer"
  info ""

  info "Checking Docker..."
  check_prereqs
  info "Docker OK."
  info ""

  local install_dir=""
  prompt install_dir "Install directory [./${DEFAULT_DIR}]: "
  install_dir="${install_dir:-./${DEFAULT_DIR}}"
  install_dir="${install_dir/#\~/$HOME}"

  mkdir -p "$install_dir"
  cd "$install_dir"
  info "Installing to: $(pwd)"
  info ""

  local update_only=0
  if [[ -f .env && -f docker-compose.yml ]]; then
    local ans=""
    prompt ans "Existing install found. Update images only (keep .env)? [Y/n]: "
    if [[ ! "$ans" =~ ^[Nn]$ ]]; then
      update_only=1
    fi
  fi

  info "Downloading compose files..."
  download "${REPO_RAW}/docker-compose.yml" docker-compose.yml
  download "${REPO_RAW}/docker-compose.ngrok.yml" docker-compose.ngrok.yml
  download "${REPO_RAW}/.env.example" .env.example
  download "${REPO_RAW}/README.md" README.md
  download "${REPO_RAW}/INSTRUCTIONS.md" INSTRUCTIONS.md

  if [[ "$update_only" -eq 1 ]]; then
    info "Pulling latest images..."
    compose_cmd pull
    compose_cmd up -d
    wait_for_health || true
    info ""
    info "Update complete."
    info "  App: http://localhost:${APP_PORT:-5050}"
    info "  Docs: $(pwd)/README.md · $(pwd)/INSTRUCTIONS.md"
    if uses_ngrok; then
      info "  Ngrok inspector: http://localhost:4040"
      local pub
      pub=$(fetch_ngrok_public_url || true)
      [[ -n "$pub" ]] && info "  Public URL: $pub"
    fi
    exit 0
  fi

  local pg_pass=""
  prompt pg_pass "PostgreSQL password (Enter for random): " 1
  if [[ -z "$pg_pass" ]]; then
    pg_pass=$(generate_password)
    if [[ -z "$pg_pass" ]]; then
      err "Could not generate a random password on this system."
      prompt pg_pass "Enter a PostgreSQL password manually: " 1
      [[ -z "$pg_pass" ]] && { err "Password cannot be empty."; exit 1; }
    fi
    GENERATED_PASSWORD=1
  fi

  ENABLE_NGROK=0
  local ngrok_token="" ngrok_domain="" public_url=""
  local ngrok_ans=""
  prompt ngrok_ans "Enable ngrok for external HTTPS access? [y/N]: "
  if [[ "$ngrok_ans" =~ ^[Yy]$ ]]; then
    ENABLE_NGROK=1
    prompt ngrok_token "NGROK authtoken (dashboard.ngrok.com/get-started/your-authtoken): " 1
    if [[ -z "$ngrok_token" ]]; then
      err "NGROK_AUTHTOKEN is required when ngrok is enabled."
      exit 1
    fi
    prompt ngrok_domain "Reserved ngrok domain (dashboard.ngrok.com/domains, Enter to skip): "
    if [[ -n "$ngrok_domain" ]]; then
      ngrok_domain=$(normalize_ngrok_domain "$ngrok_domain") || {
        err "Invalid ngrok domain."
        exit 1
      }
      public_url="$ngrok_domain"
    else
      info "Note: without a reserved domain, your public URL changes on each ngrok restart."
    fi
  fi

  {
    write_env_line "POSTGRES_PASSWORD" "$pg_pass"
    write_env_line "APP_PORT" "5050"
    if [[ "$ENABLE_NGROK" -eq 1 ]]; then
      write_env_line "NGROK_AUTHTOKEN" "$ngrok_token"
      [[ -n "$ngrok_domain" ]] && write_env_line "NGROK_DOMAIN" "$ngrok_domain"
      [[ -n "$public_url" ]] && write_env_line "PUBLIC_URL" "$public_url"
    fi
  } > .env
  chmod 600 .env

  info "Pulling Docker images (this may take a few minutes)..."
  compose_cmd pull

  info "Starting services..."
  compose_cmd up -d

  wait_for_health || true

  local app_port="5050"
  if grep -qE '^APP_PORT=' .env 2>/dev/null; then
    app_port=$(grep -E '^APP_PORT=' .env | head -1 | cut -d= -f2- | tr -d "'\"")
  fi

  info ""
  info "Done!"
  info "  App:     http://localhost:${app_port}"
  info "  Data:    $(pwd)/data"
  if [[ "${GENERATED_PASSWORD:-0}" -eq 1 ]]; then
    info "  Postgres password (saved in .env): ${pg_pass}"
  fi
  if [[ "$ENABLE_NGROK" -eq 1 ]]; then
    info "  Ngrok inspector: http://localhost:4040"
    if [[ -n "$public_url" ]]; then
      info "  Public URL: ${public_url}"
    else
      sleep 3
      local pub
      pub=$(fetch_ngrok_public_url || true)
      if [[ -n "$pub" ]]; then
        info "  Public URL (temporary): ${pub}"
      fi
    fi
  fi
  info ""
  info "Docs:    $(pwd)/README.md"
  info "         $(pwd)/INSTRUCTIONS.md"
  info ""
  info "Commands (from this directory):"
  info "  docker compose logs -f app"
  info "  docker compose down"
}

main "$@"
