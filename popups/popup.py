#!/usr/bin/env python3
"""Drop-down panels for the Wang Lin bar.

Runs as one resident process (`popup.py --daemon`, started by scripts/popup)
that reads "NAME X" or "close" lines from a FIFO. NAME is launcher, keybinds,
sound, network, calendar, system or power; the panel opens under the bar,
centred on X. The same NAME again closes it; another NAME swaps it in place.
Esc or a click outside closes.
"""
import calendar
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import subprocess
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('Rsvg', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GtkLayerShell, Pango, Rsvg
import cairo
try: from gi.repository import GLibUnix
except ImportError: GLibUnix = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
HOME = Path.home()
STATE = Path(os.environ.get('XDG_STATE_HOME', HOME / '.local/state')) / 'wanglin-rice'
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
FIFO, PIDFILE = RUNTIME / 'wanglin-popup.fifo', RUNTIME / 'wanglin-popup.pid'
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# ── helpers ────────────────────────────────────────────────────────────────

def sh(argv, done=None, timeout=20):
    """Run argv in a worker thread; call done(code, stdout) on the GTK thread."""
    def work():
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout
        except (OSError, subprocess.SubprocessError):
            return 1, ''
    future = POOL.submit(work)
    if done:
        future.add_done_callback(lambda f: GLib.idle_add(lambda: done(*f.result()) and False))

def output(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ''

def detach(argv):
    subprocess.Popen(list(map(str, argv)), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)

def run_app(*argv):
    detach([SCRIPTS / 'run', *argv])

def launch_desktop(app_id):
    detach(['sh', '-c', 'if uwsm check is-active >/dev/null 2>&1; then exec uwsm app -- "$1"; '
            'else exec gtk-launch "$1"; fi', '_', app_id])

def css(widget, *classes):
    ctx = widget.get_style_context()
    for c in classes:
        if c: ctx.add_class(c)
    return widget

def label(text='', *classes, xalign=0.0, ellipsize=False, width=None):
    obj = Gtk.Label(label=text, xalign=xalign)
    if ellipsize: obj.set_ellipsize(Pango.EllipsizeMode.END)
    if width: obj.set_max_width_chars(width); obj.set_width_chars(width)
    return css(obj, *classes)

def box(vertical=False, spacing=0, *classes):
    obj = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)
    return css(obj, *classes)

def button(content, callback=None, *classes, tip=None):
    obj = Gtk.Button()
    obj.add(label(content, xalign=.5) if isinstance(content, str) else content)
    if callback: obj.connect('clicked', lambda _: callback())
    if tip: obj.set_tooltip_text(tip)
    return css(obj, *classes)

def icon_row(icon, text, sub=None, right=None):
    row = box(False, 10)
    row.pack_start(label(icon, 'icon', xalign=.5, width=2), False, False, 0)
    col = box(True, 1)
    col.pack_start(label(text, ellipsize=True), False, False, 0)
    if sub: col.pack_start(label(sub, 'muted', ellipsize=True), False, False, 0)
    row.pack_start(col, True, True, 0)
    if right is not None:
        row.pack_end(right if isinstance(right, Gtk.Widget) else label(right, 'muted', xalign=1), False, False, 0)
    return row

def slider(value, changed, lo=0, hi=100):
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
    scale.set_draw_value(False)
    scale.set_value(value)
    scale.handler = scale.connect('value-changed', lambda s: changed(int(s.get_value())))
    return scale

def set_quietly(scale, value):
    scale.handler_block(scale.handler)
    scale.set_value(value)
    scale.handler_unblock(scale.handler)

def switch(active, toggled):
    obj = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
    obj.handler = obj.connect('notify::active', lambda s, _: toggled(s.get_active()))
    return obj

def scrolled(child, height):
    win = Gtk.ScrolledWindow()
    win.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    win.set_min_content_height(height); win.set_max_content_height(height)
    win.add(child)
    return win

ICON_THEMES = ['Tela-circle-purple-dark', 'Tela-circle-dark', 'Tela-circle', 'hicolor', 'breeze-dark', 'breeze', 'Adwaita']
ICON_BASES = [HOME / '.local/share/icons', Path('/usr/share/icons')]

def find_svg(gicon):
    """gdk-pixbuf here has no SVG loader, so themed SVGs are located by hand."""
    if isinstance(gicon, Gio.FileIcon):
        path = gicon.get_file().get_path()
        return path if path and path.endswith('.svg') else None
    for name in (gicon.get_names() if isinstance(gicon, Gio.ThemedIcon) else []):
        for theme in ICON_THEMES:
            for base in ICON_BASES:
                path = base / theme / 'scalable/apps' / f'{name}.svg'
                if path.exists(): return str(path)
        path = Path('/usr/share/pixmaps') / f'{name}.svg'
        if path.exists(): return str(path)
    return None

def app_image(gicon, size):
    gicon = gicon or Gio.ThemedIcon.new('application-x-executable')
    path = find_svg(gicon)
    if path:
        try:
            px = size * 2
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, px, px)
            rect = Rsvg.Rectangle(); rect.x = rect.y = 0; rect.width = rect.height = px
            Rsvg.Handle.new_from_file(path).render_document(cairo.Context(surf), rect)
            surf.set_device_scale(2, 2)
            return Gtk.Image.new_from_surface(surf)
        except GLib.Error:
            pass
    image = Gtk.Image.new_from_gicon(gicon, Gtk.IconSize.DIALOG)
    image.set_pixel_size(size)
    return image

