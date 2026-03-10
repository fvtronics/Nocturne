# lyrics_page.py

from gi.repository import Gtk, Adw, GObject, GLib, Gio, Pango, Gst
from ..song import SongRow
from ...navidrome import models, get_current_integration
from ...constants import DATA_DIR
import threading, os

class LyricData(GObject.Object):
    __gtype_name__ = 'NocturneLyricData'

    content = GObject.Property(type=str)
    ms = GObject.Property(type=int)

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/lyrics_page.ui')
class PlayingLyricsPage(Gtk.Stack):
    __gtype_name__ = 'NocturnePlayingLyricsPage'

    plain_label_el = Gtk.Template.Child()
    lrc_list_el = Gtk.Template.Child()
    lrc_model_parent = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()

    def __init__(self):
        integration = get_current_integration()
        self.current_row = None
        super().__init__()
        integration.connect_to_model('currentSong', 'songId', self.song_changed, use_gtk_thread=False)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed, use_gtk_thread=False)
        self.code_is_selecting = False # used so that `on_lrc_selection` is only executed when manually selecting

    def prepare_lrc(self, lrc_str:str) -> list:
        lrc_lines = []
        for line in lrc_str.split('\n'):
            if line.startswith('['):
                timestamp, content = line[1:].split(']')[:2]
                minutes_str, rest = timestamp.split(':')
                seconds_str, ms_str = rest.split('.')
                minutes = int(minutes_str)
                seconds = int(seconds_str)
                ms = int(ms_str)
                if len(ms_str) == 2:
                    ms *= 10
                timing = (minutes * 60000) + (seconds * 1000) + ms
                lrc_lines.append({'ms': timing, 'content': content.strip()})
        return lrc_lines

    def get_lyrics(self, song_id:str, download:bool) -> dict:
        # returns these keys:
        # type (instrumental, lrc, plain, not-found, not-found-locally)
        # content (none (instrumental/not-found/not-found-locally), list (lrc), str (plain))

        integration = get_current_integration()
        model = integration.loaded_models.get(song_id)

        if not model:
            return {'type': 'not-found', 'content': None}

        lyrics_dir = os.path.join(DATA_DIR, 'lyrics')
        os.makedirs(lyrics_dir, exist_ok=True)

        file_name_without_ext = '{}|{}|{}|{}'.format(
            model.title,
            model.artist,
            model.album or model.title,
            model.duration
        )
        lrc_path = os.path.join(lyrics_dir, file_name_without_ext+'.lrc')
        plain_lyrics_path = os.path.join(lyrics_dir, file_name_without_ext+'.txt')

        if os.path.isfile(lrc_path):
            with open(lrc_path, 'r') as f:
                return {'type': 'lrc', 'content': self.prepare_lrc(f.read())}

        if os.path.isfile(plain_lyrics_path):
            with open(plain_lyrics_path, 'r') as f:
                content = f.read()
                if content == '[instrumental]':
                    return {'type': 'instrumental', 'content': None}
                else:
                    return {'type': 'plain', 'content': content}

        if not download:
            return {'type': 'not-found-locally', 'content': None}

        lyrics = integration.getLyrics(
            track_name=model.title,
            artist_name=model.artist,
            album_name=model.album or model.title,
            duration=model.duration
        )

        if lyrics.get('statusCode') == '404':
            return {'type': 'not-found', 'content': None}

        if lyrics.get('instrumental'):
            with open(plain_lyrics_path, 'w+') as f:
                f.write('[instrumental]')
            return {'type': 'instrumental', 'content': None}

        if lyrics.get('syncedLyrics'):
            with open(lrc_path, 'w+') as f:
                f.write(lyrics.get('syncedLyrics'))
            return {'type': 'lrc', 'content': self.prepare_lrc(lyrics.get('syncedLyrics'))}

        if lyrics.get('plainLyrics'):
            with open(plain_lyrics_path, 'w+') as f:
                f.write(lyrics.get('plainLyrics'))
            return {'type': 'plain', 'content': lyrics.get('plainLyrics')}

        return {'type': 'not-found', 'content': None}

    def song_changed(self, song_id:str, download:bool=False):
        GLib.idle_add(self.set_visible_child_name, 'loading')
        def update_lyrics():
            lyrics = self.get_lyrics(song_id, download)
            GLib.idle_add(self.set_visible_child_name, lyrics.get('type'))

            if lyrics.get('type') == 'plain':
                GLib.idle_add(self.plain_label_el.set_label, lyrics.get('content'))
            elif lyrics.get('type') == 'lrc':
                self.lrc_model_parent.set_model(Gio.ListStore(item_type=LyricData))
                row = LyricData(
                    ms=0,
                    content=''
                )
                GLib.idle_add(self.lrc_model_parent.get_model().append, row)
                for line in lyrics.get('content'):
                    row = LyricData(
                        ms=line.get('ms'),
                        content=line.get('content', '')
                    )
                    GLib.idle_add(self.lrc_model_parent.get_model().append, row)

        threading.Thread(target=update_lyrics).start()

    def position_changed(self, position_seconds:float):
        if self.get_visible_child_name() == 'lrc':
            ms = int(position_seconds * 1000)
            best_match = 0
            for i in range(self.lrc_model_parent.get_n_items()):
                item = self.lrc_model_parent.get_item(i)
                if item.ms <= ms:
                    best_match = i
                else:
                    break
            if best_match != self.lrc_model_parent.get_selected():
                self.code_is_selecting = True
                self.lrc_model_parent.set_selected(best_match)
                self.code_is_selecting = False

    #@Gtk.Template.Callback()
    def row_activated(self, listbox, row):
        self.get_root().playing_page.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(row.ms/1000 * Gst.SECOND)
        )

    @Gtk.Template.Callback()
    def lrc_setup(self, factory, list_item):
        label = Gtk.Label(
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            justify=Gtk.Justification.CENTER,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER
        )
        list_item.set_child(label)

    @Gtk.Template.Callback()
    def lrc_bind(self, factory, list_item):
        item_data = list_item.get_item()
        label = list_item.get_child()
        label.set_label(item_data.content or "🎶")

    @Gtk.Template.Callback()
    def on_lrc_selection(self, selection_model, position, n_items):
        if not self.code_is_selecting:
            self.get_root().playing_page.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(selection_model.get_selected_item().ms/1000 * Gst.SECOND)
            )

        GLib.idle_add(self.lrc_list_el.scroll_to,
            min(max(selection_model.get_selected() + 5, 0), len(list(selection_model))-1),
            Gtk.ListScrollFlags.FOCUS,
            None
        )

    @Gtk.Template.Callback()
    def lyric_download_requested(self, button):
        integration = get_current_integration()
        self.song_changed(integration.loaded_models.get('currentSong').songId, True)
