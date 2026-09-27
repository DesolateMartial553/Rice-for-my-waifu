#!/usr/bin/env bash
# Download the Renegade Immortal wallpapers and recolour them to the rice's
# purple palette. The artwork belongs to its creators, so it isn't stored in
# the repo; each install fetches it from Wallhaven (sources in SOURCES.txt).
#   tools/fetch-wallpapers.sh        skip images already present
set -euo pipefail
REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
OUT="$REPO/wallpapers/renegade"
mkdir -p "$OUT"

# name | wallhaven full-size URL | crop anchor
WALLS=(
    "1-lightning|https://w.wallhaven.cc/full/21/wallhaven-21ee1m.jpg|north"
    "2-doorway|https://w.wallhaven.cc/full/d8/wallhaven-d8gg3j.jpg|center"
    "3-sovereign|https://w.wallhaven.cc/full/rq/wallhaven-rq22q1.jpg|center"
    "4-calligraphy|https://w.wallhaven.cc/full/je/wallhaven-jew57q.png|center"
)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
# Palette ramp: mantle → deep → purple → lavender → text.
magick xc:'#0B0712' xc:'#251538' xc:'#6E40A1' xc:'#B88AF5' xc:'#F2ECFA' +append \
    -filter Cubic -resize 256x1! "$tmp/clut.png"

got=0 failed=0
for w in "${WALLS[@]}"; do
    IFS='|' read -r name url anchor <<<"$w"
    [[ -s $OUT/$name.png ]] && continue
    if curl -fsSL --retry 2 --max-time 90 -A "wanglin-rice installer" -o "$tmp/src" "$url" &&
       magick "$tmp/src" -resize 1920x1080^ -gravity "$anchor" -extent 1920x1080 \
           -colorspace Gray -sigmoidal-contrast 3,45% -colorspace sRGB "$tmp/clut.png" -clut "$OUT/$name.png"; then
        got=$((got + 1))
    else
        failed=$((failed + 1)); rm -f "$OUT/$name.png"
    fi
done
echo "wallpapers: $got downloaded, $failed failed, $(ls "$OUT"/*.png 2>/dev/null | wc -l) available"
((failed == 0))