def clear(container):
    for child in container.get_children(): container.remove(child)

# ── panels ─────────────────────────────────────────────────────────────────

class Panel:
    icon, title, han, width = '', '', '', 320

    def __init__(self, popup):
        self.popup = popup
        self.alive = True
        self.body = box(True, 8)

    def header(self, right=None):
        head = box(False, 10, 'header')
        head.pack_start(label(self.icon, 'header-icon', xalign=.5), False, False, 0)
        head.pack_start(label(self.title, 'header-title'), False, False, 0)
        head.pack_start(label(self.han, 'header-han'), False, False, 0)
        if right: head.pack_end(right, False, False, 0)
        return head

    def close(self): self.popup.close()
    def key(self, event): return False


class Launcher(Panel):
    icon, title, han, width = '', 'Apps', '法宝', 470

    def __init__(self, popup):
        super().__init__(popup)
        self.entry = Gtk.SearchEntry(placeholder_text='seek…')
        self.entry.connect('search-changed', lambda _: self.refilter())
        self.entry.connect('activate', lambda _: self.activate_first())
        self.entry.connect('key-press-event', self.entry_key)
        self.flow = Gtk.FlowBox(homogeneous=True, min_children_per_line=5, max_children_per_line=5,
                                selection_mode=Gtk.SelectionMode.SINGLE, activate_on_single_click=True,
                                row_spacing=4, column_spacing=4, valign=Gtk.Align.START)
        self.flow.connect('child-activated', lambda _, child: self.launch(child.app))
        self.flow.set_filter_func(self.visible)
        apps = sorted((a for a in Gio.AppInfo.get_all() if a.should_show()), key=lambda a: a.get_display_name().lower())
        for app in apps:
            child = Gtk.FlowBoxChild()
            col = box(True, 6)
            col.pack_start(app_image(app.get_icon(), 38), False, False, 0)
            name = label(app.get_display_name(), xalign=.5, ellipsize=True); name.set_max_width_chars(11)
            col.pack_start(name, False, False, 0)
            child.add(col)
            child.set_tooltip_text(app.get_description() or app.get_display_name())
            child.app = app
            words = [app.get_display_name(), app.get_id() or '', app.get_description() or '']
            if hasattr(app, 'get_keywords'):
                words += [app.get_generic_name() or '', *(app.get_keywords() or [])]
            child.words = ' '.join(words).lower()
            self.flow.add(child)
        self.count = label('', 'hint', xalign=1)
        self.body.pack_start(self.header(self.count), False, False, 0)
        self.body.pack_start(self.entry, False, False, 2)
        self.body.pack_start(scrolled(self.flow, 330), True, True, 0)
        foot = box(False, 6)
        foot.pack_start(label('Enter launch · ↓ browse · Esc close', 'hint'), True, True, 0)
        self.body.pack_start(foot, False, False, 0)
        self.refilter()
        GLib.idle_add(self.entry.grab_focus)

    def visible(self, child):
        return all(w in child.words for w in self.entry.get_text().lower().split())

    def shown(self):
        return [c for c in self.flow.get_children() if self.visible(c)]

    def refilter(self):
        self.flow.invalidate_filter()
        shown = self.shown()
        self.count.set_text(f'{len(shown)} apps')
        if shown: self.flow.select_child(shown[0])

    def activate_first(self):
        chosen = self.flow.get_selected_children() or self.shown()
        if chosen: self.launch(chosen[0].app)

    def entry_key(self, _, event):
        if event.keyval == Gdk.KEY_Down:
            shown = self.shown()
            if shown: shown[0].grab_focus(); self.flow.select_child(shown[0])
            return True
        return False

    def key(self, event):
        # Typing while the grid has focus goes back to the search box.
        if not self.entry.has_focus() and Gdk.keyval_to_unicode(event.keyval) > 32:
            self.entry.grab_focus_without_selecting()
            return self.entry.event(event)
        return False

    def launch(self, app):
        launch_desktop(app.get_id())
        self.close()


class Keybinds(Panel):
    icon, title, han, width = '', 'Keybinds', '法诀', 520
    MODS = [(64, 'SUPER'), (1, 'SHIFT'), (4, 'CTRL'), (8, 'ALT')]

    def __init__(self, popup):
        super().__init__(popup)
        self.entry = Gtk.SearchEntry(placeholder_text='filter…')
        self.entry.connect('search-changed', lambda _: self.list.invalidate_filter())
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.set_filter_func(lambda row: all(w in row.words for w in self.entry.get_text().lower().split()))
        seen = set()
        try: binds = json.loads(output(['hyprctl', 'binds', '-j']) or '[]')
        except ValueError: binds = []
        for bind in binds:
            desc = bind.get('description') or ''
            if not desc: continue
            keys = [name for bit, name in self.MODS if bind.get('modmask', 0) & bit] + [bind.get('key', '').upper()]
            if (tuple(keys), desc) in seen: continue
            seen.add((tuple(keys), desc))
            row = Gtk.ListBoxRow()
            line = box(False, 4, 'row')
            caps = box(False, 3); caps.set_size_request(190, -1)
            for key in keys: caps.pack_start(label(key, 'key'), False, False, 0)
            line.pack_start(caps, False, False, 0)
            line.pack_start(label(desc, ellipsize=True), True, True, 6)
            row.add(line)
            row.words = (' '.join(keys) + ' ' + desc).lower()
            self.list.add(row)
        self.body.pack_start(self.header(label(f'{len(seen)} binds', 'hint', xalign=1)), False, False, 0)
        self.body.pack_start(self.entry, False, False, 2)
        self.body.pack_start(scrolled(self.list, 380), True, True, 0)
        GLib.idle_add(self.entry.grab_focus)


