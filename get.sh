#!/usr/bin/env bash
# 王林 · Wang Lin rice — one-command installer.
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/DesolateMartial553/Rice-for-my-waifu/main/get.sh)
#
# Downloads (or updates) the rice into ~/wanglin-rice, then runs its install.sh.
# Any options are passed on, e.g.  … get.sh) --yes   or   … get.sh) --dry-run
# Override the source or location with WANGLIN_REPO=<git url>, WANGLIN_DIR=<path>.
set -euo pipefail

REPO_URL="${WANGLIN_REPO:-https://github.com/DesolateMartial553/Rice-for-my-waifu.git}"
DIR="${WANGLIN_DIR:-$HOME/wanglin-rice}"
say()  { printf '\033[38;2;184;138;245m::\033[0m %s\n' "$*"; }
die()  { printf '\033[38;2;240;121;155m!!\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || die "run as your normal user, not root"
command -v pacman >/dev/null || die "this rice targets Arch Linux (pacman not found)"
if ! command -v git >/dev/null; then
    say "installing git"
    sudo pacman -S --needed --noconfirm git
fi

if [[ -d $DIR/.git ]]; then
    say "updating ${DIR/#$HOME/\~}"
    git -C "$DIR" pull --ff-only
elif [[ -e $DIR ]]; then
    die "${DIR/#$HOME/\~} exists and isn't a git checkout: move it or set WANGLIN_DIR"
else
    say "downloading the rice to ${DIR/#$HOME/\~}"
    git clone --depth 1 "$REPO_URL" "$DIR"
fi

# Reattach to the terminal so install.sh can ask before using sudo, even when
# this script itself arrived through a pipe.
if [[ ! -t 0 ]] && { : </dev/tty; } 2>/dev/null; then exec "$DIR/install.sh" "$@" </dev/tty; fi
exec "$DIR/install.sh" "$@"
