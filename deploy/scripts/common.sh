#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

load_runtime() {
  local target=${1:?Environment required}
  case "$target" in DEV|QA|PROD) ;; *) fail 'Environment must be DEV, QA or PROD' ;; esac
  ENV_FILE=${ENV_FILE:-"/etc/auladata/${target,,}.env"}
  [[ -f "$ENV_FILE" ]] || fail "Create runtime configuration at $ENV_FILE"
  # This is operator-owned shell configuration, never a downloaded artifact.
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  [[ ${APP_ENV:-} == "$target" ]] || fail 'APP_ENV does not match the requested target'
  : "${DATABASE_URL:?Set DATABASE_URL}" "${JWT_SECRET:?Set JWT_SECRET}"
  : "${APP_BIND_ADDRESS:?Set the provisioned app VM address}" "${BASE_URL:?Set BASE_URL}"
  : "${CORS_ORIGINS:?Set allowed public origins for CSRF validation}"
  [[ "$DATABASE_URL" == postgresql+psycopg://* ]] || fail 'DATABASE_URL must use PostgreSQL psycopg'
  if [[ "$target" == QA || "$target" == PROD ]]; then
    [[ ${COOKIE_SECURE:-} == true && "$BASE_URL" == https://* ]] || fail 'QA/PROD require HTTPS and COOKIE_SECURE=true'
  fi
  STATE_DIR=${STATE_DIR:-"/var/lib/auladata/${target,,}"}
  export APP_ENV STATE_DIR ENV_FILE
  command -v docker >/dev/null || fail 'Docker is required'
  command -v python3 >/dev/null || fail 'Python 3 is required'
  docker compose version >/dev/null
}

load_release() {
  local manifest=${1:?Manifest required} validated
  validated=$(python3 "$SCRIPT_DIR/release.py" "$manifest") || return 1
  # Only the four validated, non-secret assignments are evaluated.
  eval "$validated"
  export BACKEND_IMAGE FRONTEND_IMAGE GIT_COMMIT APP_VERSION
}

compose() {
  docker compose --project-name "auladata-${APP_ENV,,}" --env-file "$ENV_FILE" \
    -f "$REPO_ROOT/deploy/compose.yml" "$@"
}

lock_state() {
  mkdir -p "$STATE_DIR"
  command -v flock >/dev/null || fail 'flock (util-linux) is required'
  exec 9>"$STATE_DIR/deploy.lock"
  flock -n 9 || fail 'Another deployment is already running for this environment'
}

write_release() {
  printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\nGIT_COMMIT=%s\nAPP_VERSION=%s\n' \
    "$BACKEND_IMAGE" "$FRONTEND_IMAGE" "$GIT_COMMIT" "$APP_VERSION" > "$1"
}
