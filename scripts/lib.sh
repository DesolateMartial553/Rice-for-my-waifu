# Shared helpers for Wang Lin scripts (sourced).
WL_SHARE="${HOME}/.local/share/wanglin-rice"
WL_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/wanglin-rice"
WL_WALL="${WL_SHARE}/wallpapers"
mkdir -p "$WL_STATE"
wl_low_motion() { [[ -e "$WL_STATE/low-motion" ]]; }
wl_notify() { command -v notify-send >/dev/null && notify-send -a "Wang Lin" "$@"; }
# Wallpaper: last one picked (wallpaper-cycle), then the bundled one.
wl_wallpaper() {
    local last; last=$(cat "$WL_STATE/wallpaper.current" 2>/dev/null)
    [[ -f "$last" ]] && { echo "$last"; return; }
    for f in "$WL_WALL"/wallpaper.{png,jpg,jpeg,webp} "$WL_WALL"/wanglin-placeholder.png; do
        [[ -f "$f" ]] && { echo "$f"; return; }
    done
}
