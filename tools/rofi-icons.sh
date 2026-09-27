#!/usr/bin/env bash
# Arch's librsvg no longer ships a gdk-pixbuf SVG loader, so rofi can't draw
# SVG-only icon themes like Tela. This renders PNGs (48px) of the icons your
# installed .desktop files use into a local theme that inherits Tela.
# Re-run after installing new apps:  ~/.local/share/wanglin-rice/tools/rofi-icons.sh
set -euo pipefail
SRC_THEME="Tela-circle-purple-dark"
DEST="$HOME/.local/share/icons/WangLin-rofi"
SIZE=48
mkdir -p "$DEST/${SIZE}x${SIZE}/apps"
cat > "$DEST/index.theme" <<IDX
[Icon Theme]
Name=WangLin-rofi
Comment=PNG renders of $SRC_THEME for rofi (generated)
Inherits=$SRC_THEME,hicolor
Directories=${SIZE}x${SIZE}/apps

[${SIZE}x${SIZE}/apps]
Size=$SIZE
Context=Applications
Type=Fixed
IDX
dirs=(/usr/share/applications "$HOME/.local/share/applications" /var/lib/flatpak/exports/share/applications)
n=0
while read -r icon; do
    [[ -z "$icon" || "$icon" == /* ]] && continue
    out="$DEST/${SIZE}x${SIZE}/apps/$icon.png"
    [[ -f "$out" ]] && continue
    svg=""
    for d in "/usr/share/icons/$SRC_THEME/scalable/apps" "/usr/share/icons/${SRC_THEME%-dark}/scalable/apps"; do
        [[ -f "$d/$icon.svg" ]] && { svg="$d/$icon.svg"; break; }
    done
    [[ -n "$svg" ]] || continue
    rsvg-convert -w $SIZE -h $SIZE "$svg" -o "$out" 2>/dev/null && n=$((n + 1))
done < <(shopt -s nullglob; files=(); for d in "${dirs[@]}"; do files+=("$d"/*.desktop); done
         ((${#files[@]})) && grep -hs '^Icon=' "${files[@]}" | cut -d= -f2- | sort -u)
echo "rendered $n new icons into $DEST"
