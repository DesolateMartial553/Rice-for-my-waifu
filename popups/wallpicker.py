#!/usr/bin/env python3
"""Full-screen wallpaper picker laid out like the PS4 home screen.

The selected wallpaper fills the background; a horizontal row of tiles runs
along the top with the selected tile enlarged at the left. ←/→ (or scroll)
slides the row, Enter/Space applies, Esc goes back. Started by
`scripts/wallpaper-cycle select` (SUPER+SHIFT+W).

Only the selected wallpaper is shown as a picture; the other tiles are cards
with a number and name, so one wallpaper is visible at a time.
"""
import datetime
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GtkLayerShell, Pango, PangoCairo
import cairo

ROOT = Path(__file__).resolve().parents[1]
WALLS = ROOT / 'wallpapers'
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'wanglin-rice'
LOW_MOTION = (STATE / 'low-motion').exists()
SLIDE_MS = 0 if LOW_MOTION else 320
BIG = (256, 144)     # selected tile (16:9)
SMALL = (132, 144)   # other tiles: same height, narrower, like the PS4 row
GAP = 10
X0 = 56

# Display names: stem → (title, 汉字). Anything else is title-cased.
NAMES = {
    'wallpaper': ('Wang Lin', '王林'),
    '1-lightning': ('Heavenly Tribulation', '雷劫'),
    '2-doorway': ('Beyond the Door', '问道'),
    '3-sovereign': ('The Sovereign', '至尊'),
    '4-calligraphy': ('One Cauldron Rules the Heavens', '一鼎镇天'),
}
SERIES = {'renegade': 'Renegade Immortal · 仙逆', '': 'Wang Lin Rice'}

CSS = b'''
* { font-family: "GoogleSansCode Nerd Font Propo", "Noto Sans CJK SC", sans-serif; color: #f2ecfa; text-shadow: 0 1px 6px rgba(0,0,0,0.7); }
window { background: #0b0712; }
.brand { font-size: 13px; letter-spacing: 3px; color: #d9c8f5; }
.clock { font-size: 15px; font-weight: bold; }
.han { font-size: 16px; letter-spacing: 6px; color: #c7aceb; }
.title { font-size: 26px; font-weight: bold; }
.series { font-size: 13px; letter-spacing: 2px; color: #c9bddc; }
.badge { font-size: 11px; font-weight: bold; letter-spacing: 1px; padding: 3px 10px; border-radius: 20px;
         background: rgba(184,138,245,0.28); border: 1px solid rgba(212,178,251,0.7); color: #f2ecfa; text-shadow: none; }
button { background: transparent; background-image: none; border: none; box-shadow: none; padding: 0; min-height: 0; min-width: 0; }
button.play { background: #f2ecfa; border-radius: 30px; padding: 10px 34px; box-shadow: 0 4px 18px rgba(0,0,0,0.45); }
button.play label { color: #1a0f2b; font-size: 15px; font-weight: bold; text-shadow: none; }
button.play:hover { background: #ffffff; box-shadow: 0 0 0 3px rgba(184,138,245,0.9), 0 4px 22px rgba(110,64,161,0.8); }
button.ghost { background: rgba(15,12,23,0.55); border: 1px solid rgba(242,236,250,0.35); border-radius: 30px; padding: 10px 22px; }
button.ghost label { font-size: 14px; }
button.ghost:hover { border-color: #f2ecfa; background: rgba(37,21,56,0.8); }
button.arrow { background: rgba(15,12,23,0.45); border-radius: 50%; min-width: 46px; min-height: 46px; }
button.arrow label { font-size: 22px; }
button.arrow:hover { background: rgba(110,64,161,0.75); }
.dot { min-width: 8px; min-height: 8px; border-radius: 50%; background: rgba(242,236,250,0.35); margin: 0 4px; }
.dot.on { background: #f2ecfa; min-width: 26px; border-radius: 5px; }
.count { font-size: 12px; color: #c9bddc; }
.hint { font-size: 12px; color: #d9d0e6; }
.glyph { font-size: 12px; font-weight: bold; min-width: 20px; min-height: 20px; border-radius: 50%;
         background: rgba(242,236,250,0.9); color: #1a0f2b; text-shadow: none; padding: 0 1px; }
'''


def wallpapers():
    found = [p for p in WALLS.rglob('*') if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
             and p.name != 'wanglin-placeholder.png']
    return sorted(found, key=lambda p: str(p.relative_to(WALLS)))

def current():
    try:
        path = Path((STATE / 'wallpaper.current').read_text().strip())
        if path.is_file(): return path.resolve()
    except OSError:
        pass
    return (WALLS / 'wallpaper.png').resolve()