class Power(Panel):
    icon, title, han, width = '⏻', 'Power', '归元', 290
    ACTIONS = [
        ('l', '󰌾', 'Lock', ['loginctl', 'lock-session'], False),
        ('e', '󰍃', 'Log out', [SCRIPTS / 'logout'], True),
        ('u', '󰤄', 'Suspend', ['systemctl', 'suspend'], False),
        ('r', '󰜉', 'Reboot', ['systemctl', 'reboot'], True),
        ('s', '󰐥', 'Shut down', ['systemctl', 'poweroff'], True),
    ]

    def __init__(self, popup):
        super().__init__(popup)
        self.armed = None
        up = int(float(Path('/proc/uptime').read_text().split()[0]))
        uptime = f'{up // 86400}d {up % 86400 // 3600}h' if up >= 86400 else f'{up // 3600}h {up % 3600 // 60}m'
        user = pwd.getpwuid(os.getuid())
        self.body.pack_start(self.header(), False, False, 0)
        self.body.pack_start(icon_row('󰀄', f'{user.pw_gecos.split(",")[0] or user.pw_name}',
                                      f'{user.pw_name}@{socket.gethostname()} · up {uptime}'), False, False, 2)
        self.buttons = {}
        for key, glyph, text, argv, confirm in self.ACTIONS:
            row = box(False, 10)
            row.pack_start(label(glyph, 'icon', xalign=.5, width=2), False, False, 0)
            row.text = label(text); row.pack_start(row.text, True, True, 0)
            row.pack_end(label(key.upper(), 'key'), False, False, 0)
            b = button(row, None, 'chip', 'row')
            b.connect('clicked', lambda _, k=key: self.trigger(k))
            b.row = row
            self.buttons[key] = b
            self.body.pack_start(b, False, False, 0)
        self.body.pack_start(label('Reboot, log out and shut down ask twice.', 'hint', xalign=.5), False, False, 2)

    def trigger(self, key):
        _, _, text, argv, confirm = next(a for a in self.ACTIONS if a[0] == key)
        if confirm and self.armed != key:
            self.disarm()
            self.armed = key
            self.buttons[key].get_style_context().add_class('danger')
            self.buttons[key].row.text.set_text(f'{text}? Press again')
            GLib.timeout_add_seconds(4, self.disarm)
            return
        self.popup.hide()
        GLib.timeout_add(150, lambda: (detach(argv), self.close()) and False)

    def disarm(self):
        if self.armed:
            b = self.buttons[self.armed]
            b.get_style_context().remove_class('danger')
            b.row.text.set_text(next(a[2] for a in self.ACTIONS if a[0] == self.armed))
        self.armed = None
        return False

    def key(self, event):
        k = Gdk.keyval_name(event.keyval) or ''
        if k.lower() in self.buttons:
            self.trigger(k.lower()); return True
        return False


