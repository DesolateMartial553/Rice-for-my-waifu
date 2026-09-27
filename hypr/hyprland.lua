-- ╭──────────────────────────────────────────────────────────╮
-- │  王林 · Wang Lin — Hyprland (Lua config, Hyprland ≥ 0.55)  │
-- │  Repo: ~/wanglin-rice   (symlinked by install.sh)          │
-- ╰──────────────────────────────────────────────────────────╯
-- Modules live in ~/.config/hypr/wanglin/. Per-computer settings (screen
-- scale, keyboard layout) are in ~/.config/hypr/machine.lua, written by
-- install.sh. Your own extra tweaks go in ~/.config/hypr/local.lua.

require("wanglin.env")
require("wanglin.monitors")
require("wanglin.look")
require("wanglin.input")
require("wanglin.autostart")
require("wanglin.binds")
require("wanglin.rules")
require("wanglin.reference")

local home = os.getenv("HOME") or ""
-- Loaded by full path: require() would search next to the symlink's target.
for _, name in ipairs({ "machine", "local" }) do
    local path = home .. "/.config/hypr/" .. name .. ".lua"
    local f = io.open(path, "r")
    if f then
        f:close()
        dofile(path)
    end
end
