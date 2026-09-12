#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_runtime "${1:?Usage: rollback.sh DEV|QA|PROD [previous-release.env]}"
: "${SMOKE_EMAIL:?Set SMOKE_EMAIL}" "${SMOKE_PASSWORD:?Set SMOKE_PASSWORD}"
lock_state
manifest=${2:-"$STATE_DIR/rollback.env"}
[[ -f "$manifest" ]] || fail 'No prior release; supply a known compatible manifest'
load_release "$manifest"
compose config --quiet
compose pull
# Application rollback only. Never silently downgrade or restore the database.
compose up -d --no-build --remove-orphans --wait --wait-timeout 120
python3 "$SCRIPT_DIR/smoke.py"
write_release "$STATE_DIR/current.env"
printf 'Rolled back %s to %s commit=%s; database schema unchanged.\n' "$APP_ENV" "$APP_VERSION" "$GIT_COMMIT"
