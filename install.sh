#!/usr/bin/env bash
# 王林 · Wang Lin — Hyprland rice installer for Arch Linux.
# Written for people new to Arch: every step says what it does and asks first.
#
#   ./install.sh             guided install (recommended)
#   ./install.sh --yes       accept every recommended answer (no questions)
#   ./install.sh --dry-run   show what would change, touch nothing
#   ./install.sh --no-deps   skip installing programs
#   ./install.sh --apply     also reload an already-running Hyprland session
#
# Only installing programs and enabling system services use sudo; everything
# else stays in your home folder. Anything replaced is backed up to
# ~/.local/state/wanglin-rice/backups/<time>/ and ./uninstall.sh puts it back.
# Safe to run again at any time: finished steps are skipped.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/wanglin-rice"
MANIFEST="$STATE/manifest.tsv"      # links:  target <TAB> backup|NONE
EDITS="$STATE/edits.tsv"            # edited files: target <TAB> backup|NONE
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$STATE/backups/$STAMP"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
LOG="$STATE/install-$STAMP.log"
DRY=0 APPLY=0 DEPS=1 YES=0
for a in "$@"; do
    case "$a" in
        --dry-run) DRY=1 ;;
        --apply)   APPLY=1 ;;
        --no-deps) DEPS=0 ;;
        --yes|-y)  YES=1 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) echo "Unknown option: $a   (try ./install.sh --help)" >&2; exit 2 ;;
    esac
done

