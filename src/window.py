# window.py
#
# Copyright 2026 Jeffry Samuel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Adw, GLib, Gst

from . import navidrome, actions

@Gtk.Template(resource_path='/com/jeffser/Nocturne/window.ui')
class NocturneWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturneWindow'

    breakpoint_el = Gtk.Template.Child()
    main_navigationview = Gtk.Template.Child()
    home_page = Gtk.Template.Child()
    main_bottom_sheet = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def close_request(self, window):
        integration = navidrome.get_current_integration()
        id_list = self.queue_page.song_list_el.get_all_ids()
        current_song = integration.loaded_models.get('currentSong')
        integration.savePlayQueue(id_list, current_song.songId, current_song.positionSeconds * 1000)

    def create_action(self, callback:callable, parameter_type:str="s"):
        self.get_application().create_action(
            name=callback.__name__,
            callback=lambda at, va, cb=callback, win=self: cb(win, va.unpack()),
            parameter_type=GLib.VariantType.new(parameter_type) if parameter_type else None
        )


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        """
        Actions to implement:

        play_artist_radio

        add_song_to_playlist
        add_album_to_playlist
        """

        self.create_action(actions.toggle_star)

        self.create_action(actions.play_song)
        self.create_action(actions.play_song_next)
        self.create_action(actions.play_song_later)

        self.create_action(actions.show_album)
        self.create_action(actions.play_album)
        self.create_action(actions.play_album_next)
        self.create_action(actions.play_album_later)
        self.create_action(actions.play_album_shuffle)

        self.create_action(actions.show_playlist)
        self.create_action(actions.play_playlist)
        self.create_action(actions.play_playlist_next)
        self.create_action(actions.play_playlist_later)
        self.create_action(actions.play_playlist_shuffle)

        self.create_action(actions.show_artist)

        integration = navidrome.get_current_integration()
        current_id, song_list = integration.getPlayQueue()
        if len(song_list) > 0:
            GLib.idle_add(self.queue_page.replace_queue, song_list, current_id)
            GLib.idle_add(lambda: self.playing_page.player.set_state(Gst.State.PAUSED) and False)

