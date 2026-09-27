#!/usr/bin/env python3
"""Apply the WangLin KDE colour scheme to kdeglobals and dolphinrc.

Dolphin (and other KDE apps) read colours from ~/.config/kdeglobals, not from
the .colors file, and KDE's colour manager only honours [UiSettings]
ColorScheme. Setting just [General] leaves Breeze light text on a dark theme.

Usage: kde-apply.py SCHEME.colors [CONFIG_DIR]
Merges every Colors:*, ColorEffects:* and WM section from SCHEME into
kdeglobals (other sections and keys are kept), then sets the scheme name,
widget style, icon theme and font.
"""
from pathlib import Path
import sys


def parse(text):
    """Ordered [(section, {key: value})]; keeps KDE keys like 'Name[$e]' verbatim."""
    sections, current = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', ';')):
            continue
        if line.startswith('[') and line.endswith(']'):
            current = (line[1:-1], {})
            sections.append(current)
        elif '=' in line and current is not None:
            key, value = line.split('=', 1)
            current[1][key.strip()] = value.strip()
    return sections


def render(sections):
    return '\n'.join(f'[{name}]\n' + ''.join(f'{k}={v}\n' for k, v in keys.items()) for name, keys in sections)


def update(path, changes, replace=()):
    """changes: {section: {key: value}}; sections in `replace` are overwritten wholesale."""
    sections = parse(path.read_text()) if path.exists() else []
    index = {name: keys for name, keys in sections}
    for name, keys in changes.items():
        if name not in index:
            index[name] = {}
            sections.append((name, index[name]))
        if name in replace:
            index[name].clear()
        index[name].update(keys)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(sections))


def main():
    scheme = Path(sys.argv[1])
    config = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / '.config'
    colours = {name: keys for name, keys in parse(scheme.read_text())
               if name.startswith(('Colors:', 'ColorEffects:')) or name == 'WM'}
    general = dict(parse(scheme.read_text())).get('General', {})
    changes = dict(colours)
    changes['General'] = {'ColorScheme': 'WangLin', 'Name': general.get('Name', 'Wang Lin Purple'),
                          'font': 'GoogleSansCode Nerd Font Propo,10,-1,5,400,0,0,0,0,0',
                          'fixed': 'GoogleSansCode Nerd Font Mono,10,-1,5,400,0,0,0,0,0'}
    changes['KDE'] = {'widgetStyle': 'kvantum'}
    changes['Icons'] = {'Theme': 'Tela-circle-purple-dark'}
    changes['UiSettings'] = {'ColorScheme': 'WangLin'}
    update(config / 'kdeglobals', changes, replace=colours.keys())
    update(config / 'dolphinrc', {'UiSettings': {'ColorScheme': 'WangLin'}})


if __name__ == '__main__':
    main()
