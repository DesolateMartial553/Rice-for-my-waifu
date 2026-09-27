-- Window & layer rules.
local cmn = require("wanglin.common")

-- From the stock config: ignore apps asking to maximise themselves.
hl.window_rule({ name = "suppress-maximize", match = { class = ".*" }, suppress_event = "maximize" })

-- From the stock config: XWayland drag fix.
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- Small utility windows float, centred.
hl.window_rule({
    name   = "float-utilities",
    match  = { class = "^(org.pulseaudio.pavucontrol|blueman-manager|nm-connection-editor|nwg-look|qt5ct|qt6ct|kvantummanager|com.gabm.satty|xdg-desktop-portal-gtk)$" },
    float  = true,
    center = true,
    size   = { "(monitor_w*0.6)", "(monitor_h*0.7)" },
})
hl.window_rule({ name = "float-dialogs", match = { title = "^(Open File|Save As|Open Folder|File Upload|Choose Files?)(.*)$" }, float = true, center = true })
hl.window_rule({ name = "pip", match = { title = "^Picture-in-Picture$" }, float = true, pin = true, keep_aspect_ratio = true })

-- Don't let the screen idle-lock during fullscreen video/games.
hl.window_rule({ name = "idle-fullscreen", match = { class = ".*" }, idle_inhibit = "fullscreen" })

-- Layers: frosted bar, launcher, notifications, power menu.
local blur = not cmn.low_motion
hl.layer_rule({ name = "blur-waybar",  match = { namespace = "^waybar$" },  blur = blur, ignore_alpha = 0.3 })
hl.layer_rule({ name = "blur-rofi",    match = { namespace = "^rofi$" },    blur = blur, ignore_alpha = 0.3, dim_around = true })
hl.layer_rule({ name = "blur-swaync",  match = { namespace = "^swaync-(control-center|notification-window)$" }, blur = blur, ignore_alpha = 0.3 })
hl.layer_rule({ name = "wlogout",      match = { namespace = "^logout_dialog$" }, blur = blur })
hl.layer_rule({ name = "blur-popups",  match = { namespace = "^wanglin-popup$" }, blur = blur, ignore_alpha = 0.3 })
hl.layer_rule({ name = "no-anim-shot", match = { namespace = "^(selection|hyprpicker)$" }, no_anim = true })

-- Dropdown terminal (scripts/dropdown, SUPER+ALT+T) lives on special:dropdown.
hl.window_rule({
    name      = "dropdown-terminal",
    match     = { class = "^wanglin-dropdown$" },
    workspace = "special:dropdown silent",
    float     = true,
    size      = { "(monitor_w*0.8)", "(monitor_h*0.55)" },
    move      = { "(monitor_w*0.1)", "(monitor_h*0.07)" },
})
