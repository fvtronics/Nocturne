# footer.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject
from ...navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/footer.ui')
class PlayingFooter(Gtk.Overlay):
    __gtype_name__ = 'NocturnePlayingFooter'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()

    def setup(self):
        # Called after login
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        song = integration.loaded_models.get(song_id)
        if song:
            self.title_el.set_label(song.title)
            self.artist_el.set_label(song.artists[0].get('name'))
            threading.Thread(target=self.update_cover_art).start()

    def position_changed(self, positionSeconds:float):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        song = integration.loaded_models.get(song_id)
        if song:
            self.progress_el.set_fraction(positionSeconds / song.duration)

    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        if song_id:
            paintable = integration.getCoverArt(song_id, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
            else:
                GLib.idle_add(self.cover_el.set_from_paintable, None)

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.get_root().playing_page.play_clicked(button)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.get_root().playing_page.pause_clicked(button)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.get_root().playing_page.next_clicked(button)

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.get_root().playing_page.previous_clicked(button)
