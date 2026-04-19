# player.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio, Gst

from mpris_server.adapters import MprisAdapter
from mpris_server.events import EventAdapter
from mpris_server.server import Server
from mpris_server import Metadata, ValidMetadata, Track, Position, Volume, Rate, PlayState, DbusObj, MetadataObj, ActivePlaylist, PlaylistEntry, MprisInterface

from ...constants import MPRIS_COVER_PATH
from ...integrations import get_current_integration, models
from ..lyrics import LyricsDialog
from urllib.parse import urlparse
import threading, os

Gst.init(None)

class PlayerAdapter(MprisAdapter):
    # Implementations from https://github.com/alexdelorenzo/mpris_server/blob/master/src/mpris_server/adapters.py

    def __init__(self, player):
        self.player = player
        super().__init__()

    # -- RootAdapter --

    def get_desktop_entry(self) -> str:
        return "com.jeffser.Nocturne"

    def can_fullscreen(self) -> bool:
        return False

    def can_quit(self) -> bool:
        return True

    def can_raise(self) -> bool:
        return True

    def has_tracklist(self) -> bool:
        return False

    def quit(self):
        integration = get_current_integration()
        if integration:
            integration.loaded_models.get('currentSong').set_property('songId', None)

    def set_fullscreen(self, value:bool):
        # def can_fullscreen returns false
        pass

    def set_raise(self, value:bool):
        # TODO idk maybe raise the window and open the sheet?
        pass

    # -- PlayerAdapter --

    def metadata(self) -> ValidMetadata:
        integration = get_current_integration()
        if not integration:
            return MetadataObj()
        current_song_model = integration.loaded_models.get('currentSong')
        song = integration.loaded_models.get(current_song_model.get_property('songId'))
        if not song:
            return MetadataObj()

        return MetadataObj(
            album=song.get_property('album'),
            art_url='file://{}'.format(MPRIS_COVER_PATH),
            artists=[urlparse(song.get_property('streamUrl')).netloc.capitalize()] if song.get_property('isRadio') and song.get_property('streamUrl') else [a.get('name') for a in song.get_property('artists')],
            as_text=[song.get_property('title')],
            length=song.get_property('duration')*1000000,
            title=song.get_property('title'),
            track_id='/com/jeffser/Nocturne/track/{}'.format(song.get_property('id')),
            track_number=0
        )

    def can_control(self) -> bool:
        return True

    def can_go_next(self) -> bool:
        return True

    def can_go_previous(self) -> bool:
        return True

    def can_pause(self) -> bool:
        return True

    def can_play(self) -> bool:
        return True

    def can_seek(self) -> bool:
        return True

    def get_current_position(self) -> Position:
        # Unused
        # Microseconds
        success, position = self.player.gst.query_position(Gst.Format.TIME)
        return Position(position/1000) # Microsecond

    def get_rate(self) -> Rate:
        return Rate(1)

    def get_maximum_rate(self) -> Rate:
        return Rate(1)

    def get_minimum_rate(self) -> Rate:
        return Rate(1)

    def get_next_track(self) -> Track:
        pass

    def get_playstate(self) -> PlayState:
        success, state, pending = self.player.gst.get_state(0)
        return PlayState.PLAYING if state == Gst.State.PLAYING else PlayState.PAUSED

    def get_previous_track(self) -> Track:
        pass

    def get_shuffle(self) -> bool:
        # Shuffle isn't a thing in Nocturne the queue is what it is for the most part
        return False

    def get_volume(self) -> Volume:
        return Volume(self.player.gst.get_property("volume"))

    def is_mute(self) -> bool:
        return self.player.gst.get_property("volume") == 0

    def is_playlist(self) -> bool:
        # Again, the queue is what it is, I'm not sure if I can get this info
        return False

    def is_repeating(self) -> bool:
        return self.player.settings.get_value('playback-mode').unpack() == 'repeat-one'

    def next(self):
        self.player.handle_song_change_request("next")

    def open_uri(self, uri:str):
        # ?
        pass

    def pause(self):
        self.player.gst.set_state(Gst.State.PAUSED)

    def play(self):
        self.player.gst.set_state(Gst.State.PLAYING)

    def previous(self):
        self.player.handle_song_change_request("previous")

    def resume(self):
        self.player.gst.set_state(Gst.State.PLAYING)

    def seek(self, time:Position, track_id: DbusObj | None = None):
        self.player.gst.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            time*1000
        )
        self.player.emit_changes(self.player.mpris.player, changes=['Position'])

    def set_maximum_rate(self, value:Rate):
        # Idk
        pass

    def set_minimum_rate(self, value:Rate):
        # Idk
        pass

    def set_mute(self, value:bool):
        # TODO I'm not sure what to do when unmuting, should I save previous volume?
        pass

    def set_rate(self, value:Rate):
        # Idk
        pass

    def set_repeating(self, value:bool):
        self.player.settings.set_string('playback-mode', 'repeat-one' if value else 'consecutive')

    def set_shuffle(self, value:bool):
        # TODO not sure how I could implement this
        pass

    def set_volume(self, value:Volume):
        self.player.settings.set_double('volume', value)

    def stop(self):
        self.player.gst.set_state(Gst.State.NULL)

    def activate_playlist(self, id:DbusObj):
        pass

    def get_active_playlist(self) -> ActivePlaylist:
        #TODO
        pass

    def get_playlists(self, index:int, max_count:int, order:str, reverse:bool) -> list[PlaylistEntry]:
        #TODO
        return []

    def add_track(self, uri:str, after_track:DbusObj, set_as_current:bool):
        pass

    def can_edit_tracks(self) -> bool:
        return False

    def get_tracks(self) -> list[DbusObj]:
        return []

    def get_tracks_metadata(self, track_ids:list[DbusObj]) -> list[Metadata]:
        return []

    def go_to(self, track_id:DbusObj):
        pass

    def remove_track(self, track_id:DbusObj):
        pass

