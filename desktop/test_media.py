"""Integration smoke test on a private D-Bus: player arrival, commands, loss."""
import os
from pathlib import Path
import subprocess
import sys
import time

if len(sys.argv)>1 and sys.argv[1]=='service':
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBusGMainLoop(set_as_default=True)
    bus=dbus.SessionBus()
    # Export the object before acquiring the well-known name.
    player_iface='org.mpris.MediaPlayer2.Player'
    class Player(dbus.service.Object):
        status='Playing'; track=1
        def props(self):
            return {'PlaybackStatus':self.status,'LoopStatus':'None','Rate':1.,'Shuffle':False,'Volume':1.,'Position':dbus.Int64(42000000),'MinimumRate':1.,'MaximumRate':1.,'CanGoNext':True,'CanGoPrevious':True,'CanPlay':True,'CanPause':True,'CanSeek':False,'CanControl':True,'Metadata':dbus.Dictionary({'mpris:trackid':dbus.ObjectPath('/track/'+str(self.track)),'mpris:length':dbus.Int64(180000000),'xesam:title':f'Track {self.track}','xesam:artist':dbus.Array(['Test artist'],signature='s')},signature='sv')}
        @dbus.service.method('org.freedesktop.DBus.Properties',in_signature='s',out_signature='a{sv}')
        def GetAll(self,iface):
            return self.props() if iface==player_iface else {'Identity':'Wang Lin test','CanQuit':False,'CanRaise':False,'HasTrackList':False,'SupportedUriSchemes':dbus.Array([],signature='s'),'SupportedMimeTypes':dbus.Array([],signature='s')}
        @dbus.service.method('org.freedesktop.DBus.Properties',in_signature='ss',out_signature='v')
        def Get(self,iface,key): return self.GetAll(iface)[key]
        @dbus.service.signal('org.freedesktop.DBus.Properties',signature='sa{sv}as')
        def PropertiesChanged(self,interface,changed,invalidated): pass
        @dbus.service.method(player_iface)
        def PlayPause(self):
            self.status='Paused' if self.status=='Playing' else 'Playing'
            self.PropertiesChanged(player_iface,{'PlaybackStatus':self.status},[])
        @dbus.service.method(player_iface)
        def Next(self):
            self.track+=1; self.PropertiesChanged(player_iface,{'Metadata':self.props()['Metadata']},[])
        @dbus.service.method(player_iface)
        def Previous(self):
            self.track-=1; self.PropertiesChanged(player_iface,{'Metadata':self.props()['Metadata']},[])
    obj=Player(bus,'/org/mpris/MediaPlayer2')
    name=dbus.service.BusName('org.mpris.MediaPlayer2.wanglintest',bus)
    GLib.MainLoop().run()
else:
    from shell import Media, Stats, GLib, Playerctl
    def spin(predicate,seconds=6):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            while GLib.MainContext.default().iteration(False): pass
            if predicate(): return
            time.sleep(.03)
        raise AssertionError('Timed out waiting for player state')
    card=Media(); assert card.title.get_text()=='No music'
    child=subprocess.Popen([sys.executable,__file__,'service'])
    try:
        spin(lambda:card.title.get_text()=='Track 1')
        assert card.artist.get_text()=='Test artist'
        assert card.elapsed.get_text()=='0:42'
        assert card.duration.get_text()=='3:00'
        card.play.clicked()
        spin(lambda:card.player.props.playback_status==Playerctl.PlaybackStatus.PAUSED)
        card.next.clicked(); spin(lambda:card.title.get_text()=='Track 2')
        card.previous.clicked(); spin(lambda:card.title.get_text()=='Track 1')
        child.terminate(); child.wait(timeout=3)
        spin(lambda:card.title.get_text()=='No music')
        assert not card.play.get_sensitive()
        stats=Stats(); assert len(stats.labels)==4
        assert all(lbl.get_text() for lbl in stats.labels)
        print('PASS: player arrival, metadata, progress, play/pause, next, previous, player removal, live stats',flush=True)
    finally:
        if child.poll() is None: child.terminate(); child.wait(timeout=3)
