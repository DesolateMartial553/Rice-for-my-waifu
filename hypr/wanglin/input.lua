-- Input. Keyboard layout is set per computer in ~/.config/hypr/machine.lua.
hl.config({
    input = {
        kb_layout  = "us",
        follow_mouse = 1,
        sensitivity  = 0,
        repeat_rate  = 35,
        repeat_delay = 300,
        touchpad = {
            natural_scroll       = false, -- kept from your previous config
            disable_while_typing = true,
        },
    },
    cursor = {
        hide_on_key_press = true,
    },
    binds = {
        workspace_back_and_forth = true,
    },
})

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