class Player(EventAdapter):
    __gtype_name__ = 'NocturnePlayer'

    def __init__(self, application):
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        volume = max(self.settings.get_value("volume").unpack(), 0.2)
        self.settings.set_double("volume", volume)
        self.application = application
        self.gst = Gst.ElementFactory.make("playbin", "music-player")

        self.bin = Gst.Bin.new("audio-filter-bin")

        self.equalizer = Gst.ElementFactory.make("equalizer-nbands", "equalizer")
        self.bin.add(self.equalizer)
        self.equalizer.set_property("num-bands", 6)
        for i in range(self.equalizer.get_property("num-bands")):
            band = self.equalizer.get_child_by_index(i)
            self.settings.bind(
                "eq-band-{}".format(i),
                band,
                "gain",
                Gio.SettingsBindFlags.DEFAULT
            )

        self.spectrum = Gst.ElementFactory.make("spectrum", "spectrum-analyzer")
        self.bin.add(self.spectrum)
        self.settings.bind(
            "visualizer-bar-n",
            self.spectrum,
            "bands",
            Gio.SettingsBindFlags.DEFAULT
        )
        self.spectrum.set_property("threshold", -60)
        self.spectrum.set_property("post-messages", True)
        self.spectrum.set_property("message-magnitude", True)
        self.spectrum.set_property("multi-channel", True)
        self.spectrum.set_property("interval", 50000000)

        self.equalizer.link(self.spectrum)
        sink_pad = Gst.GhostPad.new("sink", self.equalizer.get_static_pad("sink"))
        src_pad = Gst.GhostPad.new("src", self.spectrum.get_static_pad("src"))
        self.bin.add_pad(sink_pad)
        self.bin.add_pad(src_pad)
        self.gst.set_property("audio-filter", self.bin)

        self.settings.bind(
            "volume",
            self.gst,
            "volume",
            Gio.SettingsBindFlags.DEFAULT
        )

        self.bus = self.gst.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

        self.adapter = PlayerAdapter(self)
        self.mpris = Server("com.jeffser.Nocturne", adapter=self.adapter)
        super().__init__(root=self.mpris.root, player=self.mpris.player)
        self.interface = MprisInterface("Nocturne", self.adapter)
        self.mpris_published = False
        try:
            self.mpris.publish()
            self.mpris_published = True
        except Exception as e:
            print("Failed to publish MPRIS:", e)
        GLib.timeout_add(64, self.update_stream_progress)

        self.last_song_id = None
        self.pause_next_change = False
        self.last_gst_state_type = -1
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)#lambda song_id: threading.Thread(target=self.song_changed, args=(song_id,)).start())

    # ---

    def handle_new_state(self, state):
        integration = get_current_integration()
        if not integration.loaded_models.get('currentSong').get_property('seeking'):
            is_playing = (state == Gst.State.PLAYING)
            stack_page_name = 'pause' if is_playing else 'play'
            integration.loaded_models.get("currentSong").set_property("buttonState", stack_page_name)
            if root := self.application.get_active_window():
                if is_playing:
                    root.add_css_class('playing')
                else:
                    root.remove_css_class('playing')
            self.emit_changes(self.mpris.player, changes=['Metadata', 'PlaybackStatus'])

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        self.gst.set_state(Gst.State.READY)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        mode = self.settings.get_value('playback-mode').unpack()

        if action != "end" and mode == "repeat-one":
            mode = "consecutive"

        if action == "previous" and integration.loaded_models.get('currentSong').get_property('positionSeconds') > 5:
            self.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                0
            )
            self.gst.set_state(Gst.State.PLAYING)
            return

        id_list = [so.get_string() for so in integration.loaded_models.get('currentSong').get_property('queueModel')]

        integration.loaded_models.get('currentSong').set_property('magnitudes', {})
        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models.get('currentSong').set_property('songId', id_list[0])

            elif mode in ('consecutive', 'repeat-all'):
                try:
                    next_index = id_list.index(current_song_id) + (1 if action in ("next", "end") else -1)
                except ValueError: # index was not found
                    next_index = 0

                if mode == 'consecutive':
                    if next_index < 0:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[0])
                    elif next_index < len(id_list):
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[next_index])
                    elif self.settings.get_value('auto-play').unpack():
                        threading.Thread(target=self.auto_play).start()
                elif mode == 'repeat-all':
                    if next_index < len(id_list) and next_index >= 0:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[next_index])
                    else:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[0])
                        self.gst.seek_simple(
                            Gst.Format.TIME,
                            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                            0
                        )
                        self.gst.set_state(Gst.State.PLAYING)

            elif mode == 'repeat-one':
                self.gst.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    0
                )
                self.gst.set_state(Gst.State.PLAYING)
        else:
            integration.loaded_models.get('currentSong').set_property('songId', None)

    def auto_play(self):
        if integration := get_current_integration():
            generated_queue = integration.loaded_models.get('currentSong').get_property('generatedQueue')
            if generated_queue.get_property('n-items') == 0:
                self.application.get_active_window().activate_action(
                    "app.generate_auto_play_queue",
                    GLib.Variant('b', True)
                )
            else:
                self.application.get_active_window().activate_action(
                    "app.play_songs",
                    GLib.Variant("as", [so.get_string() for so in list(generated_queue)])
                )

    def handle_spectrum_message(self, struct):
        serialized = struct.serialize_full(Gst.SerializeFlags.NONE)
        channels_str = serialized.split('< < ')[1].split(' > >;')[0].replace('(float)', '').split(' >, < ')
        channels = []
        for c in channels_str:
            channels.append([float(m.strip()) for m in c.split(', ')[:int(self.spectrum.get_property('bands')/2)]])
        integration = get_current_integration()
        timestamp = struct.get_uint64('stream-time')[1] / 1000000000
        magnitudes = [(60-abs(m)) / 60 * self.settings.get_value("volume").unpack() for m in channels[0] + list(reversed(channels[1]))]
        if timestamp and magnitudes:
            if not integration.loaded_models.get('currentSong').get_property('magnitudes'):
                integration.loaded_models.get('currentSong').set_property('magnitudes', {})
            integration.loaded_models.get('currentSong').magnitudes[timestamp] = magnitudes

    def on_message(self, bus, message):
        if message.src == self.spectrum:
            struct = message.get_structure()
            if struct and struct.get_name() == "spectrum" and self.settings.get_value('show-visualizer').unpack():
                threading.Thread(target=self.handle_spectrum_message, args=(struct,)).start()
        else:
            if message.type == Gst.MessageType.STATE_CHANGED:
                old_state, new_state, pending_state = message.parse_state_changed()
                if new_state != self.last_gst_state_type:
                    self.handle_new_state(new_state)
                    self.last_gst_state_type = new_state
            elif message.type == Gst.MessageType.EOS:
                self.handle_song_change_request("end")
            elif message.type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print("Error: {}".format(err.message))

    def update_stream_progress(self):
        if integration := get_current_integration():
            if integration.loaded_models.get('currentSong').get_property('seeking'):
                return True
            success, position = self.gst.query_position(Gst.Format.TIME)
            current_song = integration.loaded_models.get('currentSong')
            if success:
                seconds = position / Gst.SECOND
                current_song.set_property('positionSeconds', seconds)
        return True


    def restore_play_queue(self):
        integration = get_current_integration()
        songs = self.application.external_songs
        if songs:
            for song in songs:
                integration.loaded_models[song.id] = song
            song_list = [s.id for s in songs]
            current_id = song_list[0]
        else:
            current_id, song_list = integration.getPlayQueue()
            for song in song_list:
                integration.verifySong(song)
        if len(song_list) > 0:
            if len(self.application.external_songs) == 0:
               self.pause_next_change = True
            self.application.get_active_window().activate_action(
                "app.play_songs",
                GLib.Variant("as", song_list)
            )
        self.application.external_songs = []

    def song_changed(self, song_id:str):
        integration = get_current_integration()

        def async_load():
            stream_url = integration.get_stream_url(song_id)
            self.gst.set_state(Gst.State.READY)
            self.gst.set_property('uri', stream_url)
            if self.pause_next_change:
                self.gst.set_state(Gst.State.PAUSED)
                self.pause_next_change = False
            else:
                self.gst.set_state(Gst.State.PLAYING)

        if song_id:
            if song_id != self.last_song_id:
                threading.Thread(target=async_load).start()
                threading.Thread(target=integration.scrobble, args=(song_id,)).start()
                self.last_song_id = song_id
        else:
            self.gst.set_state(Gst.State.NULL)


