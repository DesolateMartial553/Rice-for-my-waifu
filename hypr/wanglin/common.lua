-- Shared paths and helpers for the Wang Lin modules.
local M = {}

M.home    = os.getenv("HOME") or ""
M.share   = M.home .. "/.local/share/wanglin-rice"
M.scripts = M.share .. "/scripts"
M.state   = M.home .. "/.local/state/wanglin-rice"

-- Programs (edit to taste)
M.terminal    = "kitty"
M.fileManager = "dolphin"
M.browser     = "firefox"
M.editor      = "code"

-- Launch through uwsm when the session is uwsm-managed, so apps get
-- their own systemd scope; falls back to plain exec otherwise.
function M.run(cmd)
    return M.scripts .. "/run " .. cmd
end

-- Low-motion mode: toggled by scripts/low-motion (SUPER+SHIFT+A)
local function exists(path)
    local f = io.open(path, "r")
    if f then f:close() return true end
    return false
end
M.low_motion = exists(M.state .. "/low-motion")

return M
