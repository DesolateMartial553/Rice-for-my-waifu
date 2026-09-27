#!/usr/bin/env python3
"""Compact, navigable image browser for the reference desktop."""
import os
from pathlib import Path
import sys
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, Gio
from shell import ROOT, HOME, label, button, box, launch

class Gallery(Gtk.Window):
    def __init__(self):
        super().__init__(title='Pictures · Wang Lin')
        self.set_wmclass('wanglin-gallery','wanglin-gallery')
        self.set_decorated(False); self.set_default_size(484,226)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.path=HOME/'Pictures'; self.history=[]; self.monitor=None
        outer=box(True,6); outer.get_style_context().add_class('gallery'); self.add(outer)
        header=box(False,4); self.title_label=label()
        self.title_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        header.pack_start(self.title_label,True,True,0)
        header.pack_end(button('󰋙','Open folder in Dolphin',lambda:launch(['dolphin',self.path])),False,False,0)
        header.pack_end(button('↑','Parent folder (Alt+Up)',lambda:self.navigate(self.path.parent)),False,False,0)
        header.pack_end(button('‹','Back (Alt+Left)',self.back),False,False,0)
        outer.pack_start(header,False,False,0)
        content=box(False,6); sidebar=box(True,1); sidebar.set_size_request(122,-1)
        sidebar.get_style_context().add_class('sidebar'); self.places=[]
        for icon,name,path in [('󰈙','Documents',HOME/'Documents'),('󰇚','Downloads',HOME/'Downloads'),('󰎆','Music',HOME/'Music'),('󰉏','Pictures',HOME/'Pictures'),('󰕧','Videos',HOME/'Videos'),('󰸉','Wallpapers',HOME/'Pictures/Wallpapers'),('󰒓','Configs',HOME/'.config')]:
            b=button(f'{icon}  {name}',str(path),lambda p=path:self.navigate(p)); b.get_child().set_xalign(0)
            sidebar.pack_start(b,False,False,0); self.places.append((b,path))
        content.pack_start(sidebar,False,False,0)
        self.flow=Gtk.FlowBox(); self.flow.set_max_children_per_line(3); self.flow.set_min_children_per_line(3)
        self.flow.set_row_spacing(5); self.flow.set_column_spacing(5); self.flow.set_homogeneous(True)
        self.flow.set_valign(Gtk.Align.START); self.flow.set_activate_on_single_click(False)
        self.flow.connect('child-activated',self.open_item)
        scroll=Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); scroll.add(self.flow)
        content.pack_start(scroll,True,True,0); outer.pack_start(content,True,True,0)
        self.status=label('','muted'); outer.pack_end(self.status,False,False,0)
        self.connect('key-press-event',self.key); self.connect('destroy',Gtk.main_quit)
        self.navigate(HOME/'Pictures/Wallpapers')

    def key(self,_,event):
        if event.state & Gdk.ModifierType.MOD1_MASK:
            if event.keyval==Gdk.KEY_Up: self.navigate(self.path.parent); return True
            if event.keyval==Gdk.KEY_Left: self.back(); return True
        if event.keyval==Gdk.KEY_F5: self.refresh(); return True
        return False

    def back(self):
        if self.history: self.navigate(self.history.pop(),False)

    def navigate(self,path,remember=True):
        if not path.is_dir(): return
        if remember and self.path!=path: self.history.append(self.path)
        self.path=path
        if self.monitor: self.monitor.cancel()
        self.monitor=Gio.File.new_for_path(str(path)).monitor_directory(Gio.FileMonitorFlags.NONE,None)
        self.monitor.connect('changed',lambda *_:self.refresh())
        self.refresh()

    def refresh(self):
        for child in self.flow.get_children(): self.flow.remove(child)
        try: files=sorted((p for p in self.path.iterdir() if not p.name.startswith('.')),key=lambda p:(not p.is_dir(),p.name.casefold()))
        except OSError as e: self.status.set_text(str(e)); return
        self.title_label.set_text(f'{os.getenv("USER","you")}  {str(self.path).replace(str(HOME),"~",1)}')
        for b,p in self.places:
            context=b.get_style_context(); context.remove_class('selected')
            if p==self.path: context.add_class('selected')
        for p in files[:300]:
            tile=box(True,2); tile.set_size_request(94,72)
            try:
                if p.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.gif'): raise ValueError()
                pix=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(p),100,67,True)
                img=Gtk.Image.new_from_pixbuf(pix)
            except (GLib.Error,ValueError): img=Gtk.Image.new_from_icon_name('folder' if p.is_dir() else 'text-x-generic',Gtk.IconSize.DIALOG)
            img.set_size_request(98,57); tile.pack_start(img,True,True,0)
            name=label(p.name,'filename',.5); name.set_ellipsize(Pango.EllipsizeMode.END); name.set_max_width_chars(15)
            tile.pack_end(name,False,False,0); tile.set_tooltip_text(p.name)
            self.flow.add(tile); tile.get_parent().file_path=p
        self.status.set_text(f'{len(files)} items' + (' · first 300 shown' if len(files)>300 else '')+'  ·  double-click to open')
        self.flow.show_all()

    def open_item(self,_,child):
        p=child.file_path
        if p.is_dir(): self.navigate(p)
        else: launch(['xdg-open',p])

GLib.set_prgname('wanglin-gallery')
css=Gtk.CssProvider(); css.load_from_path(str(ROOT/'desktop/style.css'))
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_USER+1)
window=Gallery(); window.show_all(); Gtk.main()
