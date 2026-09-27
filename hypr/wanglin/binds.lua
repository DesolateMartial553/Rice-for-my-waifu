-- Keybinds: HyDE layout (HyDE-Project/HyDE key_binds.lua, 2026-09-25), wired to
-- this rice's own tools. A few Wang Lin extras sit on keys HyDE leaves free
-- (marked "extra"). Every bind has a description → SUPER+/ lists them.
-- Previous layout: ~/.local/state/wanglin-rice/hyde-binds-before-20260927-155040/
local cmn = require("wanglin.common")
local s   = cmn.scripts
local run = cmn.run
local mod = "SUPER"

local function bind(keys, dsp, desc, opts)
    opts = opts or {}
    opts.description = desc
    hl.bind(keys, dsp, opts)
end
local function exec(cmd) return hl.dsp.exec_cmd(cmd) end
local lr = { locked = true, repeating = true }

-- Floating windows move by pixels; tiled ones swap places.
local function move_window(dir, px)
    local d = ({ left = { -1, 0 }, right = { 1, 0 }, up = { 0, -1 }, down = { 0, 1 } })[dir]
    return function()
        local w = hl.get_active_window()
        if not w then return end
        hl.dispatch(hl.dsp.window.move(w.floating and { x = d[1] * px, y = d[2] * px, relative = true } or { direction = dir }))
    end
end

-- Shift+F11: windowed → maximised → fullscreen → windowed.
local function cycle_fullscreen()
    local w = hl.get_active_window()
    if not w then return end
    local nxt = ((tonumber(w.fullscreen) or 0) + 1) % 3
    hl.dispatch(hl.dsp.window.fullscreen_state({ internal = nxt, client = nxt, window = w }))
end

-- Alt+Tab: step through open windows (all workspaces) and raise the one picked.
local function alt_tab(step)
    return function()
        local wins = {}
        for _, w in ipairs(hl.get_windows({ mapped = true })) do
            if not w.hidden and w.workspace then wins[#wins + 1] = w end
        end
        if #wins < 2 then return end
        table.sort(wins, function(a, b) return a.stable_id < b.stable_id end)
        local cur = 1
        for i, w in ipairs(wins) do if w.active then cur = i end end
        local target = wins[(cur - 1 + step) % #wins + 1]
        hl.dispatch(hl.dsp.focus({ window = "address:" .. target.address }))
        hl.dispatch(hl.dsp.window.alter_zorder({ mode = "top", window = "address:" .. target.address }))
    end
end

-- ── Window management ─────────────────────────────────────────────────────
bind(mod .. " + Q",            hl.dsp.window.close(),                      "Close focused window")
bind("ALT + F4",               hl.dsp.window.close(),                      "Close focused window")
bind(mod .. " + ALT + F4",     hl.dsp.window.kill(),                       "Kill focused window")
bind(mod .. " + DELETE",       exec(s .. "/logout"),                       "Exit Hyprland session")
bind(mod .. " + W",            hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }), "Fullscreen: cover bar + dock (again to restore)")
bind(mod .. " + G",            hl.dsp.group.toggle(),                      "Toggle group")
bind("ALT + P",                hl.dsp.window.pseudo(),                     "Toggle pseudo-tile")
bind("SHIFT + F11",            cycle_fullscreen,                           "Cycle fullscreen states")
bind(mod .. " + L",            exec(s .. "/lock"),                         "Lock screen")
bind(mod .. " + SHIFT + F",    hl.dsp.window.pin({ action = "toggle" }),   "Pin focused window")
bind("CTRL + ALT + DELETE",    exec(s .. "/popup power 99999"),             "Logout / power menu")
bind(mod .. " + CTRL + B",     exec("pkill -SIGUSR1 -x waybar"),           "Hide / show the bar")
bind(mod .. " + J",            hl.dsp.layout("togglesplit"),               "Toggle split")

bind(mod .. " + CTRL + H",     hl.dsp.group.prev(),                        "Previous window in group")
bind(mod .. " + CTRL + L",     hl.dsp.group.next(),                        "Next window in group")

for _, d in ipairs({ "left", "right", "up", "down" }) do
    bind(mod .. " + " .. d, hl.dsp.focus({ direction = d }), "Focus " .. d)
end

bind("ALT + TAB",              alt_tab(1),                                 "Next window (Alt+Tab)")
bind("ALT + SHIFT + TAB",      alt_tab(-1),                                "Previous window (Alt+Tab)")

