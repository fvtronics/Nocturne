# selector_row.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...integrations import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/selector_row.ui')
class PlaylistSelectorRow(Adw.ActionRow):
    __gtype_name__ = 'NocturnePlaylistSelectorRow'

    cover_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id)
        super().__init__()

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)

    def update_cover(self, paintable:Gdk.Paintable=None):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(48)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-note-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_name(self, name:str):
        self.set_title(name)
        self.set_name(name)
        self.set_tooltip_text(_("Add songs to '{}'").format(name))

    def update_song_count(self, songCount:int):
        if songCount == 1:
            self.set_subtitle(_("1 Song"))
        else:
            self.set_subtitle(_("{} Songs").format(songCount))