# ── look & feel ──────────────────────────────────────────────────────────
P=$'\033[38;2;184;138;245m' D=$'\033[38;2;154;143;176m' G=$'\033[38;2;155;217;180m'
Y=$'\033[38;2;233;201;138m' R=$'\033[38;2;240;121;155m' B=$'\033[1m' N=$'\033[0m'
TOTAL=5 CURRENT=0 STEP_NAME="starting"
step() { CURRENT=$((CURRENT + 1)); STEP_NAME=$1; printf '\n%s━━ Step %d of %d · %s%s\n' "$P$B" "$CURRENT" "$TOTAL" "$1" "$N"; shift; for l in "$@"; do printf '   %s%s%s\n' "$D" "$l" "$N"; done; }
say()  { printf '   %s•%s %s\n' "$P" "$N" "$*"; }
ok()   { printf '   %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '   %s!%s %s\n' "$Y" "$N" "$*"; }
run()  { if ((DRY)); then printf '     %swould run:%s %s\n' "$D" "$N" "$*"; else "$@"; fi; }
# ask "question" → yes unless she types n.   ask_no "question" → no unless she types y.
ask()    { ((YES)) && return 0; [[ -t 0 ]] || return 0; local r; read -rp "   ${P}?${N} $1 ${D}[Y/n]${N} " r; [[ ${r,,} != n* ]]; }
ask_no() { ((YES)) && return 1; [[ -t 0 ]] || return 1; local r; read -rp "   ${P}?${N} $1 ${D}[y/N]${N} " r; [[ ${r,,} == y* ]]; }
pause()  { ((YES)) || [[ ! -t 0 ]] || read -rp "   ${D}Press Enter to continue…${N} " _; }

mkdir -p "$STATE"
((DRY)) || exec > >(tee -a "$LOG") 2>&1     # keep a copy of everything for troubleshooting
on_error() {
    printf '\n%s%s✗ Something went wrong during "%s".%s\n' "$R" "$B" "$STEP_NAME" "$N"
    printf '   Nothing is broken: your old settings are backed up and it is safe to run\n'
    printf '   %s./install.sh%s again. If it fails the same way, send this file to whoever\n' "$B" "$N"
    printf '   set this up for you:  %s%s%s\n\n' "$B" "${LOG/#$HOME/\~}" "$N"
}
trap on_error ERR

[[ $EUID -ne 0 ]] || { echo "Please run this as your normal user, not as root or with sudo."; exit 1; }

cat <<EOF

${P}${B}      王林 · 仙逆      Wang Lin desktop for Arch Linux${N}

   This sets up a purple, Renegade Immortal–themed desktop: top bar, dock,
   app launcher, lock screen, wallpapers and matching colours for your apps.

   ${B}What will happen${N}
     1. Check your computer is ready
     2. Install the programs the desktop needs (asks for your password)
     3. Set your screen size and keyboard layout
     4. Put the desktop's settings in place (your old ones are backed up)
     5. Double-check everything works

   It takes about 5–15 minutes, depending on your internet.
   You can stop at any question by pressing ${B}Ctrl+C${N}, nothing is half-done.
EOF
((DRY)) && printf '\n   %sDry run: nothing will actually change.%s\n' "$Y" "$N"
echo
ask "Ready to start?" || { echo "   No problem, run ./install.sh whenever you're ready."; exit 0; }

# ── 1. checks ────────────────────────────────────────────────────────────
step "Checking your computer" "Making sure this is Arch, you're online, and there's room."
command -v pacman >/dev/null || { warn "This isn't Arch Linux (no 'pacman'), so the installer can't continue."; exit 1; }
ok "Arch Linux"
if curl -fsI --max-time 10 https://archlinux.org >/dev/null 2>&1; then ok "Internet connection"
else warn "Can't reach the internet. Connect to Wi-Fi first (on a fresh Arch install: ${B}nmtui${N}) and run this again."; exit 1; fi
free_gb=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
if ((free_gb < 2)); then warn "Only ${free_gb} GB free on your disk; at least 2 GB is needed. Free some space first."; exit 1
elif ((free_gb < 4)); then
    warn "Only ${free_gb} GB free on your disk. A fresh install needs about 4 GB (less if you already have most programs)."
    ask "Continue anyway?" || exit 0
else ok "${free_gb} GB free disk space"; fi
if [[ -e /var/lib/pacman/db.lck ]]; then
    warn "Another install or update is running (or one crashed earlier)."
    warn "Wait for it to finish, then run this again. If nothing is running, reboot and try again."
    exit 1
fi
if grep -qs 0x10de /sys/bus/pci/devices/*/vendor; then
    warn "You have an ${B}NVIDIA${N} graphics card. Hyprland needs NVIDIA's driver set up first:"
    warn "https://wiki.hyprland.org/Nvidia/  (skip if you already did this)"
    ask "Continue anyway?" || exit 0
fi
if ((DEPS && !DRY)); then
    say "Some steps need administrator rights. When asked for ${B}your password${N}, type it and press Enter."
    say "${D}Nothing appears on screen while you type the password; that's normal.${N}"
    if ! sudo -v; then
        warn "Your account isn't allowed to use sudo. Ask for help adding it to the ${B}wheel${N} group:"
        warn "https://wiki.archlinux.org/title/Sudo#Example_entries"
        exit 1
    fi
    ok "Administrator access"
    # Keep sudo alive during the long install so she isn't asked again mid-way.
    while true; do sudo -n true 2>/dev/null; sleep 50; kill -0 "$$" 2>/dev/null || exit; done &
    SUDO_KEEPALIVE=$!
    trap 'kill ${SUDO_KEEPALIVE:-0} 2>/dev/null || true' EXIT
fi

# ── 2. programs ──────────────────────────────────────────────────────────
PKGS=(
    # compositor & session
    hyprland hyprlock hypridle hyprpicker hyprsunset uwsm xdg-desktop-portal-hyprland xdg-desktop-portal-gtk polkit-kde-agent
    # bar, launcher, notifications, wallpaper, terminal
    waybar rofi swaync awww kitty fastfetch btop
    # panels (GTK layer-shell + Python)
    python python-gobject python-cairo gtk3 gtk-layer-shell librsvg playerctl
    # screenshots & clipboard
    grim slurp satty wl-clipboard cliphist
    # audio, network, bluetooth, power, brightness
    pipewire pipewire-pulse wireplumber pavucontrol sof-firmware alsa-ucm-conf networkmanager network-manager-applet nm-connection-editor
    bluez bluez-utils blueman power-profiles-daemon upower brightnessctl
    # tools used by scripts
    jq imagemagick libnotify libqalculate psmisc xdg-user-dirs xdg-utils git curl
    # theming & fonts
    qt5ct qt6ct kvantum nwg-look ttf-googlesanscode-nerd noto-fonts noto-fonts-cjk noto-fonts-emoji
    # apps on the dock / shortcuts
    dolphin firefox code
)
step "Installing programs" \
     "Arch installs everything together with a full system update, so this may" \
     "also update programs you already have. That's normal and keeps things working."
if ((DEPS)); then
    mapfile -t need < <(pacman -T "${PKGS[@]}" 2>/dev/null || true)
    if ((${#need[@]})); then
        say "${#need[@]} programs to install: ${D}${need[*]}${N}"
        if ((DRY)); then
            printf '     %swould run:%s sudo pacman -Syu --needed --noconfirm %s\n' "$D" "$N" "${need[*]}"
        elif ask "Install them now (plus any waiting updates)?"; then
            sudo pacman -Syu --needed --noconfirm "${need[@]}"
            ok "Programs installed"
        else
            warn "Skipped. The desktop won't work properly until these are installed (run this again)."
        fi
    else
        ok "Everything needed is already installed"
    fi

    # Icon theme: from its authors, into your home folder (no extra tools needed).
    if [[ -d /usr/share/icons/Tela-circle-purple-dark || -d $HOME/.local/share/icons/Tela-circle-purple-dark ]]; then
        ok "Purple icon theme"
    elif ((DRY)); then
        printf '     %swould run:%s download Tela-circle purple icons to ~/.local/share/icons\n' "$D" "$N"
    else
        say "Downloading the purple icon theme…"
        tmp=$(mktemp -d)
        if git clone -q --depth 1 https://github.com/vinceliuice/Tela-circle-icon-theme.git "$tmp/tela" &&
           "$tmp/tela/install.sh" -d "$HOME/.local/share/icons" purple >/dev/null 2>&1; then ok "Purple icon theme"
        else warn "Icon theme download failed; apps will show plain icons until you run this again."; fi
        rm -rf "$tmp"
    fi

    # Services the desktop's panels talk to.
    svc=()
    for s in NetworkManager.service bluetooth.service power-profiles-daemon.service; do
        systemctl list-unit-files "$s" >/dev/null 2>&1 && ! systemctl is-enabled -q "$s" 2>/dev/null && svc+=("$s")
    done
    if [[ " ${svc[*]} " == *" NetworkManager.service "* ]] && systemctl is-active -q iwd.service systemd-networkd.service 2>/dev/null; then
        # She's online through another network tool: switching now could cut her off mid-install.
        svc=("${svc[@]/NetworkManager.service}")
        warn "Your Wi-Fi is run by a different tool than the desktop's Wi-Fi menu expects."
        warn "Everything else works; ask for help switching to NetworkManager later."
    fi
    mapfile -t svc < <(printf '%s\n' "${svc[@]}" | grep . || true)
    if ((${#svc[@]})); then
        say "These background services power Wi-Fi, Bluetooth and battery modes: ${D}${svc[*]}${N}"
        if ((DRY)); then printf '     %swould run:%s sudo systemctl enable --now %s\n' "$D" "$N" "${svc[*]}"
        elif ask "Turn them on?"; then sudo systemctl enable --now "${svc[@]}"; ok "Services on"; fi
    fi

    # Login: an existing login screen (SDDM etc.) is left exactly as it is. With
    # none, offer to start the desktop right after signing in on the text console.
    if systemctl is-enabled -q display-manager.service 2>/dev/null || [[ -e /etc/systemd/system/display-manager.service ]]; then
        ok "Login screen found (left as it is)"
        LOGIN=dm
    else
        say "You sign in on a text screen (there's no graphical login screen)."
        if ((DRY)); then
            printf '     %swould ask:%s start the desktop automatically after text-screen login\n' "$D" "$N"
            LOGIN=tty
        elif ask "Start the desktop automatically after you sign in there?"; then
            if ! grep -q "wanglin-rice autostart" "$HOME/.bash_profile" 2>/dev/null; then
                grep -qs . "$HOME/.bash_profile" || printf '[[ -f ~/.bashrc ]] && . ~/.bashrc\n' > "$HOME/.bash_profile"
                cat >> "$HOME/.bash_profile" <<'EOF2'

# >>> wanglin-rice autostart >>>
# Start Hyprland after logging in on the first text console.
if uwsm check may-start 2>/dev/null; then exec uwsm start hyprland.desktop; fi
# <<< wanglin-rice autostart <<<
EOF2
            fi
            ok "The desktop will start after you sign in on the text screen."
            LOGIN=tty
        else
            LOGIN=manual
        fi
    fi
else
    say "Skipped (--no-deps)."
    LOGIN=unknown
fi

# ── 3. screen & keyboard ─────────────────────────────────────────────────
step "Screen size and keyboard" "So text is a comfortable size and the keys type what's printed on them."
MACHINE="$CFG/hypr/machine.lua"
if [[ -f $MACHINE ]]; then
    ok "Already set ${D}(${MACHINE/#$HOME/\~}: edit it any time)${N}"
else
    read -r kb _variant panel mode scale < <("$REPO/tools/detect-machine.sh" --probe)
    say "Keyboard layout: ${B}$kb${N}  ${D}(us = American, gb = British, de = German, fr = French…)${N}"
    if ((!YES)) && [[ -t 0 ]]; then
        while :; do
            read -rp "   ${P}?${N} Press Enter to keep ${B}$kb${N}, or type another layout: " ans
            [[ -z $ans ]] && break
            if localectl list-x11-keymap-layouts 2>/dev/null | grep -qx "$ans"; then kb=$ans; break; fi
            warn "\"$ans\" isn't a layout name. Examples: us, gb, de, fr, es, it."
        done
    fi
    if [[ $panel != - ]]; then
        say "Built-in screen: ${B}$mode${N} → size ${B}${scale}×${N}  ${D}(bigger number = bigger text and icons)${N}"
        if ((!YES)) && [[ -t 0 ]]; then
            while :; do
                read -rp "   ${P}?${N} Press Enter to keep ${B}$scale${N}, or type 1, 1.25, 1.5, 2: " ans
                [[ -z $ans ]] && break
                [[ $ans =~ ^(1|1\.25|1\.5|1\.75|2|2\.5|3)$ ]] && { scale=$ans; break; }
                warn "Please type one of: 1, 1.25, 1.5, 2"
            done
        fi
    else
        say "No built-in screen found: monitors will use automatic sizing."
        scale=""
    fi
    if ((DRY)); then printf '     %swould write:%s %s\n' "$D" "$N" "${MACHINE/#$HOME/\~}"
    else
        mkdir -p "$(dirname "$MACHINE")"
        "$REPO/tools/detect-machine.sh" "$kb" "$scale" > "$MACHINE"
        printf '%s\t%s\n' "$MACHINE" "NONE" >> "$EDITS"
        ok "Saved ${D}(change later in ${MACHINE/#$HOME/\~})${N}"
    fi
fi

# ── 4. settings ──────────────────────────────────────────────────────────
step "Putting the desktop's settings in place" "Anything already there is backed up first, so nothing is lost."
# target (relative to $HOME)  ->  source (relative to repo)
LINKS=(
    ".local/share/wanglin-rice|."
    ".config/hypr/hyprland.lua|hypr/hyprland.lua"
    ".config/hypr/wanglin|hypr/wanglin"
    ".config/hypr/hyprlock.conf|hypr/hyprlock.conf"
    ".config/hypr/hypridle.conf|hypr/hypridle.conf"
    ".config/hypr/palette.conf|hypr/palette.conf"
    ".config/waybar|waybar"
    ".config/rofi|rofi"
    ".config/swaync|swaync"
    ".config/wlogout|wlogout"
    ".config/kitty/kitty.conf|kitty/kitty.conf"
    ".config/kitty/colors.conf|kitty/colors.conf"
    ".config/gtk-3.0/gtk.css|gtk/gtk.css"
    ".config/gtk-3.0/colors.css|gtk/colors.css"
    ".config/gtk-3.0/settings.ini|gtk/settings.ini"
    ".config/gtk-4.0/gtk.css|gtk/gtk.css"
    ".config/gtk-4.0/colors.css|gtk/colors.css"
    ".config/gtk-4.0/settings.ini|gtk/settings-gtk4.ini"
    ".config/qt5ct/colors/WangLin.conf|qt/WangLin.conf"
    ".config/qt6ct/colors/WangLin.conf|qt/WangLin.conf"
    ".config/Kvantum/WangLin|qt/Kvantum/WangLin"
    ".config/Kvantum/kvantum.kvconfig|qt/Kvantum/kvantum.kvconfig"
    ".local/share/color-schemes/WangLin.colors|qt/Kvantum/WangLin/WangLin.colors"
    ".config/uwsm/env-hyprland|uwsm/env-hyprland"
)
linked=0 backed=0
for entry in "${LINKS[@]}"; do
    tgt="$HOME/${entry%%|*}"
    src="$REPO/${entry#*|}"; src="${src%/.}"
    [[ -e "$src" ]] || { warn "Missing from the download, skipped: ${entry#*|}"; continue; }
    [[ -L "$tgt" && "$(readlink -f "$tgt")" == "$(readlink -f "$src")" ]] && continue   # already ours
    run mkdir -p "$(dirname "$tgt")"
    if [[ -e "$tgt" || -L "$tgt" ]]; then
        bk="$BACKUP/${entry%%|*}"
        run mkdir -p "$(dirname "$bk")"
        run mv "$tgt" "$bk"
        ((DRY)) || printf '%s\t%s\n' "$tgt" "$bk" >> "$MANIFEST"
        backed=$((backed + 1))
    else
        ((DRY)) || printf '%s\t%s\n' "$tgt" "NONE" >> "$MANIFEST"
    fi
    run ln -s "$src" "$tgt"
    linked=$((linked + 1))
done
if ((linked)); then
    extra=""; ((backed)) && extra=", $backed old ones backed up to ${BACKUP/#$HOME/\~}"
    ok "Desktop settings linked ($linked)$extra"
else ok "Desktop settings already in place"; fi

# edit TARGET: back up TARGET (first time only) so uninstall.sh can put it back.
edit() {
    local tgt=$1 rel=${1#$HOME/}
    grep -qF "$tgt"$'\t' "$EDITS" 2>/dev/null && return 0
    if [[ -e $tgt || -L $tgt ]]; then
        run mkdir -p "$(dirname "$BACKUP/$rel")"
        run cp -P "$tgt" "$BACKUP/$rel"
        ((DRY)) || printf '%s\t%s\n' "$tgt" "$BACKUP/$rel" >> "$EDITS"
    else
        ((DRY)) || printf '%s\t%s\n' "$tgt" "NONE" >> "$EDITS"
    fi
}
# Qt apps: qt5ct/qt6ct only accept an absolute colour-scheme path, so render per user.
for v in 5 6; do
    tgt="$CFG/qt${v}ct/qt${v}ct.conf"
    want=$(sed "s|@HOME@|$HOME|g" "$REPO/qt/qt${v}ct.conf.in")
    if [[ -L $tgt || ! -f $tgt || "$(cat "$tgt")" != "$want" ]]; then
        edit "$tgt"
        ((DRY)) || { rm -f "$tgt"; mkdir -p "$(dirname "$tgt")"; printf '%s\n' "$want" > "$tgt"; }
    fi
done
# Dolphin & other KDE apps read their colours from kdeglobals + dolphinrc.
edit "$CFG/kdeglobals"; edit "$CFG/dolphinrc"
((DRY)) || python "$REPO/tools/kde-apply.py" "$REPO/qt/Kvantum/WangLin/WangLin.colors" "$CFG"
ok "Purple colours for Dolphin and other apps"
# Terminal: purple prompt + system info when a terminal opens.
if ! grep -q "wanglin-rice/kitty/shell-startup.bash" "$HOME/.bashrc" 2>/dev/null; then
    edit "$HOME/.bashrc"
    ((DRY)) || cat >> "$HOME/.bashrc" <<'EOF'

# >>> wanglin-rice >>>
PS1='\[\e[38;2;184;138;245m\]╭─\u@\h \[\e[38;2;154;143;176m\]\w\n\[\e[38;2;184;138;245m\]╰─❯ \[\e[0m\]'
source "$HOME/.local/share/wanglin-rice/kitty/shell-startup.bash"
# <<< wanglin-rice <<<
EOF
fi
ok "Terminal prompt"
pics=$(xdg-user-dir PICTURES 2>/dev/null || true); [[ -z $pics || $pics == "$HOME" ]] && pics="$HOME/Pictures"
run mkdir -p "$pics/Screenshots"
# GTK apps (Firefox dialogs, settings windows…); originals saved once for uninstall.
if command -v gsettings >/dev/null; then
    GS="$STATE/gsettings.orig"
    if [[ ! -f "$GS" ]] && ((!DRY)); then
        for k in gtk-theme icon-theme cursor-theme cursor-size font-name color-scheme; do
            printf '%s\t%s\n' "$k" "$(gsettings get org.gnome.desktop.interface "$k" 2>/dev/null)" >> "$GS"
        done
    fi
    run gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark' 2>/dev/null || true
    run gsettings set org.gnome.desktop.interface icon-theme 'Tela-circle-purple-dark' 2>/dev/null || true
    run gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita' 2>/dev/null || true
    run gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true
    run gsettings set org.gnome.desktop.interface font-name 'GoogleSansCode Nerd Font Propo 10' 2>/dev/null || true
    run gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
fi
if command -v rsvg-convert >/dev/null; then
    if ((DRY)); then printf '     %swould run:%s tools/rofi-icons.sh\n' "$D" "$N"
    else "$REPO/tools/rofi-icons.sh" >/dev/null 2>&1 || warn "App-launcher icons couldn't be prepared (harmless)."; fi
fi
ok "App themes and icons"
# Renegade Immortal wallpapers: fetched from Wallhaven (not stored in the repo).
if ((DRY)); then printf '     %swould run:%s tools/fetch-wallpapers.sh\n' "$D" "$N"
elif "$REPO/tools/fetch-wallpapers.sh" >/dev/null 2>&1; then ok "Renegade Immortal wallpapers"
else warn "Some wallpapers couldn't be downloaded (the main one still works). Run this again later to retry."; fi

# ── 5. check ─────────────────────────────────────────────────────────────
step "Double-checking" "Making sure the desktop's settings load without errors."
problems=0
for bin in Hyprland waybar rofi swaync awww kitty python; do
    command -v "$bin" >/dev/null || { warn "Missing program: $bin"; problems=1; }
done
if command -v Hyprland >/dev/null; then
    hv=$(Hyprland --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ -n $hv ]] && (( $(cut -d. -f1 <<<"$hv") == 0 && $(cut -d. -f2 <<<"$hv") < 55 )); then
        warn "Hyprland $hv is too old for this desktop (needs 0.55 or newer). Update your system and run this again."
        problems=1
    fi
fi
python -c 'import gi; gi.require_version("GtkLayerShell","0.1"); from gi.repository import GtkLayerShell' 2>/dev/null ||
    { warn "The top-bar menus can't start (python gtk-layer-shell missing)."; problems=1; }
if ((!DRY)) && command -v Hyprland >/dev/null; then
    if out=$(Hyprland --verify-config -c "$CFG/hypr/hyprland.lua" 2>&1 | grep -v DEBUG) && grep -q "config ok" <<<"$out"; then
        ok "Desktop settings load correctly"
    else
        warn "Hyprland reported a problem with its settings:"; echo "$out" | tail -8 | sed 's/^/     /'
        problems=1
    fi
fi
((problems)) && warn "Run ${B}./install.sh${N} again after fixing the items above (it's safe to repeat)."

# ── done ─────────────────────────────────────────────────────────────────
trap - ERR
if ((APPLY && !DRY)) && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    hyprctl reload >/dev/null
    "$REPO/scripts/wallpaper" || true
    setsid -f "$REPO/scripts/bar" restart >/dev/null 2>&1 </dev/null
    setsid -f "$REPO/scripts/desktop" restart >/dev/null 2>&1 </dev/null
    "$REPO/scripts/popup" --daemon || true
    systemctl --user restart swaync.service 2>/dev/null || true
    ok "Reloaded into the running desktop"
fi

case ${LOGIN:-unknown} in
    dm)     start="Restart the computer and pick ${B}Hyprland (uwsm-managed)${N} on the login screen." ;;
    tty)    start="Restart the computer and log in on the text screen: the desktop starts by itself." ;;
    manual) start="After logging in on the text screen, type ${B}uwsm start hyprland.desktop${N} and press Enter." ;;
    *)      start="Log out and pick ${B}Hyprland (uwsm-managed)${N} on the login screen, or run ${B}uwsm start hyprland.desktop${N}." ;;
esac
cat <<EOF

${P}${B}━━ All done! 完成 ━━${N}

   ${B}To start:${N} $start

   ${B}The keys you'll use most${N}  ${D}(Super = the Windows key)${N}
     Super + A      open an app          Super + Q      close a window
     Super + T      terminal             Super + W      full screen
     Super + B      web browser          Super + 1…5    switch desktops
     Super + E      files                Super + L      lock the screen
     Super + /      every shortcut, searchable
   Click the icons on the top bar for Wi-Fi, sound, battery, calendar and power.
   A welcome note with these keys also pops up the first time you log in.

   ${D}Undo everything: ./uninstall.sh      Update later: run ./get.sh or git pull, then ./install.sh
   Install log: ${LOG/#$HOME/\~}${N}

EOF
if ((!DRY)) && [[ ${LOGIN:-} == dm || ${LOGIN:-} == tty ]] && [[ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    ask_no "Restart the computer now?" && systemctl reboot
fi
exit 0
