-- Reference windows are opt-in (SUPER+SHIFT+D); ordinary apps still tile.
local cmn = require('wanglin.common')
hl.window_rule({ name = 'reference-terminal', match = { class = '^wanglin-fetch$' }, float = true, workspace = "5", size = {484,280}, move = {15,94} })
hl.window_rule({ name = 'reference-gallery', match = { class = '^wanglin-gallery$' }, float = true, workspace = "5", size = {484,226}, move = {15,390} })
hl.layer_rule({ name = 'reference-glass', match = { namespace = '^wanglin-(widgets|dock)$' }, blur = true, ignore_alpha = 0.3 })
hl.bind('SUPER + SHIFT + D', hl.dsp.exec_cmd(cmn.scripts .. '/showcase'), { description = 'Open reference desktop on workspace 5' })