class Sound(Panel):
    icon, title, han, width = '󰕾', 'Sound', '音律', 350

    def __init__(self, popup):
        super().__init__(popup)
        self.body.pack_start(self.header(button('󰒓 mixer', lambda: (run_app('pavucontrol'), self.close()), 'chip',
                                                tip='Open pavucontrol')), False, False, 0)
        self.content = box(True, 6)
        self.body.pack_start(self.content, False, False, 0)
        self.dragging = False
        self.pending = None
        self.refresh()
        self.watch = subprocess.Popen(['pactl', 'subscribe'], stdout=subprocess.PIPE, text=True)
        GLib.io_add_watch(self.watch.stdout, GLib.IO_IN | GLib.IO_HUP, self.event)

    def event(self, stream, condition):
        line = stream.readline()
        if not line or not self.alive: return False
        if self.pending is None and re.search(r"'(new|remove|change)' on (sink|source|sink-input|server)", line):
            self.pending = GLib.timeout_add(120, self.refresh)
        return True

    def refresh(self):
        self.pending = None
        def load():
            data = {}
            for kind in ('sinks', 'sources', 'sink-inputs'):
                try: data[kind] = json.loads(subprocess.run(['pactl', '-f', 'json', 'list', kind], capture_output=True, text=True, timeout=5).stdout or '[]')
                except (ValueError, OSError, subprocess.SubprocessError): data[kind] = []
            data['sink'] = output(['pactl', 'get-default-sink']).strip()
            data['source'] = output(['pactl', 'get-default-source']).strip()
            return data
        POOL.submit(load).add_done_callback(lambda f: GLib.idle_add(lambda: self.render(f.result()) and False))
        return False

    @staticmethod
    def percent(item):
        vols = [int(ch['value_percent'].rstrip('%')) for ch in (item.get('volume') or {}).values()]
        return max(vols) if vols else 0

    def render(self, data):
        if self.dragging: return
        clear(self.content)
        sinks = data['sinks']
        sources = [s for s in data['sources'] if not s.get('monitor_source')]
        default = next((s for s in sinks if s['name'] == data['sink']), sinks[0] if sinks else None)
        self.content.pack_start(label('OUTPUT', 'section'), False, False, 0)
        if default: self.content.pack_start(self.control(default, 'sink', '󰕾', '󰝟'), False, False, 0)
        if any(s['name'] == 'auto_null' for s in sinks) and len(sinks) == 1:
            self.content.pack_start(label('No sound card found: PipeWire is using a dummy output.', 'warn', xalign=0), False, False, 0)
        if len(sinks) > 1:
            for s in sinks: self.content.pack_start(self.device(s, 'sink', s is default), False, False, 0)
        if sources:
            src = next((s for s in sources if s['name'] == data['source']), sources[0])
            self.content.pack_start(label('INPUT', 'section'), False, False, 0)
            self.content.pack_start(self.control(src, 'source', '󰍬', '󰍭'), False, False, 0)
            if len(sources) > 1:
                for s in sources: self.content.pack_start(self.device(s, 'source', s is src), False, False, 0)
        streams = data['sink-inputs']
        if streams:
            self.content.pack_start(label('APPS', 'section'), False, False, 0)
            for s in streams:
                p = s.get('properties', {})
                name = p.get('application.name') or p.get('application.process.binary') or 'Stream'
                self.content.pack_start(self.control(s, 'sink-input', '󰝚', '󰝛', name, p.get('media.name')), False, False, 0)
        self.content.show_all()

    def control(self, item, kind, on, off, title=None, sub=None):
        target = str(item['index']) if kind == 'sink-input' else item['name']
        muted = item.get('mute')
        col = box(True, 0)
        top = box(False, 8)
        mute = button(off if muted else on, None, 'chip', 'on' if not muted else None, tip='Mute')
        mute.connect('clicked', lambda _: sh(['pactl', f'set-{kind}-mute', target, 'toggle']))
        top.pack_start(mute, False, False, 0)
        text = box(True, 0)
        text.pack_start(label(title or item.get('description', target), ellipsize=True), False, False, 0)
        if sub: text.pack_start(label(sub, 'muted', ellipsize=True), False, False, 0)
        top.pack_start(text, True, True, 0)
        value = label(f'{self.percent(item)}%', 'accent', xalign=1); value.set_width_chars(5)
        top.pack_end(value, False, False, 0)
        col.pack_start(top, False, False, 0)
        def changed(v):
            value.set_text(f'{v}%')
            sh(['pactl', f'set-{kind}-volume', target, f'{v}%'])
        scale = slider(min(self.percent(item), 150), changed, 0, 150 if self.percent(item) > 100 else 100)
        scale.connect('button-press-event', lambda *_: setattr(self, 'dragging', True))
        scale.connect('button-release-event', lambda *_: (setattr(self, 'dragging', False), self.refresh()) and False)
        col.pack_start(scale, False, False, 0)
        return col

    def device(self, item, kind, current):
        row = icon_row('󰓃' if kind == 'sink' else '󰍬', item.get('description', item['name']), right='󰄬' if current else '')
        b = button(row, lambda: sh(['pactl', f'set-default-{kind}', item['name']]), 'row', 'current' if current else None)
        return b


def wifi_device():
    """First Wi-Fi interface NetworkManager knows (wlan0, wlp2s0, …)."""
    for line in output(['nmcli', '-t', '-f', 'DEVICE,TYPE', 'dev']).splitlines():
        dev, _, kind = line.partition(':')
        if kind == 'wifi': return dev
    return 'wlan0'

def nm_split(line):
    """Split one `nmcli -t` line, honouring backslash escapes."""
    return [f.replace('\\:', ':').replace('\\\\', '\\') for f in re.split(r'(?<!\\):', line)]

