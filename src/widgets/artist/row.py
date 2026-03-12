# row.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/row.ui')
class ArtistRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneArtistRow'

    avatar_el = Gtk.Template.Child()
    play_shuffle_el = Gtk.Template.Child()
    play_radio_el = Gtk.Template.Child()

    # using this instead of __init__ to accommodate listview
    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_shuffle_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_radio_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)
        integration.connect_to_model(self.id, 'albumCount', self.update_album_count)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(coverArt, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.avatar_el.set_custom_image, paintable)
            else:
                GLib.idle_add(self.avatar_el.set_custom_image, None)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.set_title(GLib.markup_escape_text(name))
        self.set_name(GLib.markup_escape_text(name))

    def update_album_count(self, albumCount:int):
        if albumCount == 1:
            self.set_subtitle(_("1 Album"))
        else:
            self.set_subtitle(_("{} Albums").format(albumCount))

