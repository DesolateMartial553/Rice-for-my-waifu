# 王林 · Wang Lin rice — technical notes

The friendly guide is [README.md](README.md). This file is for tinkering: palette,
keybind reference, file layout and how things were built and checked.

Dark xianxia desktop for Arch + Hyprland ≥ 0.55 (Lua config), inspired by Wang Lin
from *Renegade Immortal* (仙逆): near-black plum, violet qi, moonlit mist, restrained
silver. Developed on a 1920×1080 laptop at 1.5× scale (1280×720 logical) with uwsm + SDDM.

## Palette

One source of truth: `palette.json` → `./tools/gen-palette.py` writes every
component's colour file (Lua, GTK CSS, rasi, hyprlang, kitty, qt5ct/qt6ct).

| Role | Hex | Use | Contrast on base |
|---|---|---|---|
| base | `#100B18` | backgrounds | — |
| mantle | `#0B0712` | deepest panels, views | — |
| surface | `#1A1226` | cards, inputs, popovers | — |
| deep | `#251538` | module pills, hover | — |
| overlay | `#3A2656` | inactive borders, troughs | — |
| purple | `#6E40A1` | borders, fills, selection bg — **never text** (2.7:1) | 2.7 |
| lavender | `#B88AF5` | accent text/icons, active border | 7.4 |
| silver | `#C9C4D4` | secondary text | 11.4 |
| muted | `#9A8FB0` | tertiary text, placeholders | 6.4 |
| text | `#F2ECFA` | primary text | 16.8 |
| red / yellow / green / cyan | `#F0799B` `#E9C98A` `#9BD9B4` `#8FCFE0` | urgent, warning, charging, terminal | ≥ 7.3 |

Typography: **GoogleSansCode Nerd Font** (Propo for UI, Mono for terminal) — already
installed, carries all icon glyphs. Chinese accents use Noto CJK when present and fall
back to romanised text when it isn't, so nothing renders as tofu.

## Install

Arch Linux (or an Arch-based distro) with Hyprland ≥ 0.55, which uses the Lua config.

One command (downloads to `~/wanglin-rice`, then runs the installer):

```sh
bash <(curl -fsSL https://raw.githubusercontent.com/DesolateMartial553/Rice-for-my-waifu/main/get.sh)
```

Run it again later to update. Or do it by hand:

```sh
git clone https://github.com/DesolateMartial553/Rice-for-my-waifu.git ~/wanglin-rice
cd ~/wanglin-rice
./install.sh
```

Then pick **Hyprland (uwsm-managed)** in your login manager, or run
`uwsm start hyprland.desktop` from a TTY. Already inside Hyprland? Run `./install.sh --apply`.

The installer is written for people new to Arch. It explains each of its 5 steps,
asks before doing anything, and keeps a log in `~/.local/state/wanglin-rice/`:

1. **Checks** that this is Arch, you're online, there's disk space, and you can use `sudo`
   (warns about NVIDIA cards, which need their driver set up first).
2. **Programs:** installs what's missing together with a full system update
   (`pacman -Syu`), the purple icon theme, and turns on Wi-Fi/Bluetooth/power services.
   An existing login screen is never touched; without one, it offers to start the
   desktop straight after a text-console login.
3. **Screen & keyboard:** detects the built-in screen and keyboard layout, lets you
   confirm them, and saves them to `~/.config/hypr/machine.lua` (edit it any time).
4. **Settings:** links the rice's configs (old ones backed up), themes Dolphin/Qt/GTK,
   and adds the purple prompt + Fastfetch to `~/.bashrc`.
5. **Double-check:** makes sure Hyprland loads the config, then shows how to start and
   the keys you'll use most. A welcome note with those keys also appears on first login.

| Command | |
|---|---|
| `./install.sh --dry-run` | show every change, touch nothing |
| `./install.sh --no-deps` | skip package installation |
| `./install.sh --yes` | don't ask before installing packages |
| `./install.sh --apply` | also reload the running Hyprland session |
| `./uninstall.sh` | remove links, restore every backed-up file and gsettings |

Re-running is safe; finished steps are skipped. Personal overrides that survive updates:
`~/.config/hypr/local.lua`, `~/.config/kitty/local.conf`. After changing `palette.json`, run
`./tools/gen-palette.py`.

## What's in it

