#!/usr/bin/env bash
# Push austin311bot/ code to seanatwork/austin311bot-unofficial so its
# map-refresh GitHub Actions regenerate docs/ from the latest code.
# GitHub Pages serves from that repo; this repo's copy is authoritative.
# Run from anywhere: `bash austin311bot/sync-to-unofficial.sh`
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
git clone --quiet --depth 1 https://github.com/seanatwork/austin311bot-unofficial.git "$WORK"
rsync -a --exclude-from=- "$SRC/" "$WORK/" <<'EOF'
.git/
docs/
.venv/
__pycache__/
*.egg-info/
fly.toml
Dockerfile
nixpacks.toml
netlify.toml
railway.json
sync-to-unofficial.sh
EOF
# Sync hand-crafted docs only — DO NOT add workflow-generated files here.
# Workflow-generated files (crime, water, childcare, budget, parking/trends,
# noise/trends, homeless/trends, graffiti/trends, etc.) are owned by the batch
# workflows on austin311bot-unofficial; syncing local stale copies overwrites them.
cp "$SRC/docs/index.html"               "$WORK/docs/index.html"
cp "$SRC/docs/pulse.json"               "$WORK/docs/pulse.json"
cp "$SRC/docs/court/index.html"         "$WORK/docs/court/index.html"
cp "$SRC/docs/court/trends/index.html"  "$WORK/docs/court/trends/index.html"
mkdir -p "$WORK/docs/crashes"
cp "$SRC/docs/crashes/index.html"       "$WORK/docs/crashes/index.html"
mkdir -p "$WORK/docs/crashes/trends"
cp "$SRC/docs/crashes/trends/index.html" "$WORK/docs/crashes/trends/index.html"
mkdir -p "$WORK/docs/fun"
cp "$SRC/docs/fun/index.html"           "$WORK/docs/fun/index.html"
mkdir -p "$WORK/docs/restaurants"
cp "$SRC/docs/restaurants/index.html"   "$WORK/docs/restaurants/index.html"
cd "$WORK"
git add -A
git diff --cached --quiet && { echo "Nothing to sync."; exit 0; }
git -c user.name="sync" -c user.email="sync@local" commit -qm "sync code from All-Telegram-Bots"
git push -q
# echo "Synced. Triggering map and trends workflows..."
# for wf in generate-parking-map.yml deploy-map.yml generate-bicycle-map.yml \
#           generate-graffiti-map.yml generate-parks-map.yml generate-traffic-map.yml \
#           generate-noise-map.yml generate-water-map.yml generate-animal-map.yml \
#           generate-childcare-map.yml generate-crime-map.yml \
#           generate-graffiti-trends.yml generate-crime-trends.yml \
#           generate-noise-trends.yml \
#           generate-budget.yml generate-homeless-trends.yml; do
#   gh workflow run "$wf" --repo seanatwork/austin311bot-unofficial --ref main || true
# done
# echo "Done. Maps will regenerate in ~2-5 min."
echo "Synced. Workflows will pick up changes on their next scheduled run."