def describe(path):
    title, han = NAMES.get(path.stem, (path.stem.split('-', 1)[-1].replace('_', ' ').title(), ''))
    folder = str(path.parent.relative_to(WALLS)) if path.parent != WALLS else ''
    return title, han, SERIES.get(folder, folder.replace('-', ' ').title())

def ease(t):
    return 1 - (1 - t) ** 3

def label(text, cls, xalign=0.0):
    obj = Gtk.Label(label=text, xalign=xalign)
    obj.get_style_context().add_class(cls)
    return obj


def rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

def lerp(a, b, t):
    return a + (b - a) * t


class Picker:
    def __init__(self):
        self.walls = wallpapers()
        if not self.walls: sys.exit('no wallpapers found')
        self.applied = current()
        self.index = next((i for i, p in enumerate(self.walls) if p.resolve() == self.applied), 0)
        self.pos = float(self.index)   # animated row position
        self.cache, self.thumbs = {}, {}
        self.anim = None               # (from_index, from_pos, start_time)
        self.last_scroll = 0

        self.win = Gtk.Window()
        GtkLayerShell.init_for_window(self.win)
        GtkLayerShell.set_namespace(self.win, 'wanglin-wallpicker')
        GtkLayerShell.set_layer(self.win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.win, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self.win, -1)  # cover the bar too
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.win, edge, True)

        overlay = Gtk.Overlay()
        self.canvas = Gtk.DrawingArea()
        self.canvas.connect('draw', self.draw)
        overlay.add(self.canvas)
        self.ui = self.build_ui()
        overlay.add_overlay(self.ui)
        events = Gtk.EventBox()
        events.add(overlay)
        events.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        events.connect('scroll-event', self.scroll)
        events.connect('button-press-event', self.click)
        self.win.add(events)
        self.win.connect('key-press-event', self.key)
        self.win.connect('destroy', Gtk.main_quit)
        self.refresh_text()
        self.win.show_all()
        GLib.timeout_add_seconds(1, self.tick_clock)

    # ── layout: GTK for text/buttons, cairo for background + tile row ─────
    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_margin_start(X0); root.set_margin_end(X0); root.set_margin_top(26); root.set_margin_bottom(26)
        top = Gtk.Box(spacing=12)
        top.pack_start(label('王林  ·  WALLPAPERS', 'brand'), False, False, 0)
        self.clock = label('', 'clock', 1)
        top.pack_end(self.clock, False, False, 0)
        root.pack_start(top, False, False, 0)

        self.row_slot = Gtk.Box()               # the tile row is painted here
        self.row_slot.set_size_request(-1, BIG[1])
        self.row_slot.set_margin_top(44)
        root.pack_start(self.row_slot, False, False, 0)

        self.info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.info.set_margin_top(14)
        self.title = label('', 'title')
        self.title.set_line_wrap(True); self.title.set_max_width_chars(34)
        self.han = label('', 'han')
        meta = Gtk.Box(spacing=12)
        self.series = label('', 'series')
        self.badge = label('CURRENTLY APPLIED', 'badge')
        self.badge.set_no_show_all(True)
        meta.pack_start(self.series, False, False, 0)
        meta.pack_start(self.badge, False, False, 0)
        actions = Gtk.Box(spacing=12)
        actions.set_margin_top(16)
        play = Gtk.Button(label='Apply')
        play.get_style_context().add_class('play')
        play.connect('clicked', lambda _: self.apply())
        back = Gtk.Button(label='Back')
        back.get_style_context().add_class('ghost')
        back.connect('clicked', lambda _: self.win.destroy())
        actions.pack_start(play, False, False, 0)
        actions.pack_start(back, False, False, 0)
        for w in (self.title, self.han, meta, actions): self.info.pack_start(w, False, False, 0)
        root.pack_start(self.info, False, False, 0)

        root.pack_start(Gtk.Box(), True, True, 0)
        bottom = Gtk.Box(spacing=18)
        self.count = label('', 'count')
        bottom.pack_start(self.count, False, False, 0)
        hints = Gtk.Box(spacing=16)
        for glyph, text in (('✕', 'Apply'), ('○', 'Back'), ('◀▶', 'Browse')):
            item = Gtk.Box(spacing=6)
            item.pack_start(label(glyph, 'glyph', .5), False, False, 0)
            item.pack_start(label(text, 'hint'), False, False, 0)
            hints.pack_start(item, False, False, 0)
        bottom.pack_end(hints, False, False, 0)
        root.pack_start(bottom, False, False, 0)
        return root

    def refresh_text(self):
        path = self.walls[self.index]
        title, han, series = describe(path)
        self.title.set_text(title)
        self.han.set_text(han); self.han.set_visible(bool(han))
        self.series.set_text(series)
        self.badge.set_visible(path.resolve() == self.applied)
        self.count.set_text(f'{self.index + 1} / {len(self.walls)}')
        self.tick_clock()

    def tick_clock(self):
        self.clock.set_text(datetime.datetime.now().strftime('%H:%M'))
        return True

    # ── images ────────────────────────────────────────────────────────────
    def pixbuf(self, i):
        if i not in self.cache:
            try: self.cache[i] = GdkPixbuf.Pixbuf.new_from_file(str(self.walls[i]))
            except GLib.Error: self.cache[i] = None
        return self.cache[i]

    def thumb(self, i):
        """Tile-sized copy (2x for HiDPI) so the row stays cheap to redraw."""
        if i not in self.thumbs:
            pb = self.pixbuf(i)
            self.thumbs[i] = pb and pb.scale_simple(BIG[0] * 2, BIG[1] * 2, GdkPixbuf.InterpType.BILINEAR)
        return self.thumbs[i]

    def cover(self, cr, pb, x, y, w, h, alpha=1.0, zoom=1.0):
        """Paint pb scaled to cover the box (centre-cropped)."""
        if pb is None or alpha <= 0: return
        scale = max(w / pb.get_width(), h / pb.get_height()) * zoom
        pw, ph = pb.get_width() * scale, pb.get_height() * scale
        cr.save()
        cr.rectangle(x, y, w, h); cr.clip()
        cr.translate(x + (w - pw) / 2, y + (h - ph) / 2)
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.paint_with_alpha(alpha)
        cr.restore()

    # ── drawing ───────────────────────────────────────────────────────────
    def progress(self):
        if not self.anim: return 1.0
        return min(1.0, (time.monotonic() - self.anim[2]) * 1000 / max(1, SLIDE_MS))

    def row_y(self):
        pos = self.row_slot.translate_coordinates(self.canvas, 0, 0)
        return pos[-1] if pos else 110

    def draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgb(0.043, 0.027, 0.071); cr.paint()
        t = self.progress(); e = ease(t)
        if self.anim:
            src, start_pos, _ = self.anim
            self.pos = lerp(start_pos, self.index, e)
            self.cover(cr, self.pixbuf(src), 0, 0, w, h, 1 - e)
            self.cover(cr, self.pixbuf(self.index), 0, 0, w, h, e, 1.03 - 0.03 * e)
        else:
            self.pos = float(self.index)
            self.cover(cr, self.pixbuf(self.index), 0, 0, w, h)
        self.shade(cr, w, h)
        self.draw_row(cr, w, self.row_y())
        self.ui.set_opacity(1.0 if not self.anim else 0.4 + 0.6 * e)
        if self.anim and t >= 1.0: self.anim = None
        return False

    def shade(self, cr, w, h):
        # PS4-style wash: darker at the top (under the row) and left (under the text).
        for (x0, y0, x1, y1, a) in ((0, 0, 0, h * 0.75, 0.78), (0, 0, w * 0.6, 0, 0.55), (0, h, 0, h * 0.7, 0.6)):
            g = cairo.LinearGradient(x0, y0, x1, y1)
            g.add_color_stop_rgba(0, 0.043, 0.027, 0.071, a)
            g.add_color_stop_rgba(1, 0.043, 0.027, 0.071, 0)
            cr.set_source(g); cr.paint()

    def slot(self, rel):
        """x and width of a tile `rel` steps from the selection (fractional while sliding)."""
        k = min(1.0, abs(rel))
        width = lerp(BIG[0], SMALL[0], k)
        x = X0 + rel * (SMALL[0] + GAP) + (min(1.0, max(0.0, rel)) * (BIG[0] - SMALL[0]))
        return x, width

    def draw_row(self, cr, w, y):
        for i in range(len(self.walls)):
            rel = i - self.pos
            x, tw = self.slot(rel)
            if x + tw < -20 or x > w + 20: continue
            k = min(1.0, abs(rel))              # 0 = selected, 1 = ordinary tile
            th = BIG[1]
            alpha = 1.0 if rel > -0.5 else max(0.0, 1 + (rel + 0.5) * 1.6)   # tiles leaving left fade out
            if alpha <= 0: continue
            cr.save()
            rounded(cr, x, y, tw, th, 6); cr.clip()
            if k > 0.5:
                self.name_tile(cr, i, x, y, tw, th, alpha)
            else:                               # picture fades into a name card while sliding away
                cr.set_source_rgba(0.1, 0.07, 0.15, alpha); cr.paint()
                self.cover(cr, self.thumb(i), x, y, tw, th, alpha)
                if k > 0.2: self.name_tile(cr, i, x, y, tw, th, alpha * (k - 0.2) / 0.3)
            cr.restore()
            if k < 0.5:                         # focus frame + glow on the selected tile
                a = alpha * (1 - k * 2)
                for grow, op in ((6, 0.18), (3, 0.35)):
                    rounded(cr, x - grow, y - grow, tw + 2 * grow, th + 2 * grow, 6 + grow)
                    cr.set_source_rgba(0.72, 0.54, 0.96, op * a); cr.set_line_width(2); cr.stroke()
                rounded(cr, x - 1, y - 1, tw + 2, th + 2, 7)
                cr.set_source_rgba(0.95, 0.93, 0.98, a); cr.set_line_width(2); cr.stroke()

    def name_tile(self, cr, i, x, y, w, h, alpha):
        if alpha <= 0: return
        g = cairo.LinearGradient(x, y, x, y + h)
        g.add_color_stop_rgba(0, 0.16, 0.09, 0.26, 0.92 * alpha)
        g.add_color_stop_rgba(1, 0.07, 0.04, 0.12, 0.92 * alpha)
        cr.set_source(g); cr.rectangle(x, y, w, h); cr.fill()
        title, han, _ = describe(self.walls[i])
        self.text(cr, f'{i + 1:02d}', x + 10, y + 8, 11, (0.79, 0.74, 0.86, alpha), bold=True)
        self.text(cr, han[:2] or title[:1], x + w / 2, y + h / 2 - 20, 26, (0.78, 0.67, 0.92, alpha), centre=True)
        self.text(cr, title, x + w / 2, y + h - 34, 10, (0.95, 0.93, 0.98, alpha), centre=True, width=w - 16)

    def text(self, cr, s, x, y, size, rgba, bold=False, centre=False, width=None):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription(f'GoogleSansCode Nerd Font Propo, Noto Sans CJK SC {"Bold " if bold else ""}{size}px')
        font.set_absolute_size(size * Pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(s, -1)
        if width:
            layout.set_width(int(width * Pango.SCALE)); layout.set_wrap(Pango.WrapMode.WORD_CHAR)
            layout.set_alignment(Pango.Alignment.CENTER); layout.set_height(-2)
            layout.set_ellipsize(Pango.EllipsizeMode.END)
        tw, _ = layout.get_pixel_size()
        cr.move_to(x - (width / 2 if width else tw / 2) if centre else x, y)
        cr.set_source_rgba(*rgba)
        PangoCairo.show_layout(cr, layout)

    def animate(self, *_):
        self.canvas.queue_draw()
        return self.anim is not None

    # ── actions ───────────────────────────────────────────────────────────
    def go(self, step, absolute=None):
        if len(self.walls) < 2: return
        src = self.index
        self.index = absolute if absolute is not None else (self.index + step) % len(self.walls)
        if self.index == src: return
        self.refresh_text()
        if SLIDE_MS:
            self.anim = (src, self.pos, time.monotonic())
            self.canvas.add_tick_callback(self.animate)
        self.canvas.queue_draw()

    def apply(self):
        subprocess.Popen([str(ROOT / 'scripts/wallpaper'), str(self.walls[self.index])],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.win.destroy()

    def click(self, _, event):
        y0 = self.row_y()
        if not (y0 <= event.y <= y0 + BIG[1]): return False
        for i in range(len(self.walls)):
            x, tw = self.slot(i - self.pos)
            if x <= event.x <= x + tw:
                if i == self.index: self.apply()
                else: self.go(0, absolute=i)
                return True
        return False

    def key(self, _, event):
        k = event.keyval
        if k in (Gdk.KEY_Escape, Gdk.KEY_BackSpace, Gdk.KEY_q): self.win.destroy()
        elif k in (Gdk.KEY_Right, Gdk.KEY_l, Gdk.KEY_d, Gdk.KEY_Tab): self.go(1)
        elif k in (Gdk.KEY_Left, Gdk.KEY_h, Gdk.KEY_a, Gdk.KEY_ISO_Left_Tab): self.go(-1)
        elif k == Gdk.KEY_Home: self.go(0, absolute=0)
        elif k == Gdk.KEY_End: self.go(0, absolute=len(self.walls) - 1)
        elif k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space): self.apply()
        else: return False
        return True

    def scroll(self, _, event):
        now = time.monotonic()
        if now - self.last_scroll < 0.3: return True
        ok, dx, dy = event.get_scroll_deltas()
        step = {Gdk.ScrollDirection.DOWN: 1, Gdk.ScrollDirection.RIGHT: 1,
                Gdk.ScrollDirection.UP: -1, Gdk.ScrollDirection.LEFT: -1}.get(event.direction)
        if step is None and ok and abs(dx) + abs(dy) > 0.5:
            step = 1 if (dy if abs(dy) >= abs(dx) else dx) > 0 else -1
        if step:
            self.last_scroll = now
            self.go(step)
        return True


def main():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    Picker()
    Gtk.main()

if __name__ == '__main__':
    main()