local step = 30
bind(mod .. " + SHIFT + right", hl.dsp.window.resize({ x = step,  y = 0, relative = true }), "Resize window right", { repeating = true })
bind(mod .. " + SHIFT + left",  hl.dsp.window.resize({ x = -step, y = 0, relative = true }), "Resize window left",  { repeating = true })
bind(mod .. " + SHIFT + up",    hl.dsp.window.resize({ x = 0, y = -step, relative = true }), "Resize window up",    { repeating = true })
bind(mod .. " + SHIFT + down",  hl.dsp.window.resize({ x = 0, y = step,  relative = true }), "Resize window down",  { repeating = true })
for _, d in ipairs({ "left", "right", "up", "down" }) do
    bind(mod .. " + SHIFT + CTRL + " .. d, move_window(d, step), "Move window " .. d, { repeating = true })
end

hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true, description = "Drag window" })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })
hl.bind(mod .. " + Z",         hl.dsp.window.drag(),   { mouse = true, description = "Hold to move window" })
hl.bind(mod .. " + X",         hl.dsp.window.resize(), { mouse = true, description = "Hold to resize window" })

-- ── Launcher: apps ────────────────────────────────────────────────────────
bind(mod .. " + T",            exec(run(cmn.terminal)),                    "Terminal (kitty)")
bind(mod .. " + ALT + T",      exec(s .. "/dropdown"),                     "Dropdown terminal")
bind(mod .. " + E",            exec(run(cmn.fileManager)),                 "File manager (Dolphin)")
bind(mod .. " + C",            exec(run(cmn.editor)),                      "Text editor (Code)")
bind(mod .. " + B",            exec(run(cmn.browser)),                     "Browser (Firefox)")
bind("CTRL + SHIFT + ESCAPE",  exec(run("kitty --class btop -e btop")),    "System monitor (btop)")

-- ── Launcher: menus ───────────────────────────────────────────────────────
bind(mod .. " + A",            exec(s .. "/popup launcher 20"),            "Application finder")
bind(mod .. " + TAB",          exec(s .. "/launcher window"),              "Window switcher")
bind(mod .. " + SHIFT + E",    exec("pkill -x rofi || rofi -show filebrowser"), "File finder")
bind(mod .. " + SLASH",        exec(s .. "/popup keybinds 20"),            "Keybindings hint")
bind(mod .. " + COMMA",        exec(s .. "/emoji"),                        "Emoji picker")
bind(mod .. " + V",            exec(s .. "/clipboard"),                    "Clipboard")
bind(mod .. " + SHIFT + V",    exec(s .. "/clipboard"),                    "Clipboard manager")
bind(mod .. " + SHIFT + K",    exec(s .. "/calc"),                         "Calculator")
bind(mod .. " + SHIFT + SLASH", exec(s .. "/websearch"),                   "Web search")

-- ── Hardware controls (work on the lock screen too; OSD via scripts/osd) ──
bind("F10",                    exec(s .. "/osd volume mute"),      "Mute output",     { locked = true })
bind("F11",                    exec(s .. "/osd volume down"),      "Volume down",     lr)
bind("F12",                    exec(s .. "/osd volume up"),        "Volume up",       lr)
bind("XF86AudioMute",          exec(s .. "/osd volume mute"),      "Mute output",     { locked = true })
bind("XF86AudioMicMute",       exec(s .. "/osd mic mute"),         "Mute microphone", { locked = true })
bind("XF86AudioLowerVolume",   exec(s .. "/osd volume down"),      "Volume down",     lr)
bind("XF86AudioRaiseVolume",   exec(s .. "/osd volume up"),        "Volume up",       lr)
bind("XF86AudioPlay",          exec("playerctl play-pause"),       "Play / pause",    { locked = true })
bind("XF86AudioPause",         exec("playerctl play-pause"),       "Play / pause",    { locked = true })
bind("XF86AudioNext",          exec("playerctl next"),             "Next track",      { locked = true })
bind("XF86AudioPrev",          exec("playerctl previous"),         "Previous track",  { locked = true })
bind(mod .. " + CTRL + M",     exec(s .. "/mute-window"),          "Mute focused window")
bind("XF86MonBrightnessUp",    exec(s .. "/osd brightness up"),    "Brightness up",   lr)
bind("XF86MonBrightnessDown",  exec(s .. "/osd brightness down"),  "Brightness down", lr)

