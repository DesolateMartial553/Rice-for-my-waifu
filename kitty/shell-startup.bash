# Sourced from ~/.bashrc after its interactive-shell guard.
# Kitty's process + window IDs distinguish new windows/tabs from nested shells.
if [[ -t 1 && -n ${KITTY_WINDOW_ID:-} ]]; then
    _wanglin_terminal_id="${KITTY_PID:-$PPID}:${KITTY_WINDOW_ID}"
    if [[ ${WANGLIN_FETCH_TERMINAL:-} != "$_wanglin_terminal_id" ]]; then
        export WANGLIN_FETCH_TERMINAL="$_wanglin_terminal_id"
        if command -v fastfetch >/dev/null 2>&1; then
            fastfetch --config "$HOME/.local/share/wanglin-rice/fastfetch/config.jsonc"
        fi
    fi
    unset _wanglin_terminal_id
fi