| Component | Tool | Notes |
|---|---|---|
| Compositor | Hyprland (Lua) | modular `hypr/wanglin/*.lua`; gradient lavender→purple border, plum shadows, blur, eased fades |
| Bar | waybar | flush, full-width, 36px. Every icon opens a drop-down panel |
| Bar panels | `popups/popup.py` (GTK layer-shell) | apps · keybinds · sound · Wi-Fi · calendar · quick settings (battery, power profile, brightness, toggles) · power |
| Wallpaper picker | `popups/wallpicker.py` | full-screen, PS4-style row (SUPER+Shift+W) |
| Desktop | `desktop/shell.py` | live media card, CPU/RAM/disk/net graphs, bottom dock |
| Notifications | swaync | lavender accent, OSD for volume/brightness |
| Lock / idle | hyprlock, hypridle | blurred wallpaper, big clock; dim → lock → screen off → suspend |
| Terminal | kitty + Fastfetch | Fastfetch once per new window |
| GTK / Qt | Adwaita-dark + CSS, Kvantum WangLin | Dolphin and KDE apps themed purple; Tela-circle-purple icons |
| Screenshots | grim + slurp + satty | `~/Pictures/Screenshots` + clipboard |

## Keybinds: HyDE layout (SUPER = ⊞). Live list: **SUPER+/**

| Keys | Action |
|---|---|
| SUPER+T · SUPER+Alt+T | terminal · dropdown terminal |
| SUPER+E · SUPER+B · SUPER+C | Dolphin · Firefox · editor |
| SUPER+A / SUPER+Space · SUPER+Tab | apps · window switcher |
| SUPER+Q · Alt+F4 · SUPER+Alt+F4 | close · close · kill |
| SUPER+W · SUPER+G · Alt+P · SUPER+J | fullscreen (covers bar + dock; again restores) · group · pseudo-tile · split |
| SUPER+F · Shift+F11 · SUPER+Shift+F | toggle floating · cycle fullscreen · pin |
| Alt+Tab / Alt+Shift+Tab | cycle windows |
| SUPER+arrows | focus |
| SUPER+Shift+arrows · SUPER+Shift+Ctrl+arrows | resize · move |
| SUPER+drag / SUPER+Z · SUPER+X | move / resize with mouse |
| SUPER+1…0 · SUPER+Shift+1…0 · SUPER+Alt+1…0 | go · move · move silently |
| SUPER+Ctrl+←/→ · SUPER+Ctrl+↓ | prev/next workspace · empty workspace |
| SUPER+S · SUPER+Shift+S · SUPER+Alt+S | scratchpad · send · send silently |
| SUPER+V · SUPER+, · SUPER+Shift+K · SUPER+Shift+/ | clipboard · emoji · calculator · web search |
| SUPER+P · SUPER+Ctrl+P · SUPER+Alt+P · Print | region · frozen region · monitor · all screens |
| SUPER+Shift+P | colour picker |
| SUPER+Alt+←/→ · SUPER+Shift+W | prev/next wallpaper · wallpaper picker |
| SUPER+L · SUPER+Esc · Ctrl+Alt+Del · SUPER+Delete | lock · power · power · exit |
| SUPER+N · SUPER+Shift+N · SUPER+Ctrl+B | notifications · do-not-disturb · hide bar |
| SUPER+Ctrl+M · SUPER+Alt+G · SUPER+K | mute window · game mode · keyboard layout |
| F10 / F11 / F12, media & brightness keys | mute / volume down / up; work on the lock screen too |

## Wallpaper

`wallpapers/wallpaper.png` is the reference artwork reconstructed with the built-in
imagegen tool. The exact edit prompt is saved in `wallpapers/generation-prompt.txt`.
It is linked in `~/Pictures/Wallpapers/Wang-Lin.png`. The original procedural
placeholder is retained as a fallback. `SUPER+Shift+W` reapplies the wallpaper
and regenerates the lock-screen background.

## File tree

