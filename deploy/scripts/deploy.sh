#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

target=${1:?Usage: deploy.sh DEV|QA|PROD release.env}
manifest=${2:-${RELEASE_FILE:-}}
if [[ -z "$manifest" && -n ${IMAGE_TAG:-} ]]; then
  manifest="$REPO_ROOT/deploy/releases/$IMAGE_TAG.env"
fi
[[ -n "$manifest" ]] || fail 'Pass release.env or set RELEASE_FILE / IMAGE_TAG (stored manifest SHA)'
load_runtime "$target"
load_release "$manifest"
: "${SMOKE_EMAIL:?Set SMOKE_EMAIL}" "${SMOKE_PASSWORD:?Set SMOKE_PASSWORD}"
lock_state
trap 'printf "Deployment failed. Inspect services and use rollback.sh with the previous manifest if schema-compatible.\n" >&2' ERR

compose config --quiet
compose pull
if [[ -f "$STATE_DIR/current.env" ]]; then
  cp -- "$STATE_DIR/current.env" "$STATE_DIR/rollback.env"
fi
write_release "$STATE_DIR/pending.env"
if [[ "$APP_ENV" == PROD ]]; then
  python3 "$SCRIPT_DIR/backup.py"
fi
compose run --rm --no-deps backend alembic upgrade head
if [[ ${SEED_USERS:-false} == true ]]; then
  compose run --rm --no-deps backend python -m app.seed
fi
compose up -d --no-build --remove-orphans --wait --wait-timeout 120
python3 "$SCRIPT_DIR/smoke.py"
mv -- "$STATE_DIR/pending.env" "$STATE_DIR/current.env"
printf 'Deployed %s %s commit=%s\n' "$APP_ENV" "$APP_VERSION" "$GIT_COMMIT"
