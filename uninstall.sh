#!/usr/bin/env bash
# 王林 · Wang Lin rice — restore your previous setup.
#   ./uninstall.sh            remove the rice's links, restore backed-up files
#   ./uninstall.sh --dry-run  show what would happen
# Files are restored from ~/.local/state/wanglin-rice/backups/ using the
# manifest written by install.sh. Backups are kept (delete them yourself).
set -euo pipefail

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/wanglin-rice"
MANIFEST="$STATE/manifest.tsv"
REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
say() { printf '\033[38;2;184;138;245m::\033[0m %s\n' "$*"; }
run() { if ((DRY)); then echo "   would: $*"; else "$@"; fi; }

[[ -f "$MANIFEST" || -f "$STATE/edits.tsv" ]] || { echo "no manifest at $MANIFEST — nothing to undo"; exit 0; }
touch "$MANIFEST" 2>/dev/null || true

# Pass 1: remove every link that points into this repo.
while IFS=$'\t' read -r tgt bk; do
    if [[ -L "$tgt" ]] && [[ "$(readlink -f "$tgt")" == "$REPO"* ]]; then
        say "unlink  ${tgt/#$HOME/\~}"
        run rm "$tgt"
    fi
done < "$MANIFEST"

# Pass 2: restore backups oldest-first, so your original file wins.
while IFS=$'\t' read -r tgt bk; do
    if [[ "$bk" != NONE && -e "$bk" ]] && { ((DRY)) || [[ ! -e "$tgt" ]]; }; then
        say "restore ${tgt/#$HOME/\~}"
        run mv "$bk" "$tgt"
    fi
done < "$MANIFEST"

# Pass 3: files the installer edited or generated (kdeglobals, dolphinrc,
# qt5ct/qt6ct.conf, .bashrc): put the saved copy back, or delete if it was new.
EDITS="$STATE/edits.tsv"
if [[ -f "$EDITS" ]]; then
    while IFS=$'\t' read -r tgt bk; do
        if [[ "$tgt" == "$HOME/.bashrc" ]]; then
            # Remove only our block, so later edits to .bashrc survive.
            say "clean   ~/.bashrc (wanglin-rice block)"
            run sed -i '/^# >>> wanglin-rice >>>$/,/^# <<< wanglin-rice <<<$/d' "$tgt"
        elif [[ "$bk" == NONE ]]; then
            say "remove  ${tgt/#$HOME/\~}"
            run rm -f "$tgt"
        elif [[ -e "$bk" || -L "$bk" ]]; then
            say "restore ${tgt/#$HOME/\~}"
            run rm -f "$tgt"; run cp -P "$bk" "$tgt"
        fi
    done < "$EDITS"
    ((DRY)) || mv "$EDITS" "$EDITS.undone-$(date +%Y%m%d-%H%M%S)"
fi

# Desktop autostart added for text-console logins (install.sh step 2).
if grep -qs "wanglin-rice autostart" "$HOME/.bash_profile"; then
    say "clean   ~/.bash_profile (desktop autostart)"
    run sed -i '/^# >>> wanglin-rice autostart >>>$/,/^# <<< wanglin-rice autostart <<<$/d' "$HOME/.bash_profile"
fi
rm -f "$STATE/welcomed" 2>/dev/null || true

# Stop the rice's background helpers.
if [[ -r "${XDG_RUNTIME_DIR:-/tmp}/wanglin-popup.pid" ]]; then
    run kill "$(cat "${XDG_RUNTIME_DIR:-/tmp}/wanglin-popup.pid")" 2>/dev/null || true
fi

if [[ -f "$STATE/gsettings.orig" ]] && command -v gsettings >/dev/null; then
    while IFS=$'\t' read -r k v; do
        [[ -n "$v" ]] || continue
        say "gsettings $k → $v"
        run gsettings set org.gnome.desktop.interface "$k" "$v"
    done < "$STATE/gsettings.orig"
    ((DRY)) || rm -f "$STATE/gsettings.orig"
fi

ICONS="$HOME/.local/share/icons/WangLin-rofi"
if [[ -d "$ICONS" ]]; then say "remove  ${ICONS/#$HOME/\~} (generated)"; run rm -r "$ICONS"; fi

if ((!DRY)) && [[ -s "$MANIFEST" ]]; then
    mv "$MANIFEST" "$MANIFEST.undone-$(date +%Y%m%d-%H%M%S)"
    rm -f "$STATE/low-motion"
fi
say "restored. Reload with: hyprctl reload  (or log out and back in)"
