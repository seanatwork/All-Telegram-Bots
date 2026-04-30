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
# Sync landing page + small hand-crafted/pre-generated docs (maps excluded above — too large)
cp "$SRC/docs/index.html"               "$WORK/docs/index.html"
cp "$SRC/docs/budget/index.html"        "$WORK/docs/budget/index.html"
cp "$SRC/docs/court/index.html"         "$WORK/docs/court/index.html"
cp "$SRC/docs/court/trends/index.html"  "$WORK/docs/court/trends/index.html"
cp "$SRC/docs/parking/trends/index.html" "$WORK/docs/parking/trends/index.html"
mkdir -p "$WORK/docs/noise/trends"
cp "$SRC/docs/noise/trends/index.html"  "$WORK/docs/noise/trends/index.html"
mkdir -p "$WORK/docs/crime/trends"
cp "$SRC/docs/crime/trends/index.html"  "$WORK/docs/crime/trends/index.html"
mkdir -p "$WORK/docs/crime"
cp "$SRC/docs/crime/index.html"         "$WORK/docs/crime/index.html"
mkdir -p "$WORK/docs/water"
cp "$SRC/docs/water/index.html"         "$WORK/docs/water/index.html"
mkdir -p "$WORK/docs/childcare"
cp "$SRC/docs/childcare/index.html"     "$WORK/docs/childcare/index.html"
mkdir -p "$WORK/docs/crashes"
cp "$SRC/docs/crashes/index.html"       "$WORK/docs/crashes/index.html"
mkdir -p "$WORK/docs/crashes/trends"
cp "$SRC/docs/crashes/trends/index.html" "$WORK/docs/crashes/trends/index.html"
mkdir -p "$WORK/docs/fun"
cp "$SRC/docs/fun/index.html"           "$WORK/docs/fun/index.html"
mkdir -p "$WORK/docs/homeless/trends"
cp "$SRC/docs/homeless/trends/index.html" "$WORK/docs/homeless/trends/index.html"
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
