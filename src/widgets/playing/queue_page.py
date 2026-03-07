# queue_page.py

from gi.repository import Gtk, Adw, GObject, GLib
from ..song import SongRow
from ...navidrome import models, get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/queue_page.ui')
class PlayingQueuePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingQueuePage'

    song_list_el = Gtk.Template.Child()

    def replace_queue(self, songs:list, current_id:str=None):
        integration = get_current_integration()
        for row in list(self.song_list_el.list_el):
            GLib.idle_add(self.song_list_el.list_el.remove, row)
        if len(songs) > 0:
            if current_id is None:
                current_id = songs[0]

            for song_id in songs:
                GLib.idle_add(self.song_list_el.list_el.append,
                    SongRow(
                        song_id,
                        draggable=True,
                        removable=True
                    )
                )
        GLib.idle_add(integration.loaded_models['currentSong'].set_property, 'songId', current_id)

    def play_next(self, songs:list):
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId
        if len(list(self.song_list_el.list_el)) == 0 or not current_song_id:
            self.replace_queue(songs)
        else:
            current_song_index = -1
            for i, row in enumerate(list(self.song_list_el.list_el)):
                if row.id == current_song_id:
                    current_song_index = i + 1
            songs.reverse()
            for song_id in songs:
                self.song_list_el.list_el.insert(
                    SongRow(
                        song_id,
                        draggable=True,
                        removable=True
                    ),
                    current_song_index
                )