```
wanglin-rice/
├── palette.json                 single colour source
├── install.sh · uninstall.sh
├── tools/  gen-palette.py · gen-wallpaper.py · rofi-icons.sh
├── hypr/   hyprland.lua (entry) · hyprlock.conf · hypridle.conf · palette.conf*
│   └── wanglin/  env · monitors · look · input · autostart · binds · rules · common · palette*.lua
├── waybar/ config.jsonc · style.css · colors.css* · scripts/title
├── rofi/   config.rasi · wanglin.rasi · colors.rasi*
├── swaync/ config.json · style.css · colors.css*
├── wlogout/ layout · style.css · colors.css* · icons/ (tinted)
├── kitty/  kitty.conf · colors.conf*
├── gtk/    gtk.css · colors.css* · settings.ini · settings-gtk4.ini
├── qt/     qt5ct.conf · qt6ct.conf · WangLin.conf*
├── uwsm/   env-hyprland
├── scripts/ run · wallpaper · bar · launcher · clipboard · screenshot · osd · lock ·
│            lock-text · logout · powermenu · low-motion · keybinds · lib.sh
└── wallpapers/ wanglin-placeholder.png
                                  (* = generated by tools/gen-palette.py)
```

## Version notes

- **Hyprland 0.55+ uses Lua** (`hyprland.lua`, `hl.*` API); hyprlang is deprecated for
  the compositor. hyprlock/hypridle still use hyprlang. The syntax follows the stubs shipped
  in `/usr/share/hypr/stubs/hl.meta.lua` and the current wiki (dispatchers, window/layer rules).
- `hyprctl dispatch` now takes Lua, e.g. `hyprctl dispatch 'hl.dsp.dpms({ action = "off" })'`.
- The session is uwsm-managed: apps launch through `uwsm app --` (scripts/run), logout
  uses `uwsm stop` as the wiki advises, and env vars for systemd-launched apps live in
  `~/.config/uwsm/env-hyprland`.
- swww was renamed **awww**. swaync 0.12 (GTK4) loads its stock CSS first, and ours only
  overrides its variables.

## Validation (run 2026-09-27 on this machine)

| Check | Result |
|---|---|
| `Hyprland --verify-config` | `config ok`. Also confirmed that it rejects bogus keys, rule fields and dispatcher args, so the pass is meaningful |
| `hyprctl configerrors` after live reload | empty |
| `bash -n` on every script | ok |
| rofi `-dump-theme`, kitty config load | ok |
| waybar live log | fixed: height raised to 32 (modules need 32). Remaining: one wireplumber "invalid source node" message because no default microphone exists (harmless) |
| swaync | loads, CSS reload ok. Fixed: empty media card (blacklisted `playerctld`), OSD piling up in history (now transient) |
| Screenshots inspected at 1920×1080 | bar, rofi, notification centre, wlogout, hyprlock, bare desktop |
| Bugs found in screenshots and fixed | (1) BMP Nerd Font glyphs were stripped from files, so the sigil and workspace icons were blank. Re-inserted by codepoint (`` …). (2) rofi app icons blank because there's no SVG pixbuf loader. Added a PNG icon cache. (3) rofi too transparent over busy windows. Opacity raised |
| Functional | screenshot → file + clipboard ✔; cliphist text + image ✔; low-motion toggles animations + blur ✔; cheat sheet lists 84 binds ✔; lock renders and unlocks ✔ (tested with `--grace` and SIGUSR1) |
| Install idempotency / rollback | second run: "all links already in place"; `uninstall.sh --dry-run` restores `hyprland.lua` + 6 gsettings |

## Known limitations

- Noto Sans CJK SC is now installed per-user; Chinese titles render directly.
- **rofi icons:** Arch's librsvg no longer ships a gdk-pixbuf SVG loader and no repo package
  provides one, so `tools/rofi-icons.sh` pre-renders PNGs into `~/.local/share/icons/WangLin-rofi`.
  Re-run it after installing apps. GTK/Qt apps are unaffected.
- The wallpaper is reconstructed from the reference; hidden portions are approximated.
- Idle timeouts and suspend weren't waited out live. The idle chain was set from the
  hypridle docs and the daemon runs without errors.
- Dolphin now uses the WangLin Kvantum theme and matching KDE colors.
- The cursor stays Adwaita (the only cursor theme installed). For a themed one, install e.g.
  `breeze` or a Bibata theme and change `XCURSOR_THEME` in `hypr/wanglin/env.lua`,
  `uwsm/env-hyprland` and `gtk/settings*.ini`.
- A full logout/login cycle wasn't performed from this session. Everything was reloaded live instead.