class Network(Panel):
    icon, title, han, width = '󰤨', 'Wi-Fi', '灵网', 350
    BARS = ['󰤯', '󰤟', '󰤢', '󰤥', '󰤨']

    def __init__(self, popup):
        super().__init__(popup)
        self.dev = wifi_device()
        on = output(['nmcli', 'radio', 'wifi']).strip() == 'enabled'
        self.toggle = switch(on, self.radio)
        self.body.pack_start(self.header(self.toggle), False, False, 0)
        self.current = box(True, 4)
        self.body.pack_start(self.current, False, False, 0)
        head = box(False, 6)
        head.pack_start(label('NETWORKS', 'section'), True, True, 0)
        self.scan = button('󰑐', lambda: self.refresh(True), tip='Rescan')
        head.pack_end(self.scan, False, False, 0)
        self.body.pack_start(head, False, False, 0)
        self.list = box(True, 2)
        self.body.pack_start(scrolled(self.list, 250), False, False, 0)
        self.status = label('', 'hint')
        self.body.pack_start(self.status, False, False, 0)
        foot = box(False, 6)
        foot.pack_start(button('󰒓 Connection editor', lambda: (run_app('nm-connection-editor'), self.close()), 'chip'), True, True, 0)
        foot.pack_start(button('󰂯 Bluetooth', lambda: (run_app('blueman-manager'), self.close()), 'chip'), True, True, 0)
        self.body.pack_start(foot, False, False, 2)
        self.expanded = None
        self.refresh(False, cached=True)
        GLib.timeout_add(300, lambda: self.refresh(False) and False)

    def radio(self, on):
        self.status.set_text('Turning Wi-Fi ' + ('on…' if on else 'off…'))
        sh(['nmcli', 'radio', 'wifi', 'on' if on else 'off'], lambda *_: GLib.timeout_add(1500, lambda: self.refresh(on) and False))

    def refresh(self, rescan=False, cached=False):
        self.status.set_text('Scanning…' if rescan else 'Loading networks…')
        def load():
            mode = 'no' if cached else 'yes' if rescan else 'auto'
            try:
                nets = subprocess.run(['nmcli', '-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list', '--rescan', mode],
                                      capture_output=True, text=True, timeout=30).stdout
            except (OSError, subprocess.SubprocessError):
                nets = ''
            known = output(['nmcli', '-t', '-f', 'NAME,TYPE', 'con', 'show'])
            active = output(['nmcli', '-t', '-f', 'NAME,TYPE,DEVICE', 'con', 'show', '--active'])
            ip = output(['nmcli', '-g', 'IP4.ADDRESS', 'dev', 'show', self.dev]).strip().split('\n')[0]
            return nets, known, active, ip
        POOL.submit(load).add_done_callback(lambda f: GLib.idle_add(lambda: self.render(*f.result()) and False))
        return False

    def render(self, nets, known, active, ip):
        self.status.set_text('')
        ip = ip.split(' | ')[0]
        self.known = {nm_split(l)[0] for l in known.splitlines() if '802-11-wireless' in l}
        best = {}
        for line in nets.splitlines():
            f = nm_split(line)
            if len(f) < 4 or not f[1]: continue
            use, ssid, signal_, sec = f[0] == '*', f[1], int(f[2] or 0), f[3]
            old = best.get(ssid)
            best[ssid] = (old[0] or use, max(old[1], signal_), old[2] or sec) if old else (use, signal_, sec)
        clear(self.current)
        wired = [nm_split(l) for l in active.splitlines() if '802-3-ethernet' in l]
        connected = next(((s, v) for s, v in best.items() if v[0]), None)
        if connected:
            ssid, (_, strength, sec) = connected
            disc = button('Disconnect', lambda: self.act(['nmcli', 'dev', 'disconnect', self.dev], 'Disconnecting…'), 'chip')
            self.current.pack_start(css(icon_row(self.bars(strength), ssid, f'{strength}% · {ip or "no address"}', disc), 'row', 'current'), False, False, 0)
        elif not self.toggle.get_active():
            self.current.pack_start(icon_row('󰤮', 'Wi-Fi is off', 'Flip the switch to scan'), False, False, 0)
        for w in wired:
            self.current.pack_start(icon_row('󰈀', w[0], 'Wired'), False, False, 0)
        clear(self.list)
        for ssid, (use, strength, sec) in sorted(best.items(), key=lambda kv: (not kv[1][0], -kv[1][1])):
            if use: continue
            self.list.pack_start(self.network(ssid, strength, sec), False, False, 0)
        if not best and self.toggle.get_active():
            self.list.pack_start(label('No networks found yet.', 'muted'), False, False, 0)
        self.body.show_all()

    def bars(self, strength):
        return self.BARS[min(4, strength // 20)]

    def network(self, ssid, strength, sec):
        col = box(True, 4)
        lock = '󰌾' if sec and sec != '--' else ''
        saved = ssid in self.known
        row = icon_row(self.bars(strength), ssid, ('saved · ' if saved else '') + (sec if lock else 'open'), f'{lock} {strength}%')
        b = button(row, None, 'row')
        col.pack_start(b, False, False, 0)
        if saved or not lock:
            b.connect('clicked', lambda _: self.connect(ssid, None, saved))
        else:
            pw = Gtk.Entry(placeholder_text='password', visibility=False, no_show_all=True)
            pw.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'view-reveal-symbolic')
            pw.connect('icon-press', lambda e, *_: e.set_visibility(not e.get_visibility()))
            pw.connect('activate', lambda e: self.connect(ssid, e.get_text(), False))
            col.pack_start(pw, False, False, 0)
            def expand(_):
                if self.expanded and self.expanded is not pw: self.expanded.hide()
                pw.set_visible(not pw.get_visible()); self.expanded = pw
                if pw.get_visible(): pw.grab_focus()
            b.connect('clicked', expand)
        return col

    def connect(self, ssid, password, saved):
        if saved: argv = ['nmcli', 'con', 'up', 'id', ssid]
        else: argv = ['nmcli', 'dev', 'wifi', 'connect', ssid] + (['password', password] if password else [])
        self.act(argv, f'Connecting to {ssid}…', timeout=45)

    def act(self, argv, message, timeout=20):
        self.status.set_text(message)
        def done(code, _out):
            self.status.set_text('Done.' if code == 0 else 'Failed: check the password or signal.')
            self.refresh(False)
        sh(argv, done, timeout)


class Calendar(Panel):
    icon, title, han, width = '󰃭', 'Calendar', '岁月', 300
    HAN_DAYS = '一二三四五六日'

    def __init__(self, popup):
        super().__init__(popup)
        today = datetime.date.today()
        self.month = today.replace(day=1)
        self.body.pack_start(self.header(), False, False, 0)
        self.clock = label('', 'big')
        self.date = label('', 'muted'); self.date.set_line_wrap(True)
        self.body.pack_start(self.clock, False, False, 0)
        self.body.pack_start(self.date, False, False, 0)
        nav = box(False, 4)
        nav.pack_start(button('󰅁', lambda: self.shift(-1), 'chip', tip='Previous month'), False, False, 0)
        self.heading = label('', 'header-title', xalign=.5)
        head_btn = button(self.heading, lambda: self.go(datetime.date.today().replace(day=1)), tip='Back to today')
        nav.pack_start(head_btn, True, True, 0)
        nav.pack_start(button('󰅂', lambda: self.shift(1), 'chip', tip='Next month'), False, False, 0)
        self.body.pack_start(nav, False, False, 6)
        self.grid = Gtk.Grid(row_spacing=2, column_spacing=2, halign=Gtk.Align.CENTER)
        self.body.pack_start(self.grid, False, False, 0)
        self.tick(); GLib.timeout_add_seconds(1, self.tick)
        self.draw()

    def tick(self):
        if not self.alive: return False
        now = datetime.datetime.now()
        self.clock.set_text(now.strftime('%H:%M:%S'))
        iso = now.isocalendar()
        self.date.set_text(f'{now:%A %d %B %Y} · 星期{self.HAN_DAYS[now.weekday()]} · week {iso.week} · day {now.timetuple().tm_yday}')
        return True

    def shift(self, months):
        m = self.month.month - 1 + months
        self.go(self.month.replace(year=self.month.year + m // 12, month=m % 12 + 1))

    def go(self, month):
        self.month = month; self.draw()

    def draw(self):
        clear(self.grid)
        self.heading.set_text(f'{self.month:%B %Y}')
        for i, d in enumerate(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']):
            self.grid.attach(label(d, 'weekday', xalign=.5), i, 0, 1, 1)
        today = datetime.date.today()
        weeks = calendar.Calendar(0).monthdatescalendar(self.month.year, self.month.month)
        for r, week in enumerate(weeks, 1):
            for c, day in enumerate(week):
                cell = button(str(day.day), None, 'day',
                              'other' if day.month != self.month.month else None,
                              'weekend' if c >= 5 else None, 'today' if day == today else None)
                self.grid.attach(cell, c, r, 1, 1)
        self.grid.show_all()

    def key(self, event):
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Page_Up): self.shift(-1); return True
        if event.keyval in (Gdk.KEY_Right, Gdk.KEY_Page_Down): self.shift(1); return True
        if event.keyval == Gdk.KEY_Home: self.go(datetime.date.today().replace(day=1)); return True
        return False


class System(Panel):
    icon, title, han, width = '󰒓', 'Quick settings', '洞府', 350
    BAT = next(iter(sorted(Path('/sys/class/power_supply').glob('BAT*'))), Path('/sys/class/power_supply/BAT0'))
    PROFILES = [('power-saver', '󰌪', 'Saver'), ('balanced', '󰗑', 'Balanced'), ('performance', '󰓅', 'Boost')]

    def __init__(self, popup):
        super().__init__(popup)
        self.body.pack_start(self.header(), False, False, 0)
        # Battery
        self.bat_big = label('', 'big')
        self.bat_info = label('', 'muted')
        self.bat_bar = Gtk.ProgressBar()
        top = box(False, 12)
        top.pack_start(self.bat_big, False, False, 0)
        top.pack_start(self.bat_info, True, True, 0)
        self.body.pack_start(top, False, False, 0)
        self.body.pack_start(self.bat_bar, False, False, 0)
        # Power profile
        self.body.pack_start(label('POWER PROFILE', 'section'), False, False, 0)
        prof = box(False, 4); prof.set_homogeneous(True)
        self.prof_buttons = {}
        for name, glyph, text in self.PROFILES:
            b = button(f'{glyph}  {text}', lambda n=name: self.profile(n), 'chip')
            self.prof_buttons[name] = b; prof.pack_start(b, True, True, 0)
        self.body.pack_start(prof, False, False, 0)
        # Brightness
        self.body.pack_start(label('BRIGHTNESS', 'section'), False, False, 0)
        light = box(False, 8)
        light.pack_start(label('󰃠', 'icon', xalign=.5, width=2), False, False, 0)
        self.light_value = label('', 'accent', xalign=1); self.light_value.set_width_chars(5)
        self.light = slider(self.brightness(), self.set_brightness, 1, 100)
        light.pack_start(self.light, True, True, 0)
        light.pack_start(self.light_value, False, False, 0)
        self.light_value.set_text(f'{int(self.light.get_value())}%')
        self.body.pack_start(light, False, False, 0)
        # Toggles
        self.body.pack_start(label('TOGGLES', 'section'), False, False, 0)
        grid = Gtk.Grid(row_spacing=4, column_spacing=4, column_homogeneous=True)
        self.toggles = {}
        specs = [('wifi', '󰤨', 'Wi-Fi'), ('bt', '󰂯', 'Bluetooth'), ('dnd', '󰂛', 'Do not disturb'),
                 ('night', '󰖔', 'Night light'), ('motion', '󰪤', 'Low motion'), ('idle', '󰅶', 'Stay awake')]
        for i, (key, glyph, text) in enumerate(specs):
            b = button(f'{glyph}  {text}', lambda k=key: self.flip(k), 'chip')
            b.get_child().set_xalign(0)
            self.toggles[key] = b
            grid.attach(b, i % 2, i // 2, 1, 1)
        self.body.pack_start(grid, False, False, 0)
        # Links
        self.body.pack_start(label('APPEARANCE', 'section'), False, False, 0)
        links = box(False, 4); links.set_homogeneous(True)
        links.pack_start(button('󰏘 GTK', lambda: self.open('nwg-look'), 'chip', tip='nwg-look'), True, True, 0)
        links.pack_start(button('󰙵 Qt', lambda: self.open('kvantummanager'), 'chip', tip='Kvantum Manager'), True, True, 0)
        links.pack_start(button('󰸉 Wallpaper', lambda: (detach([SCRIPTS / 'wallpaper']), self.close()), 'chip', tip='Reapply wallpaper'), True, True, 0)
        links.pack_start(button('󰂚 Alerts', lambda: (detach(['swaync-client', '-t', '-sw']), self.close()), 'chip', tip='Notification centre'), True, True, 0)
        self.body.pack_start(links, False, False, 0)
        self.update(); GLib.timeout_add_seconds(3, self.update)

    def open(self, app):
        run_app(app); self.close()

    def read(self, name, default=''):
        try: return (self.BAT / name).read_text().strip()
        except OSError: return default

    def update(self):
        if not self.alive: return False
        cap = int(self.read('capacity', '0') or 0)
        status = self.read('status', 'Unknown')
        self.bat_big.set_text(f'{cap}%')
        self.bat_bar.set_fraction(cap / 100)
        ctx = self.bat_bar.get_style_context()
        (ctx.add_class if cap <= 20 and status != 'Charging' else ctx.remove_class)('low')
        try:
            amps, volts = int(self.read('current_now')) / 1e6, int(self.read('voltage_now')) / 1e6
            now, full = int(self.read('charge_now')) / 1e6, int(self.read('charge_full')) / 1e6
            watts = amps * volts
            hours = (now / amps if status == 'Discharging' else (full - now) / amps) if amps > 0.01 else None
        except ValueError:
            watts, hours = 0, None
        eta = f' · {int(hours)}h {int(hours * 60 % 60):02d}m {"left" if status == "Discharging" else "to full"}' if hours else ''
        health = self.read('cycle_count')
        self.bat_info.set_text(f'{status}{eta}\n{watts:.1f} W' + (f' · {health} cycles' if health and health != '0' else ''))
        sh(['powerprofilesctl', 'get'], lambda code, out: self.mark_profile(out.strip()))
        self.states()
        return True

    def mark_profile(self, current):
        for name, b in self.prof_buttons.items():
            (b.get_style_context().add_class if name == current else b.get_style_context().remove_class)('on')

    def profile(self, name):
        self.mark_profile(name)
        sh(['powerprofilesctl', 'set', name], lambda *_: self.update() and False)

    def brightness(self):
        try: return int(output(['brightnessctl', '-m', '-c', 'backlight']).split(',')[3].rstrip('%'))
        except (IndexError, ValueError): return 50

    def set_brightness(self, v):
        self.light_value.set_text(f'{v}%')
        sh(['brightnessctl', '-q', '-c', 'backlight', 'set', f'{v}%'])

    def states(self):
        def load():
            return {
                'wifi': output(['nmcli', 'radio', 'wifi']).strip() == 'enabled',
                'bt': 'Powered: yes' in output(['bluetoothctl', 'show']),
                'dnd': output(['swaync-client', '-D']).strip() == 'true',
                'night': subprocess.run(['pgrep', '-x', 'hyprsunset'], capture_output=True).returncode == 0,
                'motion': (STATE / 'low-motion').exists(),
                'idle': subprocess.run(['pgrep', '-x', 'hypridle'], capture_output=True).returncode != 0,
            }
        POOL.submit(load).add_done_callback(lambda f: GLib.idle_add(lambda: self.mark(f.result()) and False))

    def mark(self, states):
        self.state = states
        for key, on in states.items():
            ctx = self.toggles[key].get_style_context()
            (ctx.add_class if on else ctx.remove_class)('on')

    def flip(self, key):
        on = getattr(self, 'state', {}).get(key, False)
        if key == 'wifi': sh(['nmcli', 'radio', 'wifi', 'off' if on else 'on'])
        elif key == 'bt': sh(['bluetoothctl', 'power', 'off' if on else 'on'])
        elif key == 'dnd': sh(['swaync-client', '-df' if on else '-dn'])
        elif key == 'night':
            if on: sh(['pkill', '-x', 'hyprsunset'])
            else: run_app('hyprsunset', '-t', '4500')
        elif key == 'motion': detach([SCRIPTS / 'low-motion'])
        elif key == 'idle':
            if on: run_app('hypridle')
            else: sh(['pkill', '-x', 'hypridle'])
        self.mark({**getattr(self, 'state', {}), key: not on})
        GLib.timeout_add(1200, lambda: self.states() and False)


PANELS = {'launcher': Launcher, 'keybinds': Keybinds, 'power': Power, 'sound': Sound,
          'network': Network, 'calendar': Calendar, 'system': System}

# ── window ─────────────────────────────────────────────────────────────────

class Popup:
    """One visible panel. The daemon builds a fresh one per request."""

    def __init__(self, daemon, name, x, animate=True):
        self.daemon, self.name, self.x = daemon, name, x
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.win.set_visual(self.win.get_screen().get_rgba_visual())
        self.win.set_app_paintable(True)
        GtkLayerShell.init_for_window(self.win)
        GtkLayerShell.set_namespace(self.win, 'wanglin-popup')
        GtkLayerShell.set_layer(self.win, GtkLayerShell.Layer.OVERLAY)
        # On-demand, not exclusive: an exclusive grab swallowed the first click on
        # another bar icon, so switching panels took two clicks.
        GtkLayerShell.set_keyboard_mode(self.win, GtkLayerShell.KeyboardMode.ON_DEMAND)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.win, edge, True)
        GtkLayerShell.set_exclusive_zone(self.win, 0)  # stays below the bar's reserved strip

        self.panel = PANELS[name](self)
        card = css(box(True), 'panel')
        card.pack_start(self.panel.body, True, True, 0)
        card.set_size_request(self.panel.width, -1)
        frame = Gtk.EventBox(visible_window=False)
        frame.add(card)
        frame.connect('button-press-event', lambda *_: True)  # clicks inside never close
        slide = animate and not (STATE / 'low-motion').exists()
        self.revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                                     transition_duration=170 if slide else 0)
        self.revealer.add(frame)
        self.fixed = Gtk.Fixed()
        self.fixed.put(self.revealer, 0, 0)
        outside = Gtk.EventBox()
        outside.add(self.fixed)
        outside.connect('button-press-event', lambda *_: self.close())
        self.win.add(outside)
        self.win.connect('key-press-event', self.key)
        self.win.show_all()
        self.place()
        if slide: GLib.idle_add(lambda: self.revealer.set_reveal_child(True))
        else: self.revealer.set_reveal_child(True)

    def place(self):
        # Centre under the clicked icon, clamped to the screen.
        full = max(self.revealer.get_child().get_preferred_width()[1], self.panel.width + 20)
        left = max(0, min(self.screen_width() - full, self.x - full / 2))
        self.fixed.move(self.revealer, int(left), 0)

    @staticmethod
    def screen_width():
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(0, 0) or display.get_monitor(0)
        return monitor.get_geometry().width

    def key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close(); return True
        return self.panel.key(event)

    def hide(self):
        self.win.hide()

    def close(self):
        self.daemon.close(self)

    def destroy(self):
        self.panel.alive = False
        if getattr(self.panel, 'watch', None): self.panel.watch.kill()
        self.win.destroy()


class Daemon:
    def __init__(self):
        self.popup = None
        self.buffer = b''
        try:  # one daemon only: two would each take turns reading the FIFO
            other = int(PIDFILE.read_text())
            if other != os.getpid() and b'popups/popup.py' in Path(f'/proc/{other}/cmdline').read_bytes():
                sys.exit(0)
        except (OSError, ValueError):
            pass
        if FIFO.exists() and not FIFO.is_fifo(): FIFO.unlink()
        if not FIFO.exists(): os.mkfifo(FIFO, 0o600)
        # O_RDWR keeps a writer open ourselves, so the FIFO never reports EOF.
        fd = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)
        GLib.io_add_watch(GLib.IOChannel.unix_new(fd), GLib.PRIORITY_DEFAULT, GLib.IO_IN, self.read, fd)
        PIDFILE.write_text(str(os.getpid()))

    def read(self, _channel, _condition, fd):
        try: self.buffer += os.read(fd, 4096)
        except BlockingIOError: return True
        *lines, self.buffer = self.buffer.split(b'\n')
        for line in lines:
            try: self.command(line.decode().split())
            except Exception as error:  # a bad panel must not kill the daemon
                print(f'popup: {line!r}: {error!r}', file=sys.stderr)
        return True

    def command(self, words):
        if not words: return
        name = words[0]
        if name == 'close' or (self.popup and self.popup.name == name):
            self.close(); return
        if name not in PANELS: return
        try: x = float(words[1])
        except (IndexError, ValueError): x = Popup.screen_width() / 2
        old = self.popup
        # Map the new panel before dropping the old one, so a swap has no gap.
        self.popup = Popup(self, name, x, animate=old is None)
        if old: old.destroy()

    def close(self, popup=None):
        if self.popup and (popup is None or popup is self.popup):
            self.popup.destroy()
            self.popup = None

    def quit(self):
        try:
            if PIDFILE.read_text().strip() == str(os.getpid()): PIDFILE.unlink()
        except OSError:
            pass
        Gtk.main_quit()
        return False


def main():
    if sys.argv[1:] != ['--daemon']:
        sys.exit('usage: popup.py --daemon   (use scripts/popup NAME [x] to open panels)')
    provider = Gtk.CssProvider()
    provider.load_from_path(str(Path(__file__).with_name('style.css')))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    daemon = Daemon()
    for sig in (signal.SIGTERM, signal.SIGINT):
        (GLibUnix.signal_add if GLibUnix else GLib.unix_signal_add)(GLib.PRIORITY_DEFAULT, sig, daemon.quit)
    Gtk.main()

if __name__ == '__main__':
    main()
