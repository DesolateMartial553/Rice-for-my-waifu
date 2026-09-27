-- Screens: preferred mode, automatic scale. The built-in screen's scale is set
-- per computer in ~/.config/hypr/machine.lua (install.sh picks one so the
-- desktop is about 1280–1500 px wide, which the rice is sized for).
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})
