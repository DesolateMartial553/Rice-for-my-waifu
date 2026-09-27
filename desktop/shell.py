#!/usr/bin/env python3
"""Small Wayland desktop panels with real MPRIS controls and /proc telemetry."""
import collections
import concurrent.futures
import fcntl
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('Playerctl', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GtkLayerShell, Playerctl, Pango

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def launch(argv):
    subprocess.Popen([str(ROOT / 'scripts/run'), *map(str, argv)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def label(text='', css=None, xalign=0):
    obj = Gtk.Label(label=text, xalign=xalign)
    if css: obj.get_style_context().add_class(css)
    return obj

def button(text, tip, callback, css=None):
    obj = Gtk.Button()
    obj.add(label(text, css, .5))
    obj.set_tooltip_text(tip)
    obj.connect('clicked', lambda _: callback())
    return obj

def box(vertical=False, spacing=0):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)

def surface(name, layer, anchors, margins):
    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_visual(win.get_screen().get_rgba_visual())
    GtkLayerShell.init_for_window(win)
    GtkLayerShell.set_namespace(win, name)
    GtkLayerShell.set_layer(win, layer)
    GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
    GtkLayerShell.set_exclusive_zone(win, -1)
    for edge in anchors: GtkLayerShell.set_anchor(win, edge, True)
    for edge, margin in margins.items(): GtkLayerShell.set_margin(win, edge, margin)
    return win

class Graph(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.values = collections.deque([0.] * 36, maxlen=36)
        self.set_size_request(66, 20)
        self.connect('draw', self.draw)

    def push(self, value):
        self.values.append(max(0., min(1., value)))
        self.queue_draw()

    def draw(self, _, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cr.set_source_rgba(.6, .4, .8, .18)
        cr.set_line_width(.5)
        for y in (h*.25, h*.75):
            cr.move_to(0, y); cr.line_to(w, y)
        cr.stroke()
        points = [(i*w/35, h-2-v*(h-4)) for i,v in enumerate(self.values)]
        cr.move_to(0,h)
        for x,y in points: cr.line_to(x,y)
        cr.line_to(w,h); cr.close_path()
        cr.set_source_rgba(.68,.38,.92,.12); cr.fill()
        for i,(x,y) in enumerate(points):
            (cr.move_to if i == 0 else cr.line_to)(x,y)
        cr.set_source_rgba(.68,.4,.88,.85); cr.set_line_width(.8); cr.stroke()

def counters():
    cpu = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    net = [0,0]
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        name, data = line.split(':'); fields = data.split()
        if name.strip() != 'lo': net[0] += int(fields[0]); net[1] += int(fields[8])
    return sum(cpu), cpu[3]+cpu[4], net, time.monotonic()

class Stats:
    def __init__(self):
        self.widget = box(True, 9)
        self.widget.get_style_context().add_class('card')
        self.labels, self.graphs = [], []
        for icon, name in [('󰻠','CPU'),('󰍛','RAM'),('󰋊','Disk'),('󰖩','Net')]:
            row = box(False, 5)
            row.pack_start(label(icon),False,False,0)
            title = label(name); title.set_size_request(30,-1)
            row.pack_start(title,False,False,0)
            value = label('', 'muted', 1); value.set_size_request(63,-1)
            row.pack_start(value,True,True,0)
            graph = Graph(); row.pack_start(graph,False,False,0)
            self.labels.append(value); self.graphs.append(graph)
            self.widget.pack_start(row,False,False,0)
        self.previous = counters()
        GLib.timeout_add_seconds(2,self.update)
        self.update()

    def update(self):
        total,idle,net,now = counters()
        old_total,old_idle,old_net,old_time = self.previous
        self.previous = total,idle,net,now
        cpu = 1-(idle-old_idle)/max(1,total-old_total)
        mem = {parts[0].rstrip(':'):int(parts[1]) for line in Path('/proc/meminfo').read_text().splitlines() if (parts:=line.split())}
        used = mem['MemTotal']-mem['MemAvailable']; ram = used/mem['MemTotal']
        disk = shutil.disk_usage(HOME); fraction = disk.used/disk.total
        down,up = [max(0,(a-b)/max(.01,now-old_time)) for a,b in zip(net,old_net)]
        def rate(n): return f'{n/1048576:.1f}M' if n>=1048576 else f'{n/1024:.0f}K'
        values = [f'{cpu:.0%}',f'{used/1048576:.1f}/{mem["MemTotal"]/1048576:.1f}G',f'{fraction:.0%}',f'↓{rate(down)} ↑{rate(up)}']
        for lbl,text in zip(self.labels,values): lbl.set_text(text)
        for graph,value in zip(self.graphs,[cpu,ram,fraction,min(1,(down+up)/1048576)]): graph.push(value)
        self.widget.set_tooltip_text('Live CPU, memory, home filesystem use and network throughput · 2 second samples')
        return True

class Media:
    def __init__(self):
        self.player = None; self.art_url = None; self.art_generation = 0
        self.widget = box(True, 13); self.widget.get_style_context().add_class('card')
        self.widget.set_size_request(186,152)
        row = box(False, 12)
        self.art = Gtk.Image()
        self.cover = Gtk.Stack()
        self.empty_art = label('󰝚', 'empty-art', .5)
        self.cover.add_named(self.empty_art, 'empty')
        self.cover.add_named(self.art, 'art')
        self.cover.set_visible_child_name('empty')
        self.art.set_pixel_size(52); self.art.set_size_request(76,76)
        self.cover.set_size_request(76,76)
        row.pack_start(self.cover,False,False,0)
        info = box(True,6)
        self.title = label('No music','track'); self.artist = label('Open a music app','muted')
        for item in (self.title,self.artist):
            item.set_ellipsize(Pango.EllipsizeMode.END); item.set_width_chars(1); item.set_max_width_chars(12)
            info.pack_start(item,False,False,0)
        self.progress = Gtk.ProgressBar(); info.pack_start(self.progress,False,False,3)
        times = box(); self.elapsed = label('0:00','muted'); self.duration = label('0:00','muted',1)
        times.pack_start(self.elapsed,True,True,0); times.pack_end(self.duration,True,True,0)
        info.pack_start(times,False,False,0); row.pack_start(info,True,True,0)
        self.widget.pack_start(row,True,True,0)
        controls = box(False, 10)
        controls.pack_start(button('󰝚','Open Spotify',lambda:launch(['spotify']),'icon'),True,True,0)
        self.previous = button('󰒮','Previous track',lambda:self.action('previous'),'icon')
        self.play = button('󰐊','Play / pause',lambda:self.action('play_pause'),'icon')
        self.next = button('󰒭','Next track',lambda:self.action('next'),'icon')
        for control in (self.previous,self.play,self.next): controls.pack_start(control,True,True,0)
        self.widget.pack_end(controls,False,False,0)
        self.manager = Playerctl.PlayerManager()
        self.manager.connect('name-appeared',lambda _,name:self.add(name))
        self.manager.connect('player-vanished',lambda *_:self.choose())
        for name in self.manager.props.player_names: self.add(name)
        GLib.timeout_add_seconds(1,self.update); self.update()

    def add(self,name):
        if name.name == 'playerctld': return
        try:
            player=Playerctl.Player.new_from_name(name); self.manager.manage_player(player)
            player.connect('playback-status',lambda *_:self.choose())
            player.connect('metadata',lambda *_:self.update())
            self.choose()
        except GLib.Error: pass

    def choose(self):
        players = list(self.manager.props.players)
        playing = [p for p in players if p.props.playback_status == Playerctl.PlaybackStatus.PLAYING]
        self.player = next(iter(playing),next(iter(players),None)); self.update()

    def action(self,method):
        try:
            if self.player: getattr(self.player,method)()
        except GLib.Error: pass
        self.update()

    @staticmethod
    def stamp(us):
        seconds=max(0,int(us)//1000000); return f'{seconds//60}:{seconds%60:02}'

    def update(self):
        p=self.player
        for b in (self.previous,self.play,self.next): b.set_sensitive(p is not None)
        if not p:
            self.title.set_text('No music'); self.artist.set_text('Open a music app')
            self.progress.set_fraction(0); self.elapsed.set_text('0:00'); self.duration.set_text('0:00')
            self.play.get_child().set_text('󰐊'); self.set_art(''); return True
        try:
            metadata=p.props.metadata.unpack()
            self.title.set_text(p.get_title() or 'Unknown title'); self.artist.set_text(p.get_artist() or p.props.player_name)
            self.widget.set_tooltip_text(f'{p.get_title() or ""} — {p.get_artist() or ""}')
            length=metadata.get('mpris:length',0); position=p.get_position()
            self.progress.set_fraction(max(0,min(1,position/length)) if length else 0)
            self.elapsed.set_text(self.stamp(position)); self.duration.set_text(self.stamp(length))
            self.play.get_child().set_text('󰏤' if p.props.playback_status == Playerctl.PlaybackStatus.PLAYING else '󰐊')
            self.set_art(metadata.get('mpris:artUrl',''))
        except GLib.Error: pass
        return True

    def set_art(self,url):
        if url == self.art_url: return
        self.art_url=url; self.art_generation+=1; generation=self.art_generation
        self.cover.set_visible_child_name('empty')
        if not url: return
        def fetch():
            try:
                parsed=urlparse(url)
                if parsed.scheme=='file': path=Path(unquote(parsed.path))
                elif parsed.scheme in ('https','http'):
                    # Cover art is fetched off the GTK thread and is bounded in size/time.
                    import urllib.request, hashlib
                    path=HOME/'.cache/wanglin-rice'/('art-'+hashlib.sha256(url.encode()).hexdigest()+'.img')
                    path.parent.mkdir(parents=True,exist_ok=True)
                    if not path.exists():
                        with urllib.request.urlopen(url,timeout=5) as response:
                            data=response.read(5*1024*1024+1)
                            if len(data)>5*1024*1024: return
                            path.write_bytes(data)
                else: return
                pix=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),76,76,True)
                GLib.idle_add(self.apply_art,generation,pix)
            except Exception: pass
        POOL.submit(fetch)

    def apply_art(self,generation,pix):
        if generation==self.art_generation:
            self.art.set_from_pixbuf(pix)
            self.cover.set_visible_child_name('art')
        return False

def desktop():
    state=HOME/'.local/state/wanglin-rice'; state.mkdir(parents=True,exist_ok=True)
    lock=open(state/'desktop.lock','a+')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: return
    lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
    top,right,bottom=GtkLayerShell.Edge.TOP,GtkLayerShell.Edge.RIGHT,GtkLayerShell.Edge.BOTTOM
    widgets=surface('wanglin-widgets',GtkLayerShell.Layer.BOTTOM,[top,right],{top:65,right:13})
    column=box(True,12); media=Media(); stats=Stats()
    column.pack_start(media.widget,False,False,0); column.pack_start(stats.widget,False,False,0)
    widgets.add(column); widgets.show_all()
    dock=surface('wanglin-dock',GtkLayerShell.Layer.TOP,[bottom],{bottom:7})
    GtkLayerShell.auto_exclusive_zone_enable(dock)
    row=box(); row.get_style_context().add_class('dock')
    apps=[('󰞷','Terminal',['kitty']),('󰉋','Files',['dolphin']),('󰈹','Firefox',['firefox']),('󰗃','YouTube',['xdg-open','https://www.youtube.com/']),('󰓇','Spotify',['spotify']),('󰖣','WhatsApp (web)',['xdg-open','https://web.whatsapp.com/']),('󰒊','Telegram (web)',['xdg-open','https://web.telegram.org/']),('󰒓','Appearance settings',['nwg-look'])]
    for icon,tip,argv in apps: row.pack_start(button(icon,tip,lambda a=argv:launch(a)),False,False,0)
    dock.add(row); dock.show_all()
    signal.signal(signal.SIGTERM,lambda *_:Gtk.main_quit())
    Gtk.main(); POOL.shutdown(wait=False,cancel_futures=True)

if __name__=='__main__':
    GLib.set_prgname('wanglin-desktop')
    css=Gtk.CssProvider(); css.load_from_path(str(ROOT/'desktop/style.css'))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_USER+1)
    desktop()
