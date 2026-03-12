# artist.py

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from ...navidrome import get_current_integration, models
from ..artist import ArtistRow
import re

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/artists.ui')
class ArtistsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistsPage'

    list_el = Gtk.Template.Child()
    loaded = False

    def reload(self):
        # call in different thread
        if self.loaded:
            return
        self.loaded = True
        for row in list(self.list_el):
            GLib.idle_add(self.list_el.remove, row)
        integration = get_current_integration()
        indexes = integration.getArtistsIndexes()
        for name, artists in indexes.items():
            index_row = Gtk.ListBoxRow(
                child=Gtk.Label(
                    label=name,
                    css_classes=['title-3', 'p10', 'dimmed'],
                    halign=Gtk.Align.START
                ),
                activatable=False
            )
            GLib.idle_add(self.list_el.append, index_row)
            for id in artists:
                GLib.idle_add(self.list_el.append, ArtistRow(id))

    @Gtk.Template.Callback()
    def on_search_changed(self, search_entry):
        query = search_entry.get_text()
        for child in list(self.list_el):
            child.set_visible(child.get_name() != 'GtkListBoxRow' and re.search(query, child.get_name(), re.IGNORECASE))
            
