-- Look & feel: violet qi borders, soft plum shadows, restrained motion.
local c   = require("wanglin.palette")
local cmn = require("wanglin.common")
local low = cmn.low_motion

hl.config({
    general = {
        gaps_in     = 4,
        gaps_out    = { top = 6, right = 10, bottom = 10, left = 10 },
        border_size = 1,
        col = {
            active_border   = { colors = { c.rgba("lavender", 0.95), c.rgba("purple", 0.85) }, angle = 135 },
            inactive_border = c.rgba("overlay", 0.70),
        },
        resize_on_border = true,
        allow_tearing    = false,
        layout           = "dwindle",
    },

    decoration = {
        rounding       = 6,
        rounding_power = 2,
        active_opacity   = 1.0,
        inactive_opacity = 0.96,

        shadow = {
            enabled        = not low,
            range          = 14,
            render_power   = 3,
            color          = c.rgba("purple", 0.28),
            color_inactive = c.rgba("mantle", 0.55),
        },

        -- Blur is cheap-ish on JasperLake with 2 passes; off in low-motion mode.
        blur = {
            enabled   = not low,
            size      = 6,
            passes    = 2,
            noise     = 0.02,
            contrast  = 0.95,
            brightness = 0.85,
            vibrancy  = 0.2,
            popups    = true,
        },
    },

    animations = { enabled = not low },

    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo   = true,
        disable_splash_rendering = true,
        background_color        = c.rgba("base"),
        focus_on_activate       = true,
        -- Laptop: don't render hidden windows at full rate.
        render_unfocused_fps    = 15,
    },

    dwindle = { preserve_split = true },
    master  = { new_status = "master" },

    group = {
        col = {
            border_active   = c.rgba("lavender", 0.9),
            border_inactive = c.rgba("overlay", 0.7),
        },
        groupbar = {
            font_family = "GoogleSansCode Nerd Font Propo",
            font_size   = 10,
            col = {
                active   = c.rgba("purple", 0.9),
                inactive = c.rgba("surface", 0.9),
            },
        },
    },
})

-- Motion: short, eased, no bounce. "Mist" = soft fade/slide.
hl.curve("mist",   { type = "bezier", points = { {0.22, 1}, {0.36, 1} } })
hl.curve("drift",  { type = "bezier", points = { {0.4, 0}, {0.2, 1} } })
hl.curve("linear", { type = "bezier", points = { {0, 0}, {1, 1} } })

hl.animation({ leaf = "global",      enabled = true, speed = 6,   bezier = "mist" })
hl.animation({ leaf = "border",      enabled = true, speed = 6,   bezier = "mist" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 3.5, bezier = "mist",  style = "popin 92%" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 2.5, bezier = "drift", style = "popin 92%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 3.5, bezier = "mist" })
hl.animation({ leaf = "fade",        enabled = true, speed = 3,   bezier = "mist" })
hl.animation({ leaf = "layers",      enabled = true, speed = 3,   bezier = "mist",  style = "fade" })
hl.animation({ leaf = "workspaces",  enabled = true, speed = 3.5, bezier = "mist",  style = "slidefade 12%" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3, bezier = "mist", style = "slidefadevert 10%" })
