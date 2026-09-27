-- Autostart. Already handled elsewhere on this machine (not duplicated):
--   swaync        → systemd user service (swaync.service)
--   nm-applet, blueman-applet, polkit-kde agent → XDG autostart via uwsm
local cmn = require("wanglin.common")
local s   = cmn.scripts

hl.on("hyprland.start", function()
    hl.exec_cmd(s .. "/wallpaper")
    hl.exec_cmd(s .. "/bar")
    hl.exec_cmd(s .. "/desktop")
    hl.exec_cmd(s .. "/popup --daemon")
    hl.exec_cmd(s .. "/welcome")
    hl.exec_cmd(cmn.run("hypridle"))
    hl.exec_cmd(cmn.run("wl-paste --type text --watch cliphist store"))
    hl.exec_cmd(cmn.run("wl-paste --type image --watch cliphist store"))
end)
