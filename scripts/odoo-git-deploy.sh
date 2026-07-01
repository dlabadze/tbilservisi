#!/bin/bash
# Pull latest tbilservisi from GitHub and deploy Odoo modules to custom_addons.
# Usage:
#   odoo-git-deploy.sh          # pull if remote changed, then deploy
#   odoo-git-deploy.sh --local  # deploy current repo state (skip git pull)
set -euo pipefail

REPO="/home/fmg/tbilservisi"
ADDONS="/opt/odoo/odoo18/custom_addons"
LOG="/home/fmg/logs/odoo-deploy.log"
LOCK="/tmp/odoo-git-deploy.lock"
LAST_SHA_FILE="/home/fmg/logs/last-deployed-sha"
LOCAL_ONLY=0

if [[ "${1:-}" == "--local" ]]; then
  LOCAL_ONLY=1
fi

mkdir -p "$(dirname "$LOG")"

deploy_module_dir() {
  local src="$1"
  local name
  name=$(basename "$src")
  echo "Deploying module: $name"
  mkdir -p "$ADDONS/$name"
  rsync -a --delete --omit-dir-times \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude ".git" \
    "$src/" "$ADDONS/$name/"
  find "$ADDONS/$name" -type d -exec chmod 755 {} +
  find "$ADDONS/$name" -type f -exec chmod 644 {} +
}

run_deploy() {
  echo "=== $(date -Is) deploy start (local_only=$LOCAL_ONLY) ==="

  if [[ "$LOCAL_ONLY" -eq 0 ]]; then
    cd "$REPO"
    git fetch origin main
    LOCAL_SHA=$(git rev-parse HEAD)
    REMOTE_SHA=$(git rev-parse origin/main)
    if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
      echo "Updating $LOCAL_SHA -> $REMOTE_SHA"
      git pull --ff-only origin main
    fi
  else
    cd "$REPO"
  fi

  CURRENT_SHA=$(git -C "$REPO" rev-parse HEAD)
  LAST_SHA=""
  if [[ -f "$LAST_SHA_FILE" ]]; then
    LAST_SHA=$(cat "$LAST_SHA_FILE")
  fi

  if [[ "$LOCAL_ONLY" -eq 0 && "$CURRENT_SHA" == "$LAST_SHA" ]]; then
    echo "Already deployed commit $CURRENT_SHA"
    return 0
  fi

  echo "Deploying commit $CURRENT_SHA (previous: ${LAST_SHA:-none})"

  if sudo -n chown -R fmg:odoo "$ADDONS" 2>/dev/null; then
    echo "Reset ownership on custom_addons to fmg:odoo"
  fi

  shopt -s nullglob
  for manifest in "$REPO"/*/__manifest__.py; do
    deploy_module_dir "$(dirname "$manifest")"
  done

  DESKTOP_REPO="$REPO/Desktop/Tbilserv/custom_addons"
  if [[ -d "$DESKTOP_REPO" ]]; then
    for manifest in "$DESKTOP_REPO"/*/__manifest__.py; do
      name=$(basename "$(dirname "$manifest")")
      if [[ ! -f "$ADDONS/$name/__manifest__.py" ]]; then
        deploy_module_dir "$(dirname "$manifest")"
      fi
    done
  fi

  echo "Deploy finished."
  echo "$CURRENT_SHA" > "$LAST_SHA_FILE"
  if sudo -n systemctl restart odoo 2>/dev/null; then
    echo "Odoo restarted."
  else
    echo "Odoo restart skipped (run: sudo systemctl restart odoo)"
  fi
}

(
  flock -n 9 || { echo "Deploy already running, skipping."; exit 0; }
  exec >>"$LOG" 2>&1
  run_deploy
) 9>"$LOCK"