-- ── Utilities ─────────────────────────────────────────────────────────────
bind(mod .. " + K",            exec("hyprctl switchxkblayout all next"), "Switch keyboard layout", { locked = true })
bind(mod .. " + ALT + G",      exec(s .. "/low-motion"),                 "Game mode (low motion: no animations/blur)")
bind(mod .. " + SHIFT + P",    exec("hyprpicker -an"),                   "Colour picker → clipboard")
bind(mod .. " + P",            exec(s .. "/screenshot region"),          "Screenshot region")
bind(mod .. " + CTRL + P",     exec(s .. "/screenshot freeze"),          "Freeze screen and snip")
bind(mod .. " + ALT + P",      exec(s .. "/screenshot monitor"),         "Screenshot monitor")
bind("Print",                  exec(s .. "/screenshot screen"),          "Screenshot all monitors")

-- ── Theming & wallpaper ───────────────────────────────────────────────────
bind(mod .. " + ALT + right",  exec(s .. "/wallpaper-cycle next"),       "Next wallpaper")
bind(mod .. " + ALT + left",   exec(s .. "/wallpaper-cycle prev"),       "Previous wallpaper")
bind(mod .. " + SHIFT + W",    exec(s .. "/wallpaper-cycle select"),     "Select a wallpaper")

-- ── Workspaces ────────────────────────────────────────────────────────────
local kp = { { "KP_1", "KP_End" }, { "KP_2", "KP_Down" }, { "KP_3", "KP_Next" }, { "KP_4", "KP_Left" },
             { "KP_5", "KP_Begin" }, { "KP_6", "KP_Right" }, { "KP_7", "KP_Home" }, { "KP_8", "KP_Up" },
             { "KP_9", "KP_Prior" }, { "KP_0", "KP_Insert" } }
for i = 1, 10 do
    local key = i % 10
    bind(mod .. " + " .. key,         hl.dsp.focus({ workspace = i }),                      "Go to workspace " .. i)
    bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }),                "Move window to workspace " .. i)
    bind(mod .. " + ALT + " .. key,   hl.dsp.window.move({ workspace = i, follow = false }), "Move window to workspace " .. i .. " (silent)")
    for _, k in ipairs(kp[i]) do
        bind(mod .. " + " .. k,         hl.dsp.focus({ workspace = tostring(i + 10) }),       "Go to workspace " .. (i + 10))
        bind(mod .. " + SHIFT + " .. k, hl.dsp.window.move({ workspace = tostring(i + 10) }), "Move window to workspace " .. (i + 10))
    end
end
bind(mod .. " + CTRL + right",       hl.dsp.focus({ workspace = "r+1" }),       "Next workspace")
bind(mod .. " + CTRL + left",        hl.dsp.focus({ workspace = "r-1" }),       "Previous workspace")
bind(mod .. " + CTRL + down",        hl.dsp.focus({ workspace = "empty" }),     "Nearest empty workspace")
bind(mod .. " + CTRL + ALT + right", hl.dsp.window.move({ workspace = "r+1" }), "Move window to next workspace")
bind(mod .. " + CTRL + ALT + left",  hl.dsp.window.move({ workspace = "r-1" }), "Move window to previous workspace")
bind(mod .. " + mouse_down",         hl.dsp.focus({ workspace = "e+1" }),       "Next workspace")
bind(mod .. " + mouse_up",           hl.dsp.focus({ workspace = "e-1" }),       "Previous workspace")

bind(mod .. " + S",           hl.dsp.workspace.toggle_special("magic"),                               "Toggle scratchpad")
bind(mod .. " + SHIFT + S",   hl.dsp.window.move({ workspace = "special:magic" }),                    "Move window to scratchpad")
bind(mod .. " + ALT + S",     hl.dsp.window.move({ workspace = "special:magic", follow = false }),    "Move window to scratchpad (silent)")

-- ── Wang Lin extras (keys HyDE leaves free) ───────────────────────────────
bind(mod .. " + SPACE",       exec(s .. "/popup launcher 20"),  "Application finder (extra)")
bind(mod .. " + F",           hl.dsp.window.float({ action = "toggle" }), "Toggle floating")
bind(mod .. " + ESCAPE",      exec(s .. "/popup power 99999"),   "Power menu (extra)")
bind(mod .. " + N",           exec("swaync-client -t -sw"),     "Notification centre (extra)")
bind(mod .. " + SHIFT + N",   exec("swaync-client -d -sw"),     "Toggle do-not-disturb (extra)")
bind(mod .. " + SHIFT + B",   exec(s .. "/bar restart"),        "Restart the bar (extra)")
bind(mod .. " + PRINT",       exec(s .. "/screenshot edit"),    "Screenshot → annotate (extra)")
