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
cd "$WORK"
git add -A
git diff --cached --quiet && { echo "Nothing to sync."; exit 0; }
git -c user.name="sync" -c user.email="sync@local" commit -qm "sync code from All-Telegram-Bots"
git push -q
echo "Synced. Triggering map workflows..."
for wf in generate-parking-map.yml deploy-map.yml generate-bicycle-map.yml \
          generate-graffiti-map.yml generate-parks-map.yml generate-traffic-map.yml \
          generate-noise-map.yml generate-water-map.yml generate-animal-map.yml \
          generate-childcare-map.yml generate-crime-map.yml \
          generate-graffiti-trends.yml generate-crime-trends.yml \
          generate-noise-trends.yml generate-parking-trends.yml; do
  gh workflow run "$wf" --repo seanatwork/austin311bot-unofficial --ref main || true
done
echo "Done. Maps will regenerate in ~2-5 min."
