# control_page.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio
from ...navidrome import get_current_integration
import threading, random, io, colorsys
from datetime import datetime
from PIL import Image
from colorthief import ColorThief

Gst.init(None)

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    show_sidebar_el = Gtk.Template.Child()
    volume_button_el = Gtk.Template.Child()
    volume_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    mode_button_el = Gtk.Template.Child()

    def __init__(self):
        # Used to disconnect star_el when song changes
        self.starred_connection = None
        self.last_song_id = None

        integration = get_current_integration()
        super().__init__()
        integration.connect_to_model('currentSong', 'songId', self.song_changed, use_gtk_thread=False)

        integration.loaded_models.get('currentSong').bind_property(
            "positionSeconds",
            self.progress_el.get_adjustment(),
            "value",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            None,
            None
        )

        self.is_seeking = False
        self.player = Gst.ElementFactory.make("playbin", "music-player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_player_message)
        self.volume_el.set_value(0.25) ##TODO save volume within sessions
        self.player.set_property("volume", 0.25)
        GLib.idle_add(self.setup_sidebar_button_connection)

    def setup_sidebar_button_connection(self):
        self.get_root().breakpoint_el.connect('apply', lambda *_: self.show_sidebar_el.set_visible(True))
        self.get_root().breakpoint_el.connect('unapply', lambda *_: self.show_sidebar_el.set_visible(False))
        condition = self.get_root().breakpoint_el.get_condition().to_string()
        is_small = self.get_root().get_width() < int(condition.split(': ')[1].strip('sp'))
        self.show_sidebar_el.set_visible(is_small)

    @Gtk.Template.Callback()
    def seek_start(self, gesture, n_press, x, y):
        self.is_seeking = True

    @Gtk.Template.Callback()
    def seek_end(self, gesture):
        self.is_seeking = False

    @Gtk.Template.Callback()
    def progress_bar_changed(self, adjustment):
        if self.is_seeking:
            nanoseconds = int(adjustment.get_value() * Gst.SECOND)
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.player.set_state(Gst.State.PLAYING)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.player.set_state(Gst.State.PAUSED)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.handle_song_change_request("next")

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.handle_song_change_request("previous")

    @Gtk.Template.Callback()
    def on_volume_changed(self, scale_el):
        value = round(scale_el.get_value(), 2)
        self.player.set_property("volume", value)
        if value == 0:
            self.volume_button_el.set_icon_name("speaker-0-symbolic")
        elif value < 0.33:
            self.volume_button_el.set_icon_name("speaker-1-symbolic")
        elif value < 0.66:
            self.volume_button_el.set_icon_name("speaker-2-symbolic")
        else:
            self.volume_button_el.set_icon_name("speaker-3-symbolic")

    @Gtk.Template.Callback()
    def mode_changed(self, button):
        integration = get_current_integration()
        self.mode_button_el.set_icon_name(button.get_icon_name())
        self.mode_button_el.set_tooltip_text(button.get_tooltip_text())
        self.mode_button_el.get_popover().popdown()
        integration.loaded_models['currentSong'].playbackMode = button.get_name()

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        view = self.get_ancestor(Adw.NavigationSplitView)
        if view:
            view.set_show_content(True)

    def handle_new_state(self, state):
        if not self.is_seeking:
            stack_page_name = 'play' if state in (Gst.State.NULL, Gst.State.READY, Gst.State.PAUSED) else 'pause'
            self.state_stack_el.set_visible_child_name(stack_page_name)

    def auto_play(self):
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId
        current_song = integration.loaded_models.get(current_song_id)
        if current_song:
            similar_songs = integration.getSimilarSongs(current_song.artists[0].get('id'))
            if len(similar_songs) > 1 and False:
                GLib.idle_add(self.get_root().queue_page.replace_queue, similar_songs)
            else:
                random_songs = integration.getRandomSongs()
                GLib.idle_add(self.get_root().queue_page.replace_queue, random_songs)

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        self.player.set_state(Gst.State.READY)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        mode = integration.loaded_models['currentSong'].playbackMode

        if action != "end" and mode == "repeat-one":
            mode = "consecutive"

        if action == "previous" and integration.loaded_models.get('currentSong').positionSeconds > 5:
            integration.loaded_models['currentSong'].songId = current_song_id
            return

        id_list = self.get_root().queue_page.song_list_el.get_all_ids()

        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models['currentSong'].songId = id_list[0]

            elif mode in ('consecutive', 'repeat-all'):
                try:
                    next_index = id_list.index(current_song_id) + (1 if action in ("next", "end") else -1)
                except ValueError: # index was not found
                    next_index = 0

                if mode == 'consecutive':
                    if next_index < 0:
                        integration.loaded_models['currentSong'].songId = id_list[0]
                    elif next_index < len(id_list):
                        integration.loaded_models['currentSong'].songId = id_list[next_index]
                    elif Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('auto-play').unpack():
                        threading.Thread(target=self.auto_play).start()
                elif mode == 'repeat-all':
                    if next_index < len(id_list) and next_index >= 0:
                        integration.loaded_models['currentSong'].songId = id_list[next_index]
                    else:
                        integration.loaded_models['currentSong'].songId = id_list[0]

            elif mode == 'repeat-one':
                integration.loaded_models['currentSong'].songId = current_song_id
        else:
            integration.loaded_models['currentSong'].songId = None

    def on_player_message(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.player:
                old_state, new_state, pending_state = message.parse_state_changed()
                self.handle_new_state(new_state)

        elif message.type == Gst.MessageType.EOS:
            self.handle_song_change_request("end")

        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: {}".format(err.message))

    def change_bottom_sheet_state(self, playing:bool):
        bottom_sheet = self.get_ancestor(Adw.BottomSheet)
        if bottom_sheet:
            bottom_sheet.set_can_open(playing)
            if not playing:
                bottom_sheet.set_open(False)
            bottom_sheet.set_reveal_bottom_bar(playing)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        model = integration.loaded_models.get(song_id)
        if model:
            # Title
            self.title_el.set_label(model.title)
            self.title_el.set_tooltip_text(model.title)

            # Artist
            if len(model.artists) > 0:
                self.artist_el.get_child().set_label(model.artists[0].get('name'))
                self.artist_el.set_action_target_value(GLib.Variant.new_string(model.artists[0].get('id')))
                self.artist_el.set_tooltip_text(model.artists[0].get('name'))
            self.artist_el.set_visible(model.artists)

            # Album
            self.album_el.get_child().set_label(model.album)
            self.album_el.set_action_target_value(GLib.Variant.new_string(model.albumId))
            self.album_el.set_tooltip_text(model.album)

            # Progressbar
            self.progress_el.get_adjustment().set_upper(model.duration)
            integration.loaded_models.get('currentSong').positionSeconds = 0

            # Cover
            threading.Thread(target=self.update_cover_art).start()

            self.start_current_song()
        GLib.idle_add(self.change_bottom_sheet_state, bool(song_id))

        if self.last_song_id and self.starred_connection:
            integration.loaded_models.get(self.last_song_id).disconnect(self.starred_connection)

        if model:
            self.star_el.set_action_target_value(GLib.Variant.new_string(song_id))
            self.starred_connection = integration.connect_to_model(song_id, 'starred', self.update_starred)
            self.last_song_id = song_id
        else:
            self.star_el.set_action_target_value(GLib.Variant.new_string(""))
            self.starred_connection = None
            self.last_song_id = None

    def update_palette(self, raw_bytes:bytes):
        img_io = io.BytesIO(raw_bytes)
        palette = ColorThief(img_io).get_palette(quality=10, color_count=2)
        css = f"""
        .dynamic-accent-bg, .dynamic-accent-bg > .sidebar-pane {{
            background-image: linear-gradient(
                to bottom right,
                rgba({','.join([str(c) for c in palette[0]])},0.25),
                rgba({','.join([str(c) for c in palette[1]])},0.25)
            );
            transition: background-image 0.5s ease-in-out;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        return
        accent = ColorThief(img_io).get_color(quality=10)
        r, g, b = [x / 255.0 for x in accent]
        h, l, s = colorsys.rgb_to_hls(r,g,b)

        rgb1 = [str(int(x * 255)) for x in colorsys.hls_to_rgb((h + 0.1) % 1.0, l, s)]
        rgb2 = [str(int(x * 255)) for x in colorsys.hls_to_rgb(h, l, s)]

        css = f"""
        .dynamic-accent-bg, .dynamic-accent-bg > .sidebar-pane {{
            background-image: linear-gradient(
                to bottom right,
                rgba({','.join(rgb1)},0.25),
                rgba({','.join(rgb2)},0.25)
            );
            transition: background-image 0.5s ease-in-out;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        song = integration.loaded_models.get(song_id)
        if song:
            raw_bytes, paintable = integration.getCoverArtWithBytes(song.coverArt, 480)

            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.cover_el.set_paintable, paintable)
                threading.Thread(target=self.update_palette, args=(raw_bytes,)).start()
            else:
                GLib.idle_add(self.cover_el.set_paintable, None)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def start_current_song(self):
        integration = get_current_integration()
        self.player.set_state(Gst.State.READY)
        songId = integration.loaded_models.get('currentSong').songId
        if songId:
            stream_url = integration.get_stream_url(songId)
            self.player.set_property('uri', stream_url)
            self.player.set_state(Gst.State.PLAYING)
            GLib.timeout_add(500, self.update_stream_progress)

    def update_stream_progress(self):
        if self.is_seeking:
            return True # don't update if seeking but keep the loop alive
        integration = get_current_integration()
        success, position = self.player.query_position(Gst.Format.TIME)
        if success:
            seconds = position / Gst.SECOND
            integration.loaded_models.get('currentSong').positionSeconds = seconds

        return True
        



